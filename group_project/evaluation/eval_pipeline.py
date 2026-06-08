"""Offline, reproducible evaluation for the local RAG pipeline."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag_utils import ollama_chat, tokenize
from src.task10_generation import (
    SYSTEM_PROMPT,
    TEMPERATURE,
    TOP_P,
    _fallback_extractive_answer,
    format_context,
    reorder_for_llm,
)
from src.task5_semantic_search import semantic_search
from src.task9_retrieval_pipeline import retrieve

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_PATH = Path(__file__).parent / "results.md"
TOP_K = 5

STOPWORDS = {
    "a",
    "ai",
    "bị",
    "các",
    "có",
    "cho",
    "của",
    "đã",
    "được",
    "đến",
    "điều",
    "do",
    "gì",
    "khi",
    "là",
    "một",
    "nào",
    "như",
    "những",
    "phải",
    "quy",
    "ra",
    "sẽ",
    "theo",
    "thế",
    "trong",
    "từ",
    "và",
    "về",
    "việc",
    "với",
}

MEMBERS = [
    (
        "Lê Quốc Anh",
        "2A202600824",
        "Dữ liệu và tài liệu nguồn",
        "Thu thập văn bản pháp luật và tin tức; chuẩn hoá legal/news; kiểm tra nội dung, provenance và metadata; bổ sung tài liệu còn thiếu khi evaluation phát hiện context recall thấp.",
    ),
    (
        "Nguyễn Đức Khang",
        "2A202600588",
        "Lõi RAG pipeline",
        "Chunking và vector index; semantic/BM25 retrieval; RRF/MMR reranking; PageIndex fallback; generation có citation; tối ưu retrieval dựa trên các câu bottom performers.",
    ),
    (
        "Nguyễn Đức Mạnh",
        "2A202600945",
        "Frontend và tích hợp API",
        "Kết nối UI với FastAPI; conversation memory; trạng thái loading/error; hiển thị citation và source documents; kiểm thử luồng hỏi đáp end-to-end với data mới.",
    ),
    (
        "Lý Hải Long",
        "2A202600568",
        "Evaluation và báo cáo",
        "Quản lý golden dataset; chạy A/B; tổng hợp 4 metrics; phân tích câu điểm thấp; cập nhật results.md; kiểm tra lệnh chạy và chuẩn bị nội dung demo evaluation.",
    ),
]


def load_golden_dataset() -> list[dict]:
    with GOLDEN_DATASET_PATH.open(encoding="utf-8") as file:
        dataset = json.load(file)
    if len(dataset) < 15:
        raise ValueError("Golden dataset must contain at least 15 test cases")
    return dataset


def _terms(text: str) -> list[str]:
    return [
        term
        for term in tokenize(text)
        if len(term) > 1 and term not in STOPWORDS and not term.isdigit()
    ]


def _f1(reference: str, candidate: str) -> float:
    reference_terms = Counter(_terms(reference))
    candidate_terms = Counter(_terms(candidate))
    if not reference_terms or not candidate_terms:
        return 0.0
    overlap = sum((reference_terms & candidate_terms).values())
    precision = overlap / sum(candidate_terms.values())
    recall = overlap / sum(reference_terms.values())
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _recall(reference: str, candidate: str) -> float:
    reference_terms = set(_terms(reference))
    candidate_terms = set(_terms(candidate))
    if not reference_terms:
        return 0.0
    return len(reference_terms & candidate_terms) / len(reference_terms)


def _generate_answer(question: str, chunks: list[dict]) -> str:
    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    try:
        return ollama_chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{question}",
                },
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
    except Exception:
        return _fallback_extractive_answer(question, reordered)


def _retrieve(config_name: str, question: str) -> list[dict]:
    if config_name == "hybrid_rerank":
        return retrieve(
            question,
            top_k=TOP_K,
            score_threshold=-1.0,
            use_reranking=True,
        )
    if config_name == "dense_only":
        return semantic_search(question, top_k=TOP_K)
    raise ValueError(f"Unknown config: {config_name}")


def _score_case(item: dict, answer: str, sources: list[dict]) -> dict:
    context_texts = [source.get("content", "") for source in sources]
    combined_context = "\n".join(context_texts)
    expected_evidence = f"{item['expected_answer']} {item['expected_context']}"

    answer_terms = set(_terms(answer))
    context_terms = set(_terms(combined_context))
    faithfulness = (
        len(answer_terms & context_terms) / len(answer_terms) if answer_terms else 0.0
    )

    answer_relevance = (
        0.7 * _f1(item["expected_answer"], answer)
        + 0.3 * _recall(item["question"], answer)
    )
    context_recall = _recall(expected_evidence, combined_context)

    useful_chunks = 0
    chunk_scores = []
    for context in context_texts:
        overlap = _recall(expected_evidence, context)
        chunk_scores.append(overlap)
        if overlap >= 0.15:
            useful_chunks += 1
    context_precision = useful_chunks / len(context_texts) if context_texts else 0.0

    return {
        "faithfulness": round(faithfulness, 4),
        "answer_relevance": round(answer_relevance, 4),
        "context_recall": round(context_recall, 4),
        "context_precision": round(context_precision, 4),
        "best_chunk_overlap": round(max(chunk_scores, default=0.0), 4),
    }


def evaluate_config(config_name: str, golden_dataset: list[dict]) -> dict:
    cases = []
    for index, item in enumerate(golden_dataset, 1):
        print(f"[{config_name}] {index:02d}/{len(golden_dataset)}: {item['question']}")
        sources = _retrieve(config_name, item["question"])
        answer = _generate_answer(item["question"], sources)
        scores = _score_case(item, answer, sources)
        cases.append(
            {
                "index": index,
                "question": item["question"],
                "expected_answer": item["expected_answer"],
                "expected_context": item["expected_context"],
                "answer": answer,
                "source_names": [
                    source.get("metadata", {}).get("source", "unknown")
                    for source in sources
                ],
                **scores,
            }
        )

    metric_names = [
        "faithfulness",
        "answer_relevance",
        "context_recall",
        "context_precision",
    ]
    averages = {
        metric: round(sum(case[metric] for case in cases) / len(cases), 4)
        for metric in metric_names
    }
    averages["average"] = round(sum(averages.values()) / len(metric_names), 4)
    return {"config": config_name, "averages": averages, "cases": cases}


def _failure_stage(case: dict) -> tuple[str, str]:
    if case["context_recall"] < 0.35:
        return (
            "Retrieval/data",
            "Expected evidence is absent or weakly represented in retrieved chunks.",
        )
    if case["context_precision"] < 0.4:
        return (
            "Retrieval ranking",
            "Most retrieved chunks have little overlap with the expected evidence.",
        )
    if case["answer_relevance"] < 0.35:
        return (
            "Generation",
            "The answer is grounded but does not sufficiently match the expected answer.",
        )
    return ("Mixed", "No single stage dominates the error.")


def _dataset_audit(dataset: list[dict]) -> list[str]:
    corpus = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (PROJECT_ROOT / "data" / "standardized").rglob("*.md")
    ).lower()
    findings = []
    for index, item in enumerate(dataset, 1):
        expected_context = item["expected_context"].lower()
        article_match = re.search(r"điều\s+\d+", expected_context)
        document_terms = [
            term
            for term in re.split(r"[,/]", expected_context)
            if term.strip() and not term.strip().lower().startswith("điều ")
        ]
        document_found = any(term.strip().lower() in corpus for term in document_terms)
        article_found = bool(article_match and article_match.group(0) in corpus)
        if not document_found or (article_match and not article_found):
            findings.append(
                f"Case {index}: `{item['expected_context']}` is not clearly represented in the current standardized corpus."
            )
    return findings


def export_results(
    dataset: list[dict],
    config_a: dict,
    config_b: dict,
) -> None:
    metrics = [
        ("Faithfulness", "faithfulness"),
        ("Answer Relevance", "answer_relevance"),
        ("Context Recall", "context_recall"),
        ("Context Precision", "context_precision"),
        ("**Average**", "average"),
    ]
    rows = []
    for label, key in metrics:
        score_a = config_a["averages"][key]
        score_b = config_b["averages"][key]
        rows.append(
            f"| {label} | {score_a:.3f} | {score_b:.3f} | {score_a - score_b:+.3f} |"
        )

    combined_cases = []
    for case_a, case_b in zip(config_a["cases"], config_b["cases"]):
        mean_score = sum(
            case_a[key]
            for key in (
                "faithfulness",
                "answer_relevance",
                "context_recall",
                "context_precision",
            )
        ) / 4
        combined_cases.append((mean_score, case_a, case_b))
    worst = sorted(combined_cases, key=lambda item: item[0])[:3]

    worst_rows = []
    for rank, (_, case_a, _) in enumerate(worst, 1):
        stage, cause = _failure_stage(case_a)
        worst_rows.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    case_a["question"].replace("|", "/"),
                    f"{case_a['faithfulness']:.3f}",
                    f"{case_a['answer_relevance']:.3f}",
                    f"{case_a['context_recall']:.3f}",
                    stage,
                    cause,
                ]
            )
            + " |"
        )

    winner = (
        "Config A"
        if config_a["averages"]["average"] >= config_b["averages"]["average"]
        else "Config B"
    )
    audit = _dataset_audit(dataset)
    member_rows = [
        f"| {name} | {student_id} | {role} | {details} | Hoàn thành |"
        for name, student_id, role, details in MEMBERS
    ]

    content = f"""# RAG Evaluation Results

