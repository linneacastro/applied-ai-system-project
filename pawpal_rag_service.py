"""RAG service: holds the index and LLM client, returns grounded explanations.

The index is built once at construction so apps (e.g. Streamlit) can hold a
single instance and call explain() repeatedly without reloading the model.
"""

from anthropic import Anthropic
from dotenv import load_dotenv

from pawpal_rag import build_index, retrieve

load_dotenv()

MODEL_NAME = "claude-haiku-4-5"

SYSTEM_PROMPT = """You are a pet care assistant for the PawPal+ scheduler.
Use only the provided context to answer the user's question.
If the context does not contain enough information to answer, say so directly — do not guess.
Cite the source filename(s) you used at the end of your answer."""


def _format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        blocks.append(f"[{i}] (source: {c['source']})\n{c['text']}")
    return "\n\n".join(blocks)


class RagService:
    def __init__(self) -> None:
        self.index = build_index()
        self.client = Anthropic()

    def explain(self, query: str, k: int = 3) -> dict:
        chunks = retrieve(query, self.index, k=k)
        if not chunks:
            return {
                "answer": "No relevant context found in the knowledge base.",
                "sources": [],
                "chunks": [],
                "usage": {"input_tokens": 0, "output_tokens": 0},
            }

        user_message = f"Context:\n{_format_context(chunks)}\n\nQuestion: {query}"
        response = self.client.messages.create(
            model=MODEL_NAME,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        answer = "".join(b.text for b in response.content if b.type == "text")
        sources = list(dict.fromkeys(c["source"] for c in chunks))

        return {
            "answer": answer,
            "sources": sources,
            "chunks": chunks,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }
