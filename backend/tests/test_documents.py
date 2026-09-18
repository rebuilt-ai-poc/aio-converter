"""Document converter tests (TXT/MD/DOCX -> PDF)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.converters.documents import (
    docx_to_pdf,
    epub_to_markdown,
    epub_to_pdf,
    epub_to_txt,
    find_soffice,
    markdown_to_pdf,
    txt_to_pdf,
)


# ---------------------------------------------------------------------------
# TXT -> PDF
# ---------------------------------------------------------------------------
def test_txt_to_pdf_roundtrip(tmp_path: Path, fixtures_dir: Path) -> None:
    """Convert TXT -> PDF, then extract text with PyMuPDF and compare."""
    import pymupdf

    out = tmp_path / "out.pdf"
    txt_to_pdf(fixtures_dir / "plain.txt", out, {})
    assert out.exists() and out.stat().st_size > 0

    doc = pymupdf.open(out)
    try:
        extracted = "\n".join(p.get_text("text") for p in doc)
    finally:
        doc.close()
    assert "quick brown fox" in extracted
    assert "line two of the plain text fixture" in extracted


def test_txt_to_pdf_unicode(tmp_path: Path, fixtures_dir: Path) -> None:
    import pymupdf

    out = tmp_path / "out.pdf"
    txt_to_pdf(fixtures_dir / "unicode.txt", out, {})
    doc = pymupdf.open(out)
    try:
        extracted = "\n".join(p.get_text("text") for p in doc)
    finally:
        doc.close()
    # Bundled Noto Sans covers Latin extended, Greek, and Cyrillic.
    assert "café" in extracted
    assert "Über" in extracted
    assert "Καλημέρα" in extracted
    assert "Привет" in extracted


def test_txt_to_pdf_landscape_letter(tmp_path: Path, fixtures_dir: Path) -> None:
    import pymupdf

    out = tmp_path / "out.pdf"
    txt_to_pdf(
        fixtures_dir / "plain.txt",
        out,
        {"page_size": "letter", "orientation": "landscape", "margins": "narrow", "font_size": 14},
    )
    doc = pymupdf.open(out)
    try:
        page = doc[0]
        w, h = page.rect.width, page.rect.height
    finally:
        doc.close()
    # Landscape means width > height.
    assert w > h


# ---------------------------------------------------------------------------
# Markdown -> PDF (skipped if pandoc/typst missing)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    shutil.which("pandoc") is None or shutil.which("typst") is None,
    reason="pandoc and typst are required for md->pdf",
)
def test_markdown_to_pdf(tmp_path: Path, fixtures_dir: Path) -> None:
    import pymupdf

    out = tmp_path / "out.pdf"
    markdown_to_pdf(fixtures_dir / "simple.md", out, {})
    assert out.exists() and out.stat().st_size > 0
    doc = pymupdf.open(out)
    try:
        text = "\n".join(p.get_text("text") for p in doc)
    finally:
        doc.close()
    assert "Simple Document" in text
    assert "Subsection" in text
    assert "item one" in text


# ---------------------------------------------------------------------------
# DOCX -> PDF (skipped if soffice missing)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(find_soffice() is None, reason="LibreOffice not installed")
def test_docx_to_pdf(tmp_path: Path, fixtures_dir: Path) -> None:
    import pymupdf

    out = tmp_path / "out.pdf"
    docx_to_pdf(fixtures_dir / "simple.docx", out, {})
    assert out.exists() and out.stat().st_size > 0
    doc = pymupdf.open(out)
    try:
        text = "\n".join(p.get_text("text") for p in doc)
    finally:
        doc.close()
    assert "Sample Document" in text
    assert "paragraph inside a DOCX fixture" in text


# ---------------------------------------------------------------------------
# EPUB -> TXT / Markdown / PDF (all need Pandoc; PDF also needs Typst)
# ---------------------------------------------------------------------------
_pandoc_missing = pytest.mark.skipif(
    shutil.which("pandoc") is None, reason="pandoc required for EPUB conversions"
)
_typst_missing = pytest.mark.skipif(
    shutil.which("typst") is None, reason="typst required for EPUB -> PDF"
)


@_pandoc_missing
def test_epub_to_txt_preserves_content(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "out.txt"
    epub_to_txt(fixtures_dir / "simple.epub", out, {})
    text = out.read_text(encoding="utf-8")
    assert "Chapter One" in text
    assert "Chapter Two" in text
    assert "SIMPLE_EPUB_CH2" in text
    assert "café" in text


@_pandoc_missing
def test_epub_to_txt_preserves_spine_order(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "out.txt"
    epub_to_txt(fixtures_dir / "ordered.epub", out, {})
    text = out.read_text(encoding="utf-8")
    i1, i2, i3 = text.find("EP#1"), text.find("EP#2"), text.find("EP#3")
    assert 0 <= i1 < i2 < i3, text


@_pandoc_missing
def test_epub_to_markdown_preserves_structure(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "out.md"
    epub_to_markdown(fixtures_dir / "simple.epub", out, {})
    md = out.read_text(encoding="utf-8")
    # Headings survive as ATX-style H1 (gfm target).
    assert "# Chapter One" in md
    assert "# Chapter Two" in md
    # List survives.
    assert "alpha" in md and "beta" in md and "gamma" in md
    # Should not still contain XHTML source markup.
    assert "<html" not in md and "<body" not in md


@_pandoc_missing
@_typst_missing
def test_epub_to_pdf_opens_and_has_content(tmp_path: Path, fixtures_dir: Path) -> None:
    import pymupdf

    out = tmp_path / "out.pdf"
    epub_to_pdf(fixtures_dir / "simple.epub", out, {})
    assert out.exists() and out.stat().st_size > 0
    doc = pymupdf.open(out)
    try:
        assert doc.page_count >= 1
        text = "\n".join(p.get_text("text") for p in doc)
    finally:
        doc.close()
    assert "Chapter One" in text
    assert "Chapter Two" in text
    assert "SIMPLE_EPUB_CH2" in text
