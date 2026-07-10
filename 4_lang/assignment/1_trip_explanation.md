# Explanation — LangGraph Travel Agent Assignment

**Raz Systems · Agentic AI Engineering Curriculum**

This explains the reasoning behind every answer in `solution.py`, and connects it back to the original three class files: `V1_AutoAgentLangGraph.py`, `v3_toolnode.py`, and `travelApp.py`. Read this alongside `assignment.py` and `solution.py` open side by side.

---

## Part A — Diagnostic questions (V1)

### A1. What actually sets `flight_cost` and `hotel_cost` in V1?

In `V1_AutoAgentLangGraph.py`, `reason_and_act()` does call `search_web()` twice and builds `flight_results` / `hotel_results` — but those variables are only ever used later, inside the LLM prompt that writes the *itinerary text*. The actual numbers that drive the budget decision come from two lines further down:

```python
flight_cost = random.randint(500, 1500)
hotel_cost = random.randint(300, 1200)
```

Directly above those two lines, commented out, sit the lines that should be doing the real work:

```python
#flight_cost = extract_price(flight_results, "flight")
#hotel_cost = extract_price(hotel_results, "hotel")
```

`extract_price()` is a fully working function elsewhere in the same file — it sends the search text to the LLM with a strict "return only a number" prompt and regexes out the result. So V1 isn't missing the capability to do real pricing; it's just not wired up. This is the single most important thing to notice about V1: the search results are fetched, displayed, and then completely ignored by the decision logic.

### A2. Does `return {}` mean "nothing happened"?

No — and this is a common point of confusion. LangGraph nodes communicate by returning a **partial update** to the shared state, which LangGraph merges into the existing state dict (shallow merge, key by key). Returning `{}` means "I have no updates for you" — every existing key in state stays exactly as it was. It is not the same as clearing state, and it is not the same as returning `None` (which can actually cause errors in some LangGraph configurations, since the framework expects a dict-like update).

`perceive()` and `notify()` in V1 (and `notify()` in `v3_toolnode.py` / `solution.py`) both `return {}` because their entire job is side effects — printing to console, sending a push notification — with nothing that needs to persist into `TravelState` / `State` for later nodes to read.

### A3. The three `decide()` return values, and what wires them up

In `v3_toolnode.py` and `solution.py`, `decide()` returns one of:

- `"notify"` — budget met
- `END` — over budget, but `MAX_ATTEMPTS` reached
- `"search"` — over budget, try again

`decide()` itself is just a plain Python function — it has no idea these strings mean anything. The line that gives them meaning is:

```python
graph.add_conditional_edges("observe", decide)
```

This tells LangGraph: "after the `observe` node runs, call `decide(state)`, and whatever string comes back, treat it as the name of the next node to run" (or, for `END`, stop the graph). Without this line, `decide()` would just be a function that returns strings into the void — the routing behavior is entirely a property of `add_conditional_edges`, not of `decide()`.

---

## Part B — Build: adding `search_activities` through `ToolNode`

### B1. The tool itself, and the one real place to register it

```python
@tool
def search_activities(destination: str, preferences: str = "") -> str:
    """Search for popular tourist activities and their typical costs in a destination."""
    query = f"top tourist activities and prices in {destination} {preferences}"
    ...
```

