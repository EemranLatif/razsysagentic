"""
<h1>RAZ Systems </h1>

LangGraph Human-in-the-Loop — Complete Sample Code
====================================================
Pattern: Perceive → Reason → Act → Observe
with human approval checkpoints to avoid infinite loops.

Three agents:
  1. Travel Agent
  2. Financial Analyst Agent
  3. DevOps Agent

Install:
  pip install langgraph langchain langchain-openai python-dotenv

Run:
  export OPENAI_API_KEY=sk-...
  python langgraph_human_in_loop.py
"""

import random
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command

# ─── LLM (used for reasoning nodes if you want to swap in real LLM calls) ────
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ─── Helpers ─────────────────────────────────────────────────────────────────
MAX_ATTEMPTS = 3  # global loop-guard limit


def banner(title: str):
    print(f"\n{'━'*60}\n  {title}\n{'━'*60}")


def step(icon: str, label: str, msg: str):
    print(f"\n  {icon}  [{label}]  {msg}")


# ══════════════════════════════════════════════════════════════════════════════
# EXAMPLE 1 — TRAVEL AGENT
# ══════════════════════════════════════════════════════════════════════════════

class TravelState(TypedDict):
    messages:    Annotated[list, add_messages]
    destination: str
    budget:      float
    flight_cost: float
    hotel_cost:  float
    itinerary:   str
    approved:    bool
    attempts:    int   # ← loop guard


# ── Tool stubs (swap with real Skyscanner / Booking.com APIs) ─────────────────
@tool
def search_flights(destination: str) -> dict:
    """Search cheapest flights to a destination."""
    return {
        "destination": destination,
        "price": random.randint(400, 1200),
        "airline": "AirMock",
    }


@tool
def search_hotels(destination: str, nights: int = 3) -> dict:
    """Search hotel availability and nightly price."""
    return {
        "hotel": "MockInn",
        "nights": nights,
        "total": random.randint(80, 300) * nights,
    }


@tool
def build_itinerary(destination: str, flight: dict, hotel: dict) -> str:
    """Compile the full travel itinerary string."""
    total = flight["price"] + hotel["total"]
    return (
        f"  ✈  Flight  → {destination}: ${flight['price']} ({flight['airline']})\n"
        f"  🏨  Hotel   → {hotel['nights']} nights:  ${hotel['total']} ({hotel['hotel']})\n"
        f"  💰  Total   → ${total}"
    )


# ── Nodes ─────────────────────────────────────────────────────────────────────
def travel_perceive(state: TravelState) -> dict:
    step("👁", "PERCEIVE", f"Destination={state['destination']}, Budget=${state['budget']}")
    return {"attempts": state.get("attempts", 0) + 1}


def travel_reason(state: TravelState) -> dict:
    step("🧠", "REASON", "Plan: search flights → hotels → build itinerary")
    return {}


def travel_act(state: TravelState) -> dict:
    step("⚡", "ACT", "Calling flight & hotel APIs …")
    flight = search_flights.invoke({"destination": state["destination"]})
    hotel  = search_hotels.invoke({"destination": state["destination"], "nights": 3})
    itinerary = build_itinerary.invoke({
        "destination": state["destination"],
        "flight": flight,
        "hotel": hotel,
    })
    step("⚡", "ACT", f"Itinerary built:\n{itinerary}")
    return {
        "flight_cost": flight["price"],
        "hotel_cost":  hotel["total"],
        "itinerary":   itinerary,
    }


def travel_observe(state: TravelState) -> dict:
    total   = state["flight_cost"] + state["hotel_cost"]
    within  = total <= state["budget"]
    step("🔍", "OBSERVE", f"Total=${total}, Budget=${state['budget']}, OK={within}")
    return {}


