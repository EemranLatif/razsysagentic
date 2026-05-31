# 🤖 AI Agent Patterns — Three Versions Compared

<h1>RAZ Systems </h1>

A guide for understanding how LLM-powered agents evolve from simple scripts  
to true autonomous tool-calling systems.

---

## The Three Versions at a Glance

| | Version 1 | Version 2 | Version 3 |
|---|---|---|---|
| **Name** | Direct Functions | Tool Calling (You Control) | Tool Calling (LLM Controls) |
| **Who decides what to call?** | You (hardcoded) | You (hardcoded) | The LLM |
| **Tools defined with `@tool`?** | ❌ | ✅ | ✅ |
| **LLM bound to tools?** | ❌ | ✅ (but bypassed) | ✅ (fully used) |
| **Agentic loop?** | ❌ | ❌ | ✅ |
| **Predictable?** | ✅ Very | ✅ Very | ⚠️ Less so |
| **Flexible?** | ❌ | ❌ | ✅ |
| **Best for** | Fixed pipelines | Learning tool syntax | Open-ended agents |

---

## Version 1 — Direct Functions (Your Original Code)

```python
# You call the function directly — no LLM involvement
flight_results = search_web(f"cheap flights to {destination}")
hotel_results  = search_web(f"cheap hotels in {destination}")

flight_cost = random.randint(500, 1500)   # simulated
hotel_cost  = random.randint(300, 1200)
```

### What's happening
- Functions are plain Python — `search_web()` is just a `requests.post()`
- You decide the order: always flights, then hotels, then LLM writes itinerary
- Prices were simulated with `random.randint()` (not real data)
- The LLM is only used at the end to format the itinerary

### Technical characteristics
- **Execution flow:** Linear, deterministic, you control everything
- **LLM role:** Writer only — given data, produces text
- **State updates:** Explicit — you set `flight_cost`, `hotel_cost` in the return dict
- **Retry logic:** Simple `if/else` with hardcoded hints (`"cheap economy"`, `"budget hostel"`)

### Pros
- Easy to read, debug, and teach
- Fast — no extra LLM calls to decide what to do
- Fully predictable — same input → same execution path

### Cons
- Not flexible — adding a new tool means rewriting the node
- Prices were fake (`random.randint`) — not real search results
- LLM has no agency — it can't decide to search differently

### When to use
Fixed pipelines where the sequence never changes.  
Example: always search flights → always search hotels → always summarize.

---

## Version 2 — Tool Calling, You Control the Loop

```python
@tool
def search_flights(destination: str, departure_date: str, ...) -> str:
    """Search for flight prices to a destination for specific dates."""
    ...

# Tools are defined but YOU still call them directly
flight_results = search_flights.invoke({
    "destination": destination,
    "departure_date": str(departure_date),
    ...
})

# Then pass results to a plain LLM (no tools bound)
response = llm.invoke(prompt_with_results)
```

### What's happening
- Functions are decorated with `@tool` — they have names, docstrings, and typed schemas
- But you still decide when and how to call them — the LLM doesn't pick the tools
- `llm_with_tools` is set up but the actual search calls bypass it
- Results are injected into the prompt manually

### Technical characteristics
- **Execution flow:** Still linear, you control order
- **LLM role:** Writer + cost estimator — given raw search snippets, extracts prices and writes itinerary
- **Tool schema:** Exists (OpenAI can see it) but not used for routing
- **`@tool` benefit here:** Consistent interface, type hints, reusable across projects

### Pros
- Cleaner than Version 1 — tools are proper, typed, documented
- No unpredictable LLM routing — you know exactly what runs
- Good stepping stone for understanding tool syntax

### Cons
- `@tool` + `bind_tools` is set up but not fully used — misleading
- Still rigid — adding a new search type requires code changes
- LLM still has no agency over the search strategy

### When to use
When you want the structure and reusability of tools, but the  
workflow is fixed and you don't need the LLM to make routing decisions.

---

## Version 3 — Tool Calling, LLM Controls the Loop

```python
@tool
def search_flights(...) -> str: ...

@tool
def search_hotels(...) -> str: ...

llm_with_tools = llm.bind_tools(tools)  # LLM is now aware of tools

# Agentic loop — LLM decides what to call
messages = [HumanMessage(content=prompt)]

while True:
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    if not response.tool_calls:   # LLM is done
        break

    tool_results = run_tool_calls(response)  # execute what LLM requested
    messages.extend(tool_results)            # feed results back
```

