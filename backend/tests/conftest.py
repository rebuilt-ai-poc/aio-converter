"""pytest configuration: ensure the `app` package is importable and fixtures exist."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from tests.fixtures.generate import generate_all  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _fixtures() -> None:
    # Only regenerate missing files; a full run is fast anyway.
    generate_all()


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return BACKEND_ROOT / "tests" / "fixtures"