def travel_human_review(state: TravelState) -> Command:
    """
    ── HUMAN-IN-THE-LOOP CHECKPOINT ──────────────────────────────
    The graph pauses here.  A real human reviews the itinerary and
    decides to approve or ask the agent to find a cheaper option.

    In production replace input() with:
      interrupt()   ← suspends graph; resume via graph.invoke() later
    ───────────────────────────────────────────────────────────────
    """
    print("\n" + "─" * 50)
    print("  🔔  HUMAN REVIEW — Travel Plan")
    print("─" * 50)
    print(state["itinerary"])
    print(f"\n  Budget: ${state['budget']}")

    answer = input("\n  Approve this trip? [y=yes / n=find cheaper]: ").strip().lower()
    attempts = state.get("attempts", 1)1
    if answer == "y":
        print("  ✅  Approved! Booking now …")
        return Command(goto="travel_book", update={"approved": True})

    # ── Loop guard: stop after MAX_ATTEMPTS ───────────────────────
    if state.get("attempts", 1) >= MAX_ATTEMPTS:
        print(f"  ⛔  Max attempts ({MAX_ATTEMPTS}) reached. Stopping.")
        return Command(goto=END, update={"approved": False})
    attempts = attempts + 1
    print("  🔄  Searching for a cheaper option …")
    return Command(goto="travel_act", update={"approved": False, "attempts": attempts})


def travel_book(state: TravelState) -> dict:
    step("🎉", "BOOKED", "Trip confirmed! Confirmation email sent.")
    return {}


# ── Graph assembly ────────────────────────────────────────────────────────────
def build_travel_graph():
    g = StateGraph(TravelState)
    for name, fn in [
        ("travel_perceive",     travel_perceive),
        ("travel_reason",       travel_reason),
        ("travel_act",          travel_act),
        ("travel_observe",      travel_observe),
        ("travel_human_review", travel_human_review),
        ("travel_book",         travel_book),
    ]:
        g.add_node(name, fn)

    g.set_entry_point("travel_perceive")
    g.add_edge("travel_perceive",     "travel_reason")
    g.add_edge("travel_reason",       "travel_act")
    g.add_edge("travel_act",          "travel_observe")
    g.add_edge("travel_observe",      "travel_human_review")
    # travel_human_review routes dynamically via Command()
    g.add_edge("travel_book",         END)
    return g.compile(checkpointer=MemorySaver())


def run_travel_agent():
    banner("EXAMPLE 1 — Travel Agent  ✈")
    graph = build_travel_graph()
    config = {"configurable": {"thread_id": "travel-1"}}
    initial = {
        "messages":    [HumanMessage(content="Book me a 3-day trip to Paris under $2000")],
        "destination": "Paris",
        "budget":      2000.0,
        "flight_cost": 0.0,
        "hotel_cost":  0.0,
        "itinerary":   "",
        "approved":    False,
        "attempts":    0,
    }
    for _ in graph.stream(initial, config, stream_mode="values"):
        pass   # nodes print their own output


# ══════════════════════════════════════════════════════════════════════════════
# EXAMPLE 2 — FINANCIAL ANALYST AGENT
# ══════════════════════════════════════════════════════════════════════════════

class FinanceState(TypedDict):
    messages:       Annotated[list, add_messages]
    ticker:         str
    price:          float
    change_pct:     float
    recommendation: str
    reasoning:      str
    decision:       str   # "execute" | "skip" | "pending"
    attempts:       int


@tool
def get_stock_price(ticker: str) -> dict:
    """Fetch latest stock quote."""
    return {
        "ticker":     ticker,
        "price":      round(random.uniform(100, 500), 2),
        "change_pct": round(random.uniform(-5, 8), 2),
    }


@tool
def analyze_stock(ticker: str, price: float, change_pct: float) -> dict:
    """Basic momentum analysis → BUY / HOLD / SELL."""
    if change_pct > 3:
        return {"recommendation": "BUY",
                "reasoning": f"{ticker} +{change_pct}% — strong momentum."}
    if change_pct < -3:
        return {"recommendation": "SELL",
                "reasoning": f"{ticker} {change_pct}% — weakness detected."}
    return {"recommendation": "HOLD",
            "reasoning": f"{ticker} flat at ${price}. Wait for clearer signal."}


