"""Wire RAG retrieval into an Anthropic LLM call.

Run:
    python pawpal_rag_explain.py "how often should I feed a young dog"
"""

import sys

from anthropic import Anthropic
from dotenv import load_dotenv

from pawpal_rag import build_index, retrieve

load_dotenv()

MODEL_NAME = "claude-haiku-4-5"

SYSTEM_PROMPT = """You are a pet care assistant for the PawPal+ scheduler.
Use only the provided context to answer the user's question.
If the context does not contain enough information to answer, say so directly — do not guess.
Cite the source filename(s) you used at the end of your answer."""


def format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        blocks.append(f"[{i}] (source: {c['source']})\n{c['text']}")
    return "\n\n".join(blocks)


def explain(query: str) -> None:
    print(f"Query: {query}\n")
    print("Building index...")
    index = build_index()
    print(f"Index built: {len(index)} chunks.\n")

    chunks = retrieve(query, index, k=3)
    if not chunks:
        print("No chunks retrieved.")
        return

    print("Top retrieved chunks:")
    for c in chunks:
        print(f"  - {c['source']} (chunk {c['chunk_index']}) score={c['score']:.3f}")
    print()

    user_message = f"Context:\n{format_context(chunks)}\n\nQuestion: {query}"

    client = Anthropic()
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    print("Answer:")
    for block in response.content:
        if block.type == "text":
            print(block.text)

    print(
        f"\n[input tokens: {response.usage.input_tokens}, "
        f"output tokens: {response.usage.output_tokens}]"
    )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print('usage: python pawpal_rag_explain.py "your query here"')
        sys.exit(0)
    explain(" ".join(sys.argv[1:]))
