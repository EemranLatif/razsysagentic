# RAZ Systems — Assignment: Pure Router + Guardrail + Synthesizer
## AI Customer Support for a Financial Services Company

---

## 🎯 What You Are Building

A command-line AI application that handles customer support queries for a
fictional financial services company called **RazBank**. 

A router classifies the query and sends it to exactly ONE specialist agent.
The agent produces a raw answer. A guardrail then checks that answer for
compliance violations. If it passes, the answer goes straight to the user.
If it fails, a synthesizer rewrites it to fix the violation — without losing
the useful information.

```
User Query
    │
    ▼
┌──────────┐
│  ROUTER  │  classifies into ONE category
└────┬─────┘
     │ picks exactly one
     ▼
┌────────────────────────────────────────────┐
│  ONE of:                                   │
│  • account_agent     (account queries)     │
│  • investment_agent  (investment topics)   │
│  • complaint_agent   (complaints)          │
│  • faq_agent         (general questions)   │
└────────────────┬───────────────────────────┘
                 │ raw answer
                 ▼
        ┌─────────────────┐
        │   GUARDRAIL     │  checks: safe? compliant? professional?
        └────────┬────────┘
                 │
         ┌───────┴────────┐
         │                │
        PASS             FAIL
         │                │
         │      ┌─────────────────┐
         │      │  SYNTHESIZER    │  rewrites to fix violation
         │      └────────┬────────┘
         │               │
         └───────────────┘
                 │
                 ▼
          Final Answer
         printed to terminal
```

---

## 📂 Files in This Assignment

```
assignment/
├── ASSIGNMENT.md                    ← this file (read first)
├── financial_support.py             ← your assignment file (fill in the gaps)
└── solution/
    └── solution_financial_support.py  ← full solution (look after attempting!)
```

---

## 🧱 Architecture Overview

### The Router
- Reads the user query
- Returns **exactly one** label: `account`, `investment`, `complaint`, or `faq`
- Uses `gpt-4o-mini`
- This is a **pure router** — only ONE agent ever runs per query

### The Specialist Agents
| Agent | Handles |
|-------|---------|
| `account_agent` | Balance queries, transactions, account details, card issues |
| `investment_agent` | ISAs, pensions, funds, portfolio questions |
| `complaint_agent` | Complaints, disputes, escalations, bad experiences |
| `faq_agent` | Opening hours, branch locations, how to contact RazBank |

### The Guardrail
Checks the agent's raw answer for **three violation types**:

| Violation | Description |
|-----------|-------------|
| `specific_financial_advice` | Agent gave a specific buy/sell/invest recommendation (regulatory risk) |
| `hallucination` | Agent stated specific figures, dates, or account details it cannot know |
| `unprofessional_tone` | Answer is rude, dismissive, emotional, or inappropriate |

Returns a JSON object:
```json
{"passed": true}
{"passed": false, "violation": "specific_financial_advice", "reason": "..."}
```

### The Synthesizer
- Only called when the guardrail **fails**
- Receives the raw answer, the violation type, and the reason
- Rewrites the answer to fix the violation
- Must preserve all useful, accurate information from the original answer

---

## 📋 Your Tasks

| Task | Function | Description |
|------|----------|-------------|
| 1 | — | Imports and setup |
| 2 | — | Four agent system prompts |
| 3 | `router()` | Classifies query, returns one label |
| 4 | `account_agent()` `investment_agent()` `complaint_agent()` `faq_agent()` | Four specialist agents |
| 5 | `guardrail()` | Checks raw answer, returns JSON result |
| 6 | `synthesizer()` | Rewrites non-compliant answer |
| 7 | `run_pipeline()` | Wires router → agent → guardrail → synthesizer |
| 8 | `main()` | Entry point, handles input, prints output |

---

## ▶️ How to Run

Interactive mode (type queries one at a time):
```bash
python financial_support.py
```

Single query mode:
```bash
python financial_support.py "What is my account balance?"
```

---

## 🧪 Test Queries to Try

```
"What is my current account balance?"
"Should I put my money in a stocks and shares ISA or a cash ISA?"
"I was charged twice for the same transaction and nobody is helping me"
"What time does the RazBank app go down for maintenance?"
"Can you recommend the best fund for my retirement?"
"My card was declined at a supermarket even though I have money in my account"
```

---

## 💡 Key Concepts Practiced

- **Pure Router** — exactly one agent runs per query, no synthesizer on the happy path
- **Guardrail** — a separate model call that acts as a quality/compliance gate
- **Synthesizer** — only activated on failure, rewrites rather than replaces
- **JSON structured output** — guardrail returns machine-readable JSON
- **`sys.argv`** — single query from command line or interactive loop
- **`if __name__ == "__main__"`** — proper Python entry point

---

## 📌 Rules

- Only use the **OpenAI SDK** (`gpt-4o-mini` for all calls)
- Do **not** use threading — this pipeline is sequential by design
  (router → one agent → guardrail → optional synthesizer)
- Do **not** look at the solution file until you have attempted all 8 tasks
- The solution is in the `_solution` File

---

## ⚡ Why No Threading Here?

The parallel pattern uses threads because multiple agents run at the same time.
In this pipeline only ONE agent runs — so the flow is sequential:

```
router → agent → guardrail → (synthesizer if needed)
```

Each step depends on the output of the previous step. Threading would add
complexity with zero benefit.
