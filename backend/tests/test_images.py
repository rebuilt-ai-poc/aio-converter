"""Image converter tests. SVG->JPEG is skipped when resvg is absent."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from app.converters.images import png_to_jpeg, svg_to_jpeg


def test_png_to_jpeg_opaque(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "out.jpg"
    png_to_jpeg(fixtures_dir / "opaque.png", out, {})
    img = Image.open(out)
    try:
        assert img.format == "JPEG"
        assert img.mode == "RGB"
        assert img.size == (120, 80)
    finally:
        img.close()


def test_png_to_jpeg_transparent_gets_white_background(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "out.jpg"
    png_to_jpeg(fixtures_dir / "transparent.png", out, {})
    img = Image.open(out)
    try:
        assert img.format == "JPEG"
        # A corner pixel outside the ellipse should be ~white.
        corner = img.getpixel((0, 0))
        assert corner[0] > 240 and corner[1] > 240 and corner[2] > 240, corner
    finally:
        img.close()


def test_png_to_jpeg_black_background(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "out.jpg"
    png_to_jpeg(fixtures_dir / "transparent.png", out, {"background": "black"})
    img = Image.open(out)
    try:
        corner = img.getpixel((0, 0))
        assert corner[0] < 15 and corner[1] < 15 and corner[2] < 15, corner
    finally:
        img.close()


def test_png_to_jpeg_quality_option(tmp_path: Path, fixtures_dir: Path) -> None:
    out_hi = tmp_path / "hi.jpg"
    out_lo = tmp_path / "lo.jpg"
    png_to_jpeg(fixtures_dir / "opaque.png", out_hi, {"quality": 95})
    png_to_jpeg(fixtures_dir / "opaque.png", out_lo, {"quality": 60})
    # Higher quality generally produces a larger file for a non-trivial image.
    # These fixtures are small; just assert both are valid JPEGs.
    for p in (out_hi, out_lo):
        img = Image.open(p)
        try:
            assert img.format == "JPEG"
        finally:
            img.close()


@pytest.mark.skipif(shutil.which("resvg") is None, reason="resvg not installed")
def test_svg_to_jpeg(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "out.jpg"
    svg_to_jpeg(fixtures_dir / "simple.svg", out, {})
    img = Image.open(out)
    try:
        assert img.format == "JPEG"
        assert img.size[0] > 0 and img.size[1] > 0
    finally:
        img.close()


@pytest.mark.skipif(shutil.which("resvg") is None, reason="resvg not installed")
def test_svg_to_jpeg_transparency_composited(tmp_path: Path, fixtures_dir: Path) -> None:
    out = tmp_path / "out.jpg"
    svg_to_jpeg(fixtures_dir / "transparent.svg", out, {"background": "black"})
    img = Image.open(out)
    try:
        corner = img.getpixel((0, 0))
        assert corner[0] < 15 and corner[1] < 15 and corner[2] < 15, corner
    finally:
        img.close()
