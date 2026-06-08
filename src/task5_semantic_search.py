"""Task 5 — Semantic Search Module.

Dense retrieval over the JSONL vector store produced by Task 4.
"""

try:
    from .rag_utils import cosine_similarity, load_index, ollama_embed
except ImportError:
    from rag_utils import cosine_similarity, load_index, ollama_embed


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Returns:
        List of {'content': str, 'score': float, 'metadata': dict}
        sorted by cosine similarity descending.
    """
    query_embedding = ollama_embed(query)[0]
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
