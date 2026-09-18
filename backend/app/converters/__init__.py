"""Conversion registry.

Each single-input conversion is registered under a (source, target) tuple.
PDF merge is a separate operation because it takes multiple inputs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .images import png_to_jpeg, svg_to_jpeg
from .documents import (
    docx_to_pdf,
    epub_to_markdown,
    epub_to_pdf,
    epub_to_txt,
    markdown_to_pdf,
    txt_to_pdf,
)
from .pdf import (  # noqa: F401
    pdf_to_txt,
    pdf_to_markdown,
    pdf_to_docx,
    merge_pdfs,
    split_pdf,
    delete_pdf_pages,
    extract_pdf_pages,
    reorder_pdf_pages,
    zip_outputs,
)


# A converter takes (input_path, output_path, options) and writes output_path.
Converter = Callable[[Path, Path, dict[str, Any]], None]

CONVERSIONS: dict[tuple[str, str], Converter] = {
    ("pdf", "txt"): pdf_to_txt,
    ("pdf", "md"): pdf_to_markdown,
    ("pdf", "docx"): pdf_to_docx,
    ("txt", "pdf"): txt_to_pdf,
    ("md", "pdf"): markdown_to_pdf,
    ("docx", "pdf"): docx_to_pdf,
    ("png", "jpg"): png_to_jpeg,
    ("svg", "jpg"): svg_to_jpeg,
    ("epub", "txt"): epub_to_txt,
    ("epub", "md"): epub_to_markdown,
    ("epub", "pdf"): epub_to_pdf,
}


def get_converter(source: str, target: str) -> Converter:
    from ..core.errors import UnsupportedFormatError

    try:
        return CONVERSIONS[(source, target)]
    except KeyError:
        raise UnsupportedFormatError(f"No converter for {source} -> {target}") from None


def possible_targets(source: str) -> list[str]:
    """List of target formats reachable from `source` via the registry."""
    return sorted({t for (s, t) in CONVERSIONS if s == source})