### What's happening
- The LLM receives the prompt and a list of available tools (their names + schemas)
- The LLM returns `tool_calls` — structured JSON like:
  ```json
  {"name": "search_flights", "args": {"destination": "Paris", "departure_date": "2026-06-15"}}
  ```
- Your code executes those calls and returns the results back to the LLM
- The LLM reads the results and either calls more tools or writes the final answer
- This loop continues until `response.tool_calls` is empty

### Technical characteristics
- **Execution flow:** Non-linear — LLM drives the sequence
- **LLM role:** Planner + executor — decides which tools, in what order, with what args
- **Message history:** Full conversation passed on every call (stateless API, stateful by design)
- **Tool schema:** Sent to OpenAI as JSON Schema — LLM reads docstrings to decide when to call
- **Retry logic:** Expressed in the prompt (`"previous attempt over budget — find cheaper"`)

### How tool calling works under the hood

When you call `llm.bind_tools(tools)`, LangChain converts your `@tool` functions  
into OpenAI's function-calling format and sends them in the API request:

```json
{
  "model": "gpt-4o-mini",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_flights",
        "description": "Search for flight prices to a destination for specific dates.",
        "parameters": {
          "type": "object",
          "properties": {
            "destination": {"type": "string"},
            "departure_date": {"type": "string"}
          }
        }
      }
    }
  ]
}
```

The LLM responds with either text OR a tool call — never both at the same time  
(until it has all the information it needs).

### Pros
- Truly flexible — LLM can decide to search differently on retry
- Adding a new tool (e.g. `search_car_rental`) requires zero logic changes — just add `@tool`
- Closer to how production agents work (LangChain, AutoGPT, OpenAI Assistants)

### Cons
- Harder to debug — you don't know in advance what the LLM will call
- More expensive — extra LLM calls for tool routing
- Can be overkill for fixed workflows

### When to use
When the LLM needs real autonomy — open-ended tasks, dynamic tool selection,  
or workflows that vary based on context.

---

## The Core Question: Who Is In Charge?

```
Version 1:  YOU  →  function()  →  LLM writes output
Version 2:  YOU  →  tool.invoke()  →  LLM writes output
Version 3:  YOU  →  LLM  →  tool()  →  LLM  →  tool()  →  LLM writes output
                    ↑ LLM is now in the driver's seat
```

---

## Best Practices

### 1. Match the pattern to the workflow

| Workflow type | Use |
|---|---|
| Always same steps, same order | Version 1 — direct functions |
| Fixed steps, want clean tool interface | Version 2 — tools, you control |
| Dynamic, open-ended, LLM decides | Version 3 — full agentic loop |

### 2. Write good `@tool` docstrings — the LLM reads them

```python
# ❌ Bad — LLM doesn't know when to use this
@tool
def search_flights(destination, departure_date, return_date):
    ...

# ✅ Good — LLM knows exactly what this does and when to call it
@tool
def search_flights(destination: str, departure_date: str, return_date: str) -> str:
    """Search for round-trip flight prices to a destination.
    Use this when the user wants to find flights for specific travel dates.
    Returns price information and airline options."""
    ...
```

### 3. Always type your tool arguments

The LLM uses the type hints to generate valid arguments.  
Without them, it may pass wrong types and cause runtime errors.

### 4. The agentic loop is not always needed

If your tools are always called in the same fixed order,  
call them directly. The loop adds complexity without benefit.

### 5. Keep state explicit in LangGraph

LangGraph passes state between nodes as a typed dict.  
Always return only what changed — not the whole state:

```python
# ✅ Return only what this node changed
return {
    "total_cost": 1200,
    "itinerary": "June 15 — Arrive in Paris..."
}

# ❌ Don't re-return unchanged fields
return {
    "destination": state["destination"],  # unnecessary
    "budget": state["budget"],            # unnecessary
    "total_cost": 1200,
    "itinerary": "..."
}
```

### 6. Conditional edges take a function, not a string

```python
# ✅ Correct — pass the function object
graph.add_conditional_edges("observe", decide)

# ❌ Wrong — this looks for a node named "decide"
graph.add_conditional_edges("observe", "decide")
```

The function receives state and returns a string (the next node name).  
The string it returns is what gets quoted — not the function itself.

---

## Summary for Students

> Start with Version 1. Understand the flow.  
> Move to Version 2 when you want clean, reusable tool interfaces.  
> Only use Version 3 when the LLM genuinely needs to decide what to do next.  
>
> Most real production agents are somewhere between Version 2 and 3 —  
> structured enough to be reliable, flexible enough to handle variation.

