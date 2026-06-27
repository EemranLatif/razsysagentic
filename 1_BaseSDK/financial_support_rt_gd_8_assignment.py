"""
RAZ Systems — Assignment: Pure Router + Guardrail + Synthesizer
===============================================================
AI Customer Support for RazBank (Financial Services)

Run interactive mode:
    python financial_support.py

Run single query:
    python financial_support.py "What is my account balance?"

Read ASSIGNMENT_financial.md before starting!
"""

# ─────────────────────────────────────────────────────────────────
# TASK 1 — Imports and setup
#
# You need:
#   - os, sys, json  (all built-in)
#   - load_dotenv from dotenv
#   - OpenAI from openai
#
# After importing:
#   - Call load_dotenv(override=True)
#   - Create an OpenAI client called `openai`
# ─────────────────────────────────────────────────────────────────

# YOUR CODE HERE
import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI   

load_dotenv(override=True)

openai = OpenAI()



# ─────────────────────────────────────────────────────────────────
# TASK 2 — Four agent system prompts
#
# Create four string variables, one per specialist agent.
# Each prompt defines the agent's persona, scope, and rules.
#
# ACCOUNT_PROMPT
#   A helpful RazBank account specialist who assists with:
#   balance queries, recent transactions, account details, card issues,
#   and payment problems.
#   IMPORTANT: the agent does NOT have access to real account data.
#   It must never invent specific figures, dates, or transaction details.
#   If asked for specific data, it should explain how the customer can
#   find this in the RazBank app or by calling the team.
#
# INVESTMENT_PROMPT
#   A knowledgeable RazBank investment guide who explains products like
#   ISAs, pensions, funds, and portfolios in plain English.
#   IMPORTANT: must never give specific investment recommendations
#   (e.g. "you should put your money in X"). Instead, explain options
#   and suggest speaking to a qualified financial adviser.
#
# COMPLAINT_PROMPT
#   An empathetic RazBank complaints handler who:
#   - Acknowledges the customer's frustration sincerely
#   - Explains the complaints process clearly
#   - Provides next steps and timelines
#   - Never dismisses or minimises the customer's experience
#   - Always ends by thanking the customer for raising the issue
#
# FAQ_PROMPT
#   A friendly RazBank assistant who answers general questions about:
#   opening hours, branch locations, app maintenance windows,
#   how to contact RazBank, and general product information.
#   Keeps answers concise and warm.
#
# All four prompts should remind the agent:
#   - You represent RazBank professionally
#   - Keep responses concise and clear
#   - Do not make up information you don't have
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
# TASK 3 — Router function
#
# Write a function called router(user_query) that:
#
#   1. Sends the user query to gpt-4o-mini
#   2. Uses a system prompt that tells the model to classify the query
#      into EXACTLY one of these four labels:
#        account      — balance, transactions, card, payments
#        investment   — ISAs, pensions, funds, portfolio
#        complaint    — disputes, bad experience, escalation
#        faq          — opening hours, contact info, general questions
#   3. Instructs the model to return ONLY the label — one word,
#      lowercase, no punctuation, no explanation
#   4. Returns the label as a stripped lowercase string
#
# Tip: be very explicit in the system prompt that the model must
#      return only one of the four exact labels and nothing else.
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
# TASK 4 — Four specialist agent functions
#
# Write four functions, all following the exact same pattern:
#
#   account_agent(user_query)    → returns response text
#   investment_agent(user_query) → returns response text
#   complaint_agent(user_query)  → returns response text
#   faq_agent(user_query)        → returns response text
#
# Each function:
#   1. Calls gpt-4o-mini with the appropriate system prompt
#   2. Passes user_query as the user message
#   3. Returns the response text
#
# Note: unlike the parallel assignment, these functions use return
#       (not results[key]) because they run sequentially, not in threads.
# ─────────────────────────────────────────────────────────────────

def account_agent(user_query):
    # YOUR CODE HERE
    pass


