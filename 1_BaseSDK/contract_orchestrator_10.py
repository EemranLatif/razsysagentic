"""
RAZ Systems — Assignment: Orchestrator Pattern
==============================================
AI Contract Reviewer with Planner + Dynamic Fan-Out + Synthesizer

Run with:
    python contract_orchestrator.py sample_contract.pdf
    python contract_orchestrator.py my_contract.pdf

Read ASSIGNMENT_orchestrator.md before starting!
"""

# ─────────────────────────────────────────────────────────────────
# TASK 1 — Imports and setup
#
# You need:
#   - os, sys, json, threading  (all built-in)
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
#   - Opens the PDF using PdfReader
#   - Loops through every page and extracts the text
#   - Returns all the text concatenated into one string
#
# Tip: page.extract_text() may return None for some pages —
#      check before concatenating.
# ─────────────────────────────────────────────────────────────────

def extract_text(pdf_path):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 3 — Four specialist agent system prompts
#
# Create four string variables:
#
# EMPLOYMENT_PROMPT
#   An employment law specialist reviewing for:
#   employment clauses, compensation, non-compete restrictions,
#   termination conditions, and garden leave.
#   Must rate risk: Low / Medium / High.
#   Must flag any clause that is unusually restrictive.
#
# IP_PROMPT
#   An IP specialist reviewing for:
#   ownership of work product, work-for-hire clauses,
#   assignment of IP rights, pre-existing IP, and moral rights waiver.
#   Must rate risk: Low / Medium / High.
#   Must flag any clause where the signing party loses IP ownership.
#
# DATA_PRIVACY_PROMPT
#   A data privacy specialist reviewing for:
#   GDPR compliance, personal data handling, data transfers,
#   breach notification obligations, and retention/deletion.
#   Must rate risk: Low / Medium / High.
#   Must flag any clause that may violate privacy regulations.
#
# FAQ_PROMPT
#   A general contract specialist reviewing for:
#   scope of services, payment terms, liability caps,
#   termination rights, and overall contract balance.
#   Must rate risk: Low / Medium / High.
#
# All prompts should instruct the model to:
#   - Use clear headings
#   - Be concise and specific
#   - Only flag what is genuinely unusual or risky
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

FAQ_PROMPT = """
# YOUR CODE HERE
"""


# ─────────────────────────────────────────────────────────────────
# TASK 4 — Four specialist agent functions
#
# Write four functions following the SAME pattern:
#
#   employment_agent(contract_text, results, key)
#   ip_agent(contract_text, results, key)
#   data_privacy_agent(contract_text, results, key)
#   faq_agent(contract_text, results, key)
#
# Each function:
#   1. Calls gpt-4o-mini with the appropriate system prompt
#   2. Passes contract_text as the user message
#   3. Stores the response at results[key]
#
# Why results[key] and not return?
#   These run inside threads. Threads cannot return values to the
#   caller. A shared dictionary lets every thread write its result
#   to a named slot that the main thread reads after .join().
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


def faq_agent(contract_text, results, key):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 5 — Planner function
#
# Write a function called planner(contract_text) that:
#
#   1. Sends the FIRST 3000 characters of contract_text to gpt-4o-mini
#      (first 3000 chars is enough to classify the contract type —
#       no need to send the full text for this call)
#
#   2. Uses a system prompt that instructs the model to:
#        - Read the contract
#        - Return a JSON array of which agents are needed
#        - Valid values: "employment", "ip", "data_privacy", "faq"
#        - Return ONLY the JSON array — no markdown, no explanation
#
#   3. Parses the response with json.loads()
#   4. Returns the list of agent names
#
# Example return values:
#   ["faq"]
#   ["employment", "ip"]
#   ["employment", "ip", "data_privacy"]
#
# This is the key function that makes this an Orchestrator —
# the planner uses AI to make the routing decision dynamically,
# not hard-coded if/else logic.
# ─────────────────────────────────────────────────────────────────

def planner(contract_text):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 6 — Run selected agents in parallel (dynamic fan-out)
#
# Write a function called run_agents(contract_text, selected_agents)
# that:
#
#   1. Creates an empty results dictionary: results = {}
#   2. Creates an agent_map dictionary mapping names to functions:
#        {
#            "employment":   employment_agent,
#            "ip":           ip_agent,
#            "data_privacy": data_privacy_agent,
#            "faq":          faq_agent,
#        }
#   3. For each agent name in selected_agents:
#        - Look up the function in agent_map
#        - Create a threading.Thread with args=(contract_text, results, name)
#        - Add the thread to a threads list
#   4. Start ALL threads before joining any
#      (this is what makes them run in parallel — the fan-out)
#   5. Join all threads
#   6. Returns the results dictionary
#
# This function is the "fan-out" — the number of threads created
# depends entirely on what the planner returned, not hard-coded logic.
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
#   1. Builds a user message containing:
#        - The first 1000 chars of contract_text (for context)
#        - Each specialist's output, clearly labelled by agent name
#   2. Calls gpt-4o-mini with a system prompt instructing it to produce
#      a unified risk report with EXACTLY these four sections:
#        ## Overall Risk Level   (Low / Medium / High + one sentence why)
#        ## Key Findings         (sub-headings per specialist)
#        ## Top 3 Risks          (specific, referenced to actual clauses)
#        ## Recommendation       (Safe to Sign / Review Needed / Do Not Sign)
#   3. Returns the synthesized report text
# ─────────────────────────────────────────────────────────────────

def synthesizer(contract_text, agent_results):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 8 — Orchestrator function
#
# Write a function called orchestrator(contract_text) that:
#
#   1. Calls planner(contract_text) and stores the list of needed agents
#      Print which agents were selected
#
#   2. Calls run_agents(contract_text, selected_agents) to run them
#      in parallel
#      Print a status message when agents complete
#
#   3. Prints each specialist's output (labelled clearly)
#
#   4. Calls synthesizer(contract_text, agent_results) and returns
#      the final report
#
# This is the function that wires everything together.
# The orchestrator is NOT a router — it does not pick one path.
# It coordinates the planner, the fan-out, and the synthesizer.
# ─────────────────────────────────────────────────────────────────

def orchestrator(contract_text):
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# TASK 9 — main() function
#
# Write the main() function that:
#   1. Reads the PDF path from sys.argv[1]
#      If no argument provided, print usage message and exit
#   2. Checks the file exists (os.path.exists)
#   3. Calls extract_text() and prints the first 200 chars
#   4. Calls orchestrator() with the contract text
#   5. Prints the final report with a clear header
#
# Call main() inside the standard Python entry point guard.
# ─────────────────────────────────────────────────────────────────

def main():
    # YOUR CODE HERE
    pass


# ─────────────────────────────────────────────────────────────────
# Entry point — do not change this
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