---

## 🌍 Real-World APIs — What to Use in Production

The app we built uses Serper (Google snippets) and simulated prices.  
Here is what a production travel agent would use instead, and why.

---

### ✈️ Flights

#### Amadeus (Recommended for students)
- **What it gives you:** Real flight availability, prices, airline codes, departure times, seat class
- **Free tier:** Yes — sandbox environment with real data structure, no credit card
- **Endpoint used:** `GET /v2/shopping/flight-offers`
- **Docs:** https://developers.amadeus.com
- **Why it's best for learning:** Free, well-documented, returns structured JSON you can parse directly

```python
@tool
def search_flights(origin: str, destination: str, departure_date: str) -> str:
    """Search real flight offers using Amadeus API."""
    from amadeus import Client
    amadeus = Client(
        client_id=os.getenv("AMADEUS_CLIENT_ID"),
        client_secret=os.getenv("AMADEUS_CLIENT_SECRET")
    )
    response = amadeus.shopping.flight_offers_search.get(
        originLocationCode=origin,        # e.g. "JFK"
        destinationLocationCode=destination,  # e.g. "CDG"
        departureDate=departure_date,     # e.g. "2026-06-15"
        adults=1,
        max=5
    )
    offers = response.data
    results = []
    for offer in offers:
        price = offer["price"]["total"]
        carrier = offer["validatingAirlineCodes"][0]
        results.append(f"{carrier} — ${price}")
    return "\n".join(results)
```

#### SerpApi — Google Flights
- **What it gives you:** Google Flights results with real prices, scraped live
- **Free tier:** 100 searches/month
- **Best for:** When you want exactly what a user sees on Google Flights
- **Docs:** https://serpapi.com/google-flights-api

#### Skyscanner
- **What it gives you:** Aggregated prices across hundreds of airlines
- **Note:** API access requires a partnership agreement — not free for individuals
- **Better alternative for students:** Use Amadeus instead

---

### 🏨 Hotels

#### Amadeus Hotel Search (same SDK)
- **Endpoint:** `GET /v3/shopping/hotel-offers`
- **Free tier:** Yes — same sandbox as flights
- **Returns:** Hotel name, address, room types, price per night, cancellation policy

```python
@tool
def search_hotels(city_code: str, checkin_date: str, checkout_date: str) -> str:
    """Search real hotel offers using Amadeus API."""
    from amadeus import Client
    amadeus = Client(
        client_id=os.getenv("AMADEUS_CLIENT_ID"),
        client_secret=os.getenv("AMADEUS_CLIENT_SECRET")
    )
    # Step 1: get hotel IDs in the city
    hotels = amadeus.reference_data.locations.hotels.by_city.get(cityCode=city_code)
    hotel_ids = [h["hotelId"] for h in hotels.data[:10]]

    # Step 2: get offers for those hotels
    offers = amadeus.shopping.hotel_offers_search.get(
        hotelIds=hotel_ids,
        checkInDate=checkin_date,
        checkOutDate=checkout_date,
        adults=1
    )
    results = []
    for offer in offers.data:
        name  = offer["hotel"]["name"]
        price = offer["offers"][0]["price"]["total"]
        results.append(f"{name} — ${price} total")
    return "\n".join(results)
```

#### Booking.com API (via RapidAPI)
- **What it gives you:** Real hotel inventory, reviews, photos, cancellation policies
- **Access:** Through RapidAPI marketplace
- **Docs:** https://rapidapi.com/apidojo/api/booking

---

### 📲 Notifications

#### Pushover (what we used)
- **Cost:** $5 one-time per platform (iOS or Android)
- **Best for:** Personal projects, quick demos
- **Limitation:** Only works with the Pushover app installed

#### Twilio SMS
- **What it gives you:** Real SMS to any phone number, no app needed
- **Free tier:** Trial credits on signup
- **Docs:** https://www.twilio.com/docs/sms

```python
@tool
def send_sms(message: str, to_number: str) -> str:
    """Send an SMS notification via Twilio."""
    from twilio.rest import Client
    client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
    client.messages.create(
        body=message,
        from_=os.getenv("TWILIO_PHONE"),
        to=to_number
    )
    return "SMS sent."
```

#### SendGrid Email
- **What it gives you:** Transactional email with HTML formatting
- **Free tier:** 100 emails/day forever
- **Best for:** Sending a formatted itinerary with clickable links
- **Docs:** https://docs.sendgrid.com

