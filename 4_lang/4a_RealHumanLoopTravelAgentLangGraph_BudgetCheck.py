"""
<h1>RAZ Systems </h1>

SIMPLE REAL AGENTIC TRAVEL WORKFLOW
==================================

This example demonstrates:

1. OpenAI LLM reasoning
2. Serper web search
3. LangGraph workflow
4. Human approval
5. Pushover notification

FLOW
────
Perceive → Search → Check Budget → (regenerate if over, up to a limit) → Review → Human Approval → Notify

This version is intentionally simplified for students.
"""

# ─────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────

import os
import requests

from dotenv import load_dotenv

from typing import TypedDict

from langgraph.graph import StateGraph, END
from langgraph.types import Command

from langchain_openai import ChatOpenAI


# ─────────────────────────────────────────────────────
# LOAD ENV VARIABLES
# ─────────────────────────────────────────────────────

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

# ─────────────────────────────────────────────────────
# CREATE LLM
# ─────────────────────────────────────────────────────

# GPT model used for reasoning
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


# ─────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────

"""
State = shared memory between all nodes

Each node can:
- read state
- update statey

"""

class TravelState(TypedDict):

    origin: str
    destination: str
    budget: float

    search_results: str

    itinerary: str

    approved: bool

    # ── budget-check fields ──
    estimated_cost: float | None   # cost the LLM extracted from the itinerary
    over_budget: bool              # True if estimated_cost > budget
    budget_check_attempts: int     # how many times we've tried to regenerate a cheaper plan


# ─────────────────────────────────────────────────────
# SERPER SEARCH FUNCTION
# ─────────────────────────────────────────────────────

def search_web(query: str) -> str:
    """
    Search Google using Serper API
    """

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

    # Take first 3 search results
    for item in data.get("organic", [])[:3]:

        results.append(
            f"""
Title: {item.get('title')}
Snippet: {item.get('snippet')}
"""
        )

    return "\n".join(results)


# ─────────────────────────────────────────────────────
# PUSHOVER FUNCTION
# ─────────────────────────────────────────────────────

def send_notification(message: str):

    response = requests.post(
        pushover_url,
        data={
            "token": PUSHOVER_APP_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "message": message
        }
    )

    print("\nNotification Status:", response.status_code)
    print("\nNotification Status:", response.text)
    print("\nNotification Status:", PUSHOVER_USER_KEY)
# ─────────────────────────────────────────────────────
# NODE 1 — PERCEIVE
# ─────────────────────────────────────────────────────

def perceive(state: TravelState):

    """
    Read user input
    """

    print("\n👁 PERCEIVE")

    print("Destination:", state["destination"])
    print("Budget:", state["budget"])

    return {}


# ─────────────────────────────────────────────────────
# NODE 2 — SEARCH
# ─────────────────────────────────────────────────────

def search(state: TravelState):

    """
    Search web + ask LLM to create itinerary
    """

    print("\n🔍 SEARCH")

    # Search flights
    flight_results = search_web(
        f"cheap flights to {state['destination']}"
    )

    # Search hotels
    hotel_results = search_web(
        f"best hotels in {state['destination']}"
    )

    # Combine search results
    combined_results = f"""
FLIGHTS:
{flight_results}

HOTELS:
{hotel_results}
"""

    print("\nWeb Search Complete")

    # Prompt sent to LLM
    prompt = f"""
Create a simple 3-day travel plan.

Destination:
{state['destination']}

Budget:
${state['budget']}

Search Results:
{combined_results}

Include:
- flight suggestion
- hotel suggestion
- estimated cost
- 3-day itinerary
"""

    # Call OpenAI
    response = llm.invoke(prompt)

    # Save into state
    return {
        "search_results": combined_results,
        "itinerary": response.content
    }


# ─────────────────────────────────────────────────────
# NODE 3 — CHECK BUDGET
# ─────────────────────────────────────────────────────

# Regenerate the itinerary at most this many times if it comes back over budget,
# so a stubborn LLM can't loop forever.
MAX_BUDGET_RETRIES = 2


