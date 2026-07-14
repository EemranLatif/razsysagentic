"""
HR Employee Handbook — RAG, rebuilt as a LangGraph graph (console version, no Gradio)
=======================================================================================
Run:  python hr_rag_langgraph_console.py
Deps: pip install langgraph openai supabase python-dotenv

What this is
------------
A LangGraph rebuild of hr_rag_app_v2.py's retrieval + rerank + answer pipeline.
Same Supabase RPC call, same MATCH_THRESH/MATCH_COUNT/TOP_K/KEYWORD_WEIGHT fix,
same keyword-overlap reranking logic -- none of that changed. What changed is
the orchestration: instead of one straight-line Python function, the pipeline
is now a graph with an explicit retrieve -> grade -> generate flow, and a real
retry loop if the first retrieval doesn't look relevant.

Two layers, clearly separated below:
  1. CORE PIPELINE   -- a faithful 1:1 port of v2's retrieve_context() +
                         build_context_block() + the OpenAI chat call, just
                         expressed as two graph nodes (retrieve, generate)
                         instead of one function. Behavior is unchanged.
  2. SELF-CORRECTING -- a NEW addition: a grade node that checks whether the
     UPGRADE            retrieved chunks actually look relevant to the
                         question, and a router that retries with a rewritten
                         query if not (same MAX_ATTEMPTS-in-code pattern as
                         the V1/V3 travel agent's decide() function).

If you only want the 1:1 port with no new behavior, skip Sections 5-6 (grade
node + conditional routing) and wire retrieve -> generate -> END directly --
the comment above the graph-assembly section shows exactly which lines to
remove to do that.
"""

import os
import re
from typing import TypedDict

from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

from langgraph.graph import StateGraph, END

# ── Config (unchanged from v2) ──────────────────────────────────────────────
load_dotenv(override=True)

SUPABASE_URL     = "https://ssrxdvbnjfruzikvages.supabase.co"
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")

EMBED_MODEL  = "text-embedding-3-small"
CHAT_MODEL   = "gpt-4o-mini"
TABLE_RPC    = "match_hr_documents"

MATCH_THRESH = 0.3     # was 0.7 -- real scores cluster around 0.5-0.6
MATCH_COUNT  = 15      # wide candidate pool, reranked below
TOP_K        = 5       # how many chunks we actually keep/show after rerank
KEYWORD_WEIGHT = 0.05  # bonus added per literal query-word match in a chunk

MAX_ATTEMPTS = 2        # NEW (self-correcting upgrade): cap retrieval retries
RELEVANCE_CHECK_MODEL = CHAT_MODEL

# ── Clients (unchanged from v2) ─────────────────────────────────────────────
supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
openai   = OpenAI(api_key=OPENAI_API_KEY)

WORD_RE = re.compile(r"[a-z]+")


# ── 1. STATE ─────────────────────────────────────────────────────────────────
# Everything the graph tracks as it runs. Compare to TravelState / State in
# the LangGraph travel-agent notebooks -- same TypedDict pattern.
class RAGState(TypedDict):
    query: str           # the user's question
    history: list         # prior turns, as [{"role":..., "content":...}, ...]
    chunks: list           # retrieved (and reranked) handbook chunks
    context: str          # chunks formatted into a single context block
    answer: str           # the model's final answer
    attempts: int          # NEW: how many retrieval attempts so far
    relevant: bool         # NEW: did the grader judge the chunks relevant?


# ── 2. CORE PIPELINE -- retrieval + rerank (1:1 port of v2's retrieve_context) ──
def get_embedding(text: str) -> list:
    response = openai.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding


