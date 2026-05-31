#
#<h1>RAZ Systems </h1>
#


# ============================================================
#  MCP AGENT WITH GRADIO UI
#  ─────────────────────────────────────────────────────────
#  This script connects to 4 MCP (Model Context Protocol)
#  servers and exposes them as tools to a LangGraph AI agent.
#
#  ARCHITECTURE OVERVIEW:
#
#   [Gradio UI]  ←→  [LangGraph Agent]  ←→  [MCP Servers]
#       │                   │                  ├─ Push
#   User types          GPT-4o-mini            ├─ SQL
#   question            decides which          ├─ File
#                       tool(s) to use         └─ WebFetch
#
#  THREADING MODEL (important for beginners!):
#
#   Main Thread:  Gradio UI runs here (blocking)
#   Background Thread:  asyncio event loop runs here
#       └─ All MCP connections and LangGraph calls happen
#          inside this loop via asyncio coroutines
#
#   Why? Gradio is synchronous but MCP uses async/await.
#   We bridge them using asyncio.run_coroutine_threadsafe()
#   which submits async work to the background loop and
#   blocks the main thread until it gets the result.
# ============================================================

import asyncio
import sys
import os
import threading
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END, MessagesState
import gradio as gr
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

load_dotenv(override=True)

# ============================================================
#  SECTION 1: MCP SERVER CONFIGURATIONS
#  ─────────────────────────────────────────────────────────
#  StdioServerParameters tells the MCP client HOW to launch
#  each server as a subprocess and communicate via stdio
#  (standard input/output pipes).
#
#  Each server needs:
#    command  = the executable to run
#    args     = command-line arguments passed to it
#    env      = environment variables the subprocess can see
#
#  IMPORTANT: If env={} or env is partial, the subprocess
#  loses access to PATH and other system variables.
#  Always pass credentials and PATH explicitly.
# ============================================================

PUSHOVER_USER_KEY  = os.getenv("PUSHOVER_USER")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_TOKEN")

# ── Push Notification Server (our own local script) ─────────
# Uses `python` directly to run our push_server.py script.
# We pass Pushover credentials as env vars so the script
# can read them with os.getenv() inside push_server.py.
push_params = StdioServerParameters(
    command=sys.executable,                              # path to current Python interpreter
    args=["d:/raz_training/6_mcp/4a_mcp_push_server.py"],
    env={
        "PUSHOVER_USER":  PUSHOVER_USER_KEY,
        "PUSHOVER_TOKEN": PUSHOVER_APP_TOKEN,
    }
)

# ── SQL / Accounts Server (3rd party via uvx) ───────────────
# uvx downloads and runs mcp-server-sqlite from PyPI.
# We point it at our local SQLite database file.
sql_params = StdioServerParameters(
    command="uvx",
    args=["mcp-server-sqlite", "--db-path", "D:/raz_training/6_mcp/bank.db"],
    env={}
)

# ── Filesystem Server (3rd party via npx) ───────────────────
# npx runs the official MCP filesystem server from npm.
# The last argument is the root directory it has access to.
file_params = StdioServerParameters(
    command="npx",
    args=[
        "-y",                                            # auto-confirm npm install
        "@modelcontextprotocol/server-filesystem",
        "D:/raz_training/6_mcp"                         # allowed root directory
    ],
    env={}
)

# ── Web Fetch Server (3rd party via uvx) ────────────────────
# Fetches and reads content from URLs.
# dict(os.environ) passes ALL current env vars to subprocess
# so it inherits PATH, proxies, etc.
webfetch_params = StdioServerParameters(
    command="uvx",
    args=["mcp-server-fetch"],
    env=dict(os.environ)                                 # inherit full environment
)

# ============================================================
#  SECTION 2: PRE-BUILT DROPDOWN QUESTIONS
#  ─────────────────────────────────────────────────────────
#  These populate the UI dropdowns so students/users can
#  quickly pick a ready-made prompt for each tool category
#  instead of typing from scratch.
# ============================================================

