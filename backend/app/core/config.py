"""Central configuration. Values overridable via environment variables."""
from __future__ import annotations

import os
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Upload limits (MB)
MAX_FILE_SIZE_MB = _int_env("MAX_FILE_SIZE_MB", 100)
MAX_MERGE_FILES = _int_env("MAX_MERGE_FILES", 50)
MAX_MERGE_TOTAL_MB = _int_env("MAX_MERGE_TOTAL_MB", 500)

MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_MERGE_TOTAL_BYTES = MAX_MERGE_TOTAL_MB * 1024 * 1024

# Subprocess timeouts (seconds)
TIMEOUT_IMAGE = _int_env("TIMEOUT_IMAGE", 30)
TIMEOUT_DOCUMENT = _int_env("TIMEOUT_DOCUMENT", 120)
TIMEOUT_LARGE_PDF = _int_env("TIMEOUT_LARGE_PDF", 300)

# Bundled asset paths
APP_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = APP_DIR / "assets" / "fonts"
NOTO_SANS_REGULAR = FONTS_DIR / "NotoSans-Regular.ttf"
NOTO_SANS_BOLD = FONTS_DIR / "NotoSans-Bold.ttf"

# Where a built frontend (frontend/dist) is expected at runtime.
FRONTEND_DIST = APP_DIR.parent.parent / "frontend" / "dist"
