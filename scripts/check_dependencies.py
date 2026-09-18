"""Report which converter engines are available on this system.

Run from the repo root:  python scripts/check_dependencies.py
"""
from __future__ import annotations

import importlib
import platform
import shutil
import sys
from pathlib import Path


PY_DEPS = [
    ("PyMuPDF", "pymupdf"),
    ("PyMuPDF4LLM", "pymupdf4llm"),
    ("python-docx", "docx"),
    ("ReportLab", "reportlab"),
    ("Pillow", "PIL"),
    ("FastAPI", "fastapi"),
]

NATIVE_DEPS = [
    ("Pandoc", "pandoc"),
    ("Typst", "typst"),
    ("LibreOffice", "soffice"),
    ("resvg", "resvg"),
]

SOFFICE_CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/opt/libreoffice/program/soffice",
]

CONVERSIONS = [
    ("PDF -> TXT", ["pymupdf"]),
    ("PDF -> Markdown", ["pymupdf", "pymupdf4llm"]),
    ("PDF -> DOCX", ["pymupdf", "docx"]),
    ("PDF merge", ["pymupdf"]),
    ("TXT -> PDF", ["reportlab"]),
    ("Markdown -> PDF", ["pandoc", "typst"]),
    ("DOCX -> PDF", ["soffice"]),
    ("PNG -> JPEG", ["PIL"]),
    ("SVG -> JPEG", ["resvg", "PIL"]),
    ("EPUB -> TXT", ["pandoc"]),
    ("EPUB -> Markdown", ["pandoc"]),
    ("EPUB -> PDF", ["pandoc", "typst"]),
]

INSTALL_HINTS = {
    "pandoc": {
        "windows": "winget install --id JohnMacFarlane.Pandoc",
        "darwin": "brew install pandoc",
        "linux": "sudo apt-get install pandoc  # or your distro's equivalent",
    },
    "typst": {
        "windows": "winget install --id Typst.Typst  (or download the Windows zip from github.com/typst/typst/releases)",
        "darwin": "brew install typst",
        "linux": "cargo install typst-cli  # or download the Linux tarball from github.com/typst/typst/releases",
    },
    "soffice": {
        "windows": "winget install --id TheDocumentFoundation.LibreOffice",
        "darwin": "brew install --cask libreoffice",
        "linux": "sudo apt-get install libreoffice",
    },
    "resvg": {
        "windows": "Download resvg-win64.zip from github.com/linebender/resvg/releases and place resvg.exe on PATH",
        "darwin": "Download resvg-macos-*.zip from github.com/linebender/resvg/releases and place `resvg` on PATH",
        "linux": "Download resvg-linux-x86_64.tar.gz from github.com/linebender/resvg/releases and place `resvg` on PATH",
    },
}


def _find_soffice() -> str | None:
    hit = shutil.which("soffice")
    if hit:
        return hit
    for c in SOFFICE_CANDIDATES:
        if Path(c).is_file():
            return c
    return None


def main() -> int:
    print("Universal Converter dependency check")
    print()

    available: dict[str, bool] = {}
    missing: list[str] = []

    print(f"  {'Python':<20} {sys.version.split()[0]}")

    for label, module in PY_DEPS:
        ok = _try_import(module)
        available[module] = ok
        print(f"  {_mark(ok)} {label:<18} ({module})")
        if not ok:
            missing.append(module)

    print()
    for label, cmd in NATIVE_DEPS:
        if cmd == "soffice":
            ok = _find_soffice() is not None
        else:
            ok = shutil.which(cmd) is not None
        available[cmd] = ok
        print(f"  {_mark(ok)} {label:<18} ({cmd})")
        if not ok:
            missing.append(cmd)

    print()
    total = len(CONVERSIONS)
    ready = 0
    for name, deps in CONVERSIONS:
        ok = all(available.get(d, False) for d in deps)
        if ok:
            ready += 1
        print(f"  {_mark(ok)} {name}")

    print()
    print(f"{ready} / {total} conversions available.")

    unavailable_conversions = [n for n, deps in CONVERSIONS if not all(available.get(d, False) for d in deps)]
    if unavailable_conversions:
        print()
        print("Missing dependencies:")
        os_key = _os_key()
        for m in sorted(set(missing) - {"fastapi"}):
            hint = INSTALL_HINTS.get(m, {}).get(os_key)
            if hint:
                print(f"  - {m}: {hint}")
            else:
                print(f"  - {m}")

    return 0 if not unavailable_conversions else 1


def _try_import(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except Exception:
        return False


def _mark(ok: bool) -> str:
    # Windows terminals still default to cp1252 in some setups. Try to switch
    # stdout to UTF-8; if not possible, fall back to ASCII markers.
    if not hasattr(_mark, "_configured"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            _mark._ascii = False  # type: ignore[attr-defined]
        except Exception:
            enc = (sys.stdout.encoding or "").lower()
            _mark._ascii = "utf" not in enc  # type: ignore[attr-defined]
        _mark._configured = True  # type: ignore[attr-defined]
    if getattr(_mark, "_ascii", False):
        return "[ok]" if ok else "[--]"
    return "✓" if ok else "✗"


def _os_key() -> str:
    s = platform.system().lower()
    if s.startswith("win"):
        return "windows"
    if s == "darwin":
        return "darwin"
    return "linux"


if __name__ == "__main__":
    raise SystemExit(main())
