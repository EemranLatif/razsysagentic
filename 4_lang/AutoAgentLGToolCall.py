"""

<h1>RAZ Systems </h1>



AUTONOMOUS AGENTIC TRAVEL WORKFLOW — with Tool Calling
=======================================================

Key change from previous version:
----------------------------------
OLD: Nodes call search_web() and extract_price() directly (manual function calls)

NEW: Tools are defined with @tool and bound to the LLM.
     The LLM autonomously decides when to call them and processes their output.
     This is real tool calling / function calling.
"""

# ─────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────

import os
import json
import requests

from dotenv import load_dotenv
from typing import TypedDict

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, END


# ─────────────────────────────────────────────────────
# LOAD ENV VARIABLES
# ─────────────────────────────────────────────────────

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_TOKEN")


# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────

MAX_ATTEMPTS = 3

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ─────────────────────────────────────────────────────
# TOOLS  ← the main change
# ─────────────────────────────────────────────────────

@tool
def search_flights(destination: str, preferences: str = "") -> str:
    """Search for flight prices to a destination. Returns price info and options."""
    query = f"cheap flights to {destination} {preferences}"
    url = "https://google.serper.dev/search"
    response = requests.post(
        url,
        json={"q": query},
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    )
    results = []
    for item in response.json().get("organic", [])[:3]:
        results.append(f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}")
    return "\n".join(results) or "No results found."


@tool
def search_hotels(destination: str, preferences: str = "") -> str:
    """Search for hotel prices in a destination. Returns price info and options."""
    query = f"cheap hotels in {destination} {preferences}"
    url = "https://google.serper.dev/search"
    response = requests.post(
        url,
        json={"q": query},
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    )
    results = []
    for item in response.json().get("organic", [])[:3]:
        results.append(f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}")
    return "\n".join(results) or "No results found."


@tool
def send_notification(message: str) -> str:
    """Send a Pushover push notification with the given message."""
    response = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": PUSHOVER_APP_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "message": message
        }
    )
    return f"Notification sent. Status: {response.status_code}"


# Bind tools to the LLM — now it can call them autonomously
tools = [search_flights, search_hotels, send_notification]
tools_by_name = {t.name: t for t in tools}
llm_with_tools = llm.bind_tools(tools)


# ─────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────

class TravelState(TypedDict):
    destination: str
    budget: float
    itinerary: str
    total_cost: float
    approved: bool
    attempts: int


# ─────────────────────────────────────────────────────
# HELPER — run tool calls the LLM requested
# ─────────────────────────────────────────────────────

def run_tool_calls(ai_message) -> list[ToolMessage]:
    """Execute any tool calls the LLM made and return ToolMessages."""
    results = []
    for call in ai_message.tool_calls:
        tool_fn = tools_by_name[call["name"]]
        output = tool_fn.invoke(call["args"])
        results.append(ToolMessage(content=str(output), tool_call_id=call["id"]))
        print(f"  🔧 Tool called: {call['name']}({call['args']}) → {str(output)[:80]}...")
    return results


# ─────────────────────────────────────────────────────
# NODE 1 — PERCEIVE
# ─────────────────────────────────────────────────────

def perceive(state: TravelState):
    print("\n👁 PERCEIVE")
    print("Destination:", state["destination"])
    print("Budget:", state["budget"])
    return {}


# ─────────────────────────────────────────────────────
# NODE 2 — REASON + ACT  (tool calling happens here)
# ─────────────────────────────────────────────────────

