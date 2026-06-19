"""
HR Employee Handbook — RAG Chatbot (v2)
Run:  python hr_rag_app_v2.py
Deps: pip install gradio openai supabase python-dotenv

What changed from v1
---------------------
- MATCH_THRESH lowered from 0.7 to 0.3. Real similarity scores for this handbook
  cluster around 0.5-0.6, so a 0.7 floor was filtering out every chunk and
  retrieve_context() always returned empty -> "no relevant sections" -> the
  model had nothing to answer from.
- MATCH_COUNT widened to 15 candidates, then reranked and trimmed to TOP_K (5)
  using a keyword-overlap boost (same technique used in the notebook), so the
  wider net doesn't just let in noise.
- Point this app at an hr_documents table populated by the heading-aware
  chunking notebook (v2) for best results — the threshold fix alone stops the
  "no response" problem, but better chunks make the retrieved sections sharper.
"""

import os
import re

import gradio as gr
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv(override=True)

SUPABASE_URL     = "https://ssrxdvbnjfruzikvages.supabase.co"
SUPABASE_API_KEY = os.getenv("SUBABASE_API_KEY")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")

EMBED_MODEL  = "text-embedding-3-small"
CHAT_MODEL   = "gpt-4o-mini"
TABLE_RPC    = "match_hr_documents"

MATCH_THRESH = 0.3     # was 0.7 — real scores cluster around 0.5-0.6
MATCH_COUNT  = 15      # wide candidate pool, reranked below
TOP_K        = 5       # how many chunks we actually keep/show after rerank
KEYWORD_WEIGHT = 0.05  # bonus added per literal query-word match in a chunk

# ── Clients ───────────────────────────────────────────────────────────────────
supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
openai   = OpenAI(api_key=OPENAI_API_KEY)

WORD_RE = re.compile(r"[a-z]+")

# ── RAG helpers ───────────────────────────────────────────────────────────────
def get_embedding(text: str) -> list:
    response = openai.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding

# ── Worked example: why the keyword rerank matters ───────────────────────────
#
# Query: "what is termination policy?"
#
# Chunk A: "...TERMINATION OF EMPLOYMENT...notices of termination
#           will be made per policy..."
#   similarity    = 0.556
#   shared words  = {"termination", "policy"}
#   keyword_score = 2
#   combined_score = 0.556 + (0.05 * 2) = 0.556 + 0.10 = 0.656
#
# Chunk B: "Students violating this policy will be disciplined..."
#   similarity    = 0.597
#   shared words  = {"policy"}
#   keyword_score = 1
#   combined_score = 0.597 + (0.05 * 1) = 0.597 + 0.05 = 0.647
#
# Before rerank: Chunk B ranks #1 (0.597 > 0.556) — wrong chunk, about
#                student discipline, not employee termination.
#
# After rerank:  Chunk A ranks #1 (0.656 > 0.647) — the keyword bonus
#                flips the order because Chunk A actually contains the
#                word "termination", not just "policy".
# ───────────────────────────────────────────────────────────────────────────

def retrieve_context(query: str) -> list:
    """Retrieve a wide candidate pool by vector similarity, then rerank by
    adding a small bonus for literal word overlap with the query. Returns
    the top TOP_K chunks after reranking."""
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


def answer_question(query: str, history: list) -> tuple:
    """
    history is a list of {"role": ..., "content": ...} dicts (Gradio 6 native format).
    Returns (cleared_input, updated_history, context_markdown).
    """
    if not query.strip():
        return "", history, ""

    # 1. Retrieve relevant chunks (wide pool -> keyword rerank -> top_k)
    chunks  = retrieve_context(query)
    context = build_context_block(chunks)

    # 2. Build OpenAI messages
    system_prompt = (
        "You are a helpful HR assistant. Answer the employee's question "
        "using ONLY the handbook excerpts provided below. "
        "If the answer is not in the excerpts, say so clearly. "
        "Be concise and professional.\n\n"
        f"=== HANDBOOK EXCERPTS ===\n{context}\n=== END OF EXCERPTS ==="
    )
    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": query})

    # 3. Call OpenAI Chat Completions
    response = openai.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    reply = response.choices[0].message.content.strip()

    # 4. Append to history in Gradio 6 native format
    updated_history = history + [
        {"role": "user",      "content": query},
        {"role": "assistant", "content": reply},
    ]

    # 5. Build context panel markdown
    if chunks:
        ctx_md = "### 📄 Retrieved Handbook Sections\n\n"
        for c in chunks:
            snippet = c["content"][:350] + ("…" if len(c["content"]) > 350 else "")
            ctx_md += (
                f"**Page {c['page_number']} · chunk {c['chunk_index']} "
                f"· similarity {c['similarity']:.2f} · keyword hits {c['keyword_score']}**\n\n"
                f"> {snippet}\n\n---\n\n"
            )
    else:
        ctx_md = "_No matching handbook sections found for this query._"

    return "", updated_history, ctx_md


# ── Gradio UI ─────────────────────────────────────────────────────────────────
with gr.Blocks(title="HR Handbook Assistant") as demo:

    gr.Markdown(
        """
        # 📋 HR Employee Handbook Assistant
        Ask any question about company policies, procedures, or benefits.
        Answers are grounded in the official employee handbook.
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

    # ── Event wiring ──────────────────────────────────────────────────────────
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

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demo.launch(share=False, theme=gr.themes.Soft(primary_hue="blue"))
