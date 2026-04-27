"""CLI smoke test for the RAG service.

Run:
    python pawpal_rag_explain.py "how often should I feed a young dog"
"""

import sys

from pawpal_rag_service import RagService


def main(query: str) -> None:
    print(f"Query: {query}\n")
    print("Building index...")
    service = RagService()
    print(f"Index built: {len(service.index)} chunks.\n")

    result = service.explain(query)

    print("Top retrieved chunks:")
    for c in result["chunks"]:
        print(f"  - {c['source']} (chunk {c['chunk_index']}) score={c['score']:.3f}")
    print()

    print("Answer:")
    print(result["answer"])

    print(
        f"\n[input tokens: {result['usage']['input_tokens']}, "
        f"output tokens: {result['usage']['output_tokens']}]"
    )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print('usage: python pawpal_rag_explain.py "your query here"')
        sys.exit(0)
    main(" ".join(sys.argv[1:]))
