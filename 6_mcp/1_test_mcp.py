# 
# <h1>RAZ Systems </h1>
# 
# mcp-server-fetch is an official Anthropic reference MCP server (from the
# modelcontextprotocol/servers repo), released as one of the original example
# servers alongside MCP's launch in Nov 2024.
# Its job: given a URL, it fetches the page over HTTP and converts the raw HTML
# into clean, LLM-friendly Markdown -- stripping out scripts, nav bars, ads,
# and other clutter so the model reads useful text instead of markup noise.
# It exposes this as a single MCP tool (commonly "fetch") that any MCP client
# (including a LangGraph/LangChain agent) can call just like any other tool,
# passing in a URL and getting back the page content as a string.
# It's meant as a teaching/reference implementation to demonstrate MCP, not a
# hardened production web scraper -- fine for coursework and demos, but treat
# it accordingly if you ever point it at untrusted or sensitive workloads.
#
# `mcp-server-fetch` runs locally, as a separate subprocess on the same machine as this client — not on any remote/Anthropic server.
# The client talks to it over stdio (its stdin/stdout), sending and receiving MCP protocol messages as JSON-RPC.
# "uvx mcp-server-fetch" downloads the package from PyPI into a temporary uv-managed environment (if not already cached) and runs it immediately — no separate pip install step needed.
# The subprocess is spawned when the MCP client session starts and terminated when it ends; it isn't a persistent background service.
# Note: the very first run on a machine needs internet access to fetch the package from PyPI; later runs use uv's local cache and start almost instantly.
#
# the program can wait for slow operations (network calls,
# subprocesses, APIs) WITHOUT freezing the entire application.
import asyncio
# Import the MCP client class.
#
# MCPServerStdio allows Python to communicate with an MCP server
# through standard input/output pipes (stdin/stdout).
#
# Think of it like:
#
# Python App  <---- text messages ---->  MCP Server
#
from agents.mcp.server import MCPServerStdio
# =====================================================
# MCP SERVER CONFIGURATION
# =====================================================

# This dictionary tells Python HOW to start the MCP server.
#
# Equivalent terminal command:
#
# uvx mcp-server-fetch
#
# Explanation:
#
# command = executable/program to run
# args    = arguments passed to that program
#
async def main():
    fetch_params = {
        "command": "uvx",
        "args": ["mcp-server-fetch"]
    }
    # It automatically:
    #
    # 1. Starts the MCP server process
    # 2. Opens communication pipes
    # 3. Establishes MCP session
    # 4. Cleans everything up automatically when done
    # If Server takes more than 60 seconds it throws timeout error
    async with MCPServerStdio(
        params=fetch_params,
        client_session_timeout_seconds=60
    ) as server:
        tools = await server.session.list_tools()    #exposes tools it has, fetch 
        print(tools)
        response1 = await server.session.call_tool(
            "fetch",
            {
                "url": "https://razsystems.com"
            }
        )
        print(f" Tool Response :\n {response1}")
asyncio.run(main())

"""
MCP TOOL CALL FLOW (6 STEPS)

1. Tool Discovery:
   The MCP server sends available tools with names, descriptions, and input schemas.

2. LLM Reads Tools:
   The LLM reviews tool metadata and understands what each tool can do.

3. User Request:
   User asks a question or gives an instruction. “What services are offered by RAZ?”

4. Tool Selection:
   The LLM decides which tool to use and generates a structured tool call
   (tool name + required parameters).
   {
        "tool_name": "fetch",
        "arguments": {
            "url": "https://example.com"
        }
   }

5. Tool Execution (Agent Runtime):
   The agent framework receives the tool call and executes it by sending
   the request to the MCP server or external system.
   Agent → MCP Server: call fetch(url=...)
6. Response + Final Answer:
   Tool result is returned to the LLM, which uses it to generate the final response. HTML / text / structured data
"""



from agents.mcp.server import MCPServerStdio
import asyncio

async def main():

    serper_params = {
        "command": "uvx",
        "args": ["serper-mcp-server"],
        "client_session_timeout_seconds": 60,
        "env": {
            "SERPER_API_KEY": "<<SERPER_API_KEY>>"
        }
    }

    async with MCPServerStdio(params=serper_params) as server:

        tools = await server.session.list_tools()
        print(tools)

asyncio.run(main())