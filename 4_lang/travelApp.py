"""

<h1>RAZ Systems </h1>

TRAVEL BUDGET FINDER — Gradio App
===================================
- Enter destination, dates, budget
- Searches real flights + hotels via Serper/Google
- LLM extracts prices and builds itinerary
- Sends Pushover notification if under budget
- Retries automatically with cheaper options if over budget
"""

import os
import re
import json
import requests
import gradio as gr
from datetime import date, timedelta
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

# ─────────────────────────────────────────────────────
# ENV
# ─────────────────────────────────────────────────────

load_dotenv()

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY  = os.getenv("SERPER_API_KEY")
PUSHOVER_USER   = os.getenv("PUSHOVER_USER")
PUSHOVER_TOKEN  = os.getenv("PUSHOVER_TOKEN")

MAX_ATTEMPTS = 3

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ─────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────

def serper_search(query: str) -> str:
    response = requests.post(
        "https://google.serper.dev/search",
        json={"q": query},
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        timeout=10
    )
    results = []
    for item in response.json().get("organic", [])[:4]:
        results.append(f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}")
    return "\n\n".join(results) or "No results found."


@tool
def search_flights(destination: str, departure_date: str, return_date: str, preferences: str = "") -> str:
    """Search for flight prices to a destination for specific dates."""
    query = f"flights to {destination} departing {departure_date} returning {return_date} price {preferences}"
    return serper_search(query)


@tool
def search_hotels(destination: str, checkin_date: str, checkout_date: str, preferences: str = "") -> str:
    """Search for hotel prices in a destination for specific dates."""
    query = f"hotels in {destination} check in {checkin_date} check out {checkout_date} price per night {preferences}"
    return serper_search(query)


@tool
def send_pushover(message: str) -> str:
    """Send a Pushover push notification."""
    if not PUSHOVER_USER or not PUSHOVER_TOKEN:
        return "Pushover not configured — skipping notification."
    response = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={"token": PUSHOVER_TOKEN, "user": PUSHOVER_USER, "message": message},
        timeout=10
    )
    return f"Notification sent. Status: {response.status_code}"


tools = [search_flights, search_hotels, send_pushover]
tools_by_name = {t.name: t for t in tools}
llm_with_tools = llm.bind_tools(tools)


# ─────────────────────────────────────────────────────
# CORE SEARCH LOGIC
# ─────────────────────────────────────────────────────

def run_tool_calls(ai_message) -> list:
    results = []
    for call in ai_message.tool_calls:
        tool_fn = tools_by_name[call["name"]]
        output = tool_fn.invoke(call["args"])
        results.append(ToolMessage(content=str(output), tool_call_id=call["id"]))
    return results


def search_trip(destination, departure_date, return_date, budget, attempt, log_fn):
    nights = (return_date - departure_date).days

    cheaper = ""
    if attempt > 1:
        cheaper = "budget economy cheapest available"

    log_fn(f"\n🔍 Attempt {attempt} — searching flights & hotels...")

    prompt = f"""
You are a travel search agent.

Trip details:
- Destination: {destination}
- Departure: {departure_date.strftime('%B %d, %Y')}
- Return: {return_date.strftime('%B %d, %Y')}
- Nights: {nights}
- Budget: ${budget} total
- Attempt: {attempt} of {MAX_ATTEMPTS} {"(previous attempt was over budget — find cheaper options)" if attempt > 1 else ""}

Steps:
1. Call search_flights with the exact dates{' and preferences="budget economy cheapest"' if attempt > 1 else ''}.
2. Call search_hotels with the exact dates{' and preferences="budget hostel cheapest"' if attempt > 1 else ''}.
3. From the results, estimate realistic USD costs:
   - flight_cost: round trip total per person
   - hotel_cost: price per night × {nights} nights
   - total_cost: flight_cost + hotel_cost
4. Write a day-by-day itinerary with REAL dates (not "Day 1").

Return ONLY this JSON (no markdown, no extra text):
{{
  "flight_cost": <number>,
  "hotel_cost": <number>,
  "total_cost": <number>,
  "flight_summary": "<airline, rough price, departure info>",
  "hotel_summary": "<hotel name or type, price per night>",
  "itinerary": "<full day-by-day itinerary with real dates>"
}}
"""

    messages = [HumanMessage(content=prompt)]

    while True:
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for call in response.tool_calls:
            log_fn(f"  🔧 Calling {call['name']}({list(call['args'].values())[0]}...)")

        tool_results = run_tool_calls(response)
        messages.extend(tool_results)

    # Parse JSON
    try:
        # Strip markdown fences if LLM added them
        text = response.content.strip()
        text = re.sub(r"```json|```", "", text).strip()
        data = json.loads(text)
    except Exception:
        data = {
            "flight_cost": 9999,
            "hotel_cost": 9999,
            "total_cost": 9999,
            "flight_summary": "Could not extract",
            "hotel_summary": "Could not extract",
            "itinerary": response.content
        }

    return data


# ─────────────────────────────────────────────────────
# MAIN APP FUNCTION
# ─────────────────────────────────────────────────────

