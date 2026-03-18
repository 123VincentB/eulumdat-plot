"""
export.py — Raster export of photometric SVG diagrams.

Converts SVG files produced by :func:`plot.plot_ldt` (or any compatible
SVG) to PNG or JPEG.

Dependencies
------------
``vl-convert-python``
    Pure-Python package embedding a compiled Rust/resvg SVG renderer.
    No native library (DLL/SO) required — the renderer is bundled in the
    wheel.  Cross-platform: Windows, Linux, macOS.
    Install with the optional extra::

        pip install "eulumdat-plot[export]"

``Pillow``
    Used for pixel-exact resizing and JPEG compression.
    Also installed via ``[export]``.
"""

from __future__ import annotations

import io
from pathlib import Path


def _check_deps() -> None:
    """Raise a clear ImportError if vl-convert-python or Pillow are missing."""
    missing = []
    for pkg, pip_name in [("vl_convert", "vl-convert-python"), ("PIL", "Pillow")]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pip_name)
    if missing:
        raise ImportError(
            f"Missing package(s) for raster export: {', '.join(missing)}\n"
            "Install with:  pip install 'eulumdat-plot[export]'"
        )


def _svg_to_pil(svg_path: Path, size_px: int, background: str):
    """
    Convert an SVG file to a square Pillow Image of exactly *size_px* pixels.

    Uses ``vl_convert`` (resvg, compiled Rust, no native DLL) for rendering,
    then ``Pillow`` for pixel-exact resizing and background compositing.

    Parameters
    ----------
    svg_path :   Path to the source SVG file.
    size_px :    Target output size in pixels (square).
    background : Background colour as a CSS hex string (e.g. ``"#FFFFFF"``).

    Returns
    -------
    PIL.Image.Image in RGB mode, size (size_px, size_px).
    """
    _check_deps()

    import vl_convert as vlc
    from PIL import Image

    svg_content = svg_path.read_text(encoding="utf-8")

    # Read the SVG canvas size from the file to compute the scale factor.
    # Layout always writes width="N" height="N" as integers.
    native_size = size_px   # fallback if parsing fails
    import re
    m = re.search(r'<svg[^>]+width="(\d+)"', svg_content)
    if m:
        native_size = int(m.group(1))

    scale = size_px / native_size
    png_bytes = vlc.svg_to_png(svg_content, scale=scale)

    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")

    # Resize to exactly size_px × size_px (float scale may be off by 1 px).
    if img.size != (size_px, size_px):
        img = img.resize((size_px, size_px), Image.LANCZOS)

    # Composite over solid background.
    bg = Image.new("RGBA", (size_px, size_px), background)
    bg.paste(img, mask=img)
    return bg.convert("RGB")


def svg_to_png(
    svg_path: str | Path,
    png_path: str | Path | None = None,
    *,
    size_px: int = 1181,
    background: str = "#FFFFFF",
) -> Path:
    """
    Convert an SVG file to PNG.

    Parameters
    ----------
    svg_path :   Path to the source SVG file.
    png_path :   Destination path.  Defaults to svg_path with .png extension.
    size_px :    Output width and height in pixels (square output).
    background : Background fill colour as a CSS hex string. Default: #FFFFFF.

    Returns
    -------
    Absolute path to the generated PNG file.
    """
    svg_path = Path(svg_path)
    png_path = Path(png_path) if png_path is not None else svg_path.with_suffix(".png")
    img = _svg_to_pil(svg_path, size_px, background)
    img.save(png_path, "PNG", optimize=True)
    return png_path.resolve()


def svg_to_jpg(
    svg_path: str | Path,
    jpg_path: str | Path | None = None,
    *,
    size_px: int = 1181,
    background: str = "#FFFFFF",
    quality: int = 95,
) -> Path:
    """
    Convert an SVG file to JPEG.

    Parameters
    ----------
    svg_path :   Path to the source SVG file.
    jpg_path :   Destination path.  Defaults to svg_path with .jpg extension.
    size_px :    Output width and height in pixels (square output).
    background : Background fill colour (CSS hex). Default: #FFFFFF.
    quality :    JPEG compression quality (1-100). Default: 95.

    Returns
    -------
    Absolute path to the generated JPEG file.
    """
    svg_path = Path(svg_path)
    jpg_path = Path(jpg_path) if jpg_path is not None else svg_path.with_suffix(".jpg")
    img = _svg_to_pil(svg_path, size_px, background)
    img.save(jpg_path, "JPEG", quality=quality, optimize=True)
    return jpg_path.resolve()
