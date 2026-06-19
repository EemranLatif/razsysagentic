"""
RAZ Systems — SOLUTION: Router + Fan-Out + Synthesizer
=======================================================
AI Legal Contract Reviewer

Run with:
    python contract_reviewer_9_solution.py sample_contract.pdf
    python contract_reviewer_9_solution.py my_contract.pdf
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
        if page_text:
            text += page_text
    return text


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 3: Specialist agent system prompts
# ─────────────────────────────────────────────────────────────────
EMPLOYMENT_PROMPT = """
You are a specialist employment lawyer reviewing a contract on behalf of the person
who is being asked to sign it. Analyse the contract for:
- Employment conditions, working hours, and compensation clauses
- Termination conditions and notice periods
- Non-compete and non-solicitation clauses
- Liability and indemnification clauses
- Any clauses that restrict the signing party's future employment

Structure your response with clear headings.
End with a Risk Level: Low / Medium / High and a one-sentence reason.
Be concise and specific — flag only what is genuinely unusual or risky.
"""

IP_PROMPT = """
You are a specialist intellectual property lawyer reviewing a contract on behalf
of the person who is being asked to sign it. Analyse the contract for:
- Ownership of work created during the engagement
- Work-for-hire clauses that transfer IP to the other party
- Licensing terms and scope
- Rights over pre-existing IP and tools the signing party brings
- Any clauses where the signing party gives up ownership of their creations

Structure your response with clear headings.
End with a Risk Level: Low / Medium / High and a one-sentence reason.
Be concise and specific — flag only what is genuinely unusual or risky.
"""

DATA_PRIVACY_PROMPT = """
You are a specialist data privacy lawyer reviewing a contract on behalf of the
person who is being asked to sign it. Analyse the contract for:
- How personal data is collected, stored, and shared
- GDPR or other privacy regulation compliance
- Confidentiality and non-disclosure obligations
- Data sharing with third parties
- Retention periods and deletion rights

Structure your response with clear headings.
End with a Risk Level: Low / Medium / High and a one-sentence reason.
Be concise and specific — flag only what is genuinely unusual or risky.
"""


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 4: Specialist agent functions
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


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 5: Router function
# ─────────────────────────────────────────────────────────────────
def router(contract_text):
    system = """
You are a legal contract classifier. Read the contract and decide which of the
following specialist reviewers are needed:

  "employment"    — if the contract involves employment, consulting, work for hire,
                    termination, non-compete, or compensation terms
  "ip"            — if the contract involves intellectual property, ownership of
                    created work, licensing, or software/creative rights
  "data_privacy"  — if the contract involves handling of personal data, GDPR,
                    confidentiality, or data sharing with third parties

Return ONLY a valid JSON array containing the relevant specialist names.
Examples:
  ["employment", "ip"]
  ["data_privacy"]
  ["employment", "ip", "data_privacy"]

No explanation. No markdown. No code fences. Only the JSON array.
"""
    # Pass only the first 3000 characters — enough for the router to
    # understand the contract type without a costly full-text call
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": contract_text[:3000]}
        ]
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 6: Run selected agents in parallel
# ─────────────────────────────────────────────────────────────────
def run_agents(contract_text, selected_agents):
    results = {}

    agent_map = {
        "employment":   employment_agent,
        "ip":           ip_agent,
        "data_privacy": data_privacy_agent,
    }

    # Create a thread for each selected agent
    threads = []
    for agent_name in selected_agents:
        fn = agent_map[agent_name]
        t = threading.Thread(
            target=fn,
            args=(contract_text, results, agent_name)
        )
        threads.append(t)

    # Start ALL threads before joining any — this is what makes them parallel
    for t in threads:
        t.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

    return results


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 7: Synthesizer
# ─────────────────────────────────────────────────────────────────
def synthesizer(contract_text, agent_results):
    system = """
You are a senior lawyer giving a final risk verdict on a contract. You have
received specialist reviews from one or more expert agents. Synthesize their
findings into a single, clear, actionable report.

Your report must contain exactly these four sections:

## Overall Risk Level
State: Low, Medium, or High — and explain why in two sentences.

## Key Findings
Summarise the most important findings from each specialist review.
Use sub-headings per specialist.

## Top 3 Risks
List the three most important risks the signing party should be aware of.
Be specific — reference actual clauses or concerns from the reviews.

## Recommendation
Choose exactly one of:
  ✅ Safe to Sign
  ⚠️  Review Needed — and state what needs to change
  ❌ Do Not Sign — and state the main reason

Keep the tone professional and direct. No filler text.
"""

    # Build the user message with all specialist outputs
    specialist_section = ""
    for agent_name, output in agent_results.items():
        label = agent_name.replace("_", " ").title()
        specialist_section += f"--- {label} Specialist Review ---\n{output}\n\n"

    user_content = (
        f"Contract excerpt (first 1000 chars):\n{contract_text[:1000]}\n\n"
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
# SOLUTION — Task 8: main() function
# ─────────────────────────────────────────────────────────────────
def main():
    # Step 1: Read PDF path from command line
    if len(sys.argv) < 2:
        print("Usage: python solution_contract_reviewer.py <path_to_contract.pdf>")
        print("Example: python solution_contract_reviewer.py sample_contract.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Error: file not found — {pdf_path}")
        sys.exit(1)

    # Step 2: Extract contract text
    print(f"\n📄 Reading contract: {pdf_path}")
    contract_text = extract_text(pdf_path)
    print(f"   Extracted {len(contract_text)} characters")
    print(f"   Preview: {contract_text[:200]}...\n")

    # Step 3: Router decides which agents are needed
    print("🔀 Router is analysing the contract...")
    selected_agents = router(contract_text)
    print(f"   Selected agents: {selected_agents}\n")

    # Step 4: Run selected agents in parallel
    print(f"⚡ Running {len(selected_agents)} agent(s) in parallel...")
    agent_results = run_agents(contract_text, selected_agents)
    print(f"   All agents completed.\n")

    # Print each specialist output for transparency
    for agent_name, output in agent_results.items():
        label = agent_name.replace("_", " ").title()
        print("=" * 60)
        print(f"📋 {label} Specialist Review:")
        print("=" * 60)
        print(output)
        print()

    # Step 5: Synthesizer combines all outputs
    print("=" * 60)
    print("⚖️  Synthesizing final report...")
    print("=" * 60)
    report = synthesizer(contract_text, agent_results)

    # Step 6: Print final report
    print("\n" + "=" * 60)
    print("📊 FINAL RISK REPORT")
    print("=" * 60)
    print(report)
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