TOOL_QUESTIONS = {
    "🔔 Push Notification": [
        "Select a question...",
        "Send a push: Server is up and running",
        "Send a push: Daily report is ready",
        "Send a push: Alert! High CPU usage detected",
        "Send a push: Task completed successfully",
        "Custom message...",
    ],
    "🗄️ SQL / Accounts": [
        "Select a question...",
        "List all accounts in the database",
        "Show total count of records in accounts table",
        "Find accounts created in the last 7 days",
        "Show the top 5 accounts by balance",
        "Custom query...",
    ],
    "📁 File Manager": [
        "Select a question...",
        "List all files in the current directory",
        "Read the contents of output.txt",
        "Write 'Hello World' to test.txt",
        "Check if report.csv exists",
        "Custom file operation...",
    ],
    "🌐 Web Fetch": [
        "Select a question...",
        "Fetch and summarize https://example.com",
        "Get the latest news from https://news.ycombinator.com",
        "Fetch https://httpbin.org/get and show the response",
        "Retrieve and summarize content from a URL I provide",
        "Custom URL to fetch...",
    ],
    "💬 Custom / Free Text": [
        "Select a question...",
        "Use all available tools to give me a status report",
        "Fetch a URL, save content to a file, then push a notification",
        "Query the accounts DB and send results as a push notification",
        "Custom input...",
    ],
}

# ── System prompt: tells the LLM what tools it has ──────────
# This is injected at the start of every LLM call so the
# model always knows its role and available capabilities.
SYSTEM_PROMPT = """You are a helpful AI assistant with access to:
- push: Send push notifications to the user's device
- sql/accounts: Query and manage database accounts
- file: Read, write, and manage files on the filesystem
- webfetch: Fetch and read content from URLs
Always use the appropriate tool(s). Confirm when actions complete."""

# ============================================================
#  SECTION 3: GLOBAL AGENT STATE
#  ─────────────────────────────────────────────────────────
#  A simple dictionary that acts as shared memory between
#  the Gradio UI callbacks and the background async thread.
#
#  graph      → the compiled LangGraph agent (set after connect)
#  exit_stack → keeps all MCP sessions alive (AsyncExitStack)
#  loop       → the background asyncio event loop
#               We save loop into agent_state so run_agent() can submit work to the same background loop that was created in connect_servers(). Without saving it, run_agent() would have no way to reach that worker.
#  status     → "disconnected" | "connecting" | "ready" | "error"
#               So status = "ready" just means "the connection attempt finished and at least something loaded" — it doesn't guarantee all 4 servers are up.
#  tool_names → list of tool names loaded (shown in UI)
# ===========

#   AsyncExitStack._exit_callbacks = [
    # ┌─────────────────────────────────────────────────┐
    # │ [0] stdio_client(push_params).__aexit__         │
    # │      └─ holds: subprocess pipe (read, write)    │
    # │              stdin/stdout to push_server.py     │
    # ├─────────────────────────────────────────────────┤
    # │ [1] ClientSession(read, write).__aexit__        │
    # │      └─ holds: MCP session state for push       │
    # │              request IDs, message buffer        │
    # ├─────────────────────────────────────────────────┤
    # │ [2] stdio_client(sql_params).__aexit__          │
    # │      └─ holds: subprocess pipe to sql server    │
    # ├─────────────────────────────────────────────────┤
    # │ [3] ClientSession.__aexit__ for sql             │
    # │      └─ holds: MCP session state for sql        │
    # ├─────────────────────────────────────────────────┤
    # │ [4] stdio_client(file_params).__aexit__         │
    # ├─────────────────────────────────────────────────┤
    # │ [5] ClientSession.__aexit__ for file            │
    # ├─────────────────────────────────────────────────┤
    # │ [6] stdio_client(webfetch_params).__aexit__     │
    # ├─────────────────────────────────────────────────┤
    # │ [7] ClientSession.__aexit__ for webfetch        │
    # └─────────────────────────────────────────────────┘
#     When exit_stack closes it calls them in reverse order (LIFO — last in, first out):
#     Close [7] ClientSession webfetch   ← close session before pipe
# Close [6] stdio_client webfetch    ← then close the pipe
# Close [5] ClientSession file
# Close [4] stdio_client file
# ...and so on
# ### loop
# asyncio.EventLoop
# │
# ├── _ready  (queue of callbacks ready to run NOW)
# │     └─ e.g. "run this coroutine step next tick"
# │
# ├── _scheduled  (heap of future callbacks with timestamps)
# │     └─ e.g. "run this after 30s timeout"
# │
# ├── _selector  (OS-level I/O watcher)
# │     └─ watches file descriptors (the stdio pipes!)
# │     └─ when push_server.py writes to stdout → loop wakes up
# │
# ├── _thread_id  (ID of the thread that owns this loop)
# │     └─ = background thread's ID
# │     └─ used to detect "wrong thread" calls
# │
# └── _running  (bool — True while loop.run_forever() is active)

