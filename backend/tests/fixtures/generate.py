"""Generate all test fixtures. Run: `python tests/fixtures/generate.py`.

Fixtures are kept tiny and deterministic. Regenerate whenever tests need
new content.
"""
from __future__ import annotations

import io
from pathlib import Path

FIXTURES = Path(__file__).parent


# ---------------------------------------------------------------------------
# PDFs (via PyMuPDF)
# ---------------------------------------------------------------------------
def _pdf_simple(path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)  # A4
    p.insert_text((72, 100), "Hello, World!", fontsize=14)
    p.insert_text((72, 130), "This is a simple test PDF.", fontsize=11)
    # Only Latin-extended Unicode here — PyMuPDF's default fonts don't have
    # CJK/emoji glyphs, and neither does the app's bundled Noto Sans (Latin).
    p.insert_text((72, 160), "Unicode: cafe - naive - Uber - Zurich", fontsize=11)
    doc.save(path)
    doc.close()


def _pdf_multipage(path: Path, pages: int, tag: str) -> None:
    import pymupdf

    doc = pymupdf.open()
    for i in range(pages):
        p = doc.new_page(width=595, height=842)
        p.insert_text((72, 100), f"{tag} page {i + 1} of {pages}", fontsize=14)
        p.insert_text((72, 130), f"Marker: {tag}#{i + 1}", fontsize=11)
    doc.save(path)
    doc.close()


def _pdf_with_headings(path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((72, 100), "Chapter One", fontsize=22)
    p.insert_text((72, 140), "Introduction", fontsize=16)
    p.insert_text(
        (72, 180),
        "This is a paragraph in the body text at the default size.",
        fontsize=11,
    )
    p.insert_text(
        (72, 210),
        "It contains multiple sentences. Some of them are short.",
        fontsize=11,
    )
    p.insert_text((72, 260), "Details", fontsize=13)
    p.insert_text(
        (72, 290),
        "A shorter section that follows a smaller subhead.",
        fontsize=11,
    )
    doc.save(path)
    doc.close()


def _pdf_with_table(path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((72, 60), "Sales report", fontsize=16)

    # Draw a 3x3 table by drawing rects and inserting text.
    rows = [
        ["Region", "Q1", "Q2"],
        ["North", "10", "12"],
        ["South", "8", "15"],
    ]
    x0, y0 = 72, 100
    cw, rh = 130, 24
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            rect = pymupdf.Rect(
                x0 + ci * cw,
                y0 + ri * rh,
                x0 + (ci + 1) * cw,
                y0 + (ri + 1) * rh,
            )
            p.draw_rect(rect, color=(0, 0, 0), width=0.5)
            p.insert_textbox(rect, cell, fontsize=11, align=1)
    doc.save(path)
    doc.close()


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
def _png_opaque(path: Path) -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (120, 80), (200, 220, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 110, 70], outline=(30, 30, 90), width=2)
    d.text((20, 30), "OPAQUE", fill=(30, 30, 90))
    img.save(path)


def _png_transparent(path: Path) -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (120, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([10, 10, 110, 70], fill=(200, 60, 60, 200))
    img.save(path)


def _svg_simple(path: Path) -> None:
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120" width="200" height="120">
  <rect x="0" y="0" width="200" height="120" fill="#eef2ff"/>
  <circle cx="100" cy="60" r="40" fill="#4f46e5"/>
  <text x="100" y="65" text-anchor="middle" fill="white" font-size="14"
        font-family="sans-serif">SVG</text>
</svg>
""",
        encoding="utf-8",
    )


def _svg_transparent(path: Path) -> None:
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120" width="200" height="120">
  <circle cx="60" cy="60" r="40" fill="rgba(255,0,0,0.7)"/>
  <circle cx="120" cy="60" r="40" fill="rgba(0,0,255,0.5)"/>
</svg>
""",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Text / Markdown
# ---------------------------------------------------------------------------
def _txt_plain(path: Path) -> None:
    path.write_text(
        "The quick brown fox jumps over the lazy dog.\n"
        "This is line two of the plain text fixture.\n"
        "\n"
        "A blank line separates paragraphs.\n",
        encoding="utf-8",
    )


def _txt_unicode(path: Path) -> None:
    # Bundled Noto Sans (Latin) covers Western + extended Latin, Greek, Cyrillic.
    # CJK / emoji require additional fonts (see README limitations).
    path.write_text(
        "English: The quick brown fox.\n"
        "Français: L'élève a mangé un café.\n"
        "Deutsch: Über der grüße Straße.\n"
        "Ελληνικά: Καλημέρα κόσμε.\n"
        "Русский: Привет, мир!\n",
        encoding="utf-8",
    )


def _md_simple(path: Path) -> None:
    path.write_text(
        "# Simple Document\n\n"
        "This is a paragraph with **bold** and *italic* text.\n\n"
        "## Subsection\n\n"
        "- item one\n- item two\n- item three\n\n"
        "A final paragraph.\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------
def _docx_simple(path: Path) -> None:
    from docx import Document

    d = Document()
    d.add_heading("Sample Document", level=1)
    d.add_paragraph("This is a paragraph inside a DOCX fixture.")
    d.add_paragraph("A second paragraph with more content.")
    d.add_heading("Details", level=2)
    d.add_paragraph("The rest of the document follows.")
    d.save(path)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def generate_all() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    _pdf_simple(FIXTURES / "simple.pdf")
    _pdf_multipage(FIXTURES / "two-page.pdf", 2, "TWO")
    _pdf_multipage(FIXTURES / "three-page.pdf", 3, "THREE")
    _pdf_with_headings(FIXTURES / "headings.pdf")
    _pdf_with_table(FIXTURES / "table.pdf")

    _png_opaque(FIXTURES / "opaque.png")
    _png_transparent(FIXTURES / "transparent.png")
    _svg_simple(FIXTURES / "simple.svg")
    _svg_transparent(FIXTURES / "transparent.svg")

    _txt_plain(FIXTURES / "plain.txt")
    _txt_unicode(FIXTURES / "unicode.txt")

    _md_simple(FIXTURES / "simple.md")

    _docx_simple(FIXTURES / "simple.docx")

    print("Generated fixtures in", FIXTURES)


if __name__ == "__main__":
    generate_all()
