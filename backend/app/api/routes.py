"""HTTP routes."""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ..converters import CONVERSIONS, get_converter, merge_pdfs, possible_targets
from ..converters.documents import find_soffice
from ..core.config import (
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    MAX_MERGE_FILES,
    MAX_MERGE_TOTAL_BYTES,
    MAX_MERGE_TOTAL_MB,
)
from ..core.errors import (
    ConversionError,
    ConverterError,
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFormatError,
)
from ..core.files import ensure_dir, output_filename, peek, remove_dir, safe_stem, save_upload
from ..core.validation import (
    SUPPORTED_OUTPUT_FORMATS,
    detect_format,
    normalize_format,
)
from ..utils.subprocess import which

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Health + system capabilities
# ---------------------------------------------------------------------------
@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/system")
def system() -> dict[str, Any]:
    engines = {
        "pymupdf": _has("pymupdf"),
        "pymupdf4llm": _has("pymupdf4llm"),
        "python_docx": _has("docx"),
        "reportlab": _has("reportlab"),
        "pillow": _has("PIL"),
        "pandoc": bool(which("pandoc")),
        "typst": bool(which("typst")),
        "libreoffice": bool(find_soffice()),
        "resvg": bool(which("resvg")),
    }
    # Which conversion pairs the frontend should treat as available.
    availability = {
        f"{s}->{t}": _pair_available(s, t, engines) for (s, t) in CONVERSIONS
    }
    availability["pdf[]->pdf"] = engines["pymupdf"]
    return {
        "engines": engines,
        "conversions": availability,
        "limits": {
            "max_file_mb": MAX_FILE_SIZE_MB,
            "max_merge_files": MAX_MERGE_FILES,
            "max_merge_total_mb": MAX_MERGE_TOTAL_MB,
        },
    }


def _has(module: str) -> bool:
    import importlib

    try:
        importlib.import_module(module)
        return True
    except Exception:
        return False


def _pair_available(source: str, target: str, engines: dict[str, bool]) -> bool:
    if (source, target) == ("md", "pdf"):
        return engines["pandoc"] and engines["typst"]
    if (source, target) == ("docx", "pdf"):
        return engines["libreoffice"]
    if (source, target) == ("svg", "jpg"):
        return engines["resvg"] and engines["pillow"]
    if source == "pdf":
        return engines["pymupdf"] and (engines["pymupdf4llm"] if target == "md" else True) and (engines["python_docx"] if target == "docx" else True)
    if (source, target) == ("txt", "pdf"):
        return engines["reportlab"]
    if (source, target) == ("png", "jpg"):
        return engines["pillow"]
    return False


# ---------------------------------------------------------------------------
# Single-file conversion
# ---------------------------------------------------------------------------
@router.post("/convert")
async def convert(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    output_format: str = Form(...),
    options: str | None = Form(None),
) -> FileResponse:
    target = normalize_format(output_format)
    if target not in SUPPORTED_OUTPUT_FORMATS:
        raise UnsupportedFormatError(f"Unsupported output format: {output_format}")

    opts = _parse_options(options)

    workdir = Path(tempfile.mkdtemp(prefix="converter-"))
    background.add_task(remove_dir, workdir)

    input_name = file.filename or "input"
    input_path = workdir / ("input_" + safe_stem(input_name))
    input_ext = Path(input_name).suffix.lower().lstrip(".")
    if input_ext:
        input_path = input_path.with_suffix("." + input_ext)

    await save_upload(file, input_path)
    source = detect_format(input_name, peek(input_path))

    converter = get_converter(source, target)
    out_name = output_filename(input_name, target)
    output_path = workdir / out_name
    converter(input_path, output_path, opts)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ConversionError("Converter produced no output")

    media_type = _media_type_for(target)
    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=out_name,
    )


# ---------------------------------------------------------------------------
# PDF merge
# ---------------------------------------------------------------------------
@router.post("/merge/pdf")
async def merge_pdf(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> FileResponse:
    if not files:
        raise InvalidFileError("No files provided")
    if len(files) < 2:
        raise InvalidFileError("Need at least 2 PDFs to merge")
    if len(files) > MAX_MERGE_FILES:
        raise InvalidFileError(f"Too many files (max {MAX_MERGE_FILES})")

    workdir = Path(tempfile.mkdtemp(prefix="merge-"))
    background.add_task(remove_dir, workdir)
    ensure_dir(workdir)

    inputs: list[Path] = []
    total = 0
    for i, up in enumerate(files):
        name = up.filename or f"file{i}.pdf"
        dest = workdir / f"in_{i:03d}_{safe_stem(name)}.pdf"
        size = await save_upload(up, dest)
        total += size
        if total > MAX_MERGE_TOTAL_BYTES:
            raise FileTooLargeError(f"Combined upload exceeds {MAX_MERGE_TOTAL_MB} MB")
        head = peek(dest)
        fmt = detect_format(name, head)
        if fmt != "pdf":
            raise InvalidFileError(f"{name} is not a PDF")
        inputs.append(dest)

    output_path = workdir / "merged.pdf"
    merge_pdfs(inputs, output_path)
    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename="merged.pdf",
    )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
def register_error_handlers(app) -> None:
    from fastapi import FastAPI  # noqa: F401 (typing hint only)

    @app.exception_handler(ConverterError)
    async def _converter_error(_: Request, exc: ConverterError):
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_options(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InvalidFileError(f"Invalid options JSON: {e}") from e
    if not isinstance(data, dict):
        raise InvalidFileError("options must be a JSON object")
    return data


def _media_type_for(fmt: str) -> str:
    return {
        "pdf": "application/pdf",
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "jpg": "image/jpeg",
    }.get(fmt, "application/octet-stream")


