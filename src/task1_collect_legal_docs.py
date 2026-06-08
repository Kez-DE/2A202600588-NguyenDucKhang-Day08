"""
Task 1 — Thu thập văn bản pháp luật về ma tuý và các chất cấm.

Hướng dẫn:
    1. Tìm tối thiểu 3 văn bản pháp luật (PDF/DOCX) từ các nguồn chính thống.
    2. Tải về và lưu vào data/landing/legal/
    3. Đặt tên file rõ ràng, không dấu, có năm ban hành.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "landing" / "legal"
MANIFEST_PATH = DATA_DIR / "legal_sources.json"

LEGAL_DOCUMENTS: list[dict[str, str]] = [
    {
        "doc_id": "luat-phong-chong-ma-tuy-120-2025-qh15",
        "title": "Luật Phòng, chống ma túy số 120/2025/QH15",
        "source_page": "https://vanban.chinhphu.vn/?pageid=27160&docid=216502&classid=1&orggroupid=1",
        "file_url": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/01/luat120-2025.pdf",
        "issued_date": "2025",
        "source_name": "Cổng Thông tin điện tử Chính phủ",
        "filename": "luat-phong-chong-ma-tuy-120-2025-qh15.pdf",
    },
    {
        "doc_id": "quyet-dinh-28-2025-qd-ttg-dia-ban-ma-tuy",
        "title": "Quyết định số 28/2025/QĐ-TTg ban hành tiêu chí xác định tuyến, địa bàn trọng điểm phức tạp về ma túy, địa bàn không ma túy",
        "source_page": "https://vanban.chinhphu.vn/?pageid=27160&docid=215036",
        "file_url": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/8/28-ttg.signed.pdf",
        "issued_date": "2025",
        "source_name": "Cổng Thông tin điện tử Chính phủ",
        "filename": "quyet-dinh-28-2025-qd-ttg-dia-ban-ma-tuy.pdf",
    },
    {
        "doc_id": "nghi-dinh-90-2024-nd-cp-danh-muc-chat-ma-tuy",
        "title": "Nghị định số 90/2024/NĐ-CP sửa đổi, bổ sung danh mục chất ma túy và tiền chất",
        "source_page": "https://vanban.chinhphu.vn/?pageid=27160&docid=210694",
        "file_url": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/7/90nd.signed.pdf",
        "issued_date": "2024-07-17",
        "source_name": "Cổng Thông tin điện tử Chính phủ",
        "filename": "nghi-dinh-90-2024-nd-cp-danh-muc-chat-ma-tuy.pdf",
    },
]


def setup_directory() -> None:
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")


def download_file(url: str, output_path: Path, timeout: int = 60) -> int:
    """Download one legal document and return its byte size."""
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (Day08 RAG Pipeline)"})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "").lower()
        content = response.read()

    if "pdf" not in content_type and not url.lower().endswith((".pdf", ".doc", ".docx")):
        raise ValueError(f"URL không giống file văn bản pháp luật: {url} ({content_type})")

    output_path.write_bytes(content)
    return output_path.stat().st_size


def collect_legal_docs(force: bool = False) -> list[dict[str, Any]]:
    """
    Download 3 official legal documents into data/landing/legal/.

    Existing files are reused by default so the script is safe to rerun.
    Use force=True to redownload everything.
    """
    setup_directory()
    manifest: list[dict[str, Any]] = []
    previous_records: dict[str, dict[str, Any]] = {}
    if MANIFEST_PATH.exists():
        previous = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        previous_records = {record.get("doc_id", ""): record for record in previous}

    for doc in LEGAL_DOCUMENTS:
        output_path = DATA_DIR / doc["filename"]
        previous_record = previous_records.get(doc["doc_id"], {})
        if output_path.exists() and output_path.stat().st_size > 0 and not force:
            size = output_path.stat().st_size
            downloaded_at = previous_record.get("downloaded_at") or datetime.now(timezone.utc).isoformat()
            print(f"✓ Đã có sẵn: {output_path.name} ({size:,} bytes)")
        else:
            print(f"Downloading: {doc['title']}")
            size = download_file(doc["file_url"], output_path)
            downloaded_at = datetime.now(timezone.utc).isoformat()
            print(f"  ✓ Saved: {output_path} ({size:,} bytes)")

        record = {
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "source_page": doc["source_page"],
            "file_url": doc["file_url"],
            "issued_date": doc["issued_date"],
            "source_name": doc["source_name"],
            "local_file": str(output_path.relative_to(PROJECT_ROOT)),
            "bytes": size,
            "downloaded_at": downloaded_at,
        }
        manifest.append(record)

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Manifest saved: {MANIFEST_PATH}")
    return manifest


if __name__ == "__main__":
    collect_legal_docs()
