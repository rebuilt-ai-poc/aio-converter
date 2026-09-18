"""PDF-source converters and PDF merge.

Heavy imports (`pymupdf`, `pymupdf4llm`, `docx`) live inside the functions
so importing this module stays cheap.
"""
from __future__ import annotations

import io
import statistics
from pathlib import Path
from typing import Any

import zipfile

from ..core.errors import ConversionError, InvalidFileError, InvalidOptionsError


# ---------------------------------------------------------------------------
# PDF -> TXT
# ---------------------------------------------------------------------------
def pdf_to_txt(input_path: Path, output_path: Path, options: dict[str, Any]) -> None:
    """Fastest PDF text extraction. Options: `preserve_page_breaks` (bool)."""
    import pymupdf

    preserve = bool(options.get("preserve_page_breaks", False))
    separator = "\f" if preserve else "\n\n"

    parts: list[str] = []
    try:
        doc = pymupdf.open(input_path)
    except Exception as e:
        raise InvalidFileError(f"Could not open PDF: {e}") from e

    try:
        for page in doc:
            parts.append(page.get_text("text", sort=True))
    finally:
        doc.close()

    text = separator.join(parts).strip()
    if not text:
        text = (
            "No extractable text was detected.\n\n"
            "This file may contain scanned pages. "
            "OCR support is not currently enabled."
        )

    output_path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# PDF -> Markdown
# ---------------------------------------------------------------------------
def pdf_to_markdown(input_path: Path, output_path: Path, options: dict[str, Any]) -> None:
    """PyMuPDF4LLM primary path; plain-text Markdown fallback on error."""
    md: str
    try:
        import pymupdf4llm  # heavy — imported lazily

        md = pymupdf4llm.to_markdown(
            str(input_path),
            write_images=False,
            embed_images=False,
        )
    except Exception:
        md = _fallback_markdown(input_path)

    if not md.strip():
        md = (
            "> No extractable text was detected.\n>\n"
            "> This file may contain scanned pages. "
            "OCR support is not currently enabled.\n"
        )
    output_path.write_text(md, encoding="utf-8")


def _fallback_markdown(input_path: Path) -> str:
    import pymupdf

    parts: list[str] = []
    doc = pymupdf.open(input_path)
    try:
        for page in doc:
            parts.append(page.get_text("text", sort=True))
    finally:
        doc.close()
    return "\n\n".join(p.strip() for p in parts if p.strip())


# ---------------------------------------------------------------------------
# PDF -> DOCX
# ---------------------------------------------------------------------------
def pdf_to_docx(input_path: Path, output_path: Path, options: dict[str, Any]) -> None:
    """Structure-preserving extraction: paragraphs, headings, bold/italic, tables, inline images."""
    import pymupdf
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, Inches

    doc_out = Document()

    try:
        pdf = pymupdf.open(input_path)
    except Exception as e:
        raise InvalidFileError(f"Could not open PDF: {e}") from e

    try:
        body_size = _median_body_size(pdf)

        for pi, page in enumerate(pdf):
            # Track which block indices have been emitted as tables so we can
            # skip the raw text blocks that overlap them.
            table_boxes: list[tuple[float, float, float, float]] = []
            try:
                tables = page.find_tables()
                for t in tables:
                    _emit_table(doc_out, t)
                    table_boxes.append(tuple(t.bbox))
            except Exception:
                # Table detection is best-effort; never fail the whole page.
                pass

            page_dict = page.get_text("dict", sort=True)
            for block in page_dict.get("blocks", []):
                btype = block.get("type", 0)
                bbox = block.get("bbox")
                if bbox and _bbox_overlaps_any(bbox, table_boxes):
                    continue

                if btype == 1:  # image block
                    _emit_image(doc_out, block)
                    continue

                lines = block.get("lines", [])
                if not lines:
                    continue
                _emit_text_block(doc_out, lines, body_size)

            if pi < pdf.page_count - 1:
                doc_out.add_page_break()
    finally:
        pdf.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc_out.save(str(output_path))


