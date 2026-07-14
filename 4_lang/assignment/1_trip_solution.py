"""
RAZ Systems — Agentic AI Engineering Curriculum
LangGraph Assignment SOLUTION: From Simulation to Production
================================================================

Fully worked solution to assignment.py — runnable end to end with:
    python solution.py

Built on top of v3_toolnode.py, extended with a third tool
(search_activities) that flows through ToolNode exactly the same way
search_flights / search_hotels already did.

See explanation.md for the full reasoning behind every answer below —
this file focuses on working code; the .md file focuses on WHY it works.
"""

import os
import re
import requests
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

SERPER_API_KEY     = os.getenv("SERPER_API_KEY")
PUSHOVER_USER_KEY  = os.getenv("PUSHOVER_USER")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_TOKEN")

MAX_ATTEMPTS = 3


# ─────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────

@tool
def search_flights(destination: str, departure_date: str, return_date: str, preferences: str = "") -> str:
    """Search for flight prices to a destination for specific travel dates."""
    query = f"cheap flights to {destination} departing {departure_date} returning {return_date} {preferences}"
    response = requests.post(
        "https://google.serper.dev/search",
        json={"q": query},
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    )
    results = [
        f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}"
        for item in response.json().get("organic", [])[:3]
    ]
    return "\n\n".join(results) or "No results found."


@tool
def search_hotels(destination: str, checkin_date: str, checkout_date: str, preferences: str = "") -> str:
    """Search for hotel prices in a destination for specific dates."""
    query = f"cheap hotels in {destination} check in {checkin_date} check out {checkout_date} {preferences}"
    response = requests.post(
        "https://google.serper.dev/search",
        json={"q": query},
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    )
    results = [
        f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}"
        for item in response.json().get("organic", [])[:3]
    ]
    return "\n\n".join(results) or "No results found."


# SOLUTION B1 — third tool, same pattern as the two above
@tool
def search_activities(destination: str, preferences: str = "") -> str:
    """Search for popular tourist activities and their typical costs in a destination."""
    query = f"top tourist activities and prices in {destination} {preferences}"
    response = requests.post(
        "https://google.serper.dev/search",
        json={"q": query},
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    )
    results = [
        f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}"
        for item in response.json().get("organic", [])[:3]
    ]
    return "\n\n".join(results) or "No results found."


def send_pushover(message: str):
    """Send a Pushover push notification — called directly, not as a tool."""
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token":   PUSHOVER_APP_TOKEN,
            "user":    PUSHOVER_USER_KEY,
            "message": message,
            "title":   "✈️ Travel Alert"
        }
    )


# SOLUTION B1 (continued) — the ONE place the tools list needs updating.
# llm_with_tools and ToolNode(tools) below both reference this same list,
# so they pick up search_activities automatically — see explanation.md B4.
tools          = [search_flights, search_hotels, search_activities]
llm_with_tools = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(tools)
plain_llm      = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ─────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────

class State(TypedDict):
    messages:    Annotated[list, add_messages]  # ← ToolNode reads/writes here
    destination: str
    departure:   str
    return_date: str
    budget:      float
    total_cost:  float  # ← set by observe node
    itinerary:   str    # ← set by observe node
    attempts:    int    # ← incremented by search node, checked by decide


# ─────────────────────────────────────────────────────
# NODE 1 — SEARCH
# Tells LLM to call search tools. ToolNode executes them next.
# ─────────────────────────────────────────────────────

def search(state: State):
    attempt = state["attempts"] + 1
    cheaper = "budget economy cheapest" if attempt > 1 else ""

    print(f"\n🔍 SEARCH — Attempt {attempt}/{MAX_ATTEMPTS}")

    # SOLUTION B2 — all three tools instructed explicitly
    prompt = SystemMessage(content=(
        f"You are a travel search agent. Attempt {attempt} of {MAX_ATTEMPTS}.\n"
        f"Call ALL THREE tools now — one for flights, one for hotels, one for activities:\n"
        f"  Flights: destination={state['destination']}, "
        f"departure_date={state['departure']}, return_date={state['return_date']}"
        f"{', preferences=' + cheaper if cheaper else ''}\n"
        f"  Hotels:  destination={state['destination']}, "
        f"checkin_date={state['departure']}, checkout_date={state['return_date']}"
        f"{', preferences=' + cheaper if cheaper else ''}\n"
        f"  Activities: destination={state['destination']}"
        f"{', preferences=' + cheaper if cheaper else ''}\n"
        f"Call all three tools now. No text."
    ))

    response = llm_with_tools.invoke([prompt])

    for call in response.tool_calls:
        print(f"  🔧 Calling: {call['name']}")

    # Reset messages each attempt so we don't carry over old search results
    return {
        "messages":  [prompt, response],
        "attempts":  attempt,
        "total_cost": 0,
    }