agent_state = {
    "graph":      None,
    "exit_stack": None,
    "loop":       None,
    "status":     "disconnected",
    "tool_names": [],
}

# ============================================================
#  SECTION 4: LANGGRAPH STATEGRAPH (the AI Agent)
#  ─────────────────────────────────────────────────────────
#  LangGraph models the agent as a GRAPH of nodes + edges.
#
#  GRAPH STRUCTURE:
#
#   [START]
#      │
#      ▼
#   [llm node] ──── has tool_calls? ──YES──► [tools node]
#      ▲                                          │
#      │◄─────────────────────────────────────────┘
#      │
#      └──── no tool_calls? ──► [END]
#
#  The agent LOOPS between llm→tools until the LLM decides
#  it has enough information and stops calling tools.
# ============================================================

def build_graph(llm_with_tools, tools_by_name):
    """
    PURPOSE: Compile the LangGraph ReAct-style agent graph.

    PARAMETERS:
      llm_with_tools  → ChatOpenAI model with tools bound to it
                        (so the LLM knows what tools are available)
      tools_by_name   → dict of {tool_name: tool_object}
                        (so we can look up and call tools by name)

    RETURNS: a compiled LangGraph graph ready to invoke
    """

    # ── Node 1: LLM ─────────────────────────────────────────
    # This node calls GPT-4o-mini with the full message history.
    # The LLM either:
    #   (a) Returns a plain text answer → graph ends
    #   (b) Returns tool_calls → graph routes to tools node
    async def call_llm(state: MessagesState):
        # Prepend system prompt so LLM always knows its role
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}                  # adds AIMessage to state

    # ── Node 2: Tools ────────────────────────────────────────
    # This node executes whatever tool(s) the LLM requested.
    # Each tool result is wrapped in a ToolMessage and added
    # to state so the LLM can see the result on the next loop.
    async def call_tools(state: MessagesState):
        last = state["messages"][-1]                     # the AIMessage with tool_calls
        results = []
        for tc in last.tool_calls:
            # tc = {"name": "push", "args": {...}, "id": "call_abc123"}
            try:
                result = await tools_by_name[tc["name"]].ainvoke(tc["args"])
            except Exception as e:
                result = f"Tool error: {e}"
            results.append(
                ToolMessage(content=str(result), tool_call_id=tc["id"])
            )
        return {"messages": results}                     # adds ToolMessages to state

    # ── Conditional Edge: should we loop or stop? ────────────
    # After the LLM responds, this function decides next step:
    #   → "tools"  if LLM made tool calls (keep looping)
    #   → END      if LLM gave a plain response (we're done)
    def should_continue(state: MessagesState):
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "tools"                               # route to tools node
        return END                                       # stop the graph

    # ── Assemble the graph ───────────────────────────────────
    g = StateGraph(MessagesState)
    g.add_node("llm",   call_llm)
    g.add_node("tools", call_tools)
    g.set_entry_point("llm")                             # always start at llm node
    g.add_conditional_edges("llm", should_continue, {"tools": "tools", END: END})
    g.add_edge("tools", "llm")                           # after tools, always go back to llm
    return g.compile()


# ============================================================
#  SECTION 5: ASYNC AGENT INITIALISATION
#  ─────────────────────────────────────────────────────────
#  This coroutine (async function) starts all 4 MCP servers
#  and builds the LangGraph agent.
#
#  WHY AsyncExitStack?
#  Each MCP server connection is an async context manager.
#  AsyncExitStack lets us open many of them and keep them
#  ALL alive for the lifetime of the app. When we eventually
#  close the stack, all connections are cleaned up together.
#
#  FLOW:
#    1. Open stdio pipe to MCP server subprocess
#    2. Create MCP ClientSession over that pipe
#    3. Call session.initialize() to do MCP handshake
#    4. load_mcp_tools() converts MCP tools → LangChain tools
#    5. Bind all tools to the LLM
#    6. Build and compile the LangGraph
# ============================================================