def _median_body_size(pdf) -> float:
    sizes: list[float] = []
    # Sample up to the first 4 pages so we don't do this on every page of a
    # very long doc, but we do enough to get a stable median.
    for page in pdf[: min(4, pdf.page_count)]:
        d = page.get_text("dict")
        for b in d.get("blocks", []):
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    sz = float(s.get("size", 0))
                    if sz > 0:
                        sizes.append(sz)
    if not sizes:
        return 11.0
    try:
        return statistics.median(sizes)
    except statistics.StatisticsError:
        return 11.0


def _emit_text_block(doc_out, lines: list[dict], body_size: float) -> None:
    from docx.shared import Pt

    # Group by line, then merge into a single paragraph unless we detect a
    # heading. Each span becomes a run so we can carry bold/italic/size.
    # Collect all spans in order for heading inference on the block as a whole.
    all_spans = [s for l in lines for s in l.get("spans", [])]
    if not all_spans:
        return

    max_size = max((float(s.get("size", 0)) for s in all_spans), default=body_size)
    bold_ratio = sum(1 for s in all_spans if _is_bold(s)) / max(1, len(all_spans))
    text = " ".join(s.get("text", "") for s in all_spans).strip()
    if not text:
        return

    heading_level = _infer_heading(max_size, body_size, bold_ratio, len(text))
    if heading_level is not None:
        p = doc_out.add_heading(text, level=heading_level)
        return

    p = doc_out.add_paragraph()
    for i, line in enumerate(lines):
        for span in line.get("spans", []):
            txt = span.get("text", "")
            if not txt:
                continue
            run = p.add_run(txt)
            sz = float(span.get("size", 0))
            if sz > 0:
                run.font.size = Pt(round(sz))
            if _is_bold(span):
                run.bold = True
            if _is_italic(span):
                run.italic = True
        if i < len(lines) - 1:
            # Preserve a soft space between wrapped lines within a paragraph.
            p.add_run(" ")


def _is_bold(span: dict) -> bool:
    flags = int(span.get("flags", 0))
    if flags & 16:  # PyMuPDF bold flag
        return True
    font = str(span.get("font", "")).lower()
    return "bold" in font or "black" in font or "heavy" in font


def _is_italic(span: dict) -> bool:
    flags = int(span.get("flags", 0))
    if flags & 2:  # italic flag
        return True
    font = str(span.get("font", "")).lower()
    return "italic" in font or "oblique" in font


def _infer_heading(max_size: float, body: float, bold_ratio: float, text_len: int) -> int | None:
    """Return 1/2/3 or None. Conservative; short bold-ish lines get promoted."""
    if body <= 0:
        return None
    ratio = max_size / body
    # Short lines are more heading-like; anything paragraph-length shouldn't
    # be flagged unless font is dramatically larger.
    short = text_len <= 120
    if ratio >= 1.6 and short:
        return 1
    if ratio >= 1.35 and short:
        return 2
    if ratio >= 1.15 and short and bold_ratio >= 0.5:
        return 3
    return None


def _emit_image(doc_out, block: dict) -> None:
    from docx.shared import Inches

    data = block.get("image")
    if not data:
        return
    try:
        stream = io.BytesIO(data)
        # Constrain to page width-ish so massive raster embeds don't blow layout.
        doc_out.add_picture(stream, width=Inches(5.5))
    except Exception:
        # A malformed image shouldn't kill the whole conversion.
        return


def _emit_table(doc_out, table) -> None:
    try:
        rows = table.extract()
    except Exception:
        return
    if not rows or not any(any(cell for cell in row) for row in rows):
        return
    ncols = max(len(r) for r in rows)
    t = doc_out.add_table(rows=len(rows), cols=ncols)
    t.style = "Table Grid"
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            t.rows[ri].cells[ci].text = (cell or "").strip() if isinstance(cell, str) else str(cell or "")


