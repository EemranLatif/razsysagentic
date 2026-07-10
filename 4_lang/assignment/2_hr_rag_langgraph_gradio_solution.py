"""
HR Employee Handbook — RAG, rebuilt as a LangGraph graph (Gradio version)
=============================================================================
Run:  python hr_rag_langgraph_gradio.py
Deps: pip install langgraph gradio openai supabase python-dotenv

Same LangGraph pipeline as hr_rag_langgraph_console.py (retrieve -> grade ->
generate, with a rewrite_query retry loop capped at MAX_ATTEMPTS) -- this
file only swaps the console while-loop for the same Gradio Blocks UI from
hr_rag_app_v2.py, with one addition: the context panel now also shows the
grader's verdict and how many retrieval attempts were needed, since that
information didn't exist in v2 and is worth surfacing now that it does.
"""

import os
import re
from typing import TypedDict

import gradio as gr
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

from langgraph.graph import StateGraph, END

# ── Config (unchanged from v2) ──────────────────────────────────────────────
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

# ── Clients (unchanged from v2) ─────────────────────────────────────────────
supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
openai   = OpenAI(api_key=OPENAI_API_KEY)

WORD_RE = re.compile(r"[a-z]+")


# ── 1. STATE ─────────────────────────────────────────────────────────────────
class RAGState(TypedDict):
    query: str
    history: list
    chunks: list
    context: str
    answer: str
    attempts: int
    relevant: bool


# ── 2. CORE PIPELINE -- retrieval + rerank (identical to v2) ─────────────────
def get_embedding(text: str) -> list:
    response = openai.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding


def retrieve_context(query: str) -> list:
    query_embedding = get_embedding(query)
    result = supabase.rpc(TABLE_RPC, {
        "query_embedding": query_embedding,
        "match_threshold":  MATCH_THRESH,
        "match_count":      MATCH_COUNT,
    }).execute()
    candidates = result.data or []

    if not candidates:
        return []

    query_terms = set(WORD_RE.findall(query.lower()))
    for c in candidates:
        text_terms = set(WORD_RE.findall(c["content"].lower()))
        c["keyword_score"]  = len(query_terms & text_terms)
        c["combined_score"] = c["similarity"] + KEYWORD_WEIGHT * c["keyword_score"]

    candidates.sort(key=lambda c: c["combined_score"], reverse=True)
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


# ── 3-7. GRAPH NODES + ROUTER (identical to console version) ────────────────
def retrieve(state: RAGState) -> dict:
    chunks = retrieve_context(state["query"])
    context = build_context_block(chunks)
    return {
        "chunks": chunks,
        "context": context,
        "attempts": state["attempts"] + 1,
    }


def generate(state: RAGState) -> dict:
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
    return {"answer": response.choices[0].message.content.strip()}


def grade(state: RAGState) -> dict:
    if not state["chunks"]:
        return {"relevant": False}

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

    return {"relevant": "yes" in verdict}


def rewrite_query(state: RAGState) -> dict:
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
    return {"query": new_query}


def decide_after_grade(state: RAGState) -> str:
    if state["relevant"]:
        return "generate"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "generate"
    return "rewrite_query"


# ── 8. ASSEMBLE THE GRAPH ────────────────────────────────────────────────────
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
graph.add_edge("rewrite_query", "retrieve")
graph.add_edge("generate", END)

app = graph.compile()


# ── 9. Gradio-facing wrapper ──────────────────────────────────────────────────
def answer_question(query: str, history: list) -> tuple:
    """
    history is a list of {"role": ..., "content": ...} dicts (Gradio 6 native format),
    same as v2. Returns (cleared_input, updated_history, context_markdown).
    """
    if not query.strip():
        return "", history, ""

    original_query = query
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


# ── 10. Gradio UI (identical layout to v2) ────────────────────────────────────
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
