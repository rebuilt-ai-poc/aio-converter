"""HTTP-level tests through FastAPI's TestClient."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


_pandoc_missing = pytest.mark.skipif(
    shutil.which("pandoc") is None, reason="pandoc required"
)
_typst_missing = pytest.mark.skipif(
    shutil.which("typst") is None, reason="typst required"
)


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_system_reports_engines() -> None:
    r = client.get("/api/system")
    assert r.status_code == 200
    body = r.json()
    assert "engines" in body and "conversions" in body
    # These pure-Python engines should always be present.
    for k in ("pymupdf", "reportlab", "pillow"):
        assert body["engines"][k] is True


def test_convert_pdf_to_txt(fixtures_dir: Path) -> None:
    with (fixtures_dir / "simple.pdf").open("rb") as f:
        r = client.post(
            "/api/convert",
            data={"output_format": "txt"},
            files={"file": ("simple.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200, r.text
    assert "Hello, World!" in r.text
    assert r.headers["content-type"].startswith("text/plain")
    disp = r.headers["content-disposition"]
    assert "simple.txt" in disp


def test_convert_png_to_jpg(fixtures_dir: Path) -> None:
    with (fixtures_dir / "opaque.png").open("rb") as f:
        r = client.post(
            "/api/convert",
            data={"output_format": "jpg"},
            files={"file": ("opaque.png", f, "image/png")},
        )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "image/jpeg"
    assert r.content[:3] == b"\xff\xd8\xff"


def test_convert_txt_to_pdf(fixtures_dir: Path) -> None:
    with (fixtures_dir / "plain.txt").open("rb") as f:
        r = client.post(
            "/api/convert",
            data={"output_format": "pdf"},
            files={"file": ("plain.txt", f, "text/plain")},
        )
    assert r.status_code == 200, r.text
    assert r.content.startswith(b"%PDF-")


def test_convert_rejects_mismatched_extension(fixtures_dir: Path) -> None:
    # Send an actual PNG but claim it's a PDF.
    with (fixtures_dir / "opaque.png").open("rb") as f:
        r = client.post(
            "/api/convert",
            data={"output_format": "txt"},
            files={"file": ("opaque.pdf", f, "application/pdf")},
        )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_FILE"


def test_convert_rejects_unsupported_pair(fixtures_dir: Path) -> None:
    with (fixtures_dir / "plain.txt").open("rb") as f:
        r = client.post(
            "/api/convert",
            data={"output_format": "docx"},
            files={"file": ("plain.txt", f, "text/plain")},
        )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_merge_pdf(fixtures_dir: Path) -> None:
    import pymupdf

    with (fixtures_dir / "two-page.pdf").open("rb") as f1, (fixtures_dir / "three-page.pdf").open("rb") as f2:
        r = client.post(
            "/api/merge/pdf",
            files=[
                ("files", ("a.pdf", f1.read(), "application/pdf")),
                ("files", ("b.pdf", f2.read(), "application/pdf")),
            ],
        )
    assert r.status_code == 200, r.text
    assert r.content.startswith(b"%PDF-")
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    try:
        assert doc.page_count == 5
    finally:
        doc.close()


def test_merge_pdf_rejects_single(fixtures_dir: Path) -> None:
    with (fixtures_dir / "two-page.pdf").open("rb") as f:
        r = client.post(
            "/api/merge/pdf",
            files=[("files", ("a.pdf", f.read(), "application/pdf"))],
        )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# EPUB round-trips (all through Pandoc; PDF needs Typst too)
# ---------------------------------------------------------------------------
@_pandoc_missing
def test_convert_epub_to_txt(fixtures_dir: Path) -> None:
    with (fixtures_dir / "simple.epub").open("rb") as f:
        r = client.post(
            "/api/convert",
            data={"output_format": "txt"},
            files={"file": ("simple.epub", f, "application/epub+zip")},
        )
    assert r.status_code == 200, r.text
    assert "Chapter One" in r.text
    assert "SIMPLE_EPUB_CH2" in r.text
    assert "simple.txt" in r.headers["content-disposition"]


@_pandoc_missing
def test_convert_epub_to_markdown(fixtures_dir: Path) -> None:
    with (fixtures_dir / "simple.epub").open("rb") as f:
        r = client.post(
            "/api/convert",
            data={"output_format": "md"},
            files={"file": ("simple.epub", f, "application/epub+zip")},
        )
    assert r.status_code == 200, r.text
    assert "# Chapter One" in r.text
    assert "alpha" in r.text
    assert r.headers["content-type"].startswith("text/markdown")


@_pandoc_missing
@_typst_missing
def test_convert_epub_to_pdf(fixtures_dir: Path) -> None:
    import pymupdf

    with (fixtures_dir / "simple.epub").open("rb") as f:
        r = client.post(
            "/api/convert",
            data={"output_format": "pdf"},
            files={"file": ("simple.epub", f, "application/epub+zip")},
        )
    assert r.status_code == 200, r.text
    assert r.content.startswith(b"%PDF-")
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    try:
        text = "\n".join(p.get_text("text") for p in doc)
    finally:
        doc.close()
    assert "Chapter One" in text
    assert "SIMPLE_EPUB_CH2" in text


# ---------------------------------------------------------------------------
# PDF page operations
# ---------------------------------------------------------------------------
def test_system_lists_pdf_operations() -> None:
    body = client.get("/api/system").json()
    for key in ("pdf:split", "pdf:delete-pages", "pdf:extract-pages", "pdf:reorder-pages"):
        assert key in body["conversions"], body["conversions"]
        assert body["conversions"][key] is True


def test_pdf_split_returns_zip(fixtures_dir: Path) -> None:
    import io
    import zipfile

    with (fixtures_dir / "ten-page.pdf").open("rb") as f:
        r = client.post(
            "/api/pdf/split",
            data={"options": '{"mode": "every_n", "n": 3}'},
            files={"file": ("ten-page.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    assert "ten-page-split.zip" in r.headers["content-disposition"]
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = sorted(zf.namelist())
    assert names == ["part-01.pdf", "part-02.pdf", "part-03.pdf", "part-04.pdf"]


def test_pdf_delete_pages(fixtures_dir: Path) -> None:
    import pymupdf

    with (fixtures_dir / "ten-page.pdf").open("rb") as f:
        r = client.post(
            "/api/pdf/delete-pages",
            data={"options": '{"pages": [3, 5]}'},
            files={"file": ("ten-page.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "ten-page-edited.pdf" in r.headers["content-disposition"]
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    try:
        text = "\n".join(p.get_text("text") for p in doc)
        assert doc.page_count == 8
    finally:
        doc.close()
    assert "PAGE#3" not in text
    assert "PAGE#5" not in text
    assert "PAGE#1" in text and "PAGE#10" in text


def test_pdf_delete_pages_rejects_deleting_all(fixtures_dir: Path) -> None:
    with (fixtures_dir / "three-page.pdf").open("rb") as f:
        r = client.post(
            "/api/pdf/delete-pages",
            data={"options": '{"pages": [1, 2, 3]}'},
            files={"file": ("three-page.pdf", f, "application/pdf")},
        )
    assert r.status_code == 400, r.text
    body = r.json()
    assert body["error"]["code"] == "INVALID_OPTIONS"


def test_pdf_extract_pages(fixtures_dir: Path) -> None:
    import pymupdf

    with (fixtures_dir / "ten-page.pdf").open("rb") as f:
        r = client.post(
            "/api/pdf/extract-pages",
            data={"options": '{"pages": [2, 4, 7, 8]}'},
            files={"file": ("ten-page.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "ten-page-extracted.pdf" in r.headers["content-disposition"]
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    try:
        assert doc.page_count == 4
        pages = [p.get_text("text") for p in doc]
    finally:
        doc.close()
    assert "PAGE#2" in pages[0]
    assert "PAGE#4" in pages[1]
    assert "PAGE#7" in pages[2]
    assert "PAGE#8" in pages[3]


def test_pdf_reorder_pages(fixtures_dir: Path) -> None:
    import pymupdf

    with (fixtures_dir / "three-page.pdf").open("rb") as f:
        r = client.post(
            "/api/pdf/reorder-pages",
            data={"options": '{"order": [3, 1, 2]}'},
            files={"file": ("three-page.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "three-page-reordered.pdf" in r.headers["content-disposition"]
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    try:
        pages = [p.get_text("text") for p in doc]
    finally:
        doc.close()
    assert "THREE#3" in pages[0]
    assert "THREE#1" in pages[1]
    assert "THREE#2" in pages[2]


def test_pdf_reorder_rejects_non_permutation(fixtures_dir: Path) -> None:
    with (fixtures_dir / "three-page.pdf").open("rb") as f:
        r = client.post(
            "/api/pdf/reorder-pages",
            data={"options": '{"order": [1, 2]}'},
            files={"file": ("three-page.pdf", f, "application/pdf")},
        )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_OPTIONS"


def test_pdf_split_rejects_non_pdf(fixtures_dir: Path) -> None:
    with (fixtures_dir / "opaque.png").open("rb") as f:
        r = client.post(
            "/api/pdf/split",
            data={"options": '{"mode": "every_page"}'},
            files={"file": ("opaque.png", f, "image/png")},
        )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_FILE"