def finance_perceive(state: FinanceState) -> dict:
    step("👁", "PERCEIVE", f"Query: Should I trade {state['ticker']}?")
    return {"attempts": state.get("attempts", 0) + 1}


def finance_reason(state: FinanceState) -> dict:
    step("🧠", "REASON", "Plan: fetch price → analyse → recommend")
    return {}


def finance_act(state: FinanceState) -> dict:
    step("⚡", "ACT", f"Fetching {state['ticker']} market data …")
    quote    = get_stock_price.invoke({"ticker": state["ticker"]})
    analysis = analyze_stock.invoke({
        "ticker":     state["ticker"],
        "price":      quote["price"],
        "change_pct": quote["change_pct"],
    })
    step("⚡", "ACT",
         f"Price=${quote['price']}, Change={quote['change_pct']}% → {analysis['recommendation']}")
    return {
        "price":          quote["price"],
        "change_pct":     quote["change_pct"],
        "recommendation": analysis["recommendation"],
        "reasoning":      analysis["reasoning"],
    }


def finance_observe(state: FinanceState) -> dict:
    step("🔍", "OBSERVE",
         f"Recommendation ready: {state['recommendation']}. Sending to human.")
    return {}


def finance_human_review(state: FinanceState) -> Command:
    """
    ── HUMAN-IN-THE-LOOP CHECKPOINT ──────────────────────────────
    No trade is ever executed without explicit human sign-off.
    Human can also request a re-analysis (counts toward MAX_ATTEMPTS).
    ───────────────────────────────────────────────────────────────
    """
    print("\n" + "─" * 50)
    print("  🔔  HUMAN REVIEW — Trade Authorisation")
    print("─" * 50)
    print(f"  Ticker:        {state['ticker']}")
    print(f"  Price:         ${state['price']}")
    print(f"  Daily Change:  {state['change_pct']}%")
    print(f"  Verdict:       {state['recommendation']}")
    print(f"  Reason:        {state['reasoning']}")

    answer = input(
        "\n  Decision? [y=execute / n=skip / r=re-analyse]: "
    ).strip().lower()

    if answer == "y":
        return Command(goto="finance_execute", update={"decision": "execute"})

    if answer == "r":
        if state.get("attempts", 1) >= MAX_ATTEMPTS:
            print(f"  ⛔  Max re-analyses ({MAX_ATTEMPTS}) reached. Aborting.")
            return Command(goto=END, update={"decision": "skip"})
        print("  🔄  Re-running analysis …")
        return Command(goto="finance_act", update={"decision": "pending"})

    print("  ⏭  Trade skipped by human.")
    return Command(goto=END, update={"decision": "skip"})


def finance_execute(state: FinanceState) -> dict:
    step("💸", "EXECUTE",
         f"{state['recommendation']} order for {state['ticker']} @ ${state['price']} placed!")
    return {}


def build_finance_graph():
    g = StateGraph(FinanceState)
    for name, fn in [
        ("finance_perceive",     finance_perceive),
        ("finance_reason",       finance_reason),
        ("finance_act",          finance_act),
        ("finance_observe",      finance_observe),
        ("finance_human_review", finance_human_review),
        ("finance_execute",      finance_execute),
    ]:
        g.add_node(name, fn)

    g.set_entry_point("finance_perceive")
    g.add_edge("finance_perceive",    "finance_reason")
    g.add_edge("finance_reason",      "finance_act")
    g.add_edge("finance_act",         "finance_observe")
    g.add_edge("finance_observe",     "finance_human_review")
    g.add_edge("finance_execute",     END)
    return g.compile(checkpointer=MemorySaver())


