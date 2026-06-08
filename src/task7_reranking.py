"""Task 7 — Reranking Module.

Implemented choices:
    - RRF for merging semantic + lexical ranked lists.
    - MMR for diversity-aware reranking.
    - A deterministic local score/overlap reranker as an offline cross-encoder fallback.
"""

try:
    from .rag_utils import cosine_similarity, ollama_embed, result_key, tokenize
except ImportError:
    from rag_utils import cosine_similarity, ollama_embed, result_key, tokenize


def rerank_cross_encoder(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """
    Offline reranker that approximates cross-encoder behavior with retrieval score
    plus query-term overlap. This keeps the demo local without Jina/OpenAI keys.
    """
    query_terms = set(tokenize(query))
    rescored = []
    for candidate in candidates:
        doc_terms = set(tokenize(candidate["content"]))
        overlap = len(query_terms & doc_terms) / max(len(query_terms), 1)
        score = 0.75 * float(candidate.get("score", 0.0)) + 0.25 * overlap
        item = candidate.copy()
        item["score"] = float(score)
        item["rerank_score"] = float(score)
        item["rerank_method"] = "local_score_overlap"
        rescored.append(item)

    return sorted(rescored, key=lambda item: item["score"], reverse=True)[:top_k]


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance.

    MMR = lambda * sim(query, doc) - (1 - lambda) * max(sim(doc, selected_docs))
    lambda=0.7 favors relevance while still reducing duplicate chunks.
    """
    if not candidates:
        return []

    selected: list[int] = []
    selected_scores: dict[int, float] = {}
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_idx = remaining[0]
        best_score = float("-inf")

        for idx in remaining:
            embedding = candidates[idx].get("embedding")
            relevance = (
                cosine_similarity(query_embedding, embedding)
                if embedding is not None
                else float(candidates[idx].get("score", 0.0))
            )
            max_sim_to_selected = 0.0
            for selected_idx in selected:
                selected_embedding = candidates[selected_idx].get("embedding")
                if embedding is not None and selected_embedding is not None:
                    max_sim_to_selected = max(
                        max_sim_to_selected,
                        cosine_similarity(embedding, selected_embedding),
                    )

            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        selected.append(best_idx)
        selected_scores[best_idx] = best_score
        remaining.remove(best_idx)

    results = []
    for idx in selected:
        item = candidates[idx].copy()
        item["score"] = float(selected_scores.get(idx, item.get("score", 0.0)))
        item["rerank_score"] = item["score"]
        item["rerank_method"] = "mmr"
        results.append(item)
    return results


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    """
    Reciprocal Rank Fusion.

    RRF(d) = sum(1 / (k + rank_r(d))). It is robust because it uses rank position
    instead of comparing dense cosine and BM25 scores on incompatible scales.
    """
    rrf_scores: dict[str, float] = {}
    content_map: dict[str, dict] = {}
    retrieval_sources: dict[str, set[str]] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = result_key(item)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            if key not in content_map or item.get("score", 0) > content_map[key].get("score", 0):
                content_map[key] = item
            retrieval_sources.setdefault(key, set()).add(item.get("source", "unknown"))

    results = []
    for key, score in sorted(rrf_scores.items(), key=lambda pair: pair[1], reverse=True)[:top_k]:
        item = content_map[key].copy()
        item["score"] = float(score)
        item["fusion_method"] = "rrf"
        item["retrieval_sources"] = sorted(retrieval_sources.get(key, []))
        results.append(item)
    return results


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "mmr",
) -> list[dict]:
    """Unified reranking interface."""
    if not candidates:
        return []
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    if method == "mmr":
        try:
            query_embedding = ollama_embed(query)[0]
            return rerank_mmr(query_embedding, candidates, top_k)
        except Exception:
            return rerank_cross_encoder(query, candidates, top_k)
    if method == "rrf":
        return rerank_rrf([candidates], top_k=top_k)
    raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    dummy_candidates = [
        {"content": "Điều 248: Tội tàng trữ trái phép chất ma tuý", "score": 0.8, "metadata": {}},
        {"content": "Nghệ sĩ X bị bắt vì sử dụng ma tuý", "score": 0.7, "metadata": {}},
        {"content": "Hình phạt tù từ 2-7 năm cho tội tàng trữ", "score": 0.6, "metadata": {}},
    ]
    results = rerank("hình phạt tàng trữ ma tuý", dummy_candidates, top_k=2, method="cross_encoder")
    for r in results:
        print(f"[{r['score']:.3f}] {r['content']}")