---

### 🗺️ Additional Tools Worth Adding

| Tool | API | What it adds |
|---|---|---|
| Car rental | Amadeus `/shopping/transfer-offers` | Complete door-to-door trip |
| Weather forecast | OpenWeatherMap (free) | "Pack an umbrella — it will rain" |
| Currency conversion | ExchangeRate-API (free) | Show prices in user's local currency |
| Points of interest | Google Places API | Real attractions with ratings |
| Travel advisories | travel.state.gov (free, no key) | Safety warnings for the destination |
| Visa requirements | Sherpa API | "You need a visa for this destination" |

---

## 🏗️ How to Enhance the App — Step by Step

### Step 1 — Replace Serper with Amadeus (biggest impact)

This is the single most important upgrade. Real prices = real decisions.

```
pip install amadeus
```

Replace `search_flights` and `search_hotels` tools with the Amadeus versions above.  
Change state to use IATA airport codes (`"CDG"`) instead of city names (`"Paris"`).  
Add a tool that converts city name → IATA code using Amadeus reference data.

---

### Step 2 — Add origin city

Right now the app assumes you're searching from anywhere.  
Add `origin` to the state and UI:

```python
class TravelState(TypedDict):
    origin: str        # e.g. "New York" / IATA: "JFK"
    destination: str   # e.g. "Paris" / IATA: "CDG"
    ...
```

---

### Step 3 — Add a memory / history node

Store past searches so the agent can say:  
*"Last time you searched Paris it was $1,400 — this one is cheaper."*

```python
# Simple: save results to a JSON file
import json, pathlib

def save_search(state):
    history = []
    path = pathlib.Path("search_history.json")
    if path.exists():
        history = json.loads(path.read_text())
    history.append({
        "destination": state["destination"],
        "total_cost": state["total_cost"],
        "date_searched": str(date.today())
    })
    path.write_text(json.dumps(history, indent=2))
```

---

### Step 4 — Add a price alert mode

Instead of searching once, run the agent on a schedule (daily/weekly).  
Only notify when the price drops below budget.

```python
# Run with APScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

@scheduler.scheduled_job("cron", hour=8)  # every day at 8am
def daily_check():
    result = app.invoke(initial_state)
    if result["approved"]:
        print("Deal found! Notification sent.")

scheduler.start()
```

---

### Step 5 — Add multi-city support

Let the LLM plan a trip with stops: NYC → Paris → Rome → NYC.  
This is where Version 3 (LLM controls the loop) really shines —  
the LLM can decide to search each leg separately without you hardcoding it.

---

### Step 6 — Add a human-in-the-loop confirmation node

Before booking (or notifying), pause and ask the user to confirm:

```python
# LangGraph supports interrupt_before for human approval
app = graph.compile(interrupt_before=["notify"])

# Run until the interrupt
result = app.invoke(initial_state)

# Show the user the plan, then resume
user_confirmed = input("Approve this trip? (y/n): ")
if user_confirmed == "y":
    app.invoke(None, config={"configurable": {"thread_id": "1"}})
```

---

## 🔑 API Keys You Need — Full List

| Service | Purpose | Free Tier | Get it at |
|---|---|---|---|
| OpenAI | LLM (GPT-4o-mini) | $5 free credit | platform.openai.com |
| Amadeus | Real flights + hotels | Yes (sandbox) | developers.amadeus.com |
| Serper | Google search snippets | 2,500/month | serper.dev |
| Pushover | Push notifications | $5 one-time | pushover.net |
| Twilio | SMS notifications | Trial credits | twilio.com |
| SendGrid | Email notifications | 100/day free | sendgrid.com |
| OpenWeatherMap | Weather forecasts | 1,000/day free | openweathermap.org |
| ExchangeRate-API | Currency conversion | 1,500/month free | exchangerate-api.com |

---

## 🗺️ Recommended Learning Path for Students

```
Week 1 — Understand Version 1
        Direct functions, LangGraph nodes, state, conditional edges

Week 2 — Understand Version 2
        @tool decorator, bind_tools, typed arguments, docstrings

Week 3 — Understand Version 3
        Agentic loop, message history, tool_calls response format

Week 4 — Replace Serper with Amadeus
        Real API integration, parsing structured JSON, IATA codes

Week 5 — Add notifications + scheduling
        Twilio or SendGrid, APScheduler for daily price checks

Week 6 — Add human-in-the-loop + memory
        LangGraph interrupt, search history, multi-city planning
```
