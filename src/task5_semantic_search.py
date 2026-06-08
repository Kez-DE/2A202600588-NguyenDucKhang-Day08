"""Task 5 — Semantic Search Module.

Dense retrieval over the JSONL vector store produced by Task 4.
"""

try:
    from .rag_utils import cosine_similarity, load_index, ollama_embed, tokenize
except ImportError:
    from rag_utils import cosine_similarity, load_index, ollama_embed, tokenize


def _local_overlap_search(query: str, top_k: int) -> list[dict]:
    """Deterministic fallback when Ollama embeddings are unavailable."""
    query_terms = set(tokenize(query))
    results = []

    for chunk in load_index():
        doc_terms = set(tokenize(chunk["content"]))
        overlap = len(query_terms & doc_terms)
        score = overlap / max(len(query_terms), 1)
        if overlap == 0:
            score = 0.0
        results.append(
            {
                "content": chunk["content"],
                "score": float(score),
                "metadata": chunk["metadata"],
                "embedding": chunk.get("embedding"),
                "source": "semantic_fallback",
            }
        )

    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Returns:
        List of {'content': str, 'score': float, 'metadata': dict}
        sorted by cosine similarity descending.
    """
    try:
        query_embedding = ollama_embed(query)[0]
    except Exception:
        return _local_overlap_search(query, top_k)

    results = []

    for chunk in load_index():
        score = cosine_similarity(query_embedding, chunk["embedding"])
        results.append(
            {
                "content": chunk["content"],
                "score": float(score),
                "metadata": chunk["metadata"],
                "embedding": chunk["embedding"],
                "source": "semantic",
            }
        )

    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    results = semantic_search("hình phạt cho tội tàng trữ ma tuý", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['metadata']['source']} :: {r['content'][:100]}...")
