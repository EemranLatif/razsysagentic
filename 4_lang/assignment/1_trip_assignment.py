"""
RAZ Systems — Agentic AI Engineering Curriculum
LangGraph Assignment: From Simulation to Production
=====================================================

This file is built on top of `v3_toolnode.py` from class — the version where
ToolNode + tools_condition make tool execution real, and MAX_ATTEMPTS lives
in state instead of a prompt.

Your job: extend this working agent with a THIRD tool (search_activities),
following the same ToolNode pattern already used for flights and hotels.

Read every TODO comment before writing code — several of them are testing
whether you noticed ALL the places a new tool needs to be registered, not
just the obvious one.

------------------------------------------------------------------------
PART A — DIAGNOSTIC QUESTIONS (answer in the docstrings below, in your own
words, before touching any code)
------------------------------------------------------------------------

A1. In V1 (V1_AutoAgentLangGraph.py), `reason_and_act()` calls search_web()
    twice, builds flight_results/hotel_results, and then never uses them
    to compute cost. What DOES set flight_cost and hotel_cost in V1?

    YOUR ANSWER:
    >>>


A2. perceive() and notify() (in V1) both `return {}`. Is that the same as
    returning nothing, or does it mean something specific in how LangGraph
    merges node outputs into state?

    YOUR ANSWER:
    >>>


A3. decide() in this file (V3-based) returns one of three different string
    values. Name them, and name the LangGraph call (elsewhere in this file)
    that actually turns a returned string into "go run that node."

    YOUR ANSWER:
    >>>


------------------------------------------------------------------------
PART B — BUILD: add a third tool via ToolNode
------------------------------------------------------------------------
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


# TODO B1 — Write a third tool, search_activities(destination, preferences="")
#   - Follow the exact same @tool pattern as search_flights / search_hotels above.
#   - It should search for "top tourist activities and prices" in the destination.
#   - Reuse the same requests.post(...) / Serper response-parsing pattern.
#
# @tool
# def search_activities(destination: str, preferences: str = "") -> str:
#     """Search for popular tourist activities and their typical costs in a destination."""
#     ...YOUR CODE HERE...


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


# TODO B1 (continued) — There are THREE places in this file that need to know
# about your new tool. This is the first one: add search_activities to this list.
tools          = [search_flights, search_hotels]  # ← add search_activities here
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

    # TODO B2 — This prompt currently tells the LLM to call BOTH tools
    # (flights, hotels). Update the instructions so it calls ALL THREE
    # tools, including search_activities, without breaking the existing
    # flight/hotel instructions.
    prompt = SystemMessage(content=(
        f"You are a travel search agent. Attempt {attempt} of {MAX_ATTEMPTS}.\n"
        f"Call BOTH tools now — one call for flights, one for hotels:\n"
        f"  Flights: destination={state['destination']}, "
        f"departure_date={state['departure']}, return_date={state['return_date']}"
        f"{', preferences=' + cheaper if cheaper else ''}\n"
        f"  Hotels:  destination={state['destination']}, "
        f"checkin_date={state['departure']}, checkout_date={state['return_date']}"
        f"{', preferences=' + cheaper if cheaper else ''}\n"
        # TODO: add an Activities instruction line here
        f"Call both tools now. No text."
        # TODO: update "both" to reflect the new tool count
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

    # TODO B3 — Update this extraction prompt so it also asks for
    # ACTIVITIES_COST as a separate line, and make sure TOTAL_COST is
    # explicitly described as flight + hotel + activities combined
    # (decide() downstream should NOT need any changes if you do this right).
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

    # TODO B3 (continued) — extract ACTIVITIES_COST the same way as TOTAL_COST
    # (you don't strictly need to USE it in decide(), but log it for visibility)

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
# TODO B4 (THINK FIRST, DON'T EDIT) — ToolNode(tools) below uses the SAME
# `tools` list you updated above. Does adding search_activities to that list
# require a NEW graph.add_node(...) call here, or does this line already
# pick up your third tool automatically? Write your answer as a comment here:
#
# YOUR ANSWER (as a comment):
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
    print(f"🚀 ASSIGNMENT — ToolNode + 3 tools + MAX_ATTEMPTS ({MAX_ATTEMPTS})")

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


# ─────────────────────────────────────────────────────
# PART C — CONCEPTUAL (answer here as a comment, no code needed)
# ─────────────────────────────────────────────────────
#
# C1. travelApp.py (the Gradio version) has NO StateGraph at all — just a
#     `for attempt in range(1, MAX_ATTEMPTS + 1):` loop inside find_trip().
#     In 3-5 sentences: why is a graph overkill there, and what ONE change
#     to travelApp.py's control flow would make a StateGraph start paying
#     for itself?
#
#     YOUR ANSWER:
#     >>>
#
#
# C2. travelApp.py still needs to execute tool calls the LLM requests, but
#     it doesn't import ToolNode. Find the function in travelApp.py that's
#     doing ToolNode's job by hand (it's named run_tool_calls). Explain,
#     line by line, what each line is doing that ToolNode would otherwise
#     do automatically.
#
#     YOUR ANSWER:
#     >>>
