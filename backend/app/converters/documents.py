"""Document-source converters.

- TXT -> PDF via ReportLab with a bundled Noto Sans font for full Unicode.
- Markdown -> PDF via Pandoc + Typst subprocess.
- DOCX -> PDF via LibreOffice headless, with an isolated per-request profile.
"""
from __future__ import annotations

import platform
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from ..core.config import (
    NOTO_SANS_BOLD,
    NOTO_SANS_REGULAR,
    TIMEOUT_DOCUMENT,
    TIMEOUT_LARGE_PDF,
)
from ..core.errors import ConversionError, DependencyMissingError
from ..utils.subprocess import run, which


# ---------------------------------------------------------------------------
# TXT -> PDF (ReportLab)
# ---------------------------------------------------------------------------
_PAGE_SIZES = {
    "a4": "A4",
    "letter": "LETTER",
}
_MARGIN_PRESETS = {  # mm
    "normal": 20.0,
    "narrow": 12.7,
}
_FONT_NAME_REGULAR = "NotoSans"
_FONT_NAME_BOLD = "NotoSans-Bold"
_fonts_registered = False


def _register_fonts() -> None:
    """Register the bundled Noto Sans TTFs once per process."""
    global _fonts_registered
    if _fonts_registered:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if NOTO_SANS_REGULAR.exists():
        pdfmetrics.registerFont(TTFont(_FONT_NAME_REGULAR, str(NOTO_SANS_REGULAR)))
    if NOTO_SANS_BOLD.exists():
        pdfmetrics.registerFont(TTFont(_FONT_NAME_BOLD, str(NOTO_SANS_BOLD)))
    _fonts_registered = True


def txt_to_pdf(input_path: Path, output_path: Path, options: dict[str, Any]) -> None:
    from reportlab.lib.pagesizes import A4, LETTER, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.pdfmetrics import stringWidth

    _register_fonts()

    page_size_name = str(options.get("page_size", "a4")).lower()
    orientation = str(options.get("orientation", "portrait")).lower()
    margin_preset = str(options.get("margins", "normal")).lower()
    font_size = _clamp(options.get("font_size", 11), 8, 24)

    page = {"a4": A4, "letter": LETTER}.get(page_size_name, A4)
    if orientation == "landscape":
        page = landscape(page)
    margin_mm = _MARGIN_PRESETS.get(margin_preset, 20.0)
    margin = margin_mm * mm

    font_name = _FONT_NAME_REGULAR if NOTO_SANS_REGULAR.exists() else "Helvetica"
    text = input_path.read_text(encoding="utf-8", errors="replace")

    page_w, page_h = page
    usable_w = page_w - 2 * margin
    line_height = font_size * 1.3

    c = canvas.Canvas(str(output_path), pagesize=page)
    c.setFont(font_name, font_size)
    y = page_h - margin

    for raw_line in text.splitlines() or [""]:
        # Word-wrap this logical line into physical lines that fit usable_w.
        wrapped = _wrap_line(raw_line, font_name, font_size, usable_w, stringWidth)
        for line in wrapped:
            if y < margin:
                c.showPage()
                c.setFont(font_name, font_size)
                y = page_h - margin
            c.drawString(margin, y - font_size, line)
            y -= line_height

    c.save()


def _wrap_line(line: str, font: str, size: float, max_w: float, measure) -> list[str]:
    if not line.strip():
        return [""]
    words = line.split(" ")
    out: list[str] = []
    cur = ""
    for word in words:
        candidate = word if not cur else cur + " " + word
        if measure(candidate, font, size) <= max_w:
            cur = candidate
            continue
        # word doesn't fit — flush current line, then handle the word itself.
        if cur:
            out.append(cur)
            cur = ""
        if measure(word, font, size) <= max_w:
            cur = word
        else:
            # Break the word into chunks that fit.
            chunk = ""
            for ch in word:
                if measure(chunk + ch, font, size) <= max_w:
                    chunk += ch
                else:
                    out.append(chunk)
                    chunk = ch
            cur = chunk
    if cur:
        out.append(cur)
    return out


def _clamp(value: Any, lo: int, hi: int) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        v = lo
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Markdown -> PDF (Pandoc + Typst)
# ---------------------------------------------------------------------------
def markdown_to_pdf(input_path: Path, output_path: Path, options: dict[str, Any]) -> None:
    pandoc = which("pandoc")
    if not pandoc:
        raise DependencyMissingError("Pandoc is required for Markdown -> PDF conversion")
    typst = which("typst")
    if not typst:
        raise DependencyMissingError("Typst is required for Markdown -> PDF conversion")

    page_size = str(options.get("page_size", "a4")).lower()
    if page_size not in _PAGE_SIZES:
        page_size = "a4"

    argv = [
        pandoc,
        str(input_path),
        "--pdf-engine=typst",
        "-V", f"papersize={page_size}",
        "-o", str(output_path),
    ]
    run(argv, timeout=TIMEOUT_DOCUMENT, dependency_label="pandoc")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ConversionError("Pandoc produced no output PDF")


# ---------------------------------------------------------------------------
# DOCX -> PDF (LibreOffice headless)
# ---------------------------------------------------------------------------
_SOFFICE_CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/opt/libreoffice/program/soffice",
]


def find_soffice() -> str | None:
    return which("soffice", _SOFFICE_CANDIDATES)


def docx_to_pdf(input_path: Path, output_path: Path, options: dict[str, Any]) -> None:
    soffice = find_soffice()
    if not soffice:
        raise DependencyMissingError("LibreOffice (soffice) is required for DOCX -> PDF conversion")

    with tempfile.TemporaryDirectory(prefix="lo-") as td:
        td_path = Path(td)
        outdir = td_path / "out"
        outdir.mkdir()
        profile = td_path / f"profile-{uuid.uuid4().hex}"
        profile.mkdir()

        # LibreOffice wants a file:// URL for -env:UserInstallation.
        profile_uri = profile.absolute().as_uri()

        argv = [
            soffice,
            f"-env:UserInstallation={profile_uri}",
            "--headless",
            "--norestore",
            "--nologo",
            "--nofirststartwizard",
            "--convert-to", "pdf",
            "--outdir", str(outdir),
            str(input_path),
        ]
        run(argv, timeout=TIMEOUT_LARGE_PDF, dependency_label="LibreOffice")

        # LibreOffice writes <basename>.pdf into outdir.
        produced = outdir / (input_path.stem + ".pdf")
        if not produced.exists():
            # Fallback: pick up any PDF written.
            pdfs = list(outdir.glob("*.pdf"))
            if not pdfs:
                raise ConversionError("LibreOffice did not produce a PDF")
            produced = pdfs[0]
        if produced.stat().st_size == 0:
            raise ConversionError("LibreOffice produced an empty PDF")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(produced), str(output_path))
