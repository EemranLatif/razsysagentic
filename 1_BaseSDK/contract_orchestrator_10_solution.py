"""
RAZ Systems — SOLUTION: Orchestrator Pattern
============================================
AI Contract Reviewer with Planner + Dynamic Fan-Out + Synthesizer

Run with:
    python contract_orchestrator_10_solution.py sample_contract.pdf
    python contract_orchestrator_10_solution.py my_contract.pdf

Expected behaviour:
    sample_contract.pdf  →  planner selects ["faq"]          → 1 or 2 agent runs
    my_contract.pdf      →  planner selects ["employment",   → more then 2 agents run
                             "ip", "data_privacy"]
"""

# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 1: Imports and setup
# ─────────────────────────────────────────────────────────────────
import os
import sys
import json
import threading

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv(override=True)
openai = OpenAI()


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 2: PDF text extraction
# ─────────────────────────────────────────────────────────────────
def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:                   # some pages may return None
            text += page_text
    return text


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 3: Four specialist agent system prompts
# ─────────────────────────────────────────────────────────────────
EMPLOYMENT_PROMPT = """
You are a specialist employment lawyer reviewing a contract on behalf of the
person who is being asked to sign it. Analyse the contract for:

- Employment conditions, working hours, and compensation structure
- Non-compete and non-solicitation clauses and their duration/scope
- Termination conditions, notice periods, and garden leave provisions
- Liability and indemnification clauses affecting the signing party
- Any clauses that unusually restrict the signing party's future career

Structure your response with clear headings for each area reviewed.
End with:  Risk Level: Low / Medium / High — and one sentence explaining why.
Be specific and concise. Only flag what is genuinely unusual or risky.
"""

IP_PROMPT = """
You are a specialist intellectual property lawyer reviewing a contract on behalf
of the person who is being asked to sign it. Analyse the contract for:

- Who owns work product, inventions, and materials created during the engagement
- Work-for-hire clauses and IP assignment provisions
- Scope of IP assignment — does it cover work done outside working hours?
- Pre-existing IP and whether any licence is granted over it
- Moral rights waiver — does the signing party waive attribution rights?
- Whether AI models, datasets, or algorithms are specifically mentioned

Structure your response with clear headings for each area reviewed.
End with:  Risk Level: Low / Medium / High — and one sentence explaining why.
Be specific. Flag every clause where the signing party loses ownership or rights.
"""

DATA_PRIVACY_PROMPT = """
You are a specialist data privacy lawyer reviewing a contract on behalf of the
person who is being asked to sign it. Analyse the contract for:

- What personal data the signing party will access or process
- GDPR and Data Protection Act 2018 compliance obligations placed on the signer
- International data transfer restrictions
- Data breach notification timelines and obligations
- Confidentiality obligations and their scope and duration
- Data retention and deletion requirements on termination

Structure your response with clear headings for each area reviewed.
End with:  Risk Level: Low / Medium / High — and one sentence explaining why.
Be specific. Flag any obligation that is unusually strict or burdensome.
"""

FAQ_PROMPT = """
You are a general contract specialist reviewing a contract on behalf of the
person who is being asked to sign it. Analyse the contract for:

- Clarity and fairness of the scope of services
- Payment terms, invoicing schedule, and late payment provisions
- Liability caps and indemnification obligations
- Termination rights — are they balanced between both parties?
- Overall balance of the contract — does it heavily favour one party?
- Any unusual or ambiguous clauses that warrant attention

Structure your response with clear headings for each area reviewed.
End with:  Risk Level: Low / Medium / High — and one sentence explaining why.
Be concise and specific. Highlight any terms that a reasonable person
would want to negotiate before signing.
"""


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 4: Four specialist agent functions
#
# All four follow identical structure — only the system prompt changes.
# They write to results[key] instead of returning because they run
# inside threads; threads cannot return values to their caller.
# ─────────────────────────────────────────────────────────────────
def employment_agent(contract_text, results, key):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": EMPLOYMENT_PROMPT},
            {"role": "user",   "content": contract_text}
        ]
    )
    results[key] = response.choices[0].message.content


def ip_agent(contract_text, results, key):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": IP_PROMPT},
            {"role": "user",   "content": contract_text}
        ]
    )
    results[key] = response.choices[0].message.content


def data_privacy_agent(contract_text, results, key):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": DATA_PRIVACY_PROMPT},
            {"role": "user",   "content": contract_text}
        ]
    )
    results[key] = response.choices[0].message.content


def faq_agent(contract_text, results, key):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": FAQ_PROMPT},
            {"role": "user",   "content": contract_text}
        ]
    )
    results[key] = response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 5: Planner function
#
# This is the intelligence behind the Orchestrator.
# The planner is itself an LLM call — it reads the contract and
# decides which specialists are actually needed for THIS input.
# That decision drives how many threads are created in run_agents().
# ─────────────────────────────────────────────────────────────────
def planner(contract_text):
    system = """
You are a legal contract classifier for an AI contract review system.
Read the contract excerpt and decide which specialist reviewers are needed.

Available specialists:
  "employment"    — employment conditions, compensation, non-compete,
                    termination, notice periods, garden leave
  "ip"            — intellectual property ownership, work-for-hire,
                    IP assignment, licensing, moral rights
  "data_privacy"  — GDPR, personal data handling, confidentiality,
                    data transfers, breach notification, retention
  "faq"           — general services scope, payment terms, liability,
                    termination rights, contract balance

Rules:
- Include a specialist ONLY if their domain is genuinely present in the contract
- A simple services agreement may only need ["faq"]
- A full employment contract may need ["employment", "ip", "data_privacy"]
- Return ONLY a valid JSON array of the needed specialist names
- No markdown, no explanation, no code fences — only the JSON array

Example outputs:
  ["faq"]
  ["employment", "ip"]
  ["employment", "ip", "data_privacy"]
"""
    # Only send the first 3000 chars — enough to classify the contract type
    # without paying for a full-text call at this planning stage
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": contract_text[:3000]}
        ]
    )
    raw = response.choices[0].message.content.strip()

    # Defensively strip markdown fences if the model adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 6: Run selected agents in parallel (dynamic fan-out)
