# Agent Log

## 2026-06-08

- Hoàn thiện Task 4: recursive chunking, Ollama `qwen3-embedding:0.6b`, JSONL vector index.
- Hoàn thiện Task 5-10: semantic search, BM25 lexical search, RRF/MMR reranking, PageIndex fallback, retrieval pipeline, generation có citation.
- Merge `tests/` từ `origin/main` về clone local.
- Cập nhật Task 8 dùng PageIndex SDK thật `PageIndexClient`, upload 3 PDF legal lên PageIndex, query trả `source="pageindex"`.
- Chạy `python -m pytest tests/test_individual.py -v`: `35 passed`.
- Thêm group Option 1:
  - `chat.py`: Streamlit chatbot có memory và hiển thị nguồn.
  - `api.py`: FastAPI endpoint `/chat` và `/health`.
  - `prompt.md`: prompt cho FastAPI behavior và Lovable UI.