async def _init_agent():
    """
    PURPOSE: Connect to all MCP servers and build the agent.
    This is an async function — it must be run inside an
    asyncio event loop (we use run_coroutine_threadsafe).

    RETURNS: (graph, exit_stack, tool_names)
    """
    # AsyncExitStack keeps all async context managers alive
    exit_stack = AsyncExitStack()
    await exit_stack.__aenter__()

    all_tools  = []
    tool_names = []

    for name, params in [
        ("push",     push_params),
        ("sql",      sql_params),
        ("file",     file_params),
        ("webfetch", webfetch_params),
    ]:
        try:
            # Step 1: Launch subprocess and get stdio pipes
            #   read  = data coming FROM the MCP server
            #   write = data going TO the MCP server
            read, write = await exit_stack.enter_async_context(
                stdio_client(params)
            )

            # Step 2: Create an MCP session over those pipes
            session = await exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            # Step 3: MCP handshake — exchange capabilities
            await session.initialize()

            # Step 4: Convert MCP tool schemas → LangChain tools
            tools = await load_mcp_tools(session)
            all_tools.extend(tools)
            tool_names.extend([t.name for t in tools])
            print(f"✅ [{name}] {len(tools)} tool(s): {[t.name for t in tools]}")

        except Exception as e:
            # One failing server won't crash the whole agent
            print(f"❌ [{name}] failed: {e}")

    # Step 5: Create LLM and bind all tools to it
    # bind_tools() adds the tool schemas to every LLM request
    # so GPT knows what tools are available and how to call them
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    tools_by_name = {t.name: t for t in all_tools}

    # Step 6: Build the LangGraph agent
    graph = build_graph(llm.bind_tools(all_tools), tools_by_name)

    return graph, exit_stack, tool_names


# ============================================================
#  SECTION 6: BACKGROUND THREAD + EVENT LOOP
#  ─────────────────────────────────────────────────────────
#  WHY DO WE NEED THIS?
#
#  Gradio runs in the MAIN thread (synchronous).
#  MCP uses asyncio (asynchronous).
#  These two worlds can't directly talk to each other.
#
#  SOLUTION:
#    1. Create a new asyncio event loop
#    2. Run it forever in a BACKGROUND DAEMON THREAD
#    3. When Gradio needs async work done, use:
#          asyncio.run_coroutine_threadsafe(coro, loop)
#       This submits the coroutine to the background loop
#       and returns a Future. Calling .result() on the Future
#       BLOCKS the main thread until the async work is done.
#
#  VISUAL:
#
#   Main Thread (Gradio)          Background Thread (asyncio)
#   ─────────────────────         ───────────────────────────
#   connect_servers()             loop.run_forever()
#     │                               │
#     ├─ run_coroutine_threadsafe ──► │ _init_agent() runs here
#     │                               │
#     ├─ .result() ◄──────────────── │ returns (graph, stack, names)
#     │
#   run_agent()
#     │
#     ├─ run_coroutine_threadsafe ──► │ graph.ainvoke() runs here
#     │                               │
#     ├─ .result() ◄──────────────── │ returns result
# ============================================================

def _run_loop(loop):
    """
    PURPOSE: Target function for the background thread.
    Sets the event loop and runs it forever so it can
    accept coroutines submitted from the main thread.
    """
    asyncio.set_event_loop(loop)
    loop.run_forever()                                   # keeps the loop alive permanently


def connect_servers():
    """
    PURPOSE: Called when user clicks 'Connect MCP Servers'.
    Starts the background thread and initialises all MCP
    connections + the LangGraph agent.

    RETURNS: (status_message, tool_badges_markdown)
             These are displayed directly in the Gradio UI.
    """
    # Don't reconnect if already connected
    if agent_state["status"] == "ready":
        return "✅ Already connected!", _badges()

    agent_state["status"] = "connecting"

    # Create a brand-new asyncio event loop (not the default one)
    loop = asyncio.new_event_loop()

    # Start the background thread that will run this loop
    # daemon=True means the thread auto-dies when main exits
    threading.Thread(target=_run_loop, args=(loop,), daemon=True).start()
    agent_state["loop"] = loop                           # save so run_agent can use it

    try:
        # Submit _init_agent() to the background loop and wait for result
        # timeout=30 raises an exception if servers take too long to start
        graph, stack, names = asyncio.run_coroutine_threadsafe(
            _init_agent(), loop
        ).result(timeout=30)

        # Save everything to global state so run_agent() can access it
        agent_state.update(
            graph=graph,
            exit_stack=stack,
            tool_names=names,
            status="ready"
        )
        return f"✅ Connected! {len(names)} tools ready.", _badges()

    except Exception as e:
        agent_state["status"] = "error"
        return f"❌ Failed: {e}", ""


