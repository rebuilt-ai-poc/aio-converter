"""HTTP-level tests through FastAPI's TestClient."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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