This follows the exact shape of `search_flights` / `search_hotels` — a `@tool`-decorated function with a docstring (the docstring matters: it's what the LLM reads to decide *when* to call this tool), making the same Serper request, parsing results the same way.

The part students most often get wrong isn't writing the tool — it's registering it. In `solution.py`, there is exactly **one line** that needs to change:

```python
tools = [search_flights, search_hotels, search_activities]
```

Everything downstream — `llm_with_tools = ChatOpenAI(...).bind_tools(tools)` and `graph.add_node("tools", ToolNode(tools))` — already reads from this same `tools` variable. If you'd instead written `ToolNode([search_flights, search_hotels, search_activities])` as a fresh list literal in the graph-building section, you'd have created two separate lists that could silently drift out of sync. Reusing the single `tools` list is the correct, drift-proof pattern — and it's exactly why this is "one real place" rather than three independent edits.

### B2. Updating the `search()` prompt

The original V3 prompt hardcodes "Call BOTH tools now" — language that's actively wrong once a third tool exists, since an LLM told to call "both" may interpret that as a hard instruction to call exactly two. The fix in `solution.py` generalizes the count and adds a third instruction block:

```python
f"Call ALL THREE tools now — one for flights, one for hotels, one for activities:\n"
...
f"  Activities: destination={state['destination']}{', preferences=' + cheaper if cheaper else ''}\n"
f"Call all three tools now. No text."
```

The instructive detail: the `cheaper` hint (used on retries to bias toward budget options) is reused for the activities call too, not just flights/hotels — consistent retry behavior across all three tools matters, otherwise a retry might cheapen flights and hotels but keep recommending expensive activities, defeating the purpose of the retry.

### B3. Updating `observe()`'s extraction format

```python
f"TOTAL_COST: <single number in USD, flight + hotel + activities combined>\n"
f"ACTIVITIES_COST: <single number in USD, activities only>\n"
```

The critical design choice: `TOTAL_COST` is defined as *already including* activities, rather than introducing a separate `ACTIVITIES_COST` that something downstream has to remember to add in. This means `decide()` — which only ever looks at `state["total_cost"]` vs `state["budget"]` — needs **zero changes**. `ACTIVITIES_COST` is extracted purely for logging/visibility (`solution.py` prints it in the observe log line), not because any decision logic depends on it.

This is a deliberate design lesson: when extending a system, prefer changes that make existing downstream code automatically correct, over changes that require you to remember to update decision logic in a second place.

### B4. Does this need a new graph node? (The core conceptual test of Part B)

**No.** This is the question the whole exercise is built around. `ToolNode(tools)` is registered once, as a single node named `"tools"`:

```python
graph.add_node("tools", ToolNode(tools))
```

`ToolNode` is not "one node per tool" — it's one node that, at runtime, reads the tool name out of whatever tool call the LLM's last response requested (e.g. `"search_activities"`), looks that name up inside the `tools` list it was constructed with, and calls the matching function. Adding a third entry to `tools` gives this *same* node a third thing it's capable of executing — the graph's shape (5 nodes: `search`, `tools`, `observe`, `notify`, plus implicit start/end) is completely unchanged.

This was verified directly by introspecting the compiled graph:

```python
>>> list(app.get_graph().nodes.keys())
['__start__', 'search', 'tools', 'observe', 'notify', '__end__']
>>> [t.name for t in tools]
['search_flights', 'search_hotels', 'search_activities']
```

Five nodes, three tools — the tool count and the node count are independent numbers. That's the entire point of `ToolNode`: it decouples "how many things the agent can call" from "how many steps are in the graph."

---

## Part C — Conceptual: comparing to `travelApp.py`

### C1. Why does `travelApp.py` skip `StateGraph` entirely?

`travelApp.py`'s core loop, inside `find_trip()`, is:

```python
for attempt in range(1, MAX_ATTEMPTS + 1):
    data = search_trip(destination, departure_date, return_date, budget, attempt, log)
    if data["total_cost"] <= budget:
        final_data = data
        break
    else:
        ...
```

There is exactly **one** decision point (in budget or not) and exactly **two** outcomes (stop early via `break`, or fall through to the next loop iteration). Compare that to `v3_toolnode.py`'s graph, which has a real three-way fork in `decide()` (`notify` / `END` / `search`) sitting on top of a separate `search -> tools -> observe` pipeline with distinct responsibilities per step.

`StateGraph` earns its complexity when there are multiple node types with different jobs and more than one meaningfully different "next step." `travelApp.py` doesn't have that — it has one job (search-and-price) repeated in a loop, wrapped in a Gradio-compatible generator (`yield` statements streaming progress to the UI). Building a graph for this would mean re-deriving control flow a plain `for` loop already gives for free, with no behavioral benefit.

**What would tip the scale:** if `travelApp.py` grew a real branch — e.g. "search flights only" vs. "search flights + hotels + activities" as a user-selectable mode that changes which functions actually run, or a human-approval step that pauses mid-search and resumes later — the binary "loop again or stop" model would stop describing the system, and `StateGraph`'s explicit nodes/edges would start paying for themselves by making that branching visible and inspectable instead of buried in nested `if` statements.

### C2. The hand-rolled `ToolNode` equivalent in `travelApp.py`

```python
def run_tool_calls(ai_message) -> list:
    results = []
    for call in ai_message.tool_calls:
        tool_fn = tools_by_name[call["name"]]
        output = tool_fn.invoke(call["args"])
        results.append(ToolMessage(content=str(output), tool_call_id=call["id"]))
    return results
```

Walking through it line by line:

- **`for call in ai_message.tool_calls:`** — an LLM response can request *multiple* tool calls in a single turn. This loop handles all of them, same as `ToolNode` does internally.
- **`tool_fn = tools_by_name[call["name"]]`** — `tools_by_name` is built earlier as `{t.name: t for t in tools}`. This dictionary lookup *is* the routing logic — matching a tool-call name string to an actual Python function — that `ToolNode` performs automatically when you hand it a `tools` list.
- **`output = tool_fn.invoke(call["args"])`** — actually executes the tool with whatever arguments the LLM supplied.
- **`results.append(ToolMessage(...))`** — wraps the result in a `ToolMessage`, tagged with `tool_call_id` so the LLM can match this result back to its own request on the next turn. This tagging is required by the underlying tool-calling protocol regardless of whether `ToolNode` or hand-written code produces it.

This function is called inside a `while True:` loop in `search_trip()` that keeps invoking the LLM and running `run_tool_calls()` until the LLM stops requesting tools — manually reproducing the `search -> tools -> search -> tools...` cycle that `tools_condition` automates in the graph-based versions. The takeaway: `ToolNode` and `tools_condition` aren't doing anything magical — they're automating a loop you can (and `travelApp.py` does) write by hand, at the cost of writing it yourself every time.

---

## Quick-reference comparison

| | V1 | v3 / `solution.py` | travelApp.py |
|---|---|---|---|
| Orchestration | `StateGraph` | `StateGraph` | Plain `for` loop |
| Tool execution | Manual call, result discarded | `ToolNode` (automatic) | Manual loop (`run_tool_calls`), by hand |
| Pricing source | `random.randint()` | Real search results | Real search results |
| Retry driver | `attempts` in state | `attempts` in state | `attempt` in `range()` |
| Tools available | 0 (fake) | 3 (after this assignment) | 3 (`search_flights`, `search_hotels`, `send_pushover`) |

## Why `MAX_ATTEMPTS` lives in code, not a prompt

All three files hardcode `MAX_ATTEMPTS = 3` and check it in real Python (`state["attempts"] >= MAX_ATTEMPTS` or `for attempt in range(1, MAX_ATTEMPTS + 1)`), rather than just telling the LLM via prompt "stop after 3 tries." This matters because a prompt-only limit is a *request*, not a *guarantee* — a model that's seen several over-budget results in a row might reason "let me try once more with a different strategy" and keep calling tools indefinitely, especially if the instruction gets deprioritized in a longer context. Enforcing the limit as a counter comparison in actual control flow means the worst case is mechanically bounded no matter what the model decides is reasonable in the moment.
