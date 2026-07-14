"""
HR Employee Handbook — RAG, rebuilt as a LangGraph graph (Gradio version)
=============================================================================
ASSIGNMENT — fill in the TODOs below.

Run:  python hr_rag_langgraph_gradio_ASSIGNMENT.py
Deps: pip install langgraph gradio openai supabase python-dotenv

Same LangGraph pipeline as the console version (retrieve -> grade -> generate,
with a rewrite_query retry loop capped at MAX_ATTEMPTS) -- this file uses the
Gradio Blocks UI, with the context panel also showing the grader's verdict and
how many retrieval attempts were needed.

YOUR TASK:
Fill in the TODOs to build the retrieval pipeline, the four LangGraph nodes,
the conditional router, the graph assembly, and the Gradio-facing wrapper
that invokes the graph.
"""

import os
import re
from typing import TypedDict

import gradio as gr
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

from langgraph.graph import StateGraph, END

# ── Config (given -- no changes needed here) ────────────────────────────────
load_dotenv(override=True)

SUPABASE_URL     = "https://ssrxdvbnjfruzikvages.supabase.co"
SUPABASE_API_KEY = os.getenv("SUBABASE_API_KEY")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")

EMBED_MODEL  = "text-embedding-3-small"
CHAT_MODEL   = "gpt-4o-mini"
TABLE_RPC    = "match_hr_documents"

MATCH_THRESH = 0.3
MATCH_COUNT  = 15
TOP_K        = 5
KEYWORD_WEIGHT = 0.05

MAX_ATTEMPTS = 2
RELEVANCE_CHECK_MODEL = CHAT_MODEL

# ── Clients (given -- no changes needed here) ───────────────────────────────
supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
openai   = OpenAI(api_key=OPENAI_API_KEY)

WORD_RE = re.compile(r"[a-z]+")


# ── 1. STATE ─────────────────────────────────────────────────────────────────
# TODO 1: Define RAGState as a TypedDict with these fields:
#   query: str            -- the current search query (may get rewritten)
#   history: list          -- prior chat turns, [{"role": ..., "content": ...}, ...]
#   chunks: list            -- retrieved handbook chunks from the last retrieve
#   context: str            -- chunks formatted into one text block for the LLM
#   answer: str             -- the generated answer
#   attempts: int           -- how many times retrieve has run so far
#   relevant: bool          -- the grader's verdict on the latest chunks
class RAGState(TypedDict):
    pass


# ── 2. CORE PIPELINE -- retrieval + rerank ───────────────────────────────────
def get_embedding(text: str) -> list:
    # TODO 2: Call openai.embeddings.create(model=EMBED_MODEL, input=text)
    # and return the embedding vector (response.data[0].embedding).
    pass


def retrieve_context(query: str) -> list:
    """
    Embeds the query, calls the Supabase RPC to get candidate chunks, then
    reranks them by combining vector similarity with a simple keyword-overlap
    score before returning the top TOP_K.
    """
    # TODO 3: Get the query embedding using get_embedding(query).
    query_embedding = None

    # TODO 4: Call supabase.rpc(TABLE_RPC, {...}).execute() with:
    #   "query_embedding": query_embedding
    #   "match_threshold": MATCH_THRESH
    #   "match_count": MATCH_COUNT
    # Store the result, then pull out result.data (or [] if it's falsy) as
    # `candidates`.
    candidates = []

    if not candidates:
        return []

    # TODO 5: Compute a keyword overlap score for each candidate:
    # - Extract lowercase word sets from the query and from each candidate's
    #   "content" field using WORD_RE.findall(...)
    # - Set candidate["keyword_score"] = size of the set intersection
    # - Set candidate["combined_score"] = candidate["similarity"]
    #   + KEYWORD_WEIGHT * candidate["keyword_score"]
    query_terms = set()
    for c in candidates:
        pass

    # TODO 6: Sort candidates by "combined_score" descending, and return only
    # the top TOP_K.
    return candidates


