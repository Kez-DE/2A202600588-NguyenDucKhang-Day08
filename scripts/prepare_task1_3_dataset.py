"""Prepare Day 08 Task 1-3 dataset.

This script uses:
- Official Vietnamese Government legal-document pages/PDFs for Task 1.
- Local Firecrawl at http://localhost:3002/v1/scrape for Task 2 news crawling.
- MarkItDown for PDF conversion and JSON markdown extraction for Task 3.

Run from repo root:
    python3 scripts/prepare_task1_3_dataset.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from markitdown import MarkItDown

ROOT = Path(__file__).resolve().parents[1]
LEGAL_DIR = ROOT / "data" / "landing" / "legal"
NEWS_DIR = ROOT / "data" / "landing" / "news"
STANDARDIZED_DIR = ROOT / "data" / "standardized"
FIRECRAWL_BASE_URL = "http://localhost:3002"

LEGAL_DOCS = [
    {
        "doc_id": "luat-phong-chong-ma-tuy-120-2025-qh15",
        "title": "Luật Phòng, chống ma túy số 120/2025/QH15",
        "source_page": "https://vanban.chinhphu.vn/?pageid=27160&docid=216502&classid=1&orggroupid=1",
        "file_url": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/01/luat120-2025.pdf",
        "issued_date": "2025",
        "source_name": "Cổng Thông tin điện tử Chính phủ",
    },
    {
        "doc_id": "quyet-dinh-28-2025-qd-ttg-dia-ban-ma-tuy",
        "title": "Quyết định số 28/2025/QĐ-TTg ban hành tiêu chí xác định tuyến, địa bàn trọng điểm phức tạp về ma túy, địa bàn không ma túy",
        "source_page": "https://vanban.chinhphu.vn/?pageid=27160&docid=215036",
        "file_url": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/8/28-ttg.signed.pdf",
        "issued_date": "2025",
        "source_name": "Cổng Thông tin điện tử Chính phủ",
    },
    {
        "doc_id": "nghi-dinh-90-2024-nd-cp-danh-muc-chat-ma-tuy",
        "title": "Nghị định số 90/2024/NĐ-CP sửa đổi, bổ sung danh mục chất ma túy và tiền chất",
        "source_page": "https://vanban.chinhphu.vn/?pageid=27160&docid=210694",
        "file_url": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/7/90nd.signed.pdf",
        "issued_date": "2024-07-17",
        "source_name": "Cổng Thông tin điện tử Chính phủ",
    },
]

NEWS_ARTICLES = [
    {
        "article_id": "dantri-20260402-truy-to-chi-dan-an-tay",
        "title": "Truy tố ca sĩ Chi Dân, người mẫu An Tây",
        "url": "https://dantri.com.vn/phap-luat/truy-to-ca-si-chi-dan-nguoi-mau-an-tay-20260402122649916.htm",
        "source_name": "Dân trí",
        "published_hint": "2026-04-02",
    },
    {
        "article_id": "dantri-20260406-an-tay-ru-ban-su-dung-ma-tuy",
        "title": "Người mẫu An Tây rủ bạn và trợ lý cùng sử dụng ma túy",
        "url": "https://dantri.com.vn/phap-luat/nguoi-mau-an-tay-ru-ban-va-tro-ly-cung-su-dung-ma-tuy-20260406152426197.htm",
        "source_name": "Dân trí",
        "published_hint": "2026-04-06",
    },
    {
        "article_id": "thanhnien-20260402-truy-to-an-tay-chi-dan-truc-phuong",
        "title": "Chuyên án bí số VN10: Truy tố người mẫu An Tây, ca sĩ Chi Dân, 'cô tiên' Trúc Phương",
        "url": "https://thanhnien.vn/chuyen-an-bi-so-vn10-truy-to-nguoi-mau-an-tay-ca-si-chi-dan-truc-phuong-185260402125551927.htm",
        "source_name": "Thanh Niên",
        "published_hint": "2026-04-02",
    },
    {
        "article_id": "thanhnien-20260403-chi-dan-ru-re-gop-tien-choi-ma-tuy",
        "title": "Chuyên án bí số VN10: Ca sĩ Chi Dân rủ rê, góp tiền 'chơi' ma túy",
        "url": "https://thanhnien.vn/chuyen-an-bi-so-vn10-ca-si-chi-dan-ru-re-gop-tien-choi-ma-tuy-185260403093444362.htm",
        "source_name": "Thanh Niên",
        "published_hint": "2026-04-03",
    },
    {
        "article_id": "dantri-20251208-andrea-aybar-chi-dan-vu-dien-hinh",
        "title": "Andrea Aybar, Chi Dân là vụ điển hình về nghệ sĩ sử dụng ma túy tại TPHCM",
        "url": "https://dantri.com.vn/phap-luat/andrea-aybar-chi-dan-la-vu-dien-hinh-ve-nghe-si-su-dung-ma-tuy-tai-tphcm-20251208100850146.htm",
        "source_name": "Dân trí",
        "published_hint": "2025-12-08",
    },
]


def ensure_dirs() -> None:
    for directory in [LEGAL_DIR, NEWS_DIR, STANDARDIZED_DIR / "legal", STANDARDIZED_DIR / "news"]:
        directory.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9-]+", "-", name)
    return re.sub(r"-+", "-", name).strip("-")


def download_file(url: str, dest: Path) -> None:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    if len(response.content) < 1024:
        raise RuntimeError(f"Downloaded file too small: {url} -> {len(response.content)} bytes")
    dest.write_bytes(response.content)


def task1_download_legal_docs() -> list[dict[str, Any]]:
    inventory = []
    for doc in LEGAL_DOCS:
        filename = safe_filename(doc["doc_id"]) + ".pdf"
        dest = LEGAL_DIR / filename
        download_file(doc["file_url"], dest)
        item = {
            **doc,
            "local_file": str(dest.relative_to(ROOT)),
            "bytes": dest.stat().st_size,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }
        inventory.append(item)
        print(f"[legal] {filename}: {dest.stat().st_size:,} bytes")

    (LEGAL_DIR / "legal_sources.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return inventory


def firecrawl_scrape(url: str) -> dict[str, Any]:
    response = requests.post(
        f"{FIRECRAWL_BASE_URL}/v1/scrape",
        json={"url": url, "formats": ["markdown"], "timeout": 120000},
        timeout=150,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"Firecrawl failed for {url}: {payload}")
    return payload


def task2_crawl_news() -> list[dict[str, Any]]:
    crawled = []
    for article in NEWS_ARTICLES:
        payload = firecrawl_scrape(article["url"])
        data = payload.get("data") or {}
        markdown = data.get("markdown") or data.get("content") or ""
        if len(markdown.strip()) < 500:
            raise RuntimeError(f"Scraped article too short: {article['url']} ({len(markdown)} chars)")

        output = {
            **article,
            "url": article["url"],
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "crawl_tool": "firecrawl-local",
            "firecrawl_endpoint": f"{FIRECRAWL_BASE_URL}/v1/scrape",
            "metadata": data.get("metadata") or {},
            "markdown": markdown,
        }
        dest = NEWS_DIR / f"{article['article_id']}.json"
        dest.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        crawled.append({k: output[k] for k in ["article_id", "title", "url", "source_name", "published_hint", "crawled_at"]})
        print(f"[news] {dest.name}: {len(markdown):,} markdown chars")

    (NEWS_DIR / "news_sources.json").write_text(
        json.dumps(
            {
                "url": "multiple-public-news-article-sources",
                "description": "Manifest for the five Firecrawl-crawled news articles in this folder.",
                "articles": crawled,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return crawled


def frontmatter(metadata: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, (list, dict)):
            rendered = json.dumps(value, ensure_ascii=False)
        else:
            rendered = str(value).replace('"', '\\"')
        lines.append(f'{key}: "{rendered}"')
    lines.append("---\n")
    return "\n".join(lines)


def task3_convert_to_markdown() -> None:
    md_converter = MarkItDown()

    for pdf_path in sorted(LEGAL_DIR.glob("*.pdf")):
        source_meta = next((doc for doc in LEGAL_DOCS if safe_filename(doc["doc_id"]) in pdf_path.stem), {})
        result = md_converter.convert(str(pdf_path))
        content = result.text_content.strip()
        conversion_method = "markitdown_pdf"
        if len(content) < 200:
            # Some official PDFs are image/scanned PDFs. Keep the PDF as the raw
            # legal source, but use Firecrawl on the official Government detail
            # page to create a useful markdown document for retrieval.
            fallback = firecrawl_scrape(source_meta.get("source_page", ""))
            content = ((fallback.get("data") or {}).get("markdown") or "").strip()
            conversion_method = "firecrawl_official_detail_page_fallback"
        if len(content) < 200:
            raise RuntimeError(f"Converted legal markdown too short: {pdf_path}")
        output_path = STANDARDIZED_DIR / "legal" / f"{pdf_path.stem}.md"
        metadata = {
            "doc_type": "legal_document",
            "title": source_meta.get("title", pdf_path.stem),
            "source_url": source_meta.get("file_url", ""),
            "source_page": source_meta.get("source_page", ""),
            "source_name": source_meta.get("source_name", ""),
            "issued_date": source_meta.get("issued_date", ""),
            "local_source_file": str(pdf_path.relative_to(ROOT)),
            "conversion_method": conversion_method,
            "converted_at": datetime.now(timezone.utc).isoformat(),
        }
        output_path.write_text(frontmatter(metadata) + content + "\n", encoding="utf-8")
        print(f"[convert/legal] {output_path.relative_to(ROOT)}: {len(content):,} chars")

    for json_path in sorted(NEWS_DIR.glob("*.json")):
        if json_path.name.endswith("_sources.json") or json_path.name == "news_sources.json":
            continue
        article = json.loads(json_path.read_text(encoding="utf-8"))
        content = (article.get("markdown") or "").strip()
        if len(content) < 200:
            raise RuntimeError(f"Converted news markdown too short: {json_path}")
        output_path = STANDARDIZED_DIR / "news" / f"{json_path.stem}.md"
        metadata = {
            "doc_type": "news_article",
            "title": article.get("title", json_path.stem),
            "source_url": article.get("url", ""),
            "source_name": article.get("source_name", ""),
            "published_hint": article.get("published_hint", ""),
            "crawl_tool": article.get("crawl_tool", ""),
            "local_source_file": str(json_path.relative_to(ROOT)),
            "converted_at": datetime.now(timezone.utc).isoformat(),
        }
        output_path.write_text(frontmatter(metadata) + content + "\n", encoding="utf-8")
        print(f"[convert/news] {output_path.relative_to(ROOT)}: {len(content):,} chars")


def verify_outputs() -> None:
    legal_files = [p for p in LEGAL_DIR.iterdir() if p.suffix.lower() in {".pdf", ".doc", ".docx"}]
    news_files = [p for p in NEWS_DIR.iterdir() if p.suffix.lower() in {".json", ".html", ".md", ".txt"} and not p.name.endswith("_sources.json")]
    md_files = list(STANDARDIZED_DIR.rglob("*.md"))
    print("\nVerification summary")
    print(f"  legal files: {len(legal_files)}")
    print(f"  news files: {len(news_files)}")
    print(f"  markdown files: {len(md_files)}")
    if len(legal_files) < 3 or len(news_files) < 5 or len(md_files) < 8:
        raise SystemExit("Verification failed: missing required Task 1-3 outputs")


def main() -> None:
    ensure_dirs()
    task1_download_legal_docs()
    task2_crawl_news()
    task3_convert_to_markdown()
    verify_outputs()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
