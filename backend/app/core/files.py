"""Upload streaming, output naming, size accounting."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile

from .config import MAX_FILE_SIZE_BYTES
from .errors import FileTooLargeError, InvalidFileError


_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def safe_stem(filename: str) -> str:
    """Strip a filename down to a safe base (no path, no unsafe chars)."""
    name = Path(filename or "").name
    stem = Path(name).stem or "file"
    stem = _UNSAFE_NAME_CHARS.sub("_", stem).strip("._-") or "file"
    return stem[:120]  # keep filenames sane


def output_filename(input_filename: str, output_ext: str) -> str:
    """`report.pdf`, `docx` -> `report.docx`."""
    return f"{safe_stem(input_filename)}.{output_ext.lstrip('.')}"


async def save_upload(
    upload: UploadFile,
    dest: Path,
    *,
    max_bytes: int = MAX_FILE_SIZE_BYTES,
) -> int:
    """Stream an UploadFile to disk, enforcing a size cap. Returns bytes written."""
    written = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(1024 * 64)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise FileTooLargeError(
                    f"File exceeds maximum size of {max_bytes // (1024*1024)} MB"
                )
            out.write(chunk)
    if written == 0:
        dest.unlink(missing_ok=True)
        raise InvalidFileError("Uploaded file is empty")
    return written


def peek(path: Path, n: int = 4096) -> bytes:
    """Read the first n bytes of a file for magic-byte detection."""
    with path.open("rb") as f:
        return f.read(n)


def copy_stream(src: BinaryIO, dst: BinaryIO, chunk: int = 64 * 1024) -> int:
    """shutil.copyfileobj wrapper that returns total bytes."""
    total = 0
    while True:
        buf = src.read(chunk)
        if not buf:
            break
        dst.write(buf)
        total += len(buf)
    return total


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def remove_dir(p: Path) -> None:
    shutil.rmtree(p, ignore_errors=True)