def build_context_block(chunks: list) -> str:
    # TODO 7: If chunks is empty, return a message saying nothing relevant
    # was found. Otherwise, format each chunk as:
    #   "[Page {page_number}, chunk {chunk_index} | similarity {similarity:.2f}]\n{content}"
    # and join them all together with "\n\n---\n\n" between chunks.
    pass


# ── 3-7. GRAPH NODES + ROUTER ─────────────────────────────────────────────────
def retrieve(state: RAGState) -> dict:
    """LangGraph node: runs one retrieval attempt and bumps the attempt
    counter."""
    # TODO 8: Call retrieve_context(state["query"]) to get chunks, then
    # build_context_block(chunks) to get the context string. Return a dict
    # with "chunks", "context", and "attempts" (state["attempts"] + 1).
    pass


def generate(state: RAGState) -> dict:
    """LangGraph node: generates the final answer using the retrieved
    context and prior conversation history."""
    # TODO 9: Build a system prompt instructing the model to answer ONLY
    # from state["context"], and to say so clearly if the answer isn't in
    # the excerpts. Include the context block in the system prompt.
    system_prompt = ""

    # TODO 10: Build the full messages list: start with the system prompt,
    # then append every turn in state["history"] (each turn already has
    # "role" and "content" keys), then append the current user query as the
    # final message.
    messages = [{"role": "system", "content": system_prompt}]

    # TODO 11: Call openai.chat.completions.create(model=CHAT_MODEL,
    # messages=messages, temperature=0.2) and return {"answer": ...} with
    # the stripped response text.
    pass


def grade(state: RAGState) -> dict:
    """LangGraph node: asks the LLM whether the retrieved chunks actually
    answer the question."""
    if not state["chunks"]:
        return {"relevant": False}

    # TODO 12: Build a grading prompt that includes the question and the
    # retrieved context, and asks the model to reply with exactly one word:
    # "yes" or "no".
    grading_prompt = ""

    # TODO 13: Call the chat model with temperature=0, get the verdict text
    # (lowercased, stripped), and return {"relevant": True/False} based on
    # whether "yes" appears in the verdict.
    pass


def rewrite_query(state: RAGState) -> dict:
    """LangGraph node: asks the LLM to rewrite the query to better match
    handbook language, when the first attempt's chunks weren't relevant."""
    # TODO 14: Build a prompt telling the model the current query didn't
    # retrieve relevant results, and asking it to rewrite the query to be
    # clearer and more likely to match handbook section headings. Reply with
    # ONLY the rewritten query.
    rewrite_prompt = ""

    # TODO 15: Call the chat model with temperature=0.3, and return
    # {"query": <rewritten query, stripped>}.
    pass


def decide_after_grade(state: RAGState) -> str:
    """Conditional edge: decides whether to generate an answer now, or
    retry retrieval with a rewritten query."""
    # TODO 16: If state["relevant"] is True, return "generate".
    # If state["attempts"] has reached MAX_ATTEMPTS, also return "generate"
    # (give up retrying and answer with the best chunks we have).
    # Otherwise, return "rewrite_query".
    pass


# ── 8. ASSEMBLE THE GRAPH ────────────────────────────────────────────────────
graph = StateGraph(RAGState)

# TODO 17: Register all four nodes: "retrieve", "grade", "rewrite_query",
# "generate", each mapped to its function above.

# TODO 18: Set the entry point to "retrieve".

# TODO 19: Wire the edges:
# - "retrieve" -> "grade" (plain edge)
# - "grade" -> conditional, using decide_after_grade, with path_map
#   {"generate": "generate", "rewrite_query": "rewrite_query"}
# - "rewrite_query" -> "retrieve" (plain edge -- this is the retry loop)
# - "generate" -> END (plain edge)

app = graph.compile()


