"""

<h1>RAZ Systems </h1>

AUTONOMOUS AGENTIC TRAVEL WORKFLOW
==================================

Difference from previous version:
---------------------------------

OLD:
Human approves manually

NEW:
Agent autonomously:
1. Searches flights/hotels
2. Calculates total cost
3. Decides if within budget
4. Retries automatically
5. Stops after MAX_ATTEMPTS
6. Sends notification automatically

This is closer to a REAL autonomous AI agent.
"""

# ─────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────

import os
import re
import requests
import random

from dotenv import load_dotenv

from typing import TypedDict

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI


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

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


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
# SERPER SEARCH
# ─────────────────────────────────────────────────────

def search_web(query: str):

    url = "https://google.serper.dev/search"

    payload = {
        "q": query
    }

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    data = response.json()

    results = []

    for item in data.get("organic", [])[:3]:

        results.append(
            f"""
Title: {item.get('title')}
Snippet: {item.get('snippet')}
"""
        )

    return "\n".join(results)


# ─────────────────────────────────────────────────────
# PUSHOVER
# ─────────────────────────────────────────────────────

def send_notification(message):

    response = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": PUSHOVER_APP_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "message": message
        }
    )

    print("\n📲 Notification Status:", response.status_code)


import re

def extract_price(text: str, item: str):

    prompt = f"""
        Extract the cheapest estimated {item} price in USD from the text.

        Rules:
        - Return ONLY a number
        - If range exists, return lower value
        - If not found, return 9999

        Text:
        {text}
        """

    response = llm.invoke(prompt).content

    # extract first number safely
    match = re.search(r"\d+", response)

    if match:
        return int(match.group())

    return 9999  # fallback instead of 0

# ─────────────────────────────────────────────────────
# NODE 1 — PERCEIVE
# ─────────────────────────────────────────────────────

def perceive(state: TravelState):

    print("\n👁 PERCEIVE")

    print("Destination:", state["destination"])
    print("Budget:", state["budget"])

    return {}


# ─────────────────────────────────────────────────────
# NODE 2 — REASON + ACT
# ─────────────────────────────────────────────────────

def reason_and_act(state: TravelState):
    """
    Agentic step:
    1. Reason about previous attempt + cost
    2. Decide what to optimize (flight / hotel / both)
    3. Act by calling search tools
    """

    attempt = state["attempts"] + 1

    print(f"\n🧠 AUTONOMOUS SEARCH — Attempt {attempt}")

    # ─────────────────────────────────────────────
    # 1. INITIALIZE HINTS (REASONING OUTPUT)
    # ─────────────────────────────────────────────

    flight_hint = ""
    hotel_hint = ""

    # ─────────────────────────────────────────────
    # 2. SIMPLE RULE-BASED REASONING
    # (student-friendly, explainable logic)
    # ─────────────────────────────────────────────

    # If flight is expensive → optimize flights
    if state.get("flight_cost", 0) > 900:
        flight_hint = "cheap economy"
        print("🧠 Reason: Flight is expensive → try cheaper flights")

    # If hotel is expensive → optimize hotels
    if state.get("hotel_cost", 0) > 700:
        hotel_hint = "budget hostel"
        print("🧠 Reason: Hotel is expensive → try cheaper hotels")

    # If first attempt → general search
    if attempt == 1:
        print("🧠 Reason: First attempt → general search")

    # ─────────────────────────────────────────────
    # 3. ACT — CALL TOOLS (SEARCH)
    # ─────────────────────────────────────────────

    flight_results = search_web(
        f"cheap flights to {state['destination']} {flight_hint}"
    )

    hotel_results = search_web(
        f"cheap hotels in {state['destination']} {hotel_hint}"
    )

    # ─────────────────────────────────────────────
    # 4. SIMULATED COSTING (replace with real APIs later)
    # ─────────────────────────────────────────────
    #flight_cost = extract_price(flight_results, "flight")
    #hotel_cost = extract_price(hotel_results, "hotel")
    flight_cost = random.randint(500, 1500)
    hotel_cost = random.randint(300, 1200)

    total_cost = flight_cost + hotel_cost

    print(f"\n✈ Flight Cost: ${flight_cost}")
    print(f"🏨 Hotel Cost: ${hotel_cost}")
    print(f"💰 Total Cost: ${total_cost}")

    # ─────────────────────────────────────────────
    # 5. REASON → GENERATE ITINERARY (LLM)
    # ─────────────────────────────────────────────

    prompt = f"""
You are a travel planning AI.

Create a simple 3-day itinerary.

Destination: {state['destination']}
Budget context available.

Flight Cost: ${flight_cost}
Hotel Cost: ${hotel_cost}
Total Cost: ${total_cost}

Flight Results:
{flight_results}

Hotel Results:
{hotel_results}

Make it concise and practical.
"""

    response = llm.invoke(prompt)

    # ─────────────────────────────────────────────
    # 6. RETURN UPDATED STATE
    # ─────────────────────────────────────────────

    return {
        "itinerary": response.content,
        "total_cost": total_cost,
        "attempts": attempt,
        "flight_cost": flight_cost,
        "hotel_cost": hotel_cost
    }

# ─────────────────────────────────────────────────────
# NODE 3 — OBSERVE
# ─────────────────────────────────────────────────────

def observe(state: TravelState):

    """
    Agent evaluates result
    """

    print("\n🔍 OBSERVE")

    print(f"Budget: ${state['budget']}")
    print(f"Trip Cost: ${state['total_cost']}")

    # Agent decision
    approved = state["total_cost"] <= state["budget"]

    print("Approved:", approved)

    return {
        "approved": approved
    }


# ─────────────────────────────────────────────────────
# NODE 4 — DECIDE
# ─────────────────────────────────────────────────────

def decide(state: TravelState):

    """
    Autonomous decision node
    """

    # SUCCESS
    if state["approved"]:

        print("\n✅ WITHIN BUDGET")

        return "notify"

    # MAX ATTEMPTS REACHED
    if state["attempts"] >= MAX_ATTEMPTS:

        print("\n⛔ MAX ATTEMPTS REACHED")

        return END

    # RETRY
    print("\n🔄 RETRYING WITH CHEAPER OPTIONS")

    return "reason_and_act"


# ─────────────────────────────────────────────────────
# NODE 5 — NOTIFY
# ─────────────────────────────────────────────────────

def notify(state: TravelState):

    print("\n📲 SENDING PUSHOVER NOTIFICATION")

    send_notification(
        f"""
Trip Approved!

Destination: {state['destination']}

Cost: ${state['total_cost']}

{state['itinerary']}
"""
    )

    return {}


# ─────────────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────────────

graph = StateGraph(TravelState)

# Add nodes
graph.add_node("perceive", perceive)

graph.add_node("reason_and_act", reason_and_act)

graph.add_node("observe", observe)

graph.add_node("notify", notify)

# Entry point
graph.set_entry_point("perceive")

# Normal edges
graph.add_edge("perceive", "reason_and_act")

graph.add_edge("reason_and_act", "observe")

# Conditional routing
graph.add_conditional_edges(
    "observe",
    decide
)

graph.add_edge("notify", END)

# Compile
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

    "attempts": 0
}

print("\n🚀 STARTING AUTONOMOUS AI AGENT")

result = app.invoke(initial_state)

print("\n✅ AGENT FINISHED")