def _badges():
    """
    PURPOSE: Format loaded tool names as markdown code badges
    for display in the UI status area.
    Example output: "`push` `list-tables` `read-file` `fetch`"
    """
    return " ".join(f"`{t}`" for t in agent_state["tool_names"])


# ============================================================
#  SECTION 7: AGENT INVOCATION (called on every user message)
#  ─────────────────────────────────────────────────────────
#  This is a GENERATOR function (uses yield instead of return).
#  Gradio supports generators for streaming — each yield
#  updates the UI immediately rather than waiting for the
#  full response.
#
#  GRADIO 6.14 HISTORY FORMAT:
#  The chatbot history is a list of dicts:
#    [
#      {"role": "user",      "content": "Hello"},
#      {"role": "assistant", "content": "Hi there!"},
#      ...
#    ]
# ============================================================

def run_agent(user_message, history):
    """
    PURPOSE: Handle a user message — invoke the LangGraph agent
    and stream the response back to the Gradio chatbot.

    PARAMETERS:
      user_message → string typed by the user
      history      → list of {"role","content"} dicts (chat history)

    YIELDS: (updated_history, cleared_input)
            Gradio updates the UI on each yield.
    """
    if history is None:
        history = []

    # Ignore empty input
    if not user_message.strip():
        yield history, ""
        return

    # Guard: agent must be connected first
    if agent_state["status"] != "ready":
        yield history + [
            {"role": "user",      "content": user_message},
            {"role": "assistant", "content": "⚠️ Not connected — click **Connect MCP Servers** first."},
        ], ""
        return

    # Show the user message in chat immediately (before agent responds)
    history = history + [{"role": "user", "content": user_message}]
    yield history, ""                                    # first yield: show user msg, clear input

    try:
        # Submit the agent invocation to the background asyncio loop
        # graph.ainvoke() runs the full LangGraph: llm → tools → llm → ... → END
        future = asyncio.run_coroutine_threadsafe(
            agent_state["graph"].ainvoke(
                {"messages": [HumanMessage(content=user_message)]}
            ),
            agent_state["loop"],
        )
        result = future.result(timeout=60)               # wait up to 60s for agent

        # The last message in state is the final AIMessage response
        response = result["messages"][-1].content

        # Second yield: append assistant response to chat history
        yield history + [{"role": "assistant", "content": response}], ""

    except Exception as e:
        yield history + [{"role": "assistant", "content": f"❌ Error: {e}"}], ""


# ============================================================
#  SECTION 8: DROPDOWN HELPER FUNCTIONS
#  ─────────────────────────────────────────────────────────
#  These handle the interactive dropdowns in the left panel.
# ============================================================

def on_category_change(cat):
    """
    PURPOSE: When the user changes the Tool Category dropdown,
    update the Pre-built Question dropdown to show questions
    relevant to that tool category.
    """
    qs = TOOL_QUESTIONS.get(cat, ["Select a question..."])
    return gr.update(choices=qs, value=qs[0])


def on_question_select(cat, q):
    """
    PURPOSE: When the user picks a pre-built question,
    auto-fill the chat input box with that question text.
    Returns empty string for placeholder options so the
    user knows to type their own text.
    """
    if not q or q == "Select a question..." or q.endswith("..."):
        return ""                                        # placeholder → don't fill input
    return q                                             # real question → fill input box


