"""Task 8 — PageIndex Vectorless RAG.

Uses the installed PageIndex SDK (`PageIndexClient`) when PAGEINDEX_API_KEY is
configured. Without uploaded/ready PageIndex documents, it falls back to local
BM25 over markdown documents so Task 9 can still run offline.
"""

from __future__ import annotations

import os
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

try:
    from .rag_utils import tokenize
except ImportError:
    from rag_utils import tokenize

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
PROJECT_ROOT = Path(__file__).parent.parent
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
LANDING_LEGAL_DIR = PROJECT_ROOT / "data" / "landing" / "legal"
PAGEINDEX_MANIFEST = PROJECT_ROOT / "data" / "index" / "pageindex_documents.json"


def _load_markdown_docs() -> list[dict]:
    docs = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            continue
        relative_path = md_file.relative_to(STANDARDIZED_DIR)
        docs.append(
            {
                "content": content,
                "metadata": {
                    "source": md_file.name,
                    "source_path": str(relative_path),
                    "doc_type": relative_path.parts[0] if len(relative_path.parts) > 1 else "unknown",
                },
            }
        )
    return docs


def upload_documents() -> dict:
    """
    Upload documents to PageIndex when an API key/client is available.

    The local fallback returns a manifest-like summary so demos still run without
    a PageIndex account.
    """
    if not PAGEINDEX_API_KEY or PAGEINDEX_API_KEY.endswith("xxx"):
        docs = _load_markdown_docs()
        return {
            "mode": "local_fallback",
            "uploaded": 0,
            "document_count": len(docs),
            "message": "PAGEINDEX_API_KEY is not configured; using local vectorless fallback.",
        }

    try:
        from pageindex import PageIndexClient
    except Exception as exc:
        docs = _load_markdown_docs()
        return {
            "mode": "local_fallback",
            "uploaded": 0,
            "document_count": len(docs),
            "message": f"PageIndex SDK unavailable ({exc}); using local fallback.",
        }

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    pdf_files = sorted(LANDING_LEGAL_DIR.glob("*.pdf"))
    existing = client.list_documents(limit=100).get("documents", [])
    existing_names = {doc.get("name") for doc in existing}

    manifest = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "documents": existing,
        "submitted": [],
    }
    uploaded = 0
    for pdf_file in pdf_files:
        if pdf_file.name in existing_names:
            continue
        result = client.submit_document(str(pdf_file), mode="mcp")
        manifest["submitted"].append({"file": str(pdf_file), **result})
        uploaded += 1

    refreshed = client.list_documents(limit=100).get("documents", [])
    manifest["documents"] = refreshed
    PAGEINDEX_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    PAGEINDEX_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "mode": "pageindex",
        "uploaded": uploaded,
        "document_count": len(refreshed),
        "manifest": str(PAGEINDEX_MANIFEST),
    }


def _pageindex_doc_ids() -> list[str]:
    if PAGEINDEX_MANIFEST.exists():
        manifest = json.loads(PAGEINDEX_MANIFEST.read_text(encoding="utf-8"))
        docs = manifest.get("documents", []) + manifest.get("submitted", [])
        doc_ids = [doc.get("id") or doc.get("doc_id") for doc in docs]
        return [doc_id for doc_id in doc_ids if doc_id]

    if PAGEINDEX_API_KEY and not PAGEINDEX_API_KEY.endswith("xxx"):
        try:
            from pageindex import PageIndexClient

            client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
            docs = client.list_documents(limit=100).get("documents", [])
            doc_ids = [doc.get("id") or doc.get("doc_id") for doc in docs]
            return [doc_id for doc_id in doc_ids if doc_id]
        except Exception:
            return []
    return []


def _extract_pageindex_hits(payload: dict, doc_id: str) -> list[dict]:
    candidates = []
    for key in ("results", "retrieval_results", "chunks", "nodes", "retrieved_nodes", "content"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    if not candidates and payload.get("answer"):
        candidates.append({"text": payload["answer"], "score": 1.0})

    hits = []
    for item in candidates:
        if isinstance(item, str):
            text = item
            score = 1.0
            metadata = {"doc_id": doc_id}
        elif isinstance(item, dict):
            text = (
                item.get("text")
                or item.get("content")
                or item.get("markdown")
                or item.get("node_text")
                or item.get("answer")
                or ""
            )
            if not text and item.get("relevant_contents"):
                parts = []
                for group in item.get("relevant_contents", []):
                    if isinstance(group, list):
                        for block in group:
                            if isinstance(block, dict):
                                title = block.get("section_title") or item.get("title") or ""
                                content = block.get("relevant_content") or ""
                                parts.append(f"{title}\n{content}".strip())
                    elif isinstance(group, dict):
                        title = group.get("section_title") or item.get("title") or ""
                        content = group.get("relevant_content") or ""
                        parts.append(f"{title}\n{content}".strip())
                text = "\n\n".join(part for part in parts if part)
            score = float(item.get("score") or item.get("similarity") or 1.0)
            metadata = item.get("metadata") or {}
            if isinstance(metadata, list):
                metadata = {
                    "doc_id": metadata[0] if len(metadata) > 0 else doc_id,
                    "source": metadata[1] if len(metadata) > 1 else "",
                    "description": metadata[3] if len(metadata) > 3 else "",
                }
            metadata = {**metadata, "doc_id": doc_id}
            if item.get("title"):
                metadata["title"] = item["title"]
        else:
            continue
        if text:
            hits.append(
                {
                    "content": text,
                    "score": score,
                    "metadata": metadata,
                    "source": "pageindex",
                }
            )
    return hits


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval. Uses PageIndex if configured; otherwise BM25 over full
    markdown documents as an offline vectorless fallback.
    """
    if PAGEINDEX_API_KEY and not PAGEINDEX_API_KEY.endswith("xxx"):
        try:
            from pageindex import PageIndexClient

            client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
            hits = []
            for doc_id in _pageindex_doc_ids():
                if not client.is_retrieval_ready(doc_id):
                    continue
                submitted = client.submit_query(doc_id=doc_id, query=query)
                retrieval_id = submitted.get("retrieval_id") or submitted.get("id")
                if not retrieval_id:
                    continue

                payload = {}
                for _ in range(20):
                    payload = client.get_retrieval(retrieval_id)
                    status = str(payload.get("status", "")).lower()
                    if status in {"completed", "complete", "succeeded", "success", "done"}:
                        break
                    time.sleep(1)
                hits.extend(_extract_pageindex_hits(payload, doc_id))

            if hits:
                return sorted(hits, key=lambda item: item["score"], reverse=True)[:top_k]
        except Exception:
            pass

    docs = _load_markdown_docs()
    bm25 = BM25Okapi([tokenize(doc["content"]) for doc in docs])
    scores = bm25.get_scores(tokenize(query))
    ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)

    fallback = []
    for idx in ranked_indices[:top_k]:
        score = float(scores[idx])
        if score <= 0:
            continue
        doc = docs[idx]
        fallback.append(
            {
                "content": doc["content"][:2500],
                "score": score,
                "metadata": doc["metadata"],
                "source": "pageindex_local_fallback",
            }
        )
    return fallback


if __name__ == "__main__":
    print(upload_documents())
    results = pageindex_search("hình phạt sử dụng ma tuý", top_k=3)
    for r in results:
        print(f"[{r['score']:.3f}] [{r['source']}] {r['metadata'].get('source')} :: {r['content'][:100]}...")
