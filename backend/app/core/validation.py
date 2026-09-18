"""File type detection and validation.

Extension + magic bytes; never trust browser-supplied MIME alone.
"""
from __future__ import annotations

from pathlib import Path

from .errors import InvalidFileError, UnsupportedFormatError

# Canonical short format codes we accept as inputs.
SUPPORTED_INPUT_FORMATS = {"pdf", "txt", "md", "docx", "png", "svg", "epub"}
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
    "epub": "epub",
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

    Magic bytes are authoritative when they decisively identify a format.
    Zip-based formats (DOCX, EPUB) may share the same PK header — an EPUB
    with its canonical STORED `mimetype` entry is recognized directly, other
    Zip files fall through to the extension.
    """
    ext_fmt: str | None = None
    ext = Path(filename or "").suffix.lower().lstrip(".")
    if ext in _EXT_MAP:
        ext_fmt = _EXT_MAP[ext]

    magic_fmt = _magic_format(head)

    if magic_fmt is not None:
        # Extension conflicts with a decisive magic → reject.
        if ext_fmt is not None and ext_fmt != magic_fmt:
            raise InvalidFileError(
                f"File contents do not match its extension "
                f"(got {magic_fmt!r}, expected {ext_fmt!r})"
            )
        return magic_fmt

    # No decisive magic — use the extension when we can sanity-check the bytes.
    if ext_fmt in {"txt", "md"}:
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            raise InvalidFileError("File is not valid UTF-8 text")
        return ext_fmt

    if ext_fmt in {"docx", "epub"}:
        # Both are Zip containers. If the file isn't a Zip, reject.
        if not _looks_like_zip(head):
            raise InvalidFileError(f"File does not appear to be a valid {ext_fmt}")
        return ext_fmt

    if ext_fmt is not None:
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

    # EPUB per OCF spec: first entry is STORED `mimetype` containing
    # "application/epub+zip". That places the marker at a fixed offset in
    # the local file header.
    if head.startswith(b"PK\x03\x04") and _has_epub_mimetype(head):
        return "epub"

    # Other Zip signatures are ambiguous (docx/xlsx/epub-nonstandard) — let
    # the extension decide.
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06") or head.startswith(b"PK\x07\x08"):
        return None

    prefix = head[:512].lstrip().lower()
    if prefix.startswith(b"<?xml") and b"<svg" in prefix:
        return "svg"
    if prefix.startswith(b"<svg"):
        return "svg"
    return None


def _has_epub_mimetype(head: bytes) -> bool:
    """True when the buffer's first ZIP entry names `mimetype` and stores it
    as `application/epub+zip` (i.e. the OCF-required layout)."""
    # bytes 30..38 hold the local-header filename when name length is 8; the
    # STORED content immediately follows.
    if len(head) < 58:
        return False
    return head[30:38] == b"mimetype" and head[38:58] == b"application/epub+zip"


def _looks_like_zip(head: bytes) -> bool:
    return head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))