def investment_agent(user_query):
    # YOUR CODE HERE
    pass


def complaint_agent(user_query):
    # YOUR CODE HERE
    pass


def faq_agent(user_query):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 5 — Guardrail function
#
# Write a function called guardrail(user_query, raw_answer) that:
#
#   1. Sends both the original user_query and the raw_answer to gpt-4o-mini
#   2. Uses a system prompt that instructs the model to check for
#      exactly THREE violation types:
#
#        specific_financial_advice
#          The answer gives a specific recommendation to buy, sell,
#          invest in, or avoid a specific product or fund.
#          (e.g. "You should put your money in a stocks ISA" is a violation)
#          (e.g. "Here are the differences between ISA types" is NOT)
#
#        hallucination
#          The answer states specific account figures, transaction amounts,
#          dates, or personal data that the model cannot actually know.
#          (e.g. "Your balance is £2,340.50" is a violation)
#
#        unprofessional_tone
#          The answer is rude, dismissive, sarcastic, or emotionally
#          inappropriate for a professional financial services context.
#
#   3. Instructs the model to return ONLY valid JSON — no markdown,
#      no explanation, no code fences.
#      If the answer is fine:   {"passed": true}
#      If there is a violation: {"passed": false, "violation": "<type>", "reason": "<brief reason>"}
#
#   4. Parses the JSON with json.loads() and returns the dictionary
#
# Tip: make the system prompt very explicit about the JSON format.
#      A model that returns markdown fences will break json.loads().
# ─────────────────────────────────────────────────────────────────

def guardrail(user_query, raw_answer):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 6 — Synthesizer function
#
# Write a function called synthesizer(user_query, raw_answer, violation, reason)
# that:
#
#   1. Calls gpt-4o-mini with a system prompt that instructs it to
#      rewrite the raw_answer to fix the specific violation
#   2. Passes the user_query, raw_answer, violation type, and reason
#      as context in the user message
#   3. The rewritten answer must:
#        - Fix the violation flagged by the guardrail
#        - Preserve all accurate and useful information from the original
#        - Remain warm, professional, and helpful
#        - NOT simply delete the answer — it must still help the customer
#   4. Returns the rewritten answer text
#
# Think of the synthesizer as an editor, not a censor.
# Its job is to make the answer compliant, not to remove it.
# ─────────────────────────────────────────────────────────────────

def synthesizer(user_query, raw_answer, violation, reason):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 7 — Pipeline function
#
# Write a function called run_pipeline(user_query) that:
#
#   1. Calls router() and prints which agent was selected
#   2. Uses an if/elif/else block to call the correct agent function
#      and store the raw answer
#      If the label is unrecognised, return a polite fallback message
#   3. Calls guardrail() with the user_query and raw answer
#   4. If guardrail passes  → return the raw answer as-is
#   5. If guardrail fails   → print the violation and reason,
#                             call synthesizer() and return the rewritten answer
#
# Print clear status messages at each step so students can see
# the pipeline in action:
#   e.g. "🔀 Router → [investment]"
#        "✅ Guardrail passed"
#        "⚠️  Guardrail failed: specific_financial_advice — ..."
#        "✏️  Synthesizer rewriting..."
# ─────────────────────────────────────────────────────────────────

def run_pipeline(user_query):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 8 — main() function
#
# Write the main() function that:
#
#   SINGLE QUERY MODE (sys.argv has a second argument):
#     - Read the query from sys.argv[1]
#     - Call run_pipeline() with it
#     - Print the final answer with a clear header
#
#   INTERACTIVE MODE (no sys.argv argument):
#     - Print a welcome message explaining what RazBank support does
#     - Loop: prompt the user to type a query (or "quit" to exit)
#     - For each query, call run_pipeline() and print the final answer
#     - Exit cleanly when the user types "quit" or "exit"
#
# Then call main() inside the standard Python entry point guard.
# ─────────────────────────────────────────────────────────────────

def main():
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# Entry point — do not change this
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