def _bbox_overlaps_any(bbox, boxes: list[tuple[float, float, float, float]]) -> bool:
    x0, y0, x1, y1 = bbox
    for bx0, by0, bx1, by1 in boxes:
        if not (x1 < bx0 or bx1 < x0 or y1 < by0 or by1 < y0):
            # any intersection at all: treat as covered by the table.
            return True
    return False


# ---------------------------------------------------------------------------
# PDF merge
# ---------------------------------------------------------------------------
def merge_pdfs(inputs: list[Path], output_path: Path) -> None:
    """Concatenate PDFs in the given order."""
    import pymupdf

    if not inputs:
        raise ConversionError("No PDFs to merge")

    output = pymupdf.open()
    try:
        for src in inputs:
            try:
                doc = pymupdf.open(src)
            except Exception as e:
                raise InvalidFileError(f"Could not open PDF {src.name}: {e}") from e
            try:
                output.insert_pdf(doc)
            finally:
                doc.close()
        output.save(str(output_path), garbage=3, deflate=True)
    finally:
        output.close()


# ---------------------------------------------------------------------------
# PDF page operations: split / delete / extract / reorder
# ---------------------------------------------------------------------------
def _open_pdf(path: Path):
    import pymupdf

    try:
        doc = pymupdf.open(path)
    except Exception as e:
        raise InvalidFileError(f"Could not open PDF: {e}") from e
    # PyMuPDF opens many document types; reject anything that's not a PDF so
    # insert_pdf/delete_pages don't crash with a raw RuntimeError downstream.
    if not doc.is_pdf:
        doc.close()
        raise InvalidFileError("Input is not a PDF")
    return doc


def _validate_page_list(
    pages: list[int], page_count: int, *, allow_repeat: bool = False, label: str = "pages"
) -> None:
    if not isinstance(pages, list) or not pages:
        raise InvalidOptionsError(f"{label} must be a non-empty list")
    for p in pages:
        if not isinstance(p, int) or isinstance(p, bool):
            raise InvalidOptionsError(f"{label} must contain integers")
        if p < 1 or p > page_count:
            raise InvalidOptionsError(
                f"Page {p} is out of range (document has {page_count} pages)"
            )
    if not allow_repeat and len(set(pages)) != len(pages):
        raise InvalidOptionsError(f"{label} must not contain duplicates")


def _validate_permutation(order: list[int], page_count: int) -> None:
    if not isinstance(order, list):
        raise InvalidOptionsError("order must be a list")
    if len(order) != page_count:
        raise InvalidOptionsError(
            f"order must contain exactly {page_count} entries (got {len(order)})"
        )
    for p in order:
        if not isinstance(p, int) or isinstance(p, bool):
            raise InvalidOptionsError("order must contain integers")
    if set(order) != set(range(1, page_count + 1)):
        raise InvalidOptionsError(
            f"order must be a permutation of 1..{page_count} with no duplicates or missing pages"
        )


def _reject_delete_all(pages: list[int], page_count: int) -> None:
    if set(pages) == set(range(1, page_count + 1)):
        raise InvalidOptionsError(
            "Cannot delete every page — the output PDF would be empty"
        )


def _build_from_indices(input_path: Path, output_path: Path, indices_0based: list[int]) -> None:
    """Build a new PDF containing the pages in `indices_0based`, in the given order."""
    import pymupdf

    source = _open_pdf(input_path)
    try:
        output = pymupdf.open()
        try:
            for i in indices_0based:
                output.insert_pdf(source, from_page=i, to_page=i)
            output.save(str(output_path), garbage=3, deflate=True)
        finally:
            output.close()
    finally:
        source.close()