def run_finance_agent():
    banner("EXAMPLE 2 — Financial Analyst Agent  📈")
    graph = build_finance_graph()
    config = {"configurable": {"thread_id": "finance-1"}}
    initial = {
        "messages":       [HumanMessage(content="Should I buy AAPL today?")],
        "ticker":         "AAPL",
        "price":          0.0,
        "change_pct":     0.0,
        "recommendation": "",
        "reasoning":      "",
        "decision":       "pending",
        "attempts":       0,
    }
    for _ in graph.stream(initial, config, stream_mode="values"):
        pass


# ══════════════════════════════════════════════════════════════════════════════
# EXAMPLE 3 — DEVOPS AGENT
# ══════════════════════════════════════════════════════════════════════════════

class DevOpsState(TypedDict):
    messages:     Annotated[list, add_messages]
    alert:        str
    diagnosis:    str
    fix_plan:     str
    fix_applied:  bool
    site_healthy: bool
    approved:     bool
    attempts:     int


@tool
def read_server_logs() -> dict:
    """Pull the latest critical error from server logs."""
    return random.choice([
        {"error": "OOMKilled",        "service": "postgres",   "severity": "critical"},
        {"error": "CrashLoopBackOff", "service": "api-server", "severity": "high"},
        {"error": "DiskPressure",     "service": "node-1",     "severity": "medium"},
    ])


@tool
def diagnose_issue(error: str, service: str) -> dict:
    """Map error to root cause and suggested remediation."""
    plans = {
        "OOMKilled":        f"Restart {service} and raise memory limit to 2Gi",
        "CrashLoopBackOff": f"Roll {service} back to last stable image",
        "DiskPressure":     f"Prune old logs and expand disk on {service}",
    }
    return {"root_cause": error, "service": service,
            "fix": plans.get(error, f"Restart {service}")}


@tool
def apply_fix(fix: str) -> dict:
    """Apply the remediation action to the cluster."""
    success = random.random() > 0.2   # 80 % success rate in this stub
    return {"fix": fix, "success": success}


@tool
def health_check() -> dict:
    """Verify whether the service is back online."""
    return {"healthy": random.random() > 0.15,
            "response_ms": random.randint(50, 2000)}


def devops_perceive(state: DevOpsState) -> dict:
    step("👁", "PERCEIVE", f"Alert: {state['alert']}")
    step("👁", "PERCEIVE", "Reading server logs …")
    log = read_server_logs.invoke({})
    diag = f"Error={log['error']}, Service={log['service']}, Severity={log['severity']}"
    step("👁", "PERCEIVE", diag)
    return {"diagnosis": diag, "attempts": state.get("attempts", 0) + 1}


def devops_reason(state: DevOpsState) -> dict:
    step("🧠", "REASON", f"Diagnosing: {state['diagnosis']}")
    parts   = state["diagnosis"].split(", ")
    error   = parts[0].split("=")[1]
    service = parts[1].split("=")[1]
    result  = diagnose_issue.invoke({"error": error, "service": service})
    step("🧠", "REASON", f"Fix plan: {result['fix']}")
    return {"fix_plan": result["fix"]}


def devops_human_review(state: DevOpsState) -> Command:
    """
    ── HUMAN-IN-THE-LOOP CHECKPOINT ──────────────────────────────
    Destructive ops (restart, rollback, disk wipe) MUST have a human
    approve before touching production.  This is the safety gate.
    ───────────────────────────────────────────────────────────────
    """
    print("\n" + "─" * 50)
    print("  🔔  HUMAN APPROVAL — Production Change")
    print("─" * 50)
    print(f"  Alert:     {state['alert']}")
    print(f"  Diagnosis: {state['diagnosis']}")
    print(f"  Fix:       {state['fix_plan']}")
    print("\n  ⚠️   This modifies a PRODUCTION system.")

    answer = input("\n  Approve? [y/n]: ").strip().lower()

    if answer == "y":
        return Command(goto="devops_act", update={"approved": True})
    print("  🚫  Rejected. Escalating to on-call engineer.")
    return Command(goto=END, update={"approved": False})


