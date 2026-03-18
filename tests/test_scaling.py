"""
tests/test_scaling.py — Scaling tests for Layout.for_size().

Verifies that:
1. All Layout dimensions scale strictly proportionally to size_px.
2. plot_ldt() produces valid SVG at every tested size.
3. Layout.for_size(1181) is equivalent to Layout().
4. Export (PNG) works at a different size than the source SVG.

Run from the project root:
    pytest tests/test_scaling.py -v
Or standalone:
    python tests/test_scaling.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_INPUT   = PROJECT_ROOT / "data" / "input"
DATA_OUTPUT  = PROJECT_ROOT / "data" / "output"
SRC          = PROJECT_ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

from eulumdat_plot import plot_ldt, Layout          # noqa: E402
from eulumdat_plot.export import svg_to_png         # noqa: E402

# ---------------------------------------------------------------------------
# Reference values at 1181 px
# ---------------------------------------------------------------------------
REF = {
    "font_size_header":    62.0,
    "margin_header":       40.0,
    "stroke_grid":          3.0,
    "font_size_grid":      42.0,
    "font_grid_offset_x":   8.0,
    "font_grid_offset_bottom": 40.0,
    "stroke_curve_solid":   9.0,
    "stroke_curve_dotted":  7.0,
    "dotted_dash":          8.0,
    "dotted_gap":           8.0,
    "stroke_frame":         3.0,
    "stroke_separator":     3.0,
}

SIZES = [300, 400, 600, 800, 1181, 1500, 2362]


# ---------------------------------------------------------------------------
# Pick one real LDT file for end-to-end tests
# ---------------------------------------------------------------------------
def _sample_ldt() -> Path:
    files = sorted(DATA_INPUT.glob("*.ldt"))
    if not files:
        raise FileNotFoundError(f"No .ldt files in {DATA_INPUT}")
    return files[19]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_for_size_proportionality() -> None:
    """Every Layout attribute scales linearly with size_px."""
    for size in SIZES:
        k = size / 1181.0
        layout = Layout.for_size(size)
        assert layout.width  == size
        assert layout.height == size
        for attr, ref_val in REF.items():
            actual   = getattr(layout, attr)
            expected = round(ref_val * k, 2)
            assert abs(actual - expected) < 0.01, (
                f"Layout.for_size({size}).{attr} = {actual}, "
                f"expected {expected} (k={k:.4f})"
            )
        assert layout.header_height > 0, (
            f"header_height not resolved at {size}px"
        )


def test_for_size_1181_equals_default() -> None:
    """Layout.for_size(1181) must be equivalent to Layout()."""
    default = Layout()
    scaled  = Layout.for_size(1181)
    for attr in REF:
        assert abs(getattr(default, attr) - getattr(scaled, attr)) < 0.01, (
            f"Mismatch on {attr}: default={getattr(default, attr)}, "
            f"scaled={getattr(scaled, attr)}"
        )
    assert abs(default.header_height - scaled.header_height) < 0.01


def test_svg_produced_at_each_size() -> None:
    """plot_ldt() produces a non-empty SVG at every tested size."""
    ldt = _sample_ldt()
    for size in SIZES:
        svg = plot_ldt(
            ldt,
            DATA_OUTPUT / f"scaling_{size}px.svg",
            code="TEST",
            layout=Layout.for_size(size),
        )
        assert svg.exists(), f"SVG not created at {size}px"
        assert svg.stat().st_size > 0, f"SVG empty at {size}px"


def test_svg_width_in_file() -> None:
    """The SVG file must declare the correct canvas width."""
    ldt = _sample_ldt()
    for size in [400, 800, 1181]:
        svg = plot_ldt(
            ldt,
            DATA_OUTPUT / f"scaling_width_{size}px.svg",
            layout=Layout.for_size(size),
        )
        content = svg.read_text(encoding="utf-8")
        # svgwrite writes: <svg ... width="N" height="N" ...>
        assert f'width="{size}"' in content, (
            f"Expected width={size} in SVG, not found"
        )


def test_png_export_independent_size() -> None:
    """
    SVG produced at one size can be exported to PNG at a different size.
    Verifies that cairosvg rescaling is independent of the SVG canvas size.
    """
    ldt  = _sample_ldt()
    svg  = plot_ldt(ldt, DATA_OUTPUT / "scaling_export_src.svg",
                    layout=Layout.for_size(1181))

    for export_size in [300, 600, 1181]:
        png = svg_to_png(svg,
                         DATA_OUTPUT / f"scaling_export_{export_size}px.png",
                         size_px=export_size)
        assert png.exists(), f"PNG not created at {export_size}px"
        assert png.stat().st_size > 0, f"PNG empty at {export_size}px"

        # Check actual image dimensions via Pillow if available
        try:
            from PIL import Image
            with Image.open(png) as img:
                w, h = img.size
                assert w == export_size and h == export_size, (
                    f"PNG size mismatch: got {w}×{h}, expected {export_size}×{export_size}"
                )
                print(f"  PNG {export_size}px: {w}×{h} ✓  ({png.stat().st_size:,} bytes)")
        except ImportError:
            pass   # Pillow not installed, skip pixel check


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def run_all() -> None:
    tests = [
        test_for_size_proportionality,
        test_for_size_1181_equals_default,
        test_svg_produced_at_each_size,
        test_svg_width_in_file,
        test_png_export_independent_size,
    ]

    print(f"\n{'─' * 60}")
    print("  eulumdat-plot scaling test")
    print(f"{'─' * 60}\n")

    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓  {t.__name__}")
            passed += 1
        except Exception as exc:
            print(f"  ✗  {t.__name__}")
            print(f"       {type(exc).__name__}: {exc}")
            failed += 1

    print(f"\n{'─' * 60}")
    print(f"  Results: {passed} passed, {failed} failed / {len(tests)} total")
    print(f"{'─' * 60}\n")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
