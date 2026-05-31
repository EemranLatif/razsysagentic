"""
<h1>RAZ Systems </h1>



VERSION 3 — ToolNode + MAX_ATTEMPTS (Proper Retry Logic)
=========================================================

The key insight:
    ToolNode handles tool EXECUTION automatically.
    MAX_ATTEMPTS is tracked in STATE — not inside the LLM.

Graph flow:
    START
      ↓
    search  ◄─────────────────────────────────────────────┐
      ↓                                                    │
    tools  (ToolNode — auto executes search_flights        │
      ↓              and search_hotels)                    │
    observe  (LLM reads results, extracts total_cost)      │
      ↓                                                    │
    decide ──→ within budget?           → notify → END     │
           ──→ over budget, attempts < MAX ────────────────┘
           ──→ over budget, attempts >= MAX → END

Why this works:
- ToolNode still handles tool execution (no manual loop)
- attempts lives in State — always visible, always real
- decide is plain Python — MAX_ATTEMPTS check is real code, not a prompt
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


tools          = [search_flights, search_hotels]  # only search tools go to ToolNode
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

    prompt = SystemMessage(content=(
        f"You are a travel search agent. Attempt {attempt} of {MAX_ATTEMPTS}.\n"
        f"Call BOTH tools now — one call for flights, one for hotels:\n"
        f"  Flights: destination={state['destination']}, "
        f"departure_date={state['departure']}, return_date={state['return_date']}"
        f"{', preferences=' + cheaper if cheaper else ''}\n"
        f"  Hotels:  destination={state['destination']}, "
        f"checkin_date={state['departure']}, checkout_date={state['return_date']}"
        f"{', preferences=' + cheaper if cheaper else ''}\n"
        f"Call both tools now. No text."
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

    extract_prompt = HumanMessage(content=(
        f"Read the flight and hotel search results above.\n"
        f"Reply ONLY in this exact format — no extra text:\n\n"
        f"TOTAL_COST: <single number in USD, flight + hotel combined>\n"
        f"ITINERARY:\n"
        f"<day-by-day plan with real dates starting {state['departure']}>"
    ))

    response   = plain_llm.invoke(state["messages"] + [extract_prompt])
    text       = response.content

    match      = re.search(r"TOTAL_COST:\s*\$?([\d,]+)", text)
    total_cost = float(match.group(1).replace(",", "")) if match else 9999.0

    itin_match = re.search(r"ITINERARY:\s*(.+)", text, re.DOTALL)
    itinerary  = itin_match.group(1).strip() if itin_match else text

    print(f"  💰 Total: ${total_cost}  |  Budget: ${state['budget']}")

    return {
        "total_cost": total_cost,
        "itinerary":  itinerary,
    }


# ─────────────────────────────────────────────────────
# NODE 4 — DECIDE
# MAX_ATTEMPTS enforced here in real Python — not in a prompt
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
    print(f"🚀 V3 — ToolNode + MAX_ATTEMPTS ({MAX_ATTEMPTS})")

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