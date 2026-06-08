"""Task 4 — Chunking & Indexing vào local vector store.

Lựa chọn cho bài này:
    - Chunking: RecursiveCharacterTextSplitter
      Các file markdown đến từ PDF và bài báo nên heading không luôn ổn định.
      Recursive splitter ưu tiên tách theo đoạn/dòng/câu, an toàn cho cả văn bản
      pháp luật và tin tức.
    - Chunk size: 800 ký tự, overlap: 120 ký tự
      800 ký tự đủ giữ một ý/điều khoản ngắn trong cùng chunk; overlap 120 giúp
      không mất ngữ cảnh ở ranh giới chunk.
    - Embedding: Ollama local `qwen3-embedding:0.6b`
      Model nhẹ, chạy local, phù hợp tiếng Việt. Dimension được detect từ vector
      đầu tiên khi index để tránh hard-code sai theo phiên bản model.
    - Vector store: JSONL local
      Mỗi dòng là một chunk kèm embedding và metadata. Cách này chạy offline,
      không cần server Weaviate/Chroma, và đủ cho Task 5 đọc lại để search dense.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
DEFAULT_INDEX_DIR = Path(__file__).parent.parent / "data" / "index" / "ollama_qwen3_recursive"
INDEX_DIR = Path(os.getenv("VECTOR_INDEX_DIR", DEFAULT_INDEX_DIR))
INDEX_FILE = INDEX_DIR / "chunks.jsonl"
MANIFEST_FILE = INDEX_DIR / "manifest.json"


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn của bạn trong comment
# =============================================================================

# RecursiveCharacterTextSplitter an toàn cho markdown convert từ PDF/news vì cấu
# trúc heading không đồng đều giữa các nguồn.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
CHUNKING_METHOD = "recursive"

# Ollama local: user yêu cầu qwen3 embedding 0.6B; dimension detect lúc chạy.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b")
EMBEDDING_DIM: int | None = None
EMBED_BATCH_SIZE = int(os.getenv("OLLAMA_EMBED_BATCH_SIZE", "16"))

# Local JSONL vector store để chạy offline, không phụ thuộc service ngoài.
VECTOR_STORE = "jsonl"


# =============================================================================
# IMPLEMENTATION
# =============================================================================

def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.

    Returns:
        List of {'content': str, 'metadata': {'source': str, 'type': str}}
    """
    documents = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            continue

        relative_path = md_file.relative_to(STANDARDIZED_DIR)
        doc_type = relative_path.parts[0] if len(relative_path.parts) > 1 else "unknown"
        documents.append(
            {
                "content": content,
                "metadata": {
                    "source": md_file.name,
                    "source_path": str(relative_path),
                    "doc_type": doc_type,
                    "stem": md_file.stem,
                },
            }
        )
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk documents theo strategy đã chọn.

    Returns:
        List of {'content': str, 'metadata': dict} — mỗi item là 1 chunk
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for index, chunk_text in enumerate(splits):
            chunk_id = _chunk_id(doc["metadata"]["source_path"], index, chunk_text)
            chunks.append(
                {
                    "id": chunk_id,
                    "content": chunk_text,
                    "metadata": {
                        **doc["metadata"],
                        "chunk_index": index,
                        "chunk_id": chunk_id,
                        "chunk_chars": len(chunk_text),
                    },
                }
            )
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng model đã chọn.

    Returns:
        Mỗi chunk dict được thêm key 'embedding': list[float]
    """
    if not chunks:
        return []

    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        texts = [chunk["content"] for chunk in batch]
        embeddings = _ollama_embed(texts)

        if len(embeddings) != len(batch):
            raise RuntimeError(
                f"Ollama returned {len(embeddings)} embeddings for {len(batch)} inputs"
            )

        for chunk, embedding in zip(batch, embeddings):
            chunk["embedding"] = embedding

        print(f"  embedded {min(start + len(batch), len(chunks))}/{len(chunks)} chunks")

    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """
    Lưu chunks vào vector store đã chọn.
    """
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    embedding_dim = len(chunks[0]["embedding"]) if chunks else 0
    with INDEX_FILE.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    manifest = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "standardized_dir": str(STANDARDIZED_DIR),
        "index_file": str(INDEX_FILE),
        "vector_store": VECTOR_STORE,
        "chunking_method": CHUNKING_METHOD,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dim": embedding_dim,
        "chunk_count": len(chunks),
        "document_count": len({chunk["metadata"]["source_path"] for chunk in chunks}),
    }
    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"  wrote {INDEX_FILE}")
    print(f"  wrote {MANIFEST_FILE}")


def _chunk_id(source_path: str, chunk_index: int, content: str) -> str:
    raw = f"{source_path}:{chunk_index}:{content}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    embeddings = payload.get("embeddings")
    if embeddings is None:
        raise RuntimeError(f"Unexpected Ollama response: {payload}")
    return embeddings


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim=detected at runtime)")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n✓ Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"✓ Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"✓ Embedded {len(chunks)} chunks")

    index_to_vectorstore(chunks)
    print("✓ Indexed to vector store")


if __name__ == "__main__":
    run_pipeline()