def retrieve_context(query: str) -> list:
    """Retrieve a wide candidate pool by vector similarity, then rerank by
    adding a small bonus for literal word overlap with the query. Returns
    the top TOP_K chunks after reranking. Identical logic to v2."""
    query_embedding = get_embedding(query)
    result = supabase.rpc(TABLE_RPC, {
        "query_embedding": query_embedding,
        "match_threshold":  MATCH_THRESH,
        "match_count":      MATCH_COUNT,
    }).execute()
    candidates = result.data or []

    if not candidates:
        return []
    # example query: "python coding"
    # Extract unique keyword terms from the (lowercased) query.
    # query.lower() -> "python coding"
    # WORD_RE.findall(...) -> ["python", "coding"]
    # set(...) -> {"python", "coding"}
    # Let's create 3 candidate documents. Each candidate is a dictionary with:
    # - "content": the actual text
    # - "similarity": a pre-calculated semantic/vector similarity score (0.0 to 1.0)
    #candidates = [
    #    {"content": "I love python", "similarity": 0.8},
    #    {"content": "coding in java", "similarity": 0.9},
    #    {"content": "python coding is fun", "similarity": 0.5},
    #]
    
    query_terms = set(WORD_RE.findall(query.lower()))
    for c in candidates:
        # Extract unique keyword terms from the (lowercased) content of this candidate.
        # For c1: "i love python" -> {"i", "love", "python"}
        # For c2: "coding in java" -> {"coding", "in", "java"}
        # For c3: "python coding is fun" -> {"python", "coding", "is", "fun"}
        text_terms = set(WORD_RE.findall(c["content"].lower()))
        # Count how many query terms appear in this candidate's content.
        # The & operator computes the intersection (common terms) of both sets.
        # len(...) gives the number of overlapping keywords.
        #
        # c1: {"python", "coding"} & {"i","love","python"} = {"python"} -> score = 1
        # c2: {"python", "coding"} & {"coding","in","java"} = {"coding"} -> score = 1
        # c3: {"python", "coding"} & {"python","coding","is","fun"} = {"python","coding"} -> score = 2
        c["keyword_score"]  = len(query_terms & text_terms)
        # Calculate the final combined score:
        # similarity  +  (KEYWORD_WEIGHT * keyword_score)
        # With KEYWORD_WEIGHT = 1.0:
        # c1: 0.8 + (1.0 * 1) = 1.8
        # c2: 0.9 + (1.0 * 1) = 1.9
        # c3: 0.5 + (1.0 * 2) = 2.5   <--- c3 wins because both keywords match!
        c["combined_score"] = c["similarity"] + KEYWORD_WEIGHT * c["keyword_score"]
    # lambda c: c["combined_score"] is a tiny function that takes a candidate
    # dictionary 'c' and returns its "combined_score" value.
    # reverse=True ensures the largest scores come first.
    candidates.sort(key=lambda c: c["combined_score"], reverse=True)
    # how lamda works
    #def get_combined_score(candidate):
        #"""Return the combined_score value from a candidate dictionary."""
        #return candidate["combined_score"]
    # Uncomment the line below to use the regular function instead of the lambda.
    # candidates.sort(key=get_combined_score, reverse=True)
    return candidates[:TOP_K]


def build_context_block(chunks: list) -> str:
    if not chunks:
        return "No relevant sections found in the handbook."
    parts = []
    for c in chunks:
        parts.append(
            f"[Page {c['page_number']}, chunk {c['chunk_index']} | "
            f"similarity {c['similarity']:.2f}]\n{c['content']}"
        )
    return "\n\n---\n\n".join(parts)


# ── 3. NODE: retrieve ────────────────────────────────────────────────────────
# Wraps retrieve_context() + build_context_block() as a graph node. Same
# logic as v2's step 1, just returning a state update instead of a local
# variable.
def retrieve(state: RAGState) -> dict:
    print(f"\n🔍 RETRIEVE (attempt {state['attempts'] + 1}) — query: {state['query']!r}")

    chunks = retrieve_context(state["query"])
    context = build_context_block(chunks)

    print(f"   → {len(chunks)} chunks retrieved")

    return {
        "chunks": chunks,
        "context": context,
        "attempts": state["attempts"] + 1,
    }


# ── 4. NODE: generate ────────────────────────────────────────────────────────
# 1:1 port of v2's OpenAI chat call (step 2-3 of answer_question). Same
# system prompt, same message construction, same model/temperature.
def generate(state: RAGState) -> dict:
    print("✍️  GENERATE — calling the chat model with retrieved context")

    system_prompt = (
        "You are a helpful HR assistant. Answer the employee's question "
        "using ONLY the handbook excerpts provided below. "
        "If the answer is not in the excerpts, say so clearly. "
        "Be concise and professional.\n\n"
        f"=== HANDBOOK EXCERPTS ===\n{state['context']}\n=== END OF EXCERPTS ==="
    )
    messages = [{"role": "system", "content": system_prompt}]
    for turn in state["history"]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": state["query"]})

    response = openai.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    reply = response.choices[0].message.content.strip()

    return {"answer": reply}


