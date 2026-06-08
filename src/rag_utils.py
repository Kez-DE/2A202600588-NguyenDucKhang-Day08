"""Shared helpers for the local RAG pipeline."""

from __future__ import annotations

import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_INDEX_DIR = PROJECT_ROOT / "data" / "index" / "ollama_qwen3_recursive"
INDEX_DIR = Path(os.getenv("VECTOR_INDEX_DIR", DEFAULT_INDEX_DIR))
INDEX_FILE = INDEX_DIR / "chunks.jsonl"
MANIFEST_FILE = INDEX_DIR / "manifest.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "hermes3:8b")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))


def tokenize(text: str) -> list[str]:
    """Simple Unicode-aware tokenizer that works acceptably for Vietnamese BM25."""
    return re.findall(r"[\wÀ-ỹ]+", text.lower(), flags=re.UNICODE)


@lru_cache(maxsize=1)
def load_index() -> list[dict]:
    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            f"Missing vector index: {INDEX_FILE}. Run `python src/task4_chunking_indexing.py` first."
        )

    rows = []
    with INDEX_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    if not MANIFEST_FILE.exists():
        return {}
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def ollama_embed(texts: list[str] | str, model: str | None = None) -> list[list[float]]:
    inputs = [texts] if isinstance(texts, str) else texts
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={"model": model or OLLAMA_EMBEDDING_MODEL, "input": inputs},
        timeout=120,
    )
    response.raise_for_status()
    embeddings = response.json().get("embeddings")
    if embeddings is None:
        raise RuntimeError(f"Unexpected Ollama embedding response: {response.text[:500]}")
    return embeddings


def ollama_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    top_p: float = 0.9,
) -> str:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": model or OLLAMA_CHAT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": OLLAMA_NUM_PREDICT,
            },
        },
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("message", {}).get("content", "").strip()


def result_key(item: dict) -> str:
    metadata = item.get("metadata", {})
    return metadata.get("chunk_id") or item.get("id") or item.get("content", "")
