"""Task 6 — Lexical Search Module (BM25)."""

from functools import lru_cache

from rank_bm25 import BM25Okapi

try:
    from .rag_utils import load_index, tokenize
except ImportError:
    from rag_utils import load_index, tokenize


def build_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """Build BM25 over Task 4 chunks."""
    tokenized_corpus = [tokenize(doc["content"]) for doc in corpus]
    return BM25Okapi(tokenized_corpus)


@lru_cache(maxsize=1)
def _corpus_and_index() -> tuple[list[dict], BM25Okapi]:
    corpus = [
        {
            "content": row["content"],
            "metadata": row["metadata"],
            "embedding": row.get("embedding"),
        }
        for row in load_index()
    ]
    return corpus, build_bm25_index(corpus)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Returns:
        List of {'content': str, 'score': float, 'metadata': dict}
        sorted by BM25 score descending.
    """
    corpus, bm25 = _corpus_and_index()
    scores = bm25.get_scores(tokenize(query))
    ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)

    results = []
    for idx in ranked_indices[:top_k]:
        score = float(scores[idx])
        if score <= 0:
            continue
        item = corpus[idx]
        results.append(
            {
                "content": item["content"],
                "score": score,
                "metadata": item["metadata"],
                "embedding": item.get("embedding"),
                "source": "lexical",
            }
        )
    return results


if __name__ == "__main__":
    results = lexical_search("Điều 248 tàng trữ trái phép chất ma tuý", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['metadata']['source']} :: {r['content'][:100]}...")