#
# This is the fan-out step. The number of threads created is NOT
# hard-coded — it is driven entirely by what the planner returned.
# For sample_contract.pdf: 1 thread (faq only)
# For my_contract.pdf:     3 threads (employment + ip + data_privacy)
#
# Critical threading rule:
#   Start ALL threads BEFORE joining ANY thread.
#   If you start t1 then immediately join t1, you wait for t1 to
#   finish before starting t2 — that is sequential, not parallel.
# ─────────────────────────────────────────────────────────────────
def run_agents(contract_text, selected_agents):
    results = {}

    # Map agent names to their functions
    agent_map = {
        "employment":   employment_agent,
        "ip":           ip_agent,
        "data_privacy": data_privacy_agent,
        "faq":          faq_agent,
    }

    # Create one thread per selected agent
    threads = []
    for agent_name in selected_agents:
        fn = agent_map[agent_name]
        t = threading.Thread(
            target=fn,
            args=(contract_text, results, agent_name)
        )
        threads.append(t)

    # Fan-out: start ALL threads before joining any
    for t in threads:
        t.start()

    # Fan-in: wait for all threads to complete
    for t in threads:
        t.join()

    return results


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 7: Synthesizer
#
# Receives all specialist outputs (however many ran) and produces
# a single unified risk report. The structure is explicit in the
# system prompt so the output is consistent regardless of whether
# 1, 2, or 3 specialists contributed.
# ─────────────────────────────────────────────────────────────────
def synthesizer(contract_text, agent_results):
    system = """
You are a senior lawyer giving a final risk verdict on a contract.
You have received reviews from one or more specialist agents.
Synthesize all findings into one clear, structured report.

Your report must contain EXACTLY these four sections:

## Overall Risk Level
State: Low, Medium, or High — and explain why in two sentences.

## Key Findings
Summarise the most important findings from each specialist.
Use a sub-heading per specialist (e.g. ### Employment, ### IP, ### Data Privacy).

## Top 3 Risks
List the three most important risks for the signing party.
Be specific — reference actual clause numbers or content from the reviews.

## Recommendation
Choose exactly one of:
  ✅ Safe to Sign
  ⚠️  Review Needed — state exactly what needs to change before signing
  ❌ Do Not Sign    — state the primary reason

Keep the tone professional and direct. No filler text.
"""
    # Build the user message — include all specialist outputs labelled clearly
    specialist_section = ""
    for agent_name, output in agent_results.items():
        label = agent_name.replace("_", " ").title()
        specialist_section += f"--- {label} Specialist Review ---\n{output}\n\n"

    user_content = (
        f"Contract excerpt (first 1000 chars for context):\n"
        f"{contract_text[:1000]}\n\n"
        f"{specialist_section}"
        f"Now produce the unified risk report."
    )

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content}
        ]
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 8: Orchestrator function
#
# This is the coordinator. It does NOT make routing decisions itself
# — it delegates that to the planner. It does NOT run agents itself
# — it delegates that to run_agents(). It does NOT combine output
# — it delegates that to the synthesizer.
#
# The orchestrator's job is purely coordination:
#   planner → run_agents → synthesizer
# ─────────────────────────────────────────────────────────────────
def orchestrator(contract_text):
    # Step 1: Planner decides which agents are needed
    print("\n🧠 Planner is reading the contract...")
    selected_agents = planner(contract_text)
    print(f"   Selected agents: {selected_agents}")
    print(f"   ({len(selected_agents)} specialist(s) will run)\n")

    # Step 2: Fan-out — run selected agents in parallel
    print(f"⚡ Running {len(selected_agents)} agent(s) in parallel...")
    agent_results = run_agents(contract_text, selected_agents)
    print(f"   All agents completed.\n")

    # Step 3: Print each specialist output for transparency
    for agent_name, output in agent_results.items():
        label = agent_name.replace("_", " ").title()
        print("=" * 60)
        print(f"📋 {label} Specialist Review:")
        print("=" * 60)
        print(output)
        print()

    # Step 4: Synthesizer combines all outputs
    print("=" * 60)
    print("⚖️  Synthesizer combining all specialist outputs...")
    print("=" * 60 + "\n")
    final_report = synthesizer(contract_text, agent_results)

    return final_report


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 9: main() function
# ─────────────────────────────────────────────────────────────────
def main():
    # Read PDF path from command line
    if len(sys.argv) < 2:
        print("Usage:   python solution_contract_orchestrator.py <path_to_contract.pdf>")
        print("Example: python solution_contract_orchestrator.py sample_contract.pdf")
        print("         python solution_contract_orchestrator.py my_contract.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Error: file not found — {pdf_path}")
        sys.exit(1)

    # Extract contract text
    print(f"\n📄 Reading contract: {pdf_path}")
    contract_text = extract_text(pdf_path)
    print(f"   Extracted {len(contract_text)} characters")
    print(f"   Preview: {contract_text[:200]}...\n")

    # Run the orchestrator pipeline
    final_report = orchestrator(contract_text)

    # Print final report
    print("\n" + "=" * 60)
    print("📊 FINAL RISK REPORT")
    print("=" * 60)
    print(final_report)
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