def split_pdf(
    input_path: Path, output_dir: Path, mode: dict[str, Any]
) -> list[Path]:
    """Split a PDF into multiple PDFs by `mode`.

    Modes:
      {"type": "every_page"}                       — one output per page
      {"type": "every_n", "n": int}                — chunks of N pages
      {"type": "ranges", "ranges": [[a, b], ...]}  — 1-indexed inclusive ranges

    Returns the written paths in order. Naming uses dynamic zero-padding
    (`part-01.pdf`, `part-001.pdf`) so alphabetical order is preserved.
    """
    import pymupdf

    if not isinstance(mode, dict):
        raise InvalidOptionsError("mode must be an object")
    kind = mode.get("type")
    if kind not in {"every_page", "every_n", "ranges"}:
        raise InvalidOptionsError(
            "mode.type must be one of 'every_page', 'every_n', 'ranges'"
        )

    source = _open_pdf(input_path)
    try:
        page_count = source.page_count
        if page_count == 0:
            raise InvalidOptionsError("Input PDF has no pages")

        chunks: list[tuple[int, int]] = []  # 0-indexed inclusive [from, to]

        if kind == "every_page":
            chunks = [(i, i) for i in range(page_count)]
        elif kind == "every_n":
            n = mode.get("n")
            if not isinstance(n, int) or isinstance(n, bool) or n < 1:
                raise InvalidOptionsError("mode.n must be a positive integer")
            for start in range(0, page_count, n):
                chunks.append((start, min(start + n - 1, page_count - 1)))
        else:  # ranges
            ranges = mode.get("ranges")
            if not isinstance(ranges, list) or not ranges:
                raise InvalidOptionsError("mode.ranges must be a non-empty list")
            for r in ranges:
                if (
                    not isinstance(r, list)
                    or len(r) != 2
                    or not all(isinstance(x, int) and not isinstance(x, bool) for x in r)
                ):
                    raise InvalidOptionsError(
                        "Each range must be a [start, end] pair of integers"
                    )
                start, end = r
                if start < 1 or end < start or end > page_count:
                    raise InvalidOptionsError(
                        f"Range [{start}, {end}] is invalid (document has {page_count} pages)"
                    )
                chunks.append((start - 1, end - 1))

        if not chunks:
            raise InvalidOptionsError("Split produced no output chunks")

        output_dir.mkdir(parents=True, exist_ok=True)
        width = max(2, len(str(len(chunks))))
        written: list[Path] = []
        for idx, (a, b) in enumerate(chunks, start=1):
            out_name = f"part-{idx:0{width}d}.pdf"
            out_path = output_dir / out_name
            output = pymupdf.open()
            try:
                output.insert_pdf(source, from_page=a, to_page=b)
                output.save(str(out_path), garbage=3, deflate=True)
            finally:
                output.close()
            written.append(out_path)
        return written
    finally:
        source.close()


def delete_pdf_pages(
    input_path: Path, output_path: Path, pages: list[int]
) -> None:
    """Delete the given 1-indexed pages. Rejects deleting every page."""
    source = _open_pdf(input_path)
    try:
        page_count = source.page_count
        _validate_page_list(pages, page_count, allow_repeat=False, label="pages")
        _reject_delete_all(pages, page_count)
        # PyMuPDF: delete_pages takes 0-indexed page numbers.
        source.delete_pages([p - 1 for p in pages])
        source.save(str(output_path), garbage=3, deflate=True)
    finally:
        source.close()


def extract_pdf_pages(
    input_path: Path, output_path: Path, pages: list[int]
) -> None:
    """Build a new PDF containing only the given 1-indexed pages, in order.

    Duplicates are disallowed in V1.
    """
    import pymupdf

    source = _open_pdf(input_path)
    try:
        page_count = source.page_count
        _validate_page_list(pages, page_count, allow_repeat=False, label="pages")
    finally:
        source.close()
    _build_from_indices(input_path, output_path, [p - 1 for p in pages])


def reorder_pdf_pages(
    input_path: Path, output_path: Path, order: list[int]
) -> None:
    """Reorder pages by an exact permutation of 1..page_count."""
    source = _open_pdf(input_path)
    try:
        page_count = source.page_count
        _validate_permutation(order, page_count)
    finally:
        source.close()
    _build_from_indices(input_path, output_path, [p - 1 for p in order])


def zip_outputs(paths: list[Path], zip_path: Path) -> None:
    """Zip the given files into `zip_path`, using their basenames as entry names."""
    if not paths:
        raise ConversionError("No files to zip")
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            zf.write(p, arcname=p.name)
