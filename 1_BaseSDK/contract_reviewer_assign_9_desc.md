# RAZ Systems — Assignment: Router + Fan-Out + Synthesizer
## AI Legal Contract Reviewer

---

## 🎯 What You Are Building

A command-line AI application that reads a legal contract PDF and produces a
unified risk report. Unlike a simple router (one agent) or pure parallel (all
agents always), this pattern is smarter — the router reads the contract first
and decides **which specialist agents are actually needed**. Only those agents
run. Their outputs are then combined by a synthesizer into one final report.

```
Contract PDF
     │
     ▼
┌──────────────┐
│    ROUTER    │  reads contract, returns a list of needed specialists
└──────┬───────┘
       │
  (dynamic — could be 1, 2, or 3 agents depending on the contract)
       │
 ┌─────┴──────────────────────┐
 ▼                            ▼                         ▼
Employment Law           IP & Copyright           Data Privacy
Agent                    Agent                    Agent
(only if selected)       (only if selected)       (only if selected)
 │                            │                         │
 └────────────────┬───────────────────────────────────-─┘
                  ▼
         ┌─────────────────┐
         │   SYNTHESIZER   │  combines all specialist outputs
         └────────┬────────┘
                  ▼
        Unified Risk Report
        printed to terminal
```

---

## 📂 Files in This Assignment

```
assignment/
├── ASSIGNMENT.md               ← this file (read first)
├── contract_reviewer.py        ← your assignment file (fill in the gaps)
├── sample_contract.pdf         ← a sample contract PDF to test with
└── solution/
    └── solution_contract_reviewer.py   ← full solution (look after attempting!)
```

---

## 🧱 Architecture Overview

### The Router
- Reads the full contract text
- Returns a **JSON list** of which agents are needed
- Example output: `["employment", "ip"]` or `["ip", "data_privacy"]`
- Uses `gpt-4o-mini`

### The Specialist Agents (run in parallel via threads)
| Agent | Covers |
|-------|--------|
| `employment_agent` | Employment clauses, termination, non-compete, liability |
| `ip_agent` | Intellectual property, ownership of work, licensing |
| `data_privacy_agent` | Data handling, GDPR, confidentiality, personal data |

### The Synthesizer
- Receives all specialist outputs
- Produces a single structured risk report with:
  - Overall risk level (Low / Medium / High)
  - Key findings per specialist
  - Top 3 risks to be aware of
  - Final recommendation (Safe / Review Needed / Do Not Sign)

---

## 📋 Your Tasks

| Task | Description |
|------|-------------|
| 1 | Imports and setup |
| 2 | PDF text extraction function |
| 3 | Three specialist agent system prompts |
| 4 | Three specialist agent functions |
| 5 | Router function (returns JSON list of agents needed) |
| 6 | Run selected agents in parallel using threads |
| 7 | Synthesizer function |
| 8 | `main()` function wiring everything together |

---

## ▶️ How to Run

```terminal
python contract_reviewer.py sample_contract.pdf
```

Or with your own PDF:
```terminal
python contract_reviewer.py my_contract.pdf
```

---

## 💡 Key Concepts Practiced

- **Router pattern** — a model makes a routing decision before any work happens
- **Dynamic fan-out** — the number of agents that run depends on the router's decision
- **Parallel execution** — selected agents run simultaneously using `threading`
- **Synthesizer** — combines multiple specialist outputs into one unified report
- **`sys.argv`** — reading command-line arguments in Python
- **`if __name__ == "__main__"`** — proper Python script entry point

---

## ⚡ Why `.py` and not a notebook?

This pipeline involves multi-step execution, threading, and potentially slow API
calls. A `.py` script is more stable, predictable, and closer to how real
agentic applications are built in production.

---

## 📌 Rules

- Only use the **OpenAI SDK** (`gpt-4o-mini` for all calls)
- Only use **`threading`** for parallelism (not `multiprocessing`)
- Do **not** look at the solution file until you have attempted all 8 tasks
- The solution file is in the `solution/` folder
