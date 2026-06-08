# RAG Evaluation Results

## Thông tin chạy

- Thời điểm: 2026-06-08 17:03:14 +0700
- Golden dataset: `group_project/evaluation/golden_dataset.json` (15 câu hỏi)
- Top-k: 5
- Chế độ đánh giá: **offline RAGAS-style deterministic metrics**
- Generation: Ollama nếu khả dụng; tự động dùng extractive fallback nếu model không phản hồi
- Thang điểm: 0.000-1.000, điểm cao hơn tốt hơn

> Các metric được tính bằng token overlap có lọc stopword, không dùng LLM-as-a-judge.
> Vì vậy kết quả có thể tái lập và không cần API key, nhưng chỉ nên dùng để so sánh A/B nội bộ.

## Overall Scores

| Metric | Config A (hybrid + rerank) | Config B (dense-only) | Δ A-B |
|--------|----------------------------|-----------------------|-------|
| Faithfulness | 0.865 | 0.860 | +0.005 |
| Answer Relevance | 0.252 | 0.238 | +0.015 |
| Context Recall | 0.717 | 0.693 | +0.023 |
| Context Precision | 0.933 | 0.920 | +0.013 |
| **Average** | 0.692 | 0.678 | +0.014 |

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

Config A có điểm trung bình cao hơn trong lần chạy này. Chênh lệch cần được đọc cùng
Context Recall và Context Precision: corpus hiện tại không chứa rõ ràng nhiều điều luật
được golden dataset kỳ vọng, nên retrieval config tốt hơn vẫn không thể khôi phục evidence
không tồn tại.

## Worst Performers - Config A

| # | Question | Faithfulness | Relevance | Recall | Failure Stage | Root Cause |
|---|----------|-------------:|----------:|-------:|---------------|------------|
| 1 | Các loại giấy tờ cần có khi thực hiện xét nghiệm ma túy theo Nghị định 57/2022/NĐ-CP? | 0.866 | 0.238 | 0.429 | Generation | The answer is grounded but does not sufficiently match the expected answer. |
| 2 | Quy định về việc cấp giấy phép sản xuất thuốc giảm đau có chứa chất gây nghiện trong Điều 13 Luật Dược 2020? | 0.826 | 0.244 | 0.474 | Generation | The answer is grounded but does not sufficiently match the expected answer. |
| 3 | Theo Luật phòng, chống ma túy 2021, hình thức xử lý giáo dục bắt buộc cho người nghiện không phụ thuộc vào mức độ nghiện như thế nào? | 0.915 | 0.209 | 0.391 | Generation | The answer is grounded but does not sufficiently match the expected answer. |

## Golden Dataset Audit

Phát hiện 7/15 expected contexts không được biểu diễn rõ ràng trong
corpus `data/standardized`. Đây là rủi ro lớn nhất đối với độ tin cậy của điểm eval.

- Case 3: `Bộ luật Hình sự 2015, Điều 254` is not clearly represented in the current standardized corpus.
- Case 5: `Bộ luật Hình sự 2015, Điều 252` is not clearly represented in the current standardized corpus.
- Case 7: `Luật Dược 2020, Điều 13` is not clearly represented in the current standardized corpus.
- Case 8: `Bộ luật Hình sự 2015, Điều 247` is not clearly represented in the current standardized corpus.
- Case 9: `Bộ luật Hình sự 2015, Điều 262` is not clearly represented in the current standardized corpus.
- Case 12: `Bộ luật Hình sự 2015, Điều 263` is not clearly represented in the current standardized corpus.
- Case 13: `Bộ luật Hình sự 2015, Điều 254` is not clearly represented in the current standardized corpus.

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
| Lê Quốc Anh | 2A202600824 | Dữ liệu và tài liệu nguồn | Thu thập văn bản pháp luật và tin tức; chuẩn hoá legal/news; kiểm tra nội dung, provenance và metadata; bổ sung tài liệu còn thiếu khi evaluation phát hiện context recall thấp. | Hoàn thành |
| Nguyễn Đức Khang | 2A202600588 | Lõi RAG pipeline | Chunking và vector index; semantic/BM25 retrieval; RRF/MMR reranking; PageIndex fallback; generation có citation; tối ưu retrieval dựa trên các câu bottom performers. | Hoàn thành |
| Nguyễn Đức Mạnh | 2A202600945 | Frontend và tích hợp API | Kết nối UI với FastAPI; conversation memory; trạng thái loading/error; hiển thị citation và source documents; kiểm thử luồng hỏi đáp end-to-end với data mới. | Hoàn thành |
| Lý Hải Long | 2A202600568 | Evaluation và báo cáo | Quản lý golden dataset; chạy A/B; tổng hợp 4 metrics; phân tích câu điểm thấp; cập nhật results.md; kiểm tra lệnh chạy và chuẩn bị nội dung demo evaluation. | Hoàn thành |

## Lệnh chạy lại

```bash
python3 group_project/evaluation/eval_pipeline.py
```