# ============================================================
#  SECTION 9: GRADIO UI
#  ─────────────────────────────────────────────────────────
#  GRADIO 6.14 RULES (learned the hard way!):
#    ✅ css goes in launch(css=...), NOT in Blocks(css=...)
#    ✅ gr.Chatbot has NO type= parameter
#    ✅ history must be list of {"role","content"} dicts
#
#  LAYOUT:
#    ┌──────────────────────────────────────────────┐
#    │              Header Banner                    │
#    ├───────────────┬──────────────────────────────┤
#    │  Left Panel   │      Right Panel              │
#    │  ① Connect    │   [Chat history window]       │
#    │  ② Dropdowns  │                               │
#    │  Graph info   │   [Input] [Send] [Clear]      │
#    └───────────────┴──────────────────────────────┘
# ============================================================

css = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@300;400;500&display=swap');
:root {
    --bg:#0d0f14; --surface:#13161e; --surface2:#1a1e2a;
    --border:#252836; --accent:#00e5a0; --accent2:#0077ff;
    --warn:#ff6b35; --text:#e8eaf0; --muted:#6b7280;
    --font-head:'Syne',sans-serif; --font-mono:'DM Mono',monospace;
}
* { box-sizing:border-box; }
body, .gradio-container { background:var(--bg)!important; font-family:var(--font-mono)!important; color:var(--text)!important; }
.header-block { background:linear-gradient(135deg,#0d0f14,#13161e,#0d1520); border:1px solid var(--border); border-radius:16px; padding:28px 36px; position:relative; overflow:hidden; margin-bottom:8px; }
.header-block::before { content:''; position:absolute; top:0;left:0;right:0;height:2px; background:linear-gradient(90deg,transparent,var(--accent),var(--accent2),transparent); }
.header-title { font-family:var(--font-head)!important; font-size:2rem!important; font-weight:800!important; background:linear-gradient(135deg,var(--accent),var(--accent2)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0!important; }
.header-sub { color:var(--muted)!important; font-size:.78rem!important; margin-top:6px!important; letter-spacing:.08em; text-transform:uppercase; }
.connect-btn { background:linear-gradient(135deg,var(--accent),#00c87a)!important; color:#0d0f14!important; font-family:var(--font-head)!important; font-weight:700!important; border:none!important; border-radius:8px!important; width:100%!important; transition:all .2s!important; }
.connect-btn:hover { transform:translateY(-1px)!important; box-shadow:0 4px 20px rgba(0,229,160,.3)!important; }
.send-btn { background:linear-gradient(135deg,var(--accent2),#0055cc)!important; color:#fff!important; font-family:var(--font-head)!important; font-weight:700!important; border:none!important; border-radius:8px!important; transition:all .2s!important; }
.send-btn:hover { transform:translateY(-1px)!important; box-shadow:0 4px 20px rgba(0,119,255,.3)!important; }
.clear-btn { background:transparent!important; color:var(--muted)!important; border:1px solid var(--border)!important; border-radius:8px!important; }
.clear-btn:hover { border-color:var(--warn)!important; color:var(--warn)!important; }
.status-box textarea,.status-box input { background:var(--surface2)!important; border:1px solid var(--border)!important; border-radius:8px!important; color:var(--accent)!important; font-family:var(--font-mono)!important; font-size:.8rem!important; }
select { background:var(--surface2)!important; border:1px solid var(--border)!important; color:var(--text)!important; border-radius:8px!important; }
label span { font-family:var(--font-mono)!important; font-size:.75rem!important; color:var(--muted)!important; text-transform:uppercase!important; letter-spacing:.08em!important; }
.gr-textbox textarea { background:var(--surface2)!important; border:1px solid var(--border)!important; border-radius:10px!important; color:var(--text)!important; font-family:var(--font-mono)!important; font-size:.88rem!important; }
.section-label { font-size:.7rem; letter-spacing:.15em; text-transform:uppercase; color:var(--muted); margin-bottom:12px; }
"""

# ── Build the Gradio UI layout ───────────────────────────────
# gr.Blocks() lets us build a fully custom layout
# (unlike gr.Interface which is a simple single-function UI)
with gr.Blocks(title="MCP Agent") as demo:

    # Header banner (plain HTML for full styling control)
    gr.HTML("""<div class="header-block">
        <div class="header-title">⬡ MCP Agent Console</div>
        <div class="header-sub">LangGraph StateGraph · GPT-4o-mini · Push · SQL · File · Web Fetch</div>
    </div>""")

    # Two-column layout: controls on left, chat on right
    with gr.Row():

        # ── LEFT COLUMN: connection + dropdowns ─────────────
        with gr.Column(scale=1, min_width=300):

            gr.HTML('<div class="section-label">① Connect MCP Servers</div>')

            # Clicking this calls connect_servers() and writes
            # results into status_box and tools_md
            connect_btn = gr.Button("⚡ Connect MCP Servers", elem_classes="connect-btn")
            status_box  = gr.Textbox(
                label="Status", value="Not connected",
                interactive=False,                       # read-only, updated by connect_btn
                elem_classes="status-box", lines=1
            )
            tools_md = gr.Markdown("")                   # shows loaded tool badges

            gr.HTML('<hr style="border-color:#252836;margin:16px 0"/>')
            gr.HTML('<div class="section-label">② Quick Questions</div>')

            # Dropdown 1: pick a tool category
            first = list(TOOL_QUESTIONS.keys())[0]
            tool_category = gr.Dropdown(
                label="Tool Category",
                choices=list(TOOL_QUESTIONS.keys()),
                value=first
            )

            # Dropdown 2: pick a pre-built question for that category
            # on_category_change() updates this when Dropdown 1 changes
            question_dropdown = gr.Dropdown(
                label="Pre-built Question",
                choices=TOOL_QUESTIONS[first],
                value=TOOL_QUESTIONS[first][0]
            )

            # Clicking this copies selected question into the chat input
            use_q_btn = gr.Button("↓ Use This Question", elem_classes="clear-btn")

            # Visual reminder of the graph flow for students
            gr.HTML('<hr style="border-color:#252836;margin:16px 0"/>')
            gr.HTML("""<div style="font-size:.72rem;color:#4b5563;line-height:1.8">
                <b style="color:#6b7280">Graph Flow</b><br>
                HumanMessage → LLM node<br>
                ↓ tool_calls? → Tools node<br>
                ↓ loop → LLM node<br>
                ↓ done → END</div>""")

        # ── RIGHT COLUMN: chat interface ─────────────────────
        with gr.Column(scale=3):

            # Chat history window
            # Gradio 6.14: NO type= parameter, uses dict format natively
            chatbot = gr.Chatbot(
                height=480,
                show_label=False,
                elem_classes="chatbot"
            )

            # Input row: text box + send/clear buttons
            with gr.Row():
                user_input = gr.Textbox(
                    placeholder="Ask the agent anything, or pick a question from the left...",
                    label="", lines=2, scale=5, elem_classes="gr-textbox"
                )
                with gr.Column(scale=1, min_width=120):
                    send_btn  = gr.Button("Send →", elem_classes="send-btn")
                    clear_btn = gr.Button("Clear",  elem_classes="clear-btn")

    # ── EVENT WIRING ────────────────────────────────────────
    # Connect UI events to Python functions.
    # inputs=  → which components to read values from
    # outputs= → which components to update with return values

    # Connect button → run connect_servers() → update status + badges
    connect_btn.click(fn=connect_servers, outputs=[status_box, tools_md])

    # Category dropdown change → update question dropdown choices
    tool_category.change(
        fn=on_category_change,
        inputs=[tool_category],
        outputs=[question_dropdown]
    )

    # Question selected → auto-fill the chat input box
    question_dropdown.change(
        fn=on_question_select,
        inputs=[tool_category, question_dropdown],
        outputs=[user_input]
    )

    # "Use This Question" button → same as selecting from dropdown
    use_q_btn.click(
        fn=on_question_select,
        inputs=[tool_category, question_dropdown],
        outputs=[user_input]
    )

    # Send button → invoke agent → update chat + clear input
    send_btn.click(
        fn=run_agent,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input]
    )

    # Also allow pressing Enter in the text box to send
    user_input.submit(
        fn=run_agent,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input]
    )

    # Clear button → empty the chat history and input box
    clear_btn.click(fn=lambda: ([], ""), outputs=[chatbot, user_input])


# ============================================================
#  SECTION 10: LAUNCH
#  ─────────────────────────────────────────────────────────
#  server_name="0.0.0.0" → listen on all network interfaces
#                           open http://localhost:PORT in browser
#  share=False            → don't create a public gradio.live link
#  css=css                → Gradio 6.14: css must go here, not Blocks()
# ============================================================

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", share=False, css=css)