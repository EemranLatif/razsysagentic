"""
RAZ Systems — SOLUTION: Pure Router + Guardrail + Synthesizer
=============================================================
AI Customer Support for RazBank (Financial Services)

Run interactive mode:
    python solution_financial_support.py

Run single query:
    python financial_support_rt_gd_8_solution.py "What is my account balance?"
    "Should I put my money in a stocks and shares ISA or a cash ISA?"
"I was charged twice for the same transaction and nobody is helping me"
"What time does the RazBank app go down for maintenance?"
"Can you recommend the best fund for my retirement?"
"My card was declined at a supermarket even though I have money in my account"
"""

# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 1: Imports and setup
# ─────────────────────────────────────────────────────────────────
import os
import sys
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
openai = OpenAI()


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 2: Four agent system prompts
# ─────────────────────────────────────────────────────────────────
ACCOUNT_PROMPT = """
You are a helpful and professional account specialist for RazBank.
You assist customers with questions about their accounts including:
balance queries, recent transactions, card issues, and payment problems.

IMPORTANT RULES:
- You do NOT have access to real customer account data.
- Never invent or state specific figures, balances, transaction amounts,
  or dates — you simply do not have this information.
- If a customer asks for specific account data, explain warmly that they
  can find this in the RazBank mobile app, online banking portal, or by
  calling the customer service team on 0800 000 000.
- Keep responses concise, clear, and professional.
- You represent RazBank — always be warm and helpful.
"""

INVESTMENT_PROMPT = """
You are a knowledgeable and friendly investment guide for RazBank.
You help customers understand investment products including:
ISAs, pensions, funds, portfolios, and savings accounts.

IMPORTANT RULES:
- You must NEVER give specific investment recommendations.
- Do not say things like "you should invest in X" or "I recommend Y fund".
- Instead, explain the options clearly and objectively in plain English.
- Always suggest the customer speaks to a qualified financial adviser
  before making investment decisions.
- Keep responses concise, clear, and professional.
- You represent RazBank — always be warm and helpful.
"""

COMPLAINT_PROMPT = """
You are an empathetic and professional complaints handler for RazBank.
You handle customer complaints, disputes, and escalations.

Your approach:
- Always acknowledge the customer's frustration sincerely and specifically
- Explain the RazBank complaints process clearly:
    Step 1: We log your complaint and assign a reference number
    Step 2: Our team investigates within 5 business days
    Step 3: We contact you with our findings and resolution
- Provide realistic timelines
- Never dismiss or minimise the customer's experience
- Never make promises you cannot keep
- Always end by thanking the customer for raising the issue
- Keep your tone warm, professional, and solution-focused.
"""

FAQ_PROMPT = """
You are a friendly and helpful general assistant for RazBank.
You answer general questions about RazBank including:
opening hours, branch locations, app information, how to contact RazBank,
account opening, and general product information.

RazBank general information (use this to answer FAQs):
- Customer service: 0800 000 000 (Mon-Fri 8am-8pm, Sat 9am-5pm)
- App maintenance: Sundays 2am-4am
- Online banking: banking.razbank.com
- Branch finder: razbank.com/branches

Keep answers concise, accurate, and warm.
You represent RazBank — always be helpful and professional.
"""


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 3: Router function
# ─────────────────────────────────────────────────────────────────
def router(user_query):
    system = """
You are a customer query classifier for RazBank, a financial services company.
Read the customer's query and classify it into EXACTLY one of these four categories:

  account     — balance queries, transactions, card issues, payment problems
  investment  — ISAs, pensions, funds, portfolios, savings products
  complaint   — disputes, bad experiences, escalations, something went wrong
  faq         — opening hours, contact info, app questions, general information

Respond with ONLY the category label — one word, lowercase, no punctuation, no explanation.
Do not write anything else. Your entire response must be one of: account, investment, complaint, faq
"""
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_query}
        ]
    )
    return response.choices[0].message.content.strip().lower()


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 4: Four specialist agent functions
# ─────────────────────────────────────────────────────────────────
def account_agent(user_query):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ACCOUNT_PROMPT},
            {"role": "user",   "content": user_query}
        ]
    )
    return response.choices[0].message.content


def investment_agent(user_query):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": INVESTMENT_PROMPT},
            {"role": "user",   "content": user_query}
        ]
    )
    return response.choices[0].message.content


def complaint_agent(user_query):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": COMPLAINT_PROMPT},
            {"role": "user",   "content": user_query}
        ]
    )
    return response.choices[0].message.content


def faq_agent(user_query):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": FAQ_PROMPT},
            {"role": "user",   "content": user_query}
        ]
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 5: Guardrail function
# ─────────────────────────────────────────────────────────────────
def guardrail(user_query, raw_answer):
    system = """
You are a compliance checker for RazBank customer support responses.
Review the agent's answer and check for exactly three violation types:

  specific_financial_advice
    The answer gives a specific recommendation to buy, sell, invest in,
    or avoid a specific product, fund, or financial instrument.
    Example violation: "You should put your money in a stocks and shares ISA."
    NOT a violation: "Here are the key differences between ISA types."

  hallucination
    The answer states specific account figures, transaction amounts, balances,
    dates, or personal data that the agent cannot actually know.
    Example violation: "Your current balance is £2,340.50."
    NOT a violation: "You can check your balance in the RazBank app."

  unprofessional_tone
    The answer is rude, dismissive, sarcastic, condescending, or emotionally
    inappropriate for a professional financial services context.

Respond with ONLY valid JSON. No markdown. No code fences. No explanation.

If the answer is acceptable:
{"passed": true}

If there is a violation:
{"passed": false, "violation": "<violation_type>", "reason": "<one sentence explaining the specific problem>"}
"""
    user_content = (
        f"Customer query: {user_query}\n\n"
        f"Agent answer to review:\n{raw_answer}"
    )
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content}
        ]
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if the model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 6: Synthesizer function
# ─────────────────────────────────────────────────────────────────
def synthesizer(user_query, raw_answer, violation, reason):
    system = """
You are an expert editor for RazBank customer support responses.
An agent produced an answer that failed a compliance check.
Your job is to rewrite the answer to fix the specific violation — 
without simply deleting the helpful content.

Rules for rewriting:
- Fix ONLY the flagged violation — do not change anything else unnecessarily
- Preserve all accurate and genuinely useful information from the original
- Keep the same warm, professional, and helpful tone
- The rewritten answer must still fully address the customer's question
- Do not add a preamble like "Here is the rewritten answer:" — just write it
"""
    user_content = (
        f"Customer query: {user_query}\n\n"
        f"Original answer (contains a violation):\n{raw_answer}\n\n"
        f"Violation type: {violation}\n"
        f"Reason it failed: {reason}\n\n"
        f"Please rewrite the answer to fix this violation."
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
# SOLUTION — Task 7: Pipeline function
# ─────────────────────────────────────────────────────────────────
def run_pipeline(user_query):
    # Step 1: Router
    label = router(user_query)
    print(f"\n🔀 Router → [{label}]")

    # Step 2: Call the correct agent
    if label == "account":
        raw_answer = account_agent(user_query)
    elif label == "investment":
        raw_answer = investment_agent(user_query)
    elif label == "complaint":
        raw_answer = complaint_agent(user_query)
    elif label == "faq":
        raw_answer = faq_agent(user_query)
    else:
        # Fallback for any unexpected label
        return "I'm sorry, I wasn't able to direct your query to the right team. Please call us on 0800 000 000."

    # Step 3: Guardrail check
    check = guardrail(user_query, raw_answer)

    if check["passed"]:
        print("✅ Guardrail passed")
        return raw_answer
    else:
        violation = check["violation"]
        reason    = check["reason"]
        print(f"⚠️  Guardrail failed: {violation} — {reason}")
        print("✏️  Synthesizer rewriting...")
        return synthesizer(user_query, raw_answer, violation, reason)


# ─────────────────────────────────────────────────────────────────
# SOLUTION — Task 8: main() function
# ─────────────────────────────────────────────────────────────────
def main():
    # Single query mode
    if len(sys.argv) > 1:
        user_query = sys.argv[1]
        print(f"\n📨 Query: {user_query}")
        answer = run_pipeline(user_query)
        print("\n" + "=" * 60)
        print("💬 RazBank Support:")
        print("=" * 60)
        print(answer)
        print("=" * 60)
        return

    # Interactive mode
    print("\n" + "=" * 60)
    print("💼 Welcome to RazBank AI Customer Support")
    print("   Powered by: Router + Guardrail + Synthesizer")
    print("=" * 60)
    print("   Ask about: accounts, investments, complaints, or general FAQs")
    print("   Type 'quit' or 'exit' to leave\n")

    while True:
        try:
            user_query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_query:
            continue

        if user_query.lower() in ("quit", "exit"):
            print("Thank you for contacting RazBank. Goodbye!")
            break

        answer = run_pipeline(user_query)
        print("\n" + "=" * 60)
        print("💬 RazBank Support:")
        print("=" * 60)
        print(answer)
        print("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
