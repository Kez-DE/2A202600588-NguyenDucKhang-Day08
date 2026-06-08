"""Task 10 — Generation Có Citation."""

try:
    import re

    from .rag_utils import ollama_chat
    from .task9_retrieval_pipeline import retrieve
except ImportError:
    import re

    from rag_utils import ollama_chat
    from task9_retrieval_pipeline import retrieve


# top_k=5 keeps enough evidence while limiting context length.
TOP_K = 5

# top_p=0.9 keeps output flexible enough for Vietnamese prose without making RAG too random.
TOP_P = 0.9

# temperature=0.2 is intentionally low because citation-grounded answers should be factual.
TEMPERATURE = 0.2


SYSTEM_PROMPT = """Bạn là trợ lý RAG trả lời bằng tiếng Việt.
Chỉ sử dụng thông tin trong CONTEXT được cung cấp.
Mỗi nhận định sự kiện hoặc pháp lý phải có citation ngay sau câu, dạng [Nguồn, Năm].
Nếu context không nêu rõ thông tin, hãy viết: "Tôi không thể xác minh thông tin này từ nguồn hiện có".
Không bịa nguồn, không dùng kiến thức ngoài context."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Avoid lost-in-the-middle: keep strongest chunks at the beginning and end.
    Example input ranking [1, 2, 3, 4, 5] becomes [1, 3, 5, 4, 2].
    """
    if len(chunks) <= 2:
        return chunks

    front = chunks[::2]
    back = chunks[1::2]
    return front + list(reversed(back))


def _source_year(metadata: dict) -> str:
    source = metadata.get("source") or metadata.get("source_path") or "Nguồn không rõ"
    match = re.search(r"(20\d{2}|19\d{2})", source)
    if match:
        return f"{source}, {match.group(1)}"
    return f"{source}, không rõ năm"


def format_context(chunks: list[dict]) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        citation = _source_year(metadata)
        context_parts.append(
            f"[Document {i}]\n"
            f"Citation: [{citation}]\n"
            f"Source: {metadata.get('source_path', metadata.get('source', 'unknown'))}\n"
            f"Type: {metadata.get('doc_type', 'unknown')}\n"
            f"Score: {chunk.get('score', 0):.4f}\n"
            f"Content:\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(context_parts)


def _fallback_extractive_answer(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return "Tôi không thể xác minh thông tin này từ nguồn hiện có"

    lines = ["Tôi tìm thấy các đoạn liên quan sau trong nguồn hiện có:"]
    for chunk in chunks[:3]:
        metadata = chunk.get("metadata", {})
        citation = _source_year(metadata)
        snippet = " ".join(chunk["content"].split())[:450]
        lines.append(f"- {snippet} [{citation}]")
    lines.append("Tôi không thể xác minh thông tin nào vượt ngoài các trích đoạn trên từ nguồn hiện có.")
    return "\n".join(lines)


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    chunks = retrieve(query, top_k=top_k)
    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"CONTEXT:\n{context}\n\nQUESTION:\n{query}"

    try:
        answer = ollama_chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
    except Exception:
        answer = _fallback_extractive_answer(query, reordered)

    return {
        "answer": answer or _fallback_extractive_answer(query, reordered),
        "sources": chunks,
        "retrieval_source": chunks[0].get("source", "none") if chunks else "none",
    }


if __name__ == "__main__":
    test_queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý theo pháp luật Việt Nam?",
        "Những nghệ sĩ nào đã bị bắt vì liên quan tới ma tuý?",
        "Quy trình cai nghiện bắt buộc theo Luật Phòng chống ma tuý?",
    ]

    for q in test_queries:
        print(f"\n{'=' * 70}")
        print(f"Q: {q}")
        print("=" * 70)
        result = generate_with_citation(q)
        print(f"\nA: {result['answer']}")
        print(f"\n[Sources: {len(result['sources'])} chunks | via {result['retrieval_source']}]")