# ─────────────────────────────────────────────────────
# NODE 2 — TOOLS  (ToolNode — defined in graph below)
# Executes tool calls from search, appends ToolMessages to state
# ─────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────
# NODE 3 — OBSERVE
# Reads tool results, extracts total_cost and itinerary
# ─────────────────────────────────────────────────────

def observe(state: State):
    print("\n📊 OBSERVE — reading results")

    # SOLUTION B3 — added ACTIVITIES_COST, and TOTAL_COST is now explicitly
    # flight + hotel + activities combined, so decide() needs ZERO changes.
    extract_prompt = HumanMessage(content=(
        f"Read the flight, hotel, and activity search results above.\n"
        f"Reply ONLY in this exact format — no extra text:\n\n"
        f"TOTAL_COST: <single number in USD, flight + hotel + activities combined>\n"
        f"ACTIVITIES_COST: <single number in USD, activities only>\n"
        f"ITINERARY:\n"
        f"<day-by-day plan with real dates starting {state['departure']}, "
        f"including 1-2 activities per day>"
    ))

    response   = plain_llm.invoke(state["messages"] + [extract_prompt])
    text       = response.content

    match      = re.search(r"TOTAL_COST:\s*\$?([\d,]+)", text)
    total_cost = float(match.group(1).replace(",", "")) if match else 9999.0

    # SOLUTION B3 (continued) — extracted for visibility/logging only;
    # decide() never needs to read this since total_cost already includes it.
    act_match      = re.search(r"ACTIVITIES_COST:\s*\$?([\d,]+)", text)
    activities_cost = float(act_match.group(1).replace(",", "")) if act_match else 0.0

    itin_match = re.search(r"ITINERARY:\s*(.+)", text, re.DOTALL)
    itinerary  = itin_match.group(1).strip() if itin_match else text

    print(f"  💰 Total: ${total_cost}  (activities: ${activities_cost})  |  Budget: ${state['budget']}")

    return {
        "total_cost": total_cost,
        "itinerary":  itinerary,
    }


# ─────────────────────────────────────────────────────
# NODE 4 — DECIDE
# MAX_ATTEMPTS enforced here in real Python — not in a prompt
# Unchanged from v3_toolnode.py — see explanation.md B3 for why.
# ─────────────────────────────────────────────────────

def decide(state: State):
    if state["total_cost"] <= state["budget"]:
        print("\n✅ WITHIN BUDGET — notifying")
        return "notify"

    if state["attempts"] >= MAX_ATTEMPTS:
        print(f"\n⛔ MAX ATTEMPTS ({MAX_ATTEMPTS}) REACHED — stopping")
        return END

    over_by = state["total_cost"] - state["budget"]
    print(f"\n🔄 OVER BUDGET by ${over_by:.0f} — attempt {state['attempts']}/{MAX_ATTEMPTS}")
    return "search"


# ─────────────────────────────────────────────────────
# NODE 5 — NOTIFY
# ─────────────────────────────────────────────────────

def notify(state: State):
    print("\n📲 SENDING NOTIFICATION")
    send_pushover(
        f"✈️ Trip Found!\n\n"
        f"Destination: {state['destination']}\n"
        f"Dates: {state['departure']} → {state['return_date']}\n"
        f"Total: ${state['total_cost']} (budget: ${state['budget']})\n\n"
        f"{state['itinerary']}"
    )
    return {}


# ─────────────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────────────

graph = StateGraph(State)

graph.add_node("search",  search)

# SOLUTION B4 — NO new graph.add_node(...) call needed. ToolNode(tools) is
# ONE node that dispatches internally to whichever tool the LLM's tool-call
# names — it looks up the function by name inside the `tools` list. Adding
# search_activities to that list gives this SAME "tools" node a third
# function it can call; it does not create a third node in the graph.
# Full reasoning in explanation.md, section B4.
graph.add_node("tools",   ToolNode(tools))  # ← auto-executes tool calls
graph.add_node("observe", observe)
graph.add_node("notify",  notify)

graph.add_edge(START,    "search")
graph.add_conditional_edges("search", tools_condition, {"tools": "tools"})
graph.add_edge("tools",  "observe")               # after tools run → observe
graph.add_conditional_edges("observe", decide)    # decide uses real MAX_ATTEMPTS
graph.add_edge("notify", END)

app = graph.compile()


# ─────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🚀 SOLUTION — ToolNode + 3 tools + MAX_ATTEMPTS ({MAX_ATTEMPTS})")

    result = app.invoke({
        "messages":    [],
        "destination": "Bangalore",
        "departure":   "2026-08-01",
        "return_date": "2026-08-08",
        "budget":      3000,
        "total_cost":  0,
        "itinerary":   "",
        "attempts":    0,
    })

    print("\n✅ DONE")
    print(result["itinerary"])
