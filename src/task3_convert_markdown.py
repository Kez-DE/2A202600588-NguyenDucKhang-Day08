"""
Task 3 — Convert toàn bộ file trong data/landing/ thành Markdown.

Sử dụng MarkItDown của Microsoft:
    https://github.com/microsoft/markitdown

Hướng dẫn:
    1. Scan toàn bộ file trong data/landing/ (PDF, DOCX, JSON)
    2. Convert sang Markdown
    3. Lưu vào data/standardized/ giữ nguyên cấu trúc thư mục
"""

from __future__ import annotations

import json
import subprocess
from importlib import import_module
from pathlib import Path
from typing import Any


def _load_markitdown_class():
    try:
        return import_module("markitdown").MarkItDown
    except ImportError:
        return None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LANDING_DIR = PROJECT_ROOT / "data" / "landing"
OUTPUT_DIR = PROJECT_ROOT / "data" / "standardized"


def _write_markdown(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"  ✓ Saved: {output_path}")


def _load_title_from_legal_manifest() -> dict[str, str]:
    manifest_path = LANDING_DIR / "legal" / "legal_sources.json"
    if not manifest_path.exists():
        return {}
    docs = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {Path(doc.get("local_file", "")).stem: doc.get("title", "") for doc in docs}


def _convert_pdf_with_pdftotext(filepath: Path) -> str:
    """Fallback PDF extraction when MarkItDown is installed without [pdf] extras."""
    completed = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(filepath), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text_content = completed.stdout.strip()
    if not text_content:
        raise ValueError(f"pdftotext không trích xuất được nội dung từ {filepath}")
    return text_content


def convert_legal_docs() -> list[Path]:
    """Convert PDF/DOCX files trong data/landing/legal/ sang markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not legal_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục legal: {legal_dir}")

    MarkItDown = _load_markitdown_class()
    md = MarkItDown() if MarkItDown is not None else None
    legal_titles = _load_title_from_legal_manifest()
    converted: list[Path] = []

    for filepath in sorted(legal_dir.iterdir()):
        if filepath.suffix.lower() not in (".pdf", ".docx", ".doc"):
            continue

        print(f"Converting: {filepath.name}")
        output_path = output_dir / f"{filepath.stem}.md"
        if output_path.exists() and output_path.read_text(encoding="utf-8").strip():
            print(f"  ✓ Reusing existing markdown: {output_path}")
            converted.append(output_path)
            continue

        if md is None:
            text_content = _convert_pdf_with_pdftotext(filepath)
        else:
            try:
                result = md.convert(str(filepath))
                text_content = getattr(result, "text_content", "") or ""
            except Exception as exc:
                if filepath.suffix.lower() == ".pdf":
                    print(f"  ! MarkItDown failed for PDF, falling back to pdftotext: {exc}")
                    text_content = _convert_pdf_with_pdftotext(filepath)
                else:
                    raise

        if not text_content.strip():
            raise ValueError(f"Không trích xuất được nội dung từ {filepath}")

        title = legal_titles.get(filepath.stem)
        header = ""
        if title:
            header = f"# {title}\n\n**Source file:** `{filepath.relative_to(PROJECT_ROOT)}`\n\n---\n\n"

        _write_markdown(output_path, header + text_content)
        converted.append(output_path)

    if len(converted) < 3:
        raise RuntimeError(f"Task 3 yêu cầu tối thiểu 3 legal markdown files, hiện có {len(converted)}")
    return converted


def _article_markdown_from_json(data: dict[str, Any]) -> str:
    title = data.get("title") or data.get("metadata", {}).get("title") or "Unknown"
    url = data.get("url") or data.get("metadata", {}).get("sourceURL") or "N/A"
    source_name = data.get("source_name") or data.get("metadata", {}).get("og:site_name") or "N/A"
    published_hint = data.get("published_hint") or "N/A"
    crawled = data.get("date_crawled") or data.get("crawled_at") or "N/A"
    body = data.get("content_markdown") or data.get("markdown") or data.get("content") or ""

    if not body.strip():
        raise ValueError(f"JSON article thiếu content_markdown/markdown: {title}")

    header = (
        f"# {title}\n\n"
        f"**Source:** {url}\n\n"
        f"**Publisher:** {source_name}\n\n"
        f"**Published hint:** {published_hint}\n\n"
        f"**Crawled:** {crawled}\n\n"
        "---\n\n"
    )
    return header + body


def convert_news_articles() -> list[Path]:
    """Convert JSON crawled articles trong data/landing/news/ sang markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not news_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục news: {news_dir}")

    converted: list[Path] = []
    for filepath in sorted(news_dir.iterdir()):
        if filepath.suffix.lower() != ".json" or filepath.name.endswith("_sources.json"):
            continue

        print(f"Converting: {filepath.name}")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        output_path = output_dir / f"{filepath.stem}.md"
        _write_markdown(output_path, _article_markdown_from_json(data))
        converted.append(output_path)

    if len(converted) < 5:
        raise RuntimeError(f"Task 3 yêu cầu tối thiểu 5 news markdown files, hiện có {len(converted)}")
    return converted


def convert_all() -> tuple[list[Path], list[Path]]:
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown (MarkItDown)")
    print("=" * 50)

    print("\n--- Legal Documents ---")
    legal_outputs = convert_legal_docs()

    print("\n--- News Articles ---")
    news_outputs = convert_news_articles()

    print("\n✓ Done! Output tại:", OUTPUT_DIR)
    print(f"✓ Legal markdown files: {len(legal_outputs)}")
    print(f"✓ News markdown files: {len(news_outputs)}")
    return legal_outputs, news_outputs


if __name__ == "__main__":
    convert_all()