def devops_act(state: DevOpsState) -> dict:
    step("⚡", "ACT", f"Applying: {state['fix_plan']} …")
    result = apply_fix.invoke({"fix": state["fix_plan"]})
    msg = "Success ✅" if result["success"] else "Failed ❌ — will observe"
    step("⚡", "ACT", msg)
    return {"fix_applied": result["success"]}


def devops_observe(state: DevOpsState) -> dict:
    step("🔍", "OBSERVE", "Running health check …")
    result = health_check.invoke({})
    step("🔍", "OBSERVE",
         f"Healthy={result['healthy']}, Latency={result['response_ms']}ms")
    return {"site_healthy": result["healthy"]}


def devops_router(state: DevOpsState) -> Literal["devops_done", "devops_reason", "__end__"]:
    """
    Post-observe decision:
    ✅ Healthy          → close incident
    🔄 Not healthy      → re-reason and retry (if under MAX_ATTEMPTS)
    ⛔ Max attempts hit → stop and escalate (LOOP GUARD)
    """
    if state["site_healthy"]:
        return "devops_done"
    if state.get("attempts", 1) >= MAX_ATTEMPTS:
        step("⛔", "LOOP GUARD",
             f"Still unhealthy after {MAX_ATTEMPTS} attempts. Escalating!")
        return "__end__"
    step("🔄", "RETRY",
         f"Attempt {state['attempts']}/{MAX_ATTEMPTS}. Re-diagnosing …")
    return "devops_reason"


def devops_done(state: DevOpsState) -> dict:
    step("🎉", "RESOLVED", "Service healthy. Incident closed. Team notified.")
    return {}


def build_devops_graph():
    g = StateGraph(DevOpsState)
    for name, fn in [
        ("devops_perceive",     devops_perceive),
        ("devops_reason",       devops_reason),
        ("devops_human_review", devops_human_review),
        ("devops_act",          devops_act),
        ("devops_observe",      devops_observe),
        ("devops_done",         devops_done),
    ]:
        g.add_node(name, fn)

    g.set_entry_point("devops_perceive")
    g.add_edge("devops_perceive",      "devops_reason")
    g.add_edge("devops_reason",        "devops_human_review")
    # human_review routes dynamically via Command()
    g.add_edge("devops_act",           "devops_observe")
    g.add_conditional_edges(
        "devops_observe",
        devops_router,
        {
            "devops_done":   "devops_done",
            "devops_reason": "devops_reason",   # loop back (capped by attempts)
            "__end__":       END,
        },
    )
    g.add_edge("devops_done", END)
    return g.compile(checkpointer=MemorySaver())


def run_devops_agent():
    banner("EXAMPLE 3 — DevOps Agent  🛠")
    graph = build_devops_graph()
    config = {"configurable": {"thread_id": "devops-1"}}
    initial = {
        "messages":     [HumanMessage(content="ALERT: Website down! Fix it!")],
        "alert":        "HTTP 503 on all endpoints.",
        "diagnosis":    "",
        "fix_plan":     "",
        "fix_applied":  False,
        "site_healthy": False,
        "approved":     False,
        "attempts":     0,
    }
    for _ in graph.stream(initial, config, stream_mode="values"):
        pass


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LangGraph Human-in-the-Loop Demo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1  →  Travel Agent
  2  →  Financial Analyst Agent
  3  →  DevOps Agent
  (Enter) → Run all three
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")

    choice = input("Pick [1/2/3] or Enter for all: ").strip()

    runners = {
        "1": run_travel_agent,
        "2": run_finance_agent,
        "3": run_devops_agent,
    }

    if choice in runners:
        runners[choice]()
    else:
        run_travel_agent()
        run_finance_agent()
        run_devops_agent()

    print("\n✅  Demo complete.\n")