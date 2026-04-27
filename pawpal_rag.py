"""PawPal RAG — knowledge loading, chunking, embedding, and retrieval.

Run as a script:
    python pawpal_rag.py "how often should I walk a senior dog"
    python pawpal_rag.py --chunks       # inspect chunk output (no embeddings)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
from sentence_transformers import SentenceTransformer

KNOWLEDGE_DIR = Path(__file__).parent / "assets" / "knowledge"
MODEL_NAME = "all-MiniLM-L6-v2"

_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it across calls."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def load_docs(knowledge_dir: Path = KNOWLEDGE_DIR) -> List[dict]:
    """Read every .md file in the knowledge directory, sorted by filename."""
    docs = []
    for path in sorted(knowledge_dir.glob("*.md")):
        docs.append({"source": path.name, "text": path.read_text(encoding="utf-8")})
    return docs


def chunk(text: str, size: int = 200, overlap: int = 40) -> List[str]:
    """Split text into overlapping word-windows.

    Overlap means consecutive chunks share text at their boundary, so a fact
    split across a chunk edge still appears whole in at least one chunk.
    """
    if size <= 0:
        raise ValueError("size must be > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")

    words = text.split()
    if not words:
        return []

    chunks = []
    step = size - overlap
    for start in range(0, len(words), step):
        window = words[start:start + size]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + size >= len(words):
            break
    return chunks


def embed(texts: List[str]) -> np.ndarray:
    """Embed a list of texts. Returns a (N, 384) array of unit-length vectors.

    normalize_embeddings=True scales every vector to length 1, which means a
    plain dot product between two vectors equals their cosine similarity.
    Saves us from computing magnitudes later.
    """
    return get_model().encode(texts, normalize_embeddings=True)


def build_index(knowledge_dir: Path = KNOWLEDGE_DIR) -> List[dict]:
    """Load docs, chunk them, embed every chunk, return a list of records.

    Each record is a dict with keys: source, chunk_index, text, embedding.
    """
    docs = load_docs(knowledge_dir)
    records = []
    for doc in docs:
        for i, c in enumerate(chunk(doc["text"])):
            records.append({"source": doc["source"], "chunk_index": i, "text": c})

    if not records:
        return []

    vectors = embed([r["text"] for r in records])
    for r, v in zip(records, vectors):
        r["embedding"] = v
    return records


def retrieve(query: str, index: List[dict], k: int = 3) -> List[dict]:
    """Return the top-k chunks most similar to the query, with cosine scores.

    The index is expected to come from build_index(). The query is embedded
    on the fly; cosine similarity is a dot product because vectors are
    pre-normalized.
    """
    if not index:
        return []
    if not query.strip():
        return []

    query_vec = embed([query])[0]
    chunk_matrix = np.array([r["embedding"] for r in index])
    scores = chunk_matrix @ query_vec

    top_indices = np.argsort(scores)[::-1][:k]
    return [
        {
            "source": index[i]["source"],
            "chunk_index": index[i]["chunk_index"],
            "text": index[i]["text"],
            "score": float(scores[i]),
        }
        for i in top_indices
    ]


def _print_chunks() -> None:
    docs = load_docs()
    print(f"Loaded {len(docs)} documents from {KNOWLEDGE_DIR}\n")
    total = 0
    for doc in docs:
        doc_chunks = chunk(doc["text"])
        total += len(doc_chunks)
        print(f"=== {doc['source']} — {len(doc_chunks)} chunk(s) ===")
        for i, c in enumerate(doc_chunks):
            print(f"\n--- chunk {i} ({len(c.split())} words) ---")
            print(c)
        print()
    print(f"Total: {len(docs)} docs -> {total} chunks")


def _run_query(query: str) -> None:
    print(f"Query: {query}\n")
    print("Building index (loading docs, chunking, embedding)...")
    index = build_index()
    print(f"Index built: {len(index)} chunks.\n")

    results = retrieve(query, index, k=3)
    if not results:
        print("No results.")
        return

    for rank, r in enumerate(results, start=1):
        print(f"=== rank {rank} | score {r['score']:.3f} | {r['source']} (chunk {r['chunk_index']}) ===")
        print(r["text"])
        print()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("usage:")
        print('  python pawpal_rag.py "your query here"')
        print("  python pawpal_rag.py --chunks")
        sys.exit(0)

    if sys.argv[1] == "--chunks":
        _print_chunks()
    else:
        _run_query(" ".join(sys.argv[1:]))
