"""
RAZ Systems — Assignment: Router + Fan-Out + Synthesizer
=========================================================
AI Legal Contract Reviewer

Run with:
    python contract_reviewer.py sample_contract.pdf

Read ASSIGNMENT.md before starting!
"""

# ─────────────────────────────────────────────────────────────────
# TASK 1 — Imports and setup
#
# You need:
#   - os, sys, json, threading (all built-in, no pip needed)
#   - load_dotenv from dotenv
#   - OpenAI from openai
#   - PdfReader from pypdf
#
# After importing:
#   - Call load_dotenv(override=True)
#   - Create an OpenAI client called `openai`
# ─────────────────────────────────────────────────────────────────

# YOUR CODE HERE




# ─────────────────────────────────────────────────────────────────
# TASK 2 — PDF text extraction
#
# Write a function called extract_text(pdf_path) that:
#   - Opens the PDF at pdf_path using PdfReader
#   - Loops through every page and extracts the text
#   - Returns all the text joined into one string
#
# Hint: page.extract_text() may return None for some pages —
#       check for this before concatenating.
# ─────────────────────────────────────────────────────────────────

def extract_text(pdf_path):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 3 — Specialist agent system prompts
#
# Create three string variables:
#
# EMPLOYMENT_PROMPT
#   An employment law specialist who reviews contracts for:
#   employment clauses, termination conditions, non-compete clauses,
#   liability, and worker rights issues.
#   Asks the model to list findings under clear headings and flag
#   any clauses that are unusual or risky.
#
# IP_PROMPT
#   An IP and copyright specialist who reviews contracts for:
#   intellectual property ownership, work-for-hire clauses,
#   licensing terms, and rights over created work.
#   Should flag any clauses where the signing party gives up IP rights.
#
# DATA_PRIVACY_PROMPT
#   A data privacy specialist who reviews contracts for:
#   data handling practices, GDPR compliance, confidentiality clauses,
#   and any sharing of personal data with third parties.
#   Should flag any clauses that may violate privacy regulations.
#
# All three prompts should instruct the model to:
#   - Structure the response with clear headings
#   - Rate the risk level as Low / Medium / High
#   - Be concise and specific — no filler text
# ─────────────────────────────────────────────────────────────────

EMPLOYMENT_PROMPT = """
# YOUR CODE HERE
"""

IP_PROMPT = """
# YOUR CODE HERE
"""

DATA_PRIVACY_PROMPT = """
# YOUR CODE HERE
"""


# ─────────────────────────────────────────────────────────────────
# TASK 4 — Specialist agent functions
#
# Write three functions, all following the same pattern:
#
#   employment_agent(contract_text, results, key)
#   ip_agent(contract_text, results, key)
#   data_privacy_agent(contract_text, results, key)
#
# Each function must:
#   1. Call gpt-4o-mini with the appropriate system prompt
#   2. Pass contract_text as the user message
#   3. Store the response text at results[key]
#
# Why results[key] instead of return?
#   These functions will be run inside threads. Threads cannot
#   return values to the caller. Instead we write into a shared
#   dictionary so the main thread can read the results after
#   all threads have finished.
# ─────────────────────────────────────────────────────────────────

def employment_agent(contract_text, results, key):
    # YOUR CODE HERE
    pass


def ip_agent(contract_text, results, key):
    # YOUR CODE HERE
    pass


def data_privacy_agent(contract_text, results, key):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 5 — Router function
#
# Write a function called router(contract_text) that:
#
#   1. Sends the contract text to gpt-4o-mini
#   2. Uses a system prompt that tells the model to read the contract
#      and return a JSON list of which specialists are needed.
#      The only valid values are: "employment", "ip", "data_privacy"
#      Example outputs:
#        ["employment", "ip"]
#        ["data_privacy"]
#        ["employment", "ip", "data_privacy"]
#   3. Instructs the model to return ONLY valid JSON — no explanation,
#      no markdown, no code fences
#   4. Parses the response with json.loads()
#   5. Returns the list of strings
#
# Tip: pass only the first 3000 characters of the contract to the
#      router to keep the call fast and cheap. The router just needs
#      enough to understand what type of contract it is.
# ─────────────────────────────────────────────────────────────────

def router(contract_text):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 6 — Run selected agents in parallel
#
# Write a function called run_agents(contract_text, selected_agents)
# that:
#
#   1. Creates an empty results dictionary: results = {}
#   2. Builds a mapping from agent name to function, e.g.:
#        agent_map = {
#            "employment":   employment_agent,
#            "ip":           ip_agent,
#            "data_privacy": data_privacy_agent,
#        }
#   3. Creates a threading.Thread for each agent in selected_agents,
#      passing contract_text, results, and the agent name as key
#   4. Starts ALL threads before joining any
#      (this is what makes them run in parallel)
#   5. Joins all threads
#   6. Returns the results dictionary
#
# Example: if selected_agents = ["employment", "ip"]
#   - results will end up as {"employment": "...", "ip": "..."}
# ─────────────────────────────────────────────────────────────────

def run_agents(contract_text, selected_agents):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 7 — Synthesizer
#
# Write a function called synthesizer(contract_text, agent_results)
# that:
#
#   1. Builds a user message that includes:
#        - The original contract text (first 1000 chars is enough)
#        - Each specialist's output, clearly labelled
#   2. Calls gpt-4o-mini with a system prompt that instructs it to
#      produce a unified risk report with these exact sections:
#        ## Overall Risk Level  (Low / Medium / High)
#        ## Key Findings
#        ## Top 3 Risks
#        ## Recommendation  (Safe to Sign / Review Needed / Do Not Sign)
#   3. Returns the synthesized report text
#
# The synthesizer should feel like a senior lawyer who has read all
# the specialist reports and is giving you a final verdict.
# ─────────────────────────────────────────────────────────────────

def synthesizer(contract_text, agent_results):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 8 — main() function
#
# Write the main() function that wires everything together:
#
#   1. Read the PDF path from sys.argv[1]
#      If no argument is provided, print a usage message and exit.
#
#   2. Call extract_text() to get the contract text.
#      Print the first 200 characters as a sanity check.
#
#   3. Call router() and print which agents were selected.
#
#   4. Call run_agents() with the contract text and selected agents.
#      Print a message as each agent completes
#      (hint: you can print after run_agents returns).
#
#   5. Call synthesizer() with the contract text and results.
#
#   6. Print the final report with a clear header.
#
# Then at the bottom of the file, call main() inside the standard
# Python entry point guard.
# ─────────────────────────────────────────────────────────────────

def main():
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# Entry point — do not change this
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
