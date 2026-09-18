"""PDF page-operation converter tests.

Covers split / delete / extract / reorder and their validation.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app.converters.pdf import (
    delete_pdf_pages,
    extract_pdf_pages,
    reorder_pdf_pages,
    split_pdf,
    zip_outputs,
)
from app.core.errors import InvalidFileError, InvalidOptionsError


def _open(path: Path):
    import pymupdf

    return pymupdf.open(path)


def _page_texts(path: Path) -> list[str]:
    doc = _open(path)
    try:
        return [p.get_text("text") for p in doc]
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# split
# ---------------------------------------------------------------------------
def test_split_every_page_produces_one_file_per_page(tmp_path: Path, fixtures_dir: Path) -> None:
    out_dir = tmp_path / "parts"
    written = split_pdf(fixtures_dir / "ten-page.pdf", out_dir, {"type": "every_page"})
    assert len(written) == 10
    for i, p in enumerate(written, start=1):
        assert p.exists()
        pages = _page_texts(p)
        assert len(pages) == 1
        assert f"PAGE#{i}" in pages[0]


def test_split_every_page_naming_pads_to_two_digits(tmp_path: Path, fixtures_dir: Path) -> None:
    out_dir = tmp_path / "parts"
    written = split_pdf(fixtures_dir / "ten-page.pdf", out_dir, {"type": "every_page"})
    names = [p.name for p in written]
    assert names[0] == "part-01.pdf"
    assert names[-1] == "part-10.pdf"


def test_split_every_n_chunks(tmp_path: Path, fixtures_dir: Path) -> None:
    out_dir = tmp_path / "parts"
    written = split_pdf(fixtures_dir / "ten-page.pdf", out_dir, {"type": "every_n", "n": 3})
    # 10 pages / n=3 → 4 files: [1-3], [4-6], [7-9], [10]
    assert len(written) == 4
    lens = [len(_page_texts(p)) for p in written]
    assert lens == [3, 3, 3, 1]
    # Spot-check markers.
    assert "PAGE#1" in _page_texts(written[0])[0]
    assert "PAGE#10" in _page_texts(written[3])[0]


def test_split_ranges(tmp_path: Path, fixtures_dir: Path) -> None:
    out_dir = tmp_path / "parts"
    written = split_pdf(
        fixtures_dir / "ten-page.pdf",
        out_dir,
        {"type": "ranges", "ranges": [[1, 2], [5, 7]]},
    )
    assert len(written) == 2
    r1 = _page_texts(written[0])
    r2 = _page_texts(written[1])
    assert len(r1) == 2 and "PAGE#1" in r1[0] and "PAGE#2" in r1[1]
    assert len(r2) == 3 and "PAGE#5" in r2[0] and "PAGE#7" in r2[2]


def test_split_padding_scales_with_part_count(tmp_path: Path) -> None:
    import pymupdf

    # Fabricate a 120-page PDF in-test to assert 3-digit padding.
    src = tmp_path / "big.pdf"
    doc = pymupdf.open()
    for i in range(120):
        p = doc.new_page(width=200, height=200)
        p.insert_text((20, 40), f"BIG#{i + 1}", fontsize=10)
    doc.save(src)
    doc.close()

    out_dir = tmp_path / "parts"
    written = split_pdf(src, out_dir, {"type": "every_page"})
    assert len(written) == 120
    assert written[0].name == "part-001.pdf"
    assert written[-1].name == "part-120.pdf"


def test_split_rejects_bad_n(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        split_pdf(fixtures_dir / "ten-page.pdf", tmp_path / "p", {"type": "every_n", "n": 0})


def test_split_rejects_reversed_range(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        split_pdf(
            fixtures_dir / "ten-page.pdf",
            tmp_path / "p",
            {"type": "ranges", "ranges": [[5, 2]]},
        )


def test_split_rejects_out_of_range(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        split_pdf(
            fixtures_dir / "ten-page.pdf",
            tmp_path / "p",
            {"type": "ranges", "ranges": [[1, 99]]},
        )


def test_split_rejects_unknown_mode(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        split_pdf(fixtures_dir / "ten-page.pdf", tmp_path / "p", {"type": "bogus"})


def test_split_rejects_non_pdf(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidFileError):
        split_pdf(fixtures_dir / "simple.md", tmp_path / "p", {"type": "every_page"})


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------
def test_delete_pdf_pages_removes_selected(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "edited.pdf"
    delete_pdf_pages(fixtures_dir / "ten-page.pdf", out, [3, 5])
    texts = _page_texts(out)
    assert len(texts) == 8
    combined = "\n".join(texts)
    assert "PAGE#3" not in combined
    assert "PAGE#5" not in combined
    assert "PAGE#1" in combined
    assert "PAGE#10" in combined


def test_delete_pdf_pages_rejects_deleting_every_page(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        delete_pdf_pages(
            fixtures_dir / "ten-page.pdf",
            tmp_path / "edited.pdf",
            list(range(1, 11)),
        )


def test_delete_pdf_pages_rejects_empty(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        delete_pdf_pages(fixtures_dir / "ten-page.pdf", tmp_path / "edited.pdf", [])


def test_delete_pdf_pages_rejects_out_of_range(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        delete_pdf_pages(fixtures_dir / "ten-page.pdf", tmp_path / "edited.pdf", [99])


def test_delete_pdf_pages_rejects_duplicates(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        delete_pdf_pages(fixtures_dir / "ten-page.pdf", tmp_path / "edited.pdf", [3, 3])


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------
def test_extract_pdf_pages_keeps_requested_order(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "ext.pdf"
    extract_pdf_pages(fixtures_dir / "ten-page.pdf", out, [2, 4, 7, 8])
    texts = _page_texts(out)
    assert len(texts) == 4
    assert "PAGE#2" in texts[0]
    assert "PAGE#4" in texts[1]
    assert "PAGE#7" in texts[2]
    assert "PAGE#8" in texts[3]


def test_extract_pdf_pages_rejects_duplicates(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        extract_pdf_pages(fixtures_dir / "ten-page.pdf", tmp_path / "ext.pdf", [2, 2, 4])


def test_extract_pdf_pages_rejects_empty(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        extract_pdf_pages(fixtures_dir / "ten-page.pdf", tmp_path / "ext.pdf", [])


def test_extract_pdf_pages_rejects_out_of_range(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        extract_pdf_pages(fixtures_dir / "ten-page.pdf", tmp_path / "ext.pdf", [0])


# ---------------------------------------------------------------------------
# reorder
# ---------------------------------------------------------------------------
def test_reorder_pdf_pages_permutes_pages(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "reord.pdf"
    # Reverse a 3-page fixture.
    reorder_pdf_pages(fixtures_dir / "three-page.pdf", out, [3, 2, 1])
    texts = _page_texts(out)
    assert len(texts) == 3
    assert "THREE#3" in texts[0]
    assert "THREE#2" in texts[1]
    assert "THREE#1" in texts[2]


def test_reorder_pdf_pages_rejects_missing_page(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        # Missing page 2.
        reorder_pdf_pages(fixtures_dir / "three-page.pdf", tmp_path / "r.pdf", [1, 3])


def test_reorder_pdf_pages_rejects_extras(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        # Extra page 4 that doesn't exist.
        reorder_pdf_pages(
            fixtures_dir / "three-page.pdf", tmp_path / "r.pdf", [1, 2, 3, 4]
        )


def test_reorder_pdf_pages_rejects_duplicates(tmp_path: Path, fixtures_dir: Path) -> None:
    with pytest.raises(InvalidOptionsError):
        # Same length but duplicate — not a permutation.
        reorder_pdf_pages(fixtures_dir / "three-page.pdf", tmp_path / "r.pdf", [1, 1, 3])


# ---------------------------------------------------------------------------
# zip_outputs
# ---------------------------------------------------------------------------
def test_zip_outputs_bundles_files(tmp_path: Path) -> None:
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    a.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    b.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    z = tmp_path / "out.zip"
    zip_outputs([a, b], z)
    with zipfile.ZipFile(z) as zf:
        names = sorted(zf.namelist())
    assert names == ["a.pdf", "b.pdf"]
