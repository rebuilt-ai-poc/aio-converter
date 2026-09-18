"""File type detection and validation.

Extension + magic bytes; never trust browser-supplied MIME alone.
"""
from __future__ import annotations

from pathlib import Path

from .errors import InvalidFileError, UnsupportedFormatError

# Canonical short format codes we accept as inputs.
SUPPORTED_INPUT_FORMATS = {"pdf", "txt", "md", "docx", "png", "svg"}
SUPPORTED_OUTPUT_FORMATS = {"pdf", "txt", "md", "docx", "jpg"}

# Extension -> canonical format code.
_EXT_MAP = {
    "pdf": "pdf",
    "txt": "txt",
    "md": "md",
    "markdown": "md",
    "docx": "docx",
    "png": "png",
    "svg": "svg",
    "jpg": "jpg",
    "jpeg": "jpg",
}


def normalize_format(value: str) -> str:
    """Normalize a user-supplied format label to the canonical code."""
    if not value:
        raise UnsupportedFormatError("Missing format")
    v = value.strip().lower().lstrip(".")
    if v not in _EXT_MAP:
        raise UnsupportedFormatError(f"Unsupported format: {value}")
    return _EXT_MAP[v]


def detect_format(filename: str, head: bytes) -> str:
    """Detect a format from filename + a leading chunk of the file's bytes.

    Extension is the primary hint; magic bytes verify or override it when they
    conflict with a text-like format. Raises on mismatch or unknown format.
    """
    ext_fmt: str | None = None
    ext = Path(filename or "").suffix.lower().lstrip(".")
    if ext in _EXT_MAP:
        ext_fmt = _EXT_MAP[ext]

    magic_fmt = _magic_format(head)

    # Magic wins when it's decisive; text-ish formats have no magic.
    if magic_fmt is not None:
        if ext_fmt is not None and ext_fmt != magic_fmt and ext_fmt in {"pdf", "png", "svg", "docx", "jpg"}:
            raise InvalidFileError(
                f"File contents do not match its extension "
                f"(got {magic_fmt!r}, expected {ext_fmt!r})"
            )
        return magic_fmt

    # No decisive magic — fall back to extension for txt/md.
    if ext_fmt in {"txt", "md"}:
        # Sanity check: must be decodable as UTF-8 or Latin-1-ish text.
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            try:
                head.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                raise InvalidFileError("File is not valid UTF-8 text")
        return ext_fmt

    if ext_fmt is not None:
        # e.g. .pdf with garbage magic bytes.
        raise InvalidFileError(f"File does not appear to be a valid {ext_fmt}")

    raise UnsupportedFormatError(f"Cannot determine format of {filename!r}")


def _magic_format(head: bytes) -> str | None:
    if not head:
        return None
    if head.startswith(b"%PDF-"):
        return "pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    # DOCX (and any other OOXML) is a Zip file with a specific content-types
    # part — but sniffing the extension is enough here plus the Zip signature.
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06") or head.startswith(b"PK\x07\x08"):
        # We treat any zip with a .docx extension as docx; the actual open
        # by python-docx / LibreOffice will fail loudly if it isn't.
        return "docx"
    # SVG — XML declaration or <svg root. Look at first ~256 bytes.
    prefix = head[:512].lstrip().lower()
    if prefix.startswith(b"<?xml") and b"<svg" in prefix:
        return "svg"
    if prefix.startswith(b"<svg"):
        return "svg"
    return None