# ── 9. Gradio-facing wrapper ──────────────────────────────────────────────────
def answer_question(query: str, history: list) -> tuple:
    """
    history is a list of {"role": ..., "content": ...} dicts (Gradio 6 native
    format). Returns (cleared_input, updated_history, context_markdown).
    """
    if not query.strip():
        return "", history, ""

    original_query = query

    # TODO 20: Call app.invoke(...) with the initial state dict:
    # query=query, history=history, chunks=[], context="", answer="",
    # attempts=0, relevant=False. Store the result.
    result = {}

    updated_history = history + [
        {"role": "user", "content": original_query},
        {"role": "assistant", "content": result["answer"]},
    ]

    chunks = result["chunks"]
    if chunks:
        ctx_md = "### 📄 Retrieved Handbook Sections\n\n"
        ctx_md += (
            f"_Resolved after {result['attempts']} retrieval attempt(s) "
            f"· grader verdict: {'relevant' if result['relevant'] else 'best-effort (max attempts reached)'}_\n\n"
        )
        for c in chunks:
            snippet = c["content"][:350] + ("…" if len(c["content"]) > 350 else "")
            ctx_md += (
                f"**Page {c['page_number']} · chunk {c['chunk_index']} "
                f"· similarity {c['similarity']:.2f} · keyword hits {c['keyword_score']}**\n\n"
                f"> {snippet}\n\n---\n\n"
            )
    else:
        ctx_md = "_No matching handbook sections found for this query, even after retries._"

    return "", updated_history, ctx_md


# ── 10. Gradio UI (given -- no changes needed here) ──────────────────────────
with gr.Blocks(title="HR Handbook Assistant (LangGraph)") as demo:

    gr.Markdown(
        """
        # 📋 HR Employee Handbook Assistant — LangGraph version
        Ask any question about company policies, procedures, or benefits.
        Answers are grounded in the official employee handbook, with a
        self-correcting retrieval step that retries with a rewritten query
        if the first search doesn't look relevant.
        """
    )

    history_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="Conversation", height=480)
            with gr.Row():
                question_box = gr.Textbox(
                    placeholder="e.g. How do I request payroll deduction changes?",
                    label="Your question",
                    lines=2,
                    scale=5,
                )
                submit_btn = gr.Button("Ask ➤", variant="primary", scale=1)
            clear_btn = gr.Button("🗑 Clear conversation", variant="secondary")

        with gr.Column(scale=2):
            context_panel = gr.Markdown(
                value="_Retrieved handbook sections will appear here._",
                label="Source Sections",
            )

    gr.Examples(
        examples=[
            "How do I address the board of education at a meeting?",
            "sick leave policy?",
            "How many days notice is needed to get on the board meeting agenda?",
            "Can I stop dues deductions to a professional organization?",
            "what is termination policy?",
        ],
        inputs=question_box,
        label="Example questions",
    )

    def on_submit(query, history):
        empty_input, new_history, ctx_md = answer_question(query, history)
        return empty_input, new_history, new_history, ctx_md

    def on_clear():
        return [], [], "_Retrieved handbook sections will appear here._"

    submit_btn.click(
        fn=on_submit,
        inputs=[question_box, history_state],
        outputs=[question_box, history_state, chatbot, context_panel],
    )
    question_box.submit(
        fn=on_submit,
        inputs=[question_box, history_state],
        outputs=[question_box, history_state, chatbot, context_panel],
    )
    clear_btn.click(
        fn=on_clear,
        outputs=[history_state, chatbot, context_panel],
    )

if __name__ == "__main__":
    demo.launch(share=False, theme=gr.themes.Soft(primary_hue="blue"))


# ─────────────────────────────────────────────────────
# REFLECTION QUESTIONS
# ─────────────────────────────────────────────────────
#
# 1. decide_after_grade checks state["attempts"] >= MAX_ATTEMPTS as a
#    fallback even when relevant is False. Why is this safety check needed --
#    what would happen without it if the grader kept saying "no" forever?
#
# 2. rewrite_query returns a new "query" value that overwrites the old one in
#    state. Trace through the graph: after rewrite_query -> retrieve loops
#    back, which query does retrieve_context actually search with -- the
#    original, or the rewritten one? How does the state update mechanism
#    make that happen automatically?
#
# 3. The context panel's message distinguishes "relevant" from "best-effort
#    (max attempts reached)". From a user's perspective, why is it valuable
#    to surface that distinction rather than just always showing the answer
#    with no indication of how confident the retrieval was?
