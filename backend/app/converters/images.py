"""Image conversions: PNG->JPEG (Pillow), SVG->JPEG (resvg -> Pillow)."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from ..core.config import TIMEOUT_IMAGE
from ..core.errors import ConversionError, InvalidFileError
from ..utils.subprocess import run, which


# ---------------------------------------------------------------------------
# PNG -> JPEG
# ---------------------------------------------------------------------------
def png_to_jpeg(input_path: Path, output_path: Path, options: dict[str, Any]) -> None:
    from PIL import Image

    quality = _clamp_quality(options.get("quality", 90))
    background = _parse_color(options.get("background", "white"))

    try:
        img = Image.open(input_path)
        img.load()
    except Exception as e:
        raise InvalidFileError(f"Could not open PNG: {e}") from e

    try:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, background)
            bg.paste(rgba, mask=rgba.split()[-1])
            out = bg
        else:
            out = img.convert("RGB")
        out.save(output_path, "JPEG", quality=quality, optimize=True)
    finally:
        img.close()


# ---------------------------------------------------------------------------
# SVG -> JPEG (via resvg)
# ---------------------------------------------------------------------------
def svg_to_jpeg(input_path: Path, output_path: Path, options: dict[str, Any]) -> None:
    resvg = which("resvg")
    if not resvg:
        from ..core.errors import DependencyMissingError

        raise DependencyMissingError("resvg is required for SVG -> JPEG conversion")

    from PIL import Image

    quality = _clamp_quality(options.get("quality", 90))
    background = _parse_color(options.get("background", "white"))
    width = options.get("width")
    height = options.get("height")
    scale = options.get("scale")

    argv: list[str] = [resvg]
    if width:
        argv += ["-w", str(int(width))]
    if height:
        argv += ["-h", str(int(height))]
    if scale:
        argv += ["--zoom", str(float(scale))]

    with tempfile.TemporaryDirectory(prefix="svg2jpg-") as td:
        tmp_png = Path(td) / "render.png"
        argv += [str(input_path), str(tmp_png)]
        run(argv, timeout=TIMEOUT_IMAGE, dependency_label="resvg")
        if not tmp_png.exists() or tmp_png.stat().st_size == 0:
            raise ConversionError("resvg produced no output")

        img = Image.open(tmp_png)
        try:
            img.load()
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, background)
                bg.paste(img, mask=img.split()[-1])
                out = bg
            else:
                out = img.convert("RGB")
            out.save(output_path, "JPEG", quality=quality, optimize=True)
        finally:
            img.close()


# ---------------------------------------------------------------------------
# Option parsing helpers
# ---------------------------------------------------------------------------
_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_NAMED = {"white": (255, 255, 255), "black": (0, 0, 0)}


def _parse_color(value: Any) -> tuple[int, int, int]:
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return tuple(int(v) & 0xFF for v in value)  # type: ignore[return-value]
    if not isinstance(value, str):
        return _NAMED["white"]
    v = value.strip().lower()
    if v in _NAMED:
        return _NAMED[v]
    m = _HEX.match(v)
    if not m:
        return _NAMED["white"]
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _clamp_quality(value: Any) -> int:
    try:
        q = int(value)
    except (TypeError, ValueError):
        q = 90
    return max(60, min(100, q))
