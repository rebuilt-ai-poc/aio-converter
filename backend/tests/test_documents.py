"""Document converter tests (TXT/MD/DOCX -> PDF)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.converters.documents import (
    docx_to_pdf,
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
