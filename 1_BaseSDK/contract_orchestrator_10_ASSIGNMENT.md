# RAZ Systems — Assignment: Orchestrator Pattern
## AI Contract Reviewer with Planner + Dynamic Fan-Out + Synthesizer

---

## 🎯 What You Are Building

An Orchestrator is the most powerful agentic pattern in Base SDK. Unlike a
Router (which picks ONE agent) or a fixed Parallel setup (which runs ALL agents
always), the Orchestrator uses a **Planner** to decide which agents are needed
for THIS specific input — then fans out to exactly those agents in parallel.

```
Contract PDF
      │
      ▼
┌─────────────┐
│   PLANNER   │  reads the contract, returns JSON list of needed specialists
└──────┬──────┘
       │  e.g. ["employment", "ip"]  or  ["ip", "data_privacy"]  or all three
       │
  (Fan-Out — only selected agents run, in parallel)
       │
 ┌─────┴──────────────────────────┐
 ▼              ▼                 ▼
Employment     IP &          Data Privacy
Agent          Copyright     Agent
(if selected)  Agent         (if selected)
               (if selected)
 │              │                 │
 └──────────────┬─────────────────┘
                ▼
       ┌─────────────────┐
       │   SYNTHESIZER   │  combines all specialist outputs
       └────────┬────────┘
                ▼
         Final Risk Report
```

---

## 📂 Files in This Assignment

```
assignment/
├── ASSIGNMENT_orchestrator.md           ← this file (read first)
├── contract_orchestrator.py             ← your assignment file
├── sample_contract.pdf                  ← single-domain contract (faq only)
├── my_contract.pdf                      ← multi-domain (employment + ip + data_privacy)
└── solution/
    └── solution_contract_orchestrator.py  ← full solution
```

---

## 🔑 The Key Insight: What Makes This an Orchestrator

| Pattern | Who decides which agents run? | How many agents run? |
|---------|-------------------------------|----------------------|
| Router | Router — at classify time | Always exactly ONE |
| Parallel | Hard-coded — always all | Always ALL |
| **Orchestrator** | **Planner LLM call — at runtime** | **1, 2, or 3 — depends on input** |

The Orchestrator pattern adds **intelligence to the fan-out decision itself**.
The planner is itself an LLM call — it reads the contract and returns a JSON
list. A simple freelance agreement might only need `["faq"]`. A full employment
contract with IP clauses and data processing needs `["employment", "ip", "data_privacy"]`.

---

## 🧱 Architecture: Three Components

### 1. Planner
- Reads the first 3000 characters of the contract (enough to classify it)
- Returns a JSON list of which specialist agents are needed
- Valid values: `"employment"`, `"ip"`, `"data_privacy"`, `"faq"`
- Uses `gpt-4o-mini`

### 2. Specialist Agents (run in parallel via threads)
| Agent | Reviews for |
|-------|-------------|
| `employment_agent` | Employment clauses, non-compete, termination, compensation |
| `ip_agent` | IP ownership, work-for-hire, licensing, moral rights |
| `data_privacy_agent` | GDPR, data handling, confidentiality, retention |
| `faq_agent` | General services scope, payment terms, liability |

### 3. Synthesizer
- Receives all specialist outputs (however many ran)
- Produces a structured final report:
  - Overall Risk Level (Low / Medium / High)
  - Key Findings per specialist
  - Top 3 Risks
  - Recommendation (Safe / Review Needed / Do Not Sign)

---

## 📋 Your Tasks

| Task | Function | Description |
|------|----------|-------------|
| 1 | — | Imports and setup |
| 2 | `extract_text()` | Read PDF text using PdfReader |
| 3 | — | Four specialist system prompts |
| 4 | `employment_agent()` `ip_agent()` `data_privacy_agent()` `faq_agent()` | Four agent functions |
| 5 | `planner()` | LLM call that returns JSON list of needed agents |
| 6 | `run_agents()` | Dynamic thread creation for selected agents only |
| 7 | `synthesizer()` | Combines all outputs into final report |
| 8 | `orchestrator()` | Calls planner → run_agents → synthesizer |
| 9 | `main()` | Entry point, reads PDF path, prints output |

---

## ▶️ How to Run

```bash
# Single-domain contract — expect 1 agent (faq)
python contract_orchestrator.py sample_contract.pdf

# Multi-domain contract — expect 3 agents (employment + ip + data_privacy)
python contract_orchestrator.py my_contract.pdf
```

---

## 💡 Fan-Out Explained

**Fan-Out** means spreading one input to multiple workers simultaneously.

```
             ┌── employment_agent ──┐
             │                     │
Input ───────┼── ip_agent          ├──→ results dict
             │                     │
             └── data_privacy_agent┘
```

The "fan" opens on the way out (fan-out) and closes when threads join.
Without fan-out, you would run agents sequentially — slower and wasteful.
With fan-out, all selected agents run at the same time.

**Why not always fan-out to all agents?**
Running unnecessary agents wastes API calls and money, adds noise to the
synthesizer, and slows the pipeline with irrelevant output. The planner
makes the selection intelligent.

---

## 📌 Rules

- Only use the **OpenAI SDK** (`gpt-4o-mini` for all calls)
- Use **`threading`** for the fan-out (not multiprocessing)
- The planner must be an **LLM call** — not hard-coded logic
- Do **not** look at the solution until you have attempted all 9 tasks