# ── 5. NODE: grade  (SELF-CORRECTING UPGRADE -- new vs. v2) ──────────────────
# v2 has no equivalent of this step -- it always generates from whatever
# retrieve_context() returned, even if every chunk was off-topic. This node
# asks the model itself whether the retrieved chunks look relevant, the same
# way you'd grade documents in any self-correcting RAG setup.
def grade(state: RAGState) -> dict:
    if not state["chunks"]:
        print("⚖️  GRADE — no chunks retrieved, marking as not relevant")
        return {"relevant": False}

    print("⚖️  GRADE — checking retrieved chunks against the question")

    grading_prompt = (
        f"Question: {state['query']}\n\n"
        f"Retrieved handbook excerpts:\n{state['context']}\n\n"
        "Do these excerpts contain information that could answer the question? "
        "Reply with exactly one word: yes or no."
    )
    verdict = openai.chat.completions.create(
        model=RELEVANCE_CHECK_MODEL,
        messages=[{"role": "user", "content": grading_prompt}],
        temperature=0,
    ).choices[0].message.content.strip().lower()

    relevant = "yes" in verdict
    print(f"   → grader verdict: {'relevant' if relevant else 'not relevant'}")

    return {"relevant": relevant}


# ── 6. NODE: rewrite_query  (SELF-CORRECTING UPGRADE -- new vs. v2) ──────────
# If the grader says the chunks aren't relevant and we haven't hit
# MAX_ATTEMPTS, rewrite the query before retrying -- same idea as V1/V3's
# "cheaper" hint on a retry, applied to query phrasing instead of price.
def rewrite_query(state: RAGState) -> dict:
    print(f"✏️  REWRITE_QUERY — original query didn't retrieve relevant chunks, rephrasing")

    rewrite_prompt = (
        f"This search query did not retrieve relevant results from an HR handbook: "
        f"{state['query']!r}\n\n"
        "Rewrite it as a clearer, more specific search query likely to match handbook "
        "language (e.g. policy section headings). Reply with ONLY the rewritten query."
    )
    new_query = openai.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": rewrite_prompt}],
        temperature=0.3,
    ).choices[0].message.content.strip()

    print(f"   → rewritten query: {new_query!r}")

    return {"query": new_query}


# ── 7. ROUTER  (SELF-CORRECTING UPGRADE -- new vs. v2) ───────────────────────
# Real Python control flow, not a prompt instruction -- same MAX_ATTEMPTS
# pattern as decide() in the travel-agent notebooks. Guarantees the retry
# loop terminates regardless of what the grader says.
def decide_after_grade(state: RAGState) -> str:
    if state["relevant"]:
        return "generate"
    if state["attempts"] >= MAX_ATTEMPTS:
        print(f"⛔ MAX_ATTEMPTS ({MAX_ATTEMPTS}) reached — generating from best-effort context anyway")
        return "generate"
    return "rewrite_query"


# ── 8. ASSEMBLE THE GRAPH ────────────────────────────────────────────────────
# To get the plain 1:1 port with NO new behavior (matches v2 exactly):
#   delete the grade/rewrite_query node registrations and conditional edge
#   below, and replace them with a single line:
#       graph.add_edge("retrieve", "generate")
#
# As shipped, this includes the self-correcting upgrade:
graph = StateGraph(RAGState)

graph.add_node("retrieve", retrieve)
graph.add_node("grade", grade)
graph.add_node("rewrite_query", rewrite_query)
graph.add_node("generate", generate)

graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "grade")
graph.add_conditional_edges("grade", decide_after_grade, {
    "generate": "generate",
    "rewrite_query": "rewrite_query",
})
graph.add_edge("rewrite_query", "retrieve")  # loop back, same shape as the travel agent's retry
graph.add_edge("generate", END)

app = graph.compile()


# ── 9. CONSOLE CHAT LOOP ──────────────────────────────────────────────────────
def ask(query: str, history: list) -> tuple:
    """Runs the graph for one question, returns (answer, updated_history, chunks)."""
    result = app.invoke({
        "query": query,
        "history": history,
        "chunks": [],
        "context": "",
        "answer": "",
        "attempts": 0,
        "relevant": False,
    })

    updated_history = history + [
        {"role": "user", "content": query},
        {"role": "assistant", "content": result["answer"]},
    ]
    return result["answer"], updated_history, result["chunks"]


if __name__ == "__main__":
    print("📋 HR Employee Handbook Assistant — LangGraph console version")
    print("Type a question, or 'quit' to exit.\n")

    history: list = []

    while True:
        query = input("You: ").strip()
        if not query:
            continue
        if query.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        answer, history, chunks = ask(query, history)

        print(f"\nAssistant: {answer}\n")
        if chunks:
            print(f"  (answered using {len(chunks)} retrieved chunk(s))")
        print()
