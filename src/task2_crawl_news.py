"""
Task 2 — Crawl bài báo về nghệ sĩ liên quan tới ma tuý.

Hướng dẫn:
    1. Crawl tối thiểu 5 bài báo từ các trang tin tức Việt Nam.
    2. Sử dụng Crawl4AI hoặc thư viện crawling tương tự.
    3. Lưu output vào data/landing/news/
    4. Mỗi bài lưu 1 file JSON với metadata (url, title, date_crawled, content).
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "landing" / "news"
MANIFEST_PATH = DATA_DIR / "news_sources.json"

ARTICLE_SOURCES: list[dict[str, str]] = [
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

# Compatibility name for the original scaffold.
ARTICLE_URLS = [article["url"] for article in ARTICLE_SOURCES]


def setup_directory() -> None:
    """Tạo thư mục data/landing/news/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _article_by_url(url: str) -> dict[str, str]:
    for article in ARTICLE_SOURCES:
        if article["url"] == url:
            return article
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", urlparse(url).path.strip("/")).strip("-")
    return {
        "article_id": slug[:80] or "article",
        "title": "Unknown",
        "url": url,
        "source_name": urlparse(url).netloc,
        "published_hint": "",
    }


def _load_cached_article(article_id: str) -> dict[str, Any] | None:
    cached_path = DATA_DIR / f"{article_id}.json"
    if not cached_path.exists():
        return None
    data = json.loads(cached_path.read_text(encoding="utf-8"))
    markdown = data.get("markdown") or data.get("content_markdown") or data.get("content")
    if markdown:
        return data
    return None


async def crawl_article(url: str, use_cache: bool = True) -> dict[str, Any]:
    """
    Crawl một bài báo và trả về dict chứa metadata + content.

    The function prefers the existing local cache when available, then uses
    Crawl4AI for a real crawl. This keeps the lab reproducible while still
    allowing a fresh crawl when the cached JSON files are absent.
    """
    article = _article_by_url(url)
    if use_cache:
        cached = _load_cached_article(article["article_id"])
        if cached is not None:
            print(f"  ✓ Using cached article: {article['article_id']}.json")
            return cached

    try:
        from importlib import import_module

        AsyncWebCrawler = import_module("crawl4ai").AsyncWebCrawler
    except ImportError as exc:
        raise RuntimeError(
            "crawl4ai chưa được cài. Chạy: pip install crawl4ai"
        ) from exc

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

    markdown = getattr(result, "markdown", "") or ""
    metadata = getattr(result, "metadata", {}) or {}
    title = metadata.get("title") or metadata.get("og:title") or article["title"]

    return {
        "article_id": article["article_id"],
        "title": title,
        "url": url,
        "source_name": article["source_name"],
        "published_hint": article["published_hint"],
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "crawl_tool": "crawl4ai",
        "metadata": metadata,
        "markdown": markdown,
        # Keep the original scaffold field name for students/tests that expect it.
        "content_markdown": markdown,
    }


async def crawl_all(use_cache: bool = True) -> list[dict[str, Any]]:
    """Crawl toàn bộ bài báo trong ARTICLE_URLS và lưu JSON output."""
    setup_directory()
    crawled_articles: list[dict[str, Any]] = []
    manifest_articles: list[dict[str, Any]] = []

    for i, article_source in enumerate(ARTICLE_SOURCES, 1):
        url = article_source["url"]
        print(f"[{i}/{len(ARTICLE_SOURCES)}] Crawling: {url}")
        article = await crawl_article(url, use_cache=use_cache)

        # Normalize keys so cached Firecrawl output and fresh Crawl4AI output share a stable schema.
        article = {
            **article_source,
            **article,
            "url": url,
            "date_crawled": article.get("date_crawled") or article.get("crawled_at") or datetime.now(timezone.utc).isoformat(),
            "content_markdown": article.get("content_markdown") or article.get("markdown") or article.get("content") or "",
        }

        filepath = DATA_DIR / f"{article_source['article_id']}.json"
        filepath.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ Saved: {filepath}")

        crawled_articles.append(article)
        manifest_articles.append(
            {
                "article_id": article_source["article_id"],
                "title": article.get("title", article_source["title"]),
                "url": url,
                "source_name": article_source["source_name"],
                "published_hint": article_source["published_hint"],
                "crawled_at": article.get("date_crawled"),
            }
        )

    manifest = {
        "url": "multiple-public-news-article-sources",
        "description": "Manifest for the five crawled news articles in this folder.",
        "articles": manifest_articles,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Manifest saved: {MANIFEST_PATH}")
    return crawled_articles


if __name__ == "__main__":
    asyncio.run(crawl_all())