def reason_and_act(state: TravelState):
    attempt = state["attempts"] + 1
    print(f"\n🧠 AUTONOMOUS SEARCH — Attempt {attempt}")

    # Build the prompt — LLM decides which tools to call and how
    messages = [
        HumanMessage(content=f"""
You are a travel planning AI agent.

Task: Find flights and hotels for a trip to {state['destination']}.
Budget: ${state['budget']} total.
Attempt: {attempt} of {MAX_ATTEMPTS}.
{"Previous attempt was over budget — search for cheaper options." if attempt > 1 else ""}

Steps:
1. Use search_flights to find flight prices.
2. Use search_hotels to find hotel prices.
3. Based on results, estimate a realistic total cost (flight + hotel).
4. Write a concise 3-day itinerary.

Respond in this exact JSON format (no markdown):
{{
  "flight_cost": <number>,
  "hotel_cost": <number>,
  "total_cost": <number>,
  "itinerary": "<3-day itinerary text>"
}}
""")
    ]

    # --- Agentic loop: LLM calls tools until it's done ---
    while True:
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            # No more tool calls — LLM is done, parse final answer
            break

        # Execute the tool calls and feed results back
        tool_results = run_tool_calls(response)
        messages.extend(tool_results)

    # Parse the LLM's final JSON response
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        # Fallback if LLM didn't follow format perfectly
        data = {"flight_cost": 9999, "hotel_cost": 9999, "total_cost": 9999, "itinerary": response.content}

    print(f"\n✈  Flight Cost: ${data['flight_cost']}")
    print(f"🏨 Hotel Cost:  ${data['hotel_cost']}")
    print(f"💰 Total Cost:  ${data['total_cost']}")

    return {
        "itinerary": data["itinerary"],
        "total_cost": data["total_cost"],
        "attempts": attempt,
    }


# ─────────────────────────────────────────────────────
# NODE 3 — OBSERVE
# ─────────────────────────────────────────────────────

def observe(state: TravelState):
    print("\n🔍 OBSERVE")
    print(f"Budget: ${state['budget']}  |  Trip Cost: ${state['total_cost']}")
    approved = state["total_cost"] <= state["budget"]
    print("Approved:", approved)
    return {"approved": approved}


# ─────────────────────────────────────────────────────
# NODE 4 — DECIDE (conditional router)
# ─────────────────────────────────────────────────────

def decide(state: TravelState):
    if state["approved"]:
        print("\n✅ WITHIN BUDGET")
        return "notify"
    if state["attempts"] >= MAX_ATTEMPTS:
        print("\n⛔ MAX ATTEMPTS REACHED")
        return END
    print("\n🔄 RETRYING WITH CHEAPER OPTIONS")
    return "reason_and_act"


# ─────────────────────────────────────────────────────
# NODE 5 — NOTIFY  (tool calling happens here too)
# ─────────────────────────────────────────────────────

def notify(state: TravelState):
    print("\n📲 SENDING NOTIFICATION VIA TOOL CALL")

    message = (
        f"Trip Approved!\n\n"
        f"Destination: {state['destination']}\n"
        f"Cost: ${state['total_cost']}\n\n"
        f"{state['itinerary']}"
    )

    # Let the LLM call send_notification as a tool
    messages = [
        HumanMessage(content=f"Send this travel notification:\n\n{message}")
    ]
    response = llm_with_tools.invoke(messages)

    if response.tool_calls:
        run_tool_calls(response)

    return {}


# ─────────────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────────────

graph = StateGraph(TravelState)

graph.add_node("perceive", perceive)
graph.add_node("reason_and_act", reason_and_act)
graph.add_node("observe", observe)
graph.add_node("notify", notify)

graph.set_entry_point("perceive")
graph.add_edge("perceive", "reason_and_act")
graph.add_edge("reason_and_act", "observe")
graph.add_conditional_edges("observe", decide)
graph.add_edge("notify", END)

app = graph.compile()


# ─────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────

initial_state = {
    "destination": "Paris",
    "budget": 900,
    "itinerary": "",
    "total_cost": 0,
    "approved": False,
    "attempts": 0,
}

print("\n🚀 STARTING AUTONOMOUS AI AGENT (Tool Calling)")
result = app.invoke(initial_state)
print("\n✅ AGENT FINISHED")