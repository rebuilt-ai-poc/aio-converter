"""Safe subprocess wrapper.

- Argument arrays only (never shell=True).
- Enforces a timeout and kills the child on expiry.
- Missing binary -> DependencyMissingError.
- Non-zero exit -> ConversionError with captured stderr snippet.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from ..core.errors import ConversionError, ConversionTimeoutError, DependencyMissingError

log = logging.getLogger(__name__)


def which(name: str, candidates: Sequence[str] = ()) -> str | None:
    """Locate a binary. `shutil.which` first, then the extra candidate paths."""
    hit = shutil.which(name)
    if hit:
        return hit
    for c in candidates:
        p = Path(c)
        if p.is_file():
            return str(p)
    return None


def run(
    argv: Sequence[str],
    *,
    timeout: int,
    cwd: Path | None = None,
    dependency_label: str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run `argv`, capturing output. Raises the mapped domain errors on failure."""
    if not argv:
        raise ConversionError("Empty command")
    label = dependency_label or Path(argv[0]).name
    try:
        proc = subprocess.run(
            list(argv),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as e:
        raise DependencyMissingError(f"{label} is required but was not found on this system") from e
    except subprocess.TimeoutExpired as e:
        raise ConversionTimeoutError(f"{label} timed out after {timeout}s") from e

    if proc.returncode != 0:
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        stdout = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
        snippet = (stderr or stdout or "").splitlines()
        tail = " | ".join(snippet[-3:])[:400]
        log.warning("%s failed rc=%s: %s", label, proc.returncode, tail)
        raise ConversionError(f"{label} failed (exit {proc.returncode}){': ' + tail if tail else ''}")

    return proc