def check_budget(state: TravelState) -> dict:

    """
    Ask the LLM to extract a single number (the estimated total cost) out of
    the itinerary it just wrote, then compare that number to state["budget"].

    This is the "real" check -- everything upstream only *asked* the LLM to
    respect the budget. This node *verifies* it, in code, with a comparison.
    """

    print("\n💰 CHECK BUDGET")

    extract_prompt = f"""
Read the itinerary below and reply with ONLY the estimated total cost as a
plain number -- no dollar sign, no commas, no words. If a range is given,
reply with the highest number in the range.

Itinerary:
{state['itinerary']}
"""

    response = llm.invoke(extract_prompt)
    raw_cost = response.content.strip()

    # The LLM should return something like "4820" -- but LLM output is text,
    # not a guaranteed number, so we defensively try/except the conversion
    # rather than trusting it blindly.
    try:
        estimated_cost = float(raw_cost.replace(",", "").replace("$", ""))
    except ValueError:
        print(f"⚠️  Could not parse a cost from: '{raw_cost}' -- treating as unknown")
        estimated_cost = None

    over_budget = estimated_cost is not None and estimated_cost > state["budget"]

    attempts = state.get("budget_check_attempts", 0) + 1

    if estimated_cost is not None:
        print(f"Estimated cost: ${estimated_cost:,.0f}   Budget: ${state['budget']:,.0f}")
        print("Over budget!" if over_budget else "Within budget.")
    else:
        print("Estimated cost unknown -- proceeding to review so a human can judge.")

    return {
        "estimated_cost": estimated_cost,
        "over_budget": over_budget,
        "budget_check_attempts": attempts,
    }


def route_after_budget_check(state: TravelState) -> str:

    """
    - If the plan is over budget AND we haven't hit the retry limit yet,
      go back to `search` to regenerate a cheaper itinerary.
    - Otherwise (within budget, cost unknown, or retries exhausted),
      move on to `review` so a human sees the final version either way.
    """

    if state["over_budget"] and state["budget_check_attempts"] < MAX_BUDGET_RETRIES:
        print(f"↩️  Regenerating itinerary (attempt {state['budget_check_attempts']}/{MAX_BUDGET_RETRIES})...")
        return "search"

    if state["over_budget"]:
        print("⚠️  Still over budget after max retries -- sending to human review anyway.")

    return "review"


# ─────────────────────────────────────────────────────
# NODE 4 — REVIEW
# ─────────────────────────────────────────────────────

def review(state: TravelState):

    """
    Display itinerary
    """

    print("\n📋 REVIEW")

    print("\n" + "=" * 60)
    print(state["itinerary"])
    print("=" * 60)

    if state.get("estimated_cost") is not None:
        flag = "⚠️  OVER BUDGET" if state["over_budget"] else "✅ within budget"
        print(f"Estimated cost: ${state['estimated_cost']:,.0f}  (budget: ${state['budget']:,.0f})  {flag}")

    return {}


# ─────────────────────────────────────────────────────
# NODE 4 — HUMAN APPROVAL
# ─────────────────────────────────────────────────────

def human_approval1(state: TravelState):

    """
    Human decides approval
    """

    print("\n🙋 HUMAN APPROVAL")

    answer = input(
        "\nApprove trip? (y/n): "
    ).lower()

    # APPROVED
    if answer == "y":

        return Command(
            goto="notify",
            update={
                "approved": True
            }
        )

    # NOT APPROVED
    return Command(
        goto=END,
        update={
            "approved": False
        }
    )

def human_approval(state: TravelState) -> dict:
    answer = input("\nApprove trip? (y/n): ").lower()
    return {"approved": answer == "y"}

def route_after_approval(state: TravelState) -> str:
    return "notify" if state["approved"] else END


# ─────────────────────────────────────────────────────
# NODE 5 — NOTIFY
# ─────────────────────────────────────────────────────

def notify(state: TravelState):

    """
    Send pushover notification
    """

    print("\n📲 SENDING NOTIFICATION")

    send_notification(
        state["itinerary"]
    )

    return {}


# ─────────────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────────────

graph = StateGraph(TravelState)

# Add nodes
graph.add_node("perceive", perceive)
graph.add_node("search", search)
graph.add_node("check_budget", check_budget)
graph.add_node("review", review)
graph.add_node("human_approval", human_approval)
graph.add_node("notify", notify)

# Starting node
graph.set_entry_point("perceive")

# Connect nodes
graph.add_edge("perceive", "search")
graph.add_edge("search", "check_budget")
graph.add_conditional_edges(
    "check_budget",
    route_after_budget_check,
    {"search": "search", "review": "review"},
)
graph.add_edge("review", "human_approval")
graph.add_conditional_edges(
    "human_approval",
    route_after_approval,
    {"notify": "notify", END: END},
)
graph.add_edge("notify", END)

# Compile graph
app = graph.compile()


# ─────────────────────────────────────────────────────
# RUN WORKFLOW
# ─────────────────────────────────────────────────────

initial_state = {

     "origin": "Washington DC",

    "destination": "Bangalore",

    "budget": 1,

    "search_results": "",

    "itinerary": "",

    "approved": False,

    "estimated_cost": None,
    "over_budget": False,
    "budget_check_attempts": 0,
}

print("\n🚀 STARTING AGENT WORKFLOW")

result = app.invoke(initial_state)

print("\n✅ WORKFLOW FINISHED")