def find_trip(destination, departure_date, return_date, budget):

    if not destination:
        yield "⚠️ Please enter a destination.", "", "", ""
        return

    if departure_date >= return_date:
        yield "⚠️ Return date must be after departure date.", "", "", ""
        return

    logs = []
    result_box = ""
    itinerary_box = ""
    status_box = ""

    def log(msg):
        logs.append(msg)

    log(f"🚀 Starting search for {destination}")
    log(f"📅 {departure_date.strftime('%b %d')} → {return_date.strftime('%b %d, %Y')}")
    log(f"💰 Budget: ${budget}")

    yield "\n".join(logs), "", "", "🔍 Searching..."

    final_data = None

    for attempt in range(1, MAX_ATTEMPTS + 1):

        data = search_trip(destination, departure_date, return_date, budget, attempt, log)

        log(f"\n✈️  Flight: ${data['flight_cost']}  |  🏨 Hotel: ${data['hotel_cost']}  |  💰 Total: ${data['total_cost']}")

        yield "\n".join(logs), "", "", f"Attempt {attempt}: ${data['total_cost']} total..."

        if data["total_cost"] <= budget:
            log(f"✅ Within budget!")
            final_data = data
            break
        else:
            log(f"❌ Over budget by ${data['total_cost'] - budget:.0f}")
            if attempt < MAX_ATTEMPTS:
                log(f"🔄 Retrying with cheaper options...")
                yield "\n".join(logs), "", "", f"Over budget — retrying..."
            else:
                log(f"⛔ Could not find a trip within ${budget} after {MAX_ATTEMPTS} attempts.")
                final_data = data  # Show best result anyway

    # Build result display
    within = final_data["total_cost"] <= budget

    result_box = f"""{'✅ WITHIN BUDGET' if within else '⚠️ BEST FOUND (over budget)'}

🗺️  Destination:   {destination}
📅  Dates:         {departure_date.strftime('%b %d')} → {return_date.strftime('%b %d, %Y')}  ({(return_date - departure_date).days} nights)

✈️  Flight:        ${final_data['flight_cost']}
               {final_data['flight_summary']}

🏨  Hotel:         ${final_data['hotel_cost']}
               {final_data['hotel_summary']}

💰  Total Cost:    ${final_data['total_cost']}
🎯  Your Budget:   ${budget}
{'💚 Savings:        $' + str(budget - final_data['total_cost']) if within else '🔴 Over by:        $' + str(final_data['total_cost'] - budget)}
"""

    itinerary_box = final_data["itinerary"]

    # Send notification if within budget
    if within:
        log("\n📲 Sending Pushover notification...")
        notification = (
            f"✈️ Trip Approved: {destination}\n"
            f"📅 {departure_date.strftime('%b %d')} - {return_date.strftime('%b %d, %Y')}\n"
            f"💰 Total: ${final_data['total_cost']} (budget: ${budget})\n\n"
            f"✈️ {final_data['flight_summary']}\n"
            f"🏨 {final_data['hotel_summary']}"
        )
        result = send_pushover.invoke({"message": notification})
        log(f"  → {result}")
        status_box = "✅ Trip found within budget! Notification sent."
    else:
        status_box = f"⚠️ Best option found: ${final_data['total_cost']} (${final_data['total_cost'] - budget} over budget)"

    yield "\n".join(logs), result_box, itinerary_box, status_box


# ─────────────────────────────────────────────────────
# GRADIO UI
# ─────────────────────────────────────────────────────

today = date.today()
default_departure = today + timedelta(days=30)
default_return    = today + timedelta(days=37)

with gr.Blocks(title="✈️ Travel Budget Finder", theme=gr.themes.Soft()) as app:

    gr.Markdown("""
    # ✈️ Travel Budget Finder
    Search for flights & hotels within your budget. Gets notified automatically when a deal is found.
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🗺️ Trip Details")
            destination   = gr.Textbox(label="Destination", placeholder="e.g. Paris, Tokyo, New York", value="Paris")
            departure     = gr.Textbox(label="Departure Date (YYYY-MM-DD)", value=str(default_departure), placeholder="2026-06-15")
            return_date   = gr.Textbox(label="Return Date (YYYY-MM-DD)",    value=str(default_return),    placeholder="2026-06-22")
            budget        = gr.Number(label="Total Budget (USD $)", value=1500, minimum=100, maximum=20000, step=50)
            search_btn    = gr.Button("🔍 Find My Trip", variant="primary", size="lg")
            status        = gr.Textbox(label="Status", interactive=False, lines=1)

        with gr.Column(scale=2):
            gr.Markdown("### 💰 Price Summary")
            result_box    = gr.Textbox(label="Results", interactive=False, lines=14)
            gr.Markdown("### 📅 Itinerary")
            itinerary_box = gr.Textbox(label="Day-by-Day Plan", interactive=False, lines=12)

    with gr.Accordion("🪵 Search Log", open=False):
        log_box = gr.Textbox(label="Log", interactive=False, lines=15)

    def handle_search(dest, dep, ret, bud):
        try:
            dep_date = date.fromisoformat(dep.strip())
            ret_date = date.fromisoformat(ret.strip())
        except ValueError:
            yield "", "", "", "⚠️ Invalid date format. Use YYYY-MM-DD (e.g. 2026-06-15)"
            return
        for logs, result, itinerary, status in find_trip(dest, dep_date, ret_date, int(bud)):
            yield logs, result, itinerary, status

    search_btn.click(
        fn=handle_search,
        inputs=[destination, departure, return_date, budget],
        outputs=[log_box, result_box, itinerary_box, status]
    )

if __name__ == "__main__":
    app.launch()