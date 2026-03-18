"""
renderer.py — Photometric polar diagram renderer (Lumtopic style).

Responsibilities
----------------
- Define :class:`Layout`: all visual parameters in one place.
- Provide :func:`make_svg`: generate a photometric polar SVG from
  pre-computed curves expressed in the *natural* coordinate system.

This module is intentionally **decoupled from EULUMDAT parsing**.
It receives lists of ``(x, y)`` points and writes an SVG file.
No knowledge of LDT file structure, C-planes, or symmetry is needed here.

Coordinate systems
------------------
**Natural system (NAT)**
    Origin at the luminaire position, *y* pointing upward.
    Angle θ = 0° points upward; angles increase clockwise.
    CIE photometric convention: γ = 0° → nadir.

**SVG system**
    Origin at top-left, *y* pointing downward.
    The conversion ``nat_to_svg`` applies a vertical flip relative to the
    luminaire origin, which is located inside the plot area.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import svgwrite


# ---------------------------------------------------------------------------
# Public type alias
# ---------------------------------------------------------------------------

NatCurve = List[Tuple[float, float]]
"""A polar curve as a list of ``(x_nat, y_nat)`` points."""


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

@dataclass
class Layout:
    """
    All visual parameters for the photometric diagram.

    All dimensions are in SVG user-units (pixels at 96 dpi by default).

    Attributes
    ----------
    width, height :
        Canvas size in pixels.  Should be square for a circular polar chart.
    header_height :
        Height of the top banner in pixels.
        The default (``-1.0``) is resolved at construction time to
        ``1.8 × font_size_header``.
    font_size_header :
        Font size for the banner text ("LED", distribution code, "cd / klm").
    margin_header :
        Horizontal margin for the left- and right-aligned banner labels.
    header_text_baseline_offset :
        Fine vertical centering of banner text.
        ``baseline_y = header_height/2 + offset × font_size_header``.
    stroke_grid :
        Stroke width for concentric circles and radial lines.
    font_size_grid :
        Font size for the radial scale labels.
    font_grid_offset_x :
        Horizontal offset (pixels, rightward) applied to scale labels.
    font_grid_offset_top :
        Vertical offset for labels when the dominant lobe is in the upper half.
    font_grid_offset_bottom :
        Vertical offset for labels when the dominant lobe is in the lower half.
    stroke_curve_solid :
        Stroke width for solid curves (C0 / C180 pair).
    stroke_curve_dotted :
        Stroke width for dotted curves (C90 / C270 pair).
    dotted_dash :
        Dash segment length for dotted curves (pixels).
    dotted_gap :
        Gap length between dashes (pixels).
    curve_margin_rel :
        Relative padding added around the curve bounding box before fitting
        the diagram to the plot area (fraction, e.g. ``0.05`` = 5 %).
    stroke_frame :
        Stroke width of the outer border rectangle.
    stroke_separator :
        Stroke width of the horizontal line between banner and plot area.
    """

    # Canvas
    width: int = 1181
    height: int = 1181

    # Banner
    header_height: float = -1.0
    """Banner height in pixels.  The default ``-1.0`` is a sentinel value
    resolved in ``__post_init__`` to ``1.8 × font_size_header``."""
    font_size_header: float = 62.0
    margin_header: float = 40.0
    header_text_baseline_offset: float = 0.35

    # Grid
    stroke_grid: float = 3.0
    font_size_grid: float = 42.0
    font_grid_offset_x: float = 8.0
    font_grid_offset_top: float = -6.0
    font_grid_offset_bottom: float = 40.0

    # Curves
    stroke_curve_solid: float = 9.0
    stroke_curve_dotted: float = 7.0
    dotted_dash: float = 8.0
    dotted_gap: float = 8.0

    # Fitting
    curve_margin_rel: float = 0.05

    # Frame
    stroke_frame: float = 3.0
    stroke_separator: float = 3.0

    def __post_init__(self) -> None:
        if self.header_height < 0.0:
            self.header_height = 1.8 * self.font_size_header

    @classmethod
    def for_size(cls, size_px: int) -> "Layout":
        """
        Create a Layout scaled proportionally to *size_px*.

        All dimensions (stroke widths, font sizes, margins…) are scaled
        from the reference size of 1181 px.  The result is visually
        identical to the default layout, just smaller or larger.

        Parameters
        ----------
        size_px :
            Target canvas width and height in pixels.

        Examples
        --------
        >>> layout = Layout.for_size(600)   # ~half-size, all strokes halved
        >>> layout = Layout.for_size(1181)  # identical to Layout()
        """
        k = size_px / 1181.0
        return cls(
            width=size_px,
            height=size_px,
            font_size_header=round(62.0 * k, 2),
            margin_header=round(40.0 * k, 2),
            stroke_grid=round(3.0 * k, 2),
            font_size_grid=round(42.0 * k, 2),
            font_grid_offset_x=round(8.0 * k, 2),
            font_grid_offset_top=round(-6.0 * k, 2),
            font_grid_offset_bottom=round(40.0 * k, 2),
            stroke_curve_solid=round(9.0 * k, 2),
            stroke_curve_dotted=round(7.0 * k, 2),
            dotted_dash=round(8.0 * k, 2),
            dotted_gap=round(8.0 * k, 2),
            stroke_frame=round(3.0 * k, 2),
            stroke_separator=round(3.0 * k, 2),
            # header_height left at sentinel -1.0 → resolved by __post_init__
        )


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def polar_to_nat(r: float, theta_deg: float) -> Tuple[float, float]:
    """
    Convert polar coordinates to the NAT Cartesian system.

    Parameters
    ----------
    r :
        Radial value (cd/klm or any consistent unit).
    theta_deg :
        Angle in degrees.  θ = 0° → +y (upward), clockwise positive.

    Returns
    -------
    ``(x_nat, y_nat)``
    """
    t = math.radians(theta_deg)
    return r * math.sin(t), r * math.cos(t)


def _nice_levels(r_max: float) -> List[int]:
    """
    Compute "round" radial scale levels (3–6 circles) in the Lumtopic style.

    The algorithm picks a step size from a set of preferred bases so that
    the number of concentric circles falls in [3, 6].  All returned values
    are integers.

    Parameters
    ----------
    r_max :
        Maximum radial value of the data (cd/klm).

    Returns
    -------
    Sorted list of integer scale levels, e.g. ``[100, 200, 300, 400]``.

    Examples
    --------
    >>> _nice_levels(500)
    [100, 200, 300, 400, 500]
    >>> _nice_levels(320)
    [80, 160, 240, 320]
    """
    if r_max <= 0:
        return []

    bases = [1, 2, 2.5, 4, 5, 8]
    candidates: List[float] = []
    exp = 0
    # Build candidates until they comfortably exceed r_max.
    while True:
        for b in bases:
            candidates.append(b * (10 ** exp))
        if candidates[-1] >= max(r_max * 2.0, 10.0):
            break
        exp += 1

    best: Optional[Tuple[float, int, float]] = None

    for step in candidates:
        n = math.ceil(r_max / step)
        if 3 <= n <= 6:
            top = n * step
            score = (top - r_max, step)   # prefer tight fit, then fine step
            if best is None or score < (best[2] - r_max, best[0]):
                best = (step, n, top)

    if best is None:
        # Fallback: fewest circles above r_max.
        step = min(candidates, key=lambda s: (math.ceil(r_max / s), s))
        n = math.ceil(r_max / step)
    else:
        step, n, _ = best

    step_int = int(round(step))
    return [step_int * k for k in range(1, n + 1)]


# ---------------------------------------------------------------------------
# SVG renderer
# ---------------------------------------------------------------------------

def make_svg(
    curves_solid: List[NatCurve],
    curves_dotted: List[NatCurve],
    r_data_max: float,
    *,
    outfile: str | Path = "photometric.svg",
    code: str = "",
    layout: Optional[Layout] = None,
    debug: bool = False,
    colors_solid: Optional[List[str]] = None,
    colors_dotted: Optional[List[str]] = None,
    strokes_solid: Optional[List[float]] = None,
    strokes_dotted: Optional[List[float]] = None,
) -> Path:
    """
    Generate a Lumtopic-style photometric polar diagram as an SVG file.

    Parameters
    ----------
    curves_solid :
        Solid curves (typically C0 / C180), each as a list of
        ``(x_nat, y_nat)`` points.
    curves_dotted :
        Dotted curves (typically C90 / C270), same format.
    r_data_max :
        Maximum intensity across all curves (cd/klm).
        Drives the radial scale computation.
    outfile :
        Destination SVG path.  Default: ``"photometric.svg"``.
    code :
        Distribution code shown in the banner centre (e.g. ``"D53"``).
        Pass an empty string to leave it blank.
    layout :
        Visual parameters.  If ``None``, :class:`Layout` defaults are used.
    debug :
        If ``True``, draw the plot area in blue and the curve bounding box
        in green as diagnostic overlays.
    colors_solid / colors_dotted :
        Per-curve SVG stroke colours.  Defaults to black for all curves.
    strokes_solid / strokes_dotted :
        Per-curve stroke widths.  Defaults to ``layout.stroke_curve_solid``
        and ``layout.stroke_curve_dotted`` respectively.

    Returns
    -------
    :class:`pathlib.Path`
        Absolute path to the generated SVG file.
    """
    outfile = Path(outfile)
    if layout is None:
        layout = Layout()

    # ------------------------------------------------------------------
    # 1. Radial scale
    # ------------------------------------------------------------------
    levels = _nice_levels(r_data_max)

    # ------------------------------------------------------------------
    # 2. Bounding box in NAT coordinates
    # ------------------------------------------------------------------
    all_pts: List[Tuple[float, float]] = [
        pt for curve in curves_solid + curves_dotted for pt in curve
    ]
    if not all_pts:
        all_pts = [(0.0, 0.0)]

    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    box_w = max_x - min_x or 1.0
    box_h = max_y - min_y or 1.0

    # ------------------------------------------------------------------
    # 3. Dominant hemisphere → label placement side
    # ------------------------------------------------------------------
    # We place the radial scale labels along the axis toward which the
    # luminous intensity is highest (upper or lower hemisphere).
    max_r = 0.0
    dominant_up = True
    for x, y in all_pts:
        r = math.hypot(x, y)
        if r > max_r:
            max_r = r
            dominant_up = (y >= 0.0)   # NAT y ≥ 0 → upper hemisphere

    label_angle = 0.0 if dominant_up else 180.0

    # ------------------------------------------------------------------
    # 4. Padding + aspect-ratio correction
    # ------------------------------------------------------------------
    pad_x = box_w * layout.curve_margin_rel
    pad_y = box_h * layout.curve_margin_rel
    min_x -= pad_x;  max_x += pad_x
    min_y -= pad_y;  max_y += pad_y
    box_w = max_x - min_x
    box_h = max_y - min_y

    W, H = layout.width, layout.height
    hdr = layout.header_height   # banner height (already resolved in __post_init__)

    # Plot area: full width, everything below the banner.
    plot_w = float(W)
    plot_h = float(H) - hdr

    # Force the NAT bounding box to the same aspect ratio as the plot area
    # so that the scale mapping is uniform in x and y.
    aspect_plot = plot_w / plot_h
    aspect_box  = box_w / box_h
    if aspect_box > aspect_plot:
        delta = box_w / aspect_plot - box_h
        min_y -= delta / 2.0;  max_y += delta / 2.0;  box_h = max_y - min_y
    else:
        delta = box_h * aspect_plot - box_w
        min_x -= delta / 2.0;  max_x += delta / 2.0;  box_w = max_x - min_x

    scale = plot_w / box_w   # px per NAT unit (same in x and y)

    # ------------------------------------------------------------------
    # 5. Coordinate transform: NAT → SVG pixels
    # ------------------------------------------------------------------
    def nat_to_svg(x: float, y: float) -> Tuple[float, float]:
        """
        Convert a point from the NAT system to SVG pixel coordinates.

        The y-axis is flipped (NAT: up = positive; SVG: up = negative).
        The plot area starts at ``y = hdr`` in SVG coordinates.
        """
        xb = (x - min_x) * scale
        yb = (y - min_y) * scale
        return xb, hdr + (plot_h - yb)

    # Luminaire origin in SVG coordinates
    cx, cy = nat_to_svg(0.0, 0.0)

    # ------------------------------------------------------------------
    # 6. Assemble SVG
    # ------------------------------------------------------------------
    dwg = svgwrite.Drawing(str(outfile), size=(W, H))

    # --- Clip path (plot area only) ---
    clip_id = "plot_clip"
    cp = dwg.clipPath(id=clip_id)
    cp.add(dwg.rect(insert=(0, hdr), size=(plot_w, plot_h)))
    dwg.defs.add(cp)
    clip_ref = f"url(#{clip_id})"

    # --- Grid: concentric circles + radial lines ---
    grid = dwg.g(id="grid", clip_path=clip_ref)

    for lvl in levels:
        r_px = float(lvl) * scale
        # Concentric circle
        grid.add(dwg.circle(
            center=(cx, cy), r=r_px,
            stroke="black", stroke_width=layout.stroke_grid, fill="none",
        ))
        # Scale label along the dominant hemisphere axis
        lx, ly = nat_to_svg(*polar_to_nat(float(lvl), label_angle))
        dy = (layout.font_grid_offset_top if dominant_up
              else layout.font_grid_offset_bottom)
        grid.add(dwg.text(
            str(lvl),
            insert=(lx + layout.font_grid_offset_x, ly + dy),
            text_anchor="start",
            font_size=layout.font_size_grid,
            font_family="Arial",
        ))

    # Radial lines: one full diameter every 30°
    # We draw a single line per diameter (−90° … +90° covers all 7 directions).
    r_far = r_data_max * 5.0   # guaranteed to reach the clip boundary
    for ang in range(-90, 91, 30):
        x1, y1 = nat_to_svg(*polar_to_nat(r_far, float(ang)))
        x2 = 2.0 * cx - x1     # symmetric through the luminaire origin
        y2 = 2.0 * cy - y1
        grid.add(dwg.line(
            start=(x1, y1), end=(x2, y2),
            stroke="black", stroke_width=layout.stroke_grid,
        ))

    dwg.add(grid)

    # --- Photometric curves ---
    n_sol = len(curves_solid)
    n_dot = len(curves_dotted)
    if colors_solid  is None: colors_solid  = ["black"] * n_sol
    if colors_dotted is None: colors_dotted = ["black"] * n_dot
    if strokes_solid  is None: strokes_solid  = [layout.stroke_curve_solid]  * n_sol
    if strokes_dotted is None: strokes_dotted = [layout.stroke_curve_dotted] * n_dot

    curves_grp = dwg.g(id="curves", clip_path=clip_ref)

    def _add_polyline(
        curve: NatCurve,
        *,
        dotted: bool,
        color: str,
        stroke_width: float,
    ) -> None:
        pts = [nat_to_svg(x, y) for x, y in curve]
        if len(pts) < 2:
            return
        kw: dict = dict(stroke=color, stroke_width=stroke_width, fill="none")
        if dotted:
            kw["stroke_dasharray"] = f"{layout.dotted_dash},{layout.dotted_gap}"
        curves_grp.add(dwg.polyline(pts, **kw))

    for curve, col, sw in zip(curves_solid,  colors_solid,  strokes_solid):
        _add_polyline(curve, dotted=False, color=col, stroke_width=sw)
    for curve, col, sw in zip(curves_dotted, colors_dotted, strokes_dotted):
        _add_polyline(curve, dotted=True,  color=col, stroke_width=sw)

    dwg.add(curves_grp)

    # --- Banner (drawn last to cover any grid / curve overflow) ---
    # White background
    dwg.add(dwg.rect(insert=(0, 0), size=(W, hdr),
                     fill="white", stroke="none"))
    # Separator line
    dwg.add(dwg.line(start=(0, hdr), end=(W, hdr),
                     stroke="black", stroke_width=layout.stroke_separator))
    # Text
    by = hdr / 2.0 + layout.header_text_baseline_offset * layout.font_size_header
    m  = layout.margin_header
    txt = dict(font_size=layout.font_size_header, font_family="Arial")
    dwg.add(dwg.text("LED",      insert=(m,     by), text_anchor="start",  **txt))
    dwg.add(dwg.text(code,       insert=(W / 2, by), text_anchor="middle", **txt))
    dwg.add(dwg.text("cd / klm", insert=(W - m, by), text_anchor="end",    **txt))

    # --- Outer frame ---
    sw = layout.stroke_frame
    dwg.add(dwg.rect(
        insert=(sw / 2, sw / 2), size=(W - sw, H - sw),
        stroke="black", stroke_width=sw, fill="none",
    ))

    # --- Debug overlays ---
    if debug:
        # Plot area in blue
        dwg.add(dwg.rect(insert=(0, hdr), size=(plot_w, plot_h),
                         stroke="blue", stroke_width=5, fill="none"))
        # NAT bounding box in green
        sx0, sy0 = nat_to_svg(min_x, min_y)
        sx1, sy1 = nat_to_svg(max_x, max_y)
        dwg.add(dwg.rect(
            insert=(min(sx0, sx1), min(sy0, sy1)),
            size=(abs(sx1 - sx0), abs(sy1 - sy0)),
            stroke="green", stroke_width=5, fill="none",
        ))

    dwg.save()
    return outfile.resolve()