## Thông tin chạy

- Thời điểm: {datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")}
- Golden dataset: `{GOLDEN_DATASET_PATH.relative_to(PROJECT_ROOT)}` ({len(dataset)} câu hỏi)
- Top-k: {TOP_K}
- Chế độ đánh giá: **offline RAGAS-style deterministic metrics**
- Generation: Ollama nếu khả dụng; tự động dùng extractive fallback nếu model không phản hồi
- Thang điểm: 0.000-1.000, điểm cao hơn tốt hơn

> Các metric được tính bằng token overlap có lọc stopword, không dùng LLM-as-a-judge.
> Vì vậy kết quả có thể tái lập và không cần API key, nhưng chỉ nên dùng để so sánh A/B nội bộ.

## Overall Scores

| Metric | Config A (hybrid + rerank) | Config B (dense-only) | Δ A-B |
|--------|----------------------------|-----------------------|-------|
{chr(10).join(rows)}

## A/B Comparison Analysis

**Config A - hybrid + rerank**

- Semantic search lấy `top_k * 4` candidates.
- BM25 lexical search lấy `top_k * 4` candidates.
- Reciprocal Rank Fusion hợp nhất hai danh sách.
- MMR reranking chọn 5 chunks cuối cùng.
- PageIndex fallback bị vô hiệu trong eval bằng `score_threshold=-1.0` để đo đúng hybrid retrieval.

**Config B - dense-only**

- Chỉ sử dụng semantic search.
- Không BM25, không RRF, không MMR và không PageIndex fallback.
- Trả trực tiếp 5 chunks có cosine similarity cao nhất.

**Kết luận**

{winner} có điểm trung bình cao hơn trong lần chạy này. Chênh lệch cần được đọc cùng
Context Recall và Context Precision: corpus hiện tại không chứa rõ ràng nhiều điều luật
được golden dataset kỳ vọng, nên retrieval config tốt hơn vẫn không thể khôi phục evidence
không tồn tại.

## Worst Performers - Config A

| # | Question | Faithfulness | Relevance | Recall | Failure Stage | Root Cause |
|---|----------|-------------:|----------:|-------:|---------------|------------|
{chr(10).join(worst_rows)}

## Golden Dataset Audit

Phát hiện {len(audit)}/{len(dataset)} expected contexts không được biểu diễn rõ ràng trong
corpus `data/standardized`. Đây là rủi ro lớn nhất đối với độ tin cậy của điểm eval.

{chr(10).join(f"- {finding}" for finding in audit)}

Ngoài ra, một số câu hỏi/đáp án cần được chuyên gia pháp lý rà soát vì tên tội danh và số
điều có dấu hiệu không khớp cấu trúc Bộ luật Hình sự. Evaluation không được xem là xác nhận
tính đúng đắn pháp lý của golden answer.

## Recommendations

### 1. Đồng bộ golden dataset với corpus

**Action:** Chỉ giữ expected context có tài liệu gốc trong `data/standardized`; bổ sung đúng
Bộ luật Hình sự, Luật Phòng chống ma túy, Luật Dược và nghị định được hỏi trước khi chạy lại.

**Expected impact:** Tăng Context Recall và giúp điểm A/B phản ánh retriever thay vì phản ánh
thiếu dữ liệu.

### 2. Rà soát pháp lý từng golden answer

**Action:** Kiểm tra số điều, tên hành vi, khung hình phạt và hiệu lực văn bản; thêm URL,
document ID, article ID và đoạn evidence nguyên văn cho từng case.

**Expected impact:** Loại bỏ ground truth sai hoặc mơ hồ, giảm false negative trong Answer
Relevance và Context Precision.

### 3. Tách eval retrieval và generation

**Action:** Bổ sung hit@k/MRR theo `document_id + article_id` cho retrieval; dùng
LLM-as-a-judge hoặc human review riêng cho faithfulness và answer relevance.

**Expected impact:** Xác định chính xác lỗi thuộc retrieval, ranking hay generation và tránh
kết luận sai từ một điểm tổng hợp.

## Phân Công Công Việc

| Thành viên | MSSV | Vai trò | Công việc chi tiết | Trạng thái |
|------------|------|---------|-------------------|------------|
{chr(10).join(member_rows)}

## Lệnh chạy lại

```bash
cd {PROJECT_ROOT}
.venv/bin/python group_project/evaluation/eval_pipeline.py
```
"""
    RESULTS_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    dataset = load_golden_dataset()
    print(f"Loaded {len(dataset)} test cases from {GOLDEN_DATASET_PATH}")
    config_a = evaluate_config("hybrid_rerank", dataset)
    config_b = evaluate_config("dense_only", dataset)
    export_results(dataset, config_a, config_b)
    print(f"Wrote evaluation report to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
