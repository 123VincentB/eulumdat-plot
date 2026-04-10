"""
plot.py — EULUMDAT (.ldt) → photometric polar diagram (SVG).

Public entry point of the ``eulumdat-plot`` package.

Pipeline
--------
1. Read the LDT file via :func:`pyldt.LdtReader.read` with
   ``expand_symmetry=True`` (default).  The returned :class:`pyldt.Ldt`
   object always exposes a **full intensity matrix** regardless of the
   file's ISYM value — symmetry handling is entirely delegated to pyldt.
2. Locate the four principal C-planes (C0, C90, C180, C270) by
   nearest-angle lookup in ``ldt.header.c_angles``.
3. Optionally resample each I(γ) curve onto a finer angular grid.
4. Convert each C-plane pair to NAT ``(x, y)`` curves.
5. Delegate SVG rendering to :func:`renderer.make_svg`.

pyldt interface
---------------
After ``LdtReader.read(path)``:

``ldt.header.c_angles``   — ``list[float]``, length ``mc``, degrees
``ldt.header.g_angles``   — ``list[float]``, length ``ng``, degrees
``ldt.intensities``       — ``list[list[float]]``, shape ``[mc][ng]``, cd/klm

All values are already in the full angular range; no ISYM logic is needed
in this module.

NAT angle convention (CIE photometric)
---------------------------------------
γ = 0°  → nadir (directly below the luminaire)
γ = 90° → horizontal plane
γ = 180°→ zenith (directly above)

Mapping to NAT polar angle θ (0° = up, clockwise):
    right half (C0  or C90 ): θ = 180° − γ
    left  half (C180 or C270): θ = 180° + γ
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from pyldt import LdtReader, Ldt

try:
    from scipy.interpolate import CubicSpline   # type: ignore[import]
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

from .renderer import Layout, NatCurve, make_svg, make_svg_str, polar_to_nat


# ---------------------------------------------------------------------------
# C-plane lookup
# ---------------------------------------------------------------------------

def _find_c_index(c_angles: List[float], target_deg: float) -> Optional[int]:
    """
    Return the index of the C-plane whose angle is closest to *target_deg*.

    The comparison is wrap-aware (0° and 360° are the same plane).

    Parameters
    ----------
    c_angles :
        List of C-plane angles from ``ldt.header.c_angles``.
    target_deg :
        Target angle in degrees (0, 90, 180, or 270).

    Returns
    -------
    Index into ``ldt.intensities``, or ``None`` if *c_angles* is empty.
    """
    if not c_angles:
        return None
    arr = np.asarray(c_angles, dtype=float)
    diff = np.abs((arr - target_deg) % 360.0)
    diff = np.minimum(diff, 360.0 - diff)
    return int(np.argmin(diff))


def _get_plane(ldt: Ldt, target_deg: float) -> Optional[np.ndarray]:
    """
    Return the intensity row (cd/klm, length ``ng``) for the C-plane
    nearest to *target_deg*.

    Returns ``None`` if the header has no C-angles or the index is out of
    range (malformed file).
    """
    idx = _find_c_index(ldt.header.c_angles, target_deg)
    if idx is None or idx >= len(ldt.intensities):
        return None
    return np.asarray(ldt.intensities[idx], dtype=float)


# ---------------------------------------------------------------------------
# Optional resampling
# ---------------------------------------------------------------------------

def _resample(
    g_deg: np.ndarray,
    *planes: Optional[np.ndarray],
    step_deg: float = 1.0,
    method: str = "linear",
) -> Tuple[np.ndarray, List[Optional[np.ndarray]]]:
    """
    Resample I(γ) curves onto a uniform angular grid.

    Parameters
    ----------
    g_deg :
        Original gamma angles (degrees), length N.
    planes :
        Intensity arrays of length N, or ``None`` (passed through unchanged).
    step_deg :
        Target angular step (degrees).  Default: 1°.
    method :
        ``"linear"`` — :func:`numpy.interp`, always available.
        ``"cubic"``  — natural cubic spline via SciPy :class:`CubicSpline`,
                       requires ≥ 4 sample points and SciPy installed.
                       Output is clamped to ``[min, max]`` of the input
                       to suppress overshoot at the boundaries.
                       Falls back silently to linear if SciPy is absent.

    Returns
    -------
    ``(g_new, [plane_0_new, plane_1_new, ...])``
        Resampled gamma grid and the corresponding intensity arrays.
    """
    if g_deg.size == 0:
        return g_deg, [None for _ in planes]

    g_min = float(g_deg.min())
    g_max = float(g_deg.max())
    n_steps = int(round((g_max - g_min) / step_deg))
    g_new = np.linspace(g_min, g_max, n_steps + 1, dtype=float)

    result: List[Optional[np.ndarray]] = []
    for arr in planes:
        if arr is None:
            result.append(None)
            continue
        arr = np.asarray(arr, dtype=float)
        if method == "cubic" and _HAS_SCIPY and g_deg.size >= 4:
            cs = CubicSpline(g_deg, arr, bc_type="natural", extrapolate=True)
            resampled = np.clip(cs(g_new), arr.min(), arr.max())
        else:
            resampled = np.interp(g_new, g_deg, arr)
        result.append(resampled)

    return g_new, result


# ---------------------------------------------------------------------------
# NAT curve builder
# ---------------------------------------------------------------------------

def _build_nat_pair(
    g_deg: np.ndarray,
    arr_right: Optional[np.ndarray],
    arr_left: Optional[np.ndarray],
) -> Tuple[Optional[NatCurve], Optional[NatCurve]]:
    """
    Convert a complementary C-plane pair to two NAT curves.

    The *right* curve corresponds to the half-plane on the right side of
    the diagram (C0 or C90), and the *left* curve to the opposite side
    (C180 or C270).

    If one array is ``None`` the other side is mirrored (symmetric lamp).
    If both are ``None``, ``(None, None)`` is returned.

    CIE γ → NAT θ mapping:
        right: θ = 180° − γ
        left:  θ = 180° + γ
    """
    if arr_right is None and arr_left is None:
        return None, None
    if arr_right is None:
        arr_right = arr_left
    if arr_left is None:
        arr_left = arr_right

    curve_right: NatCurve = [
        polar_to_nat(float(r), 180.0 - float(g))
        for g, r in zip(g_deg, arr_right)   # type: ignore[arg-type]
    ]
    curve_left: NatCurve = [
        polar_to_nat(float(r), 180.0 + float(g))
        for g, r in zip(g_deg, arr_left)    # type: ignore[arg-type]
    ]
    return curve_right, curve_left


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plot_ldt(
    ldt_path: str | Path,
    svg_path: str | Path | None = None,
    *,
    code: str = "",
    layout: Optional[Layout] = None,
    interpolate: bool = True,
    interp_step_deg: float = 1.0,
    interp_method: str = "linear",
    debug: bool = False,
) -> Path:
    """
    Generate a Lumtopic-style photometric SVG from an EULUMDAT (.ldt) file.

    Parameters
    ----------
    ldt_path :
        Path to the source ``.ldt`` file.
    svg_path :
        Destination SVG path.  Defaults to *ldt_path* with ``.svg`` extension.
    code :
        Distribution code displayed in the banner centre (e.g. ``"D53"``).
        Empty string leaves the centre blank.
    layout :
        Visual parameters; see :class:`renderer.Layout`.
        If ``None``, the default layout is used.
    interpolate :
        If ``True`` (default), resample I(γ) curves before plotting.
        Recommended: the original LDT step is usually 5° or 10°; interpolating
        to 1° produces significantly smoother curves.
    interp_step_deg :
        Angular step for resampling (degrees).  Default: 1°.
    interp_method :
        ``"linear"`` (default) or ``"cubic"``.
        Cubic requires SciPy; falls back to linear if unavailable.
    debug :
        If ``True``, overlay the plot area (blue) and bounding box (green).

    Returns
    -------
    :class:`pathlib.Path`
        Absolute path to the generated SVG file.

    Raises
    ------
    FileNotFoundError
        If *ldt_path* does not exist (propagated from pyldt).
    ValueError
        If no usable C-plane intensity data is found in the file.

    Examples
    --------
    Basic usage::

        from eulumdat_plot import plot_ldt
        svg = plot_ldt("luminaire.ldt", code="D53")

    Custom canvas size with cubic interpolation::

        from eulumdat_plot import plot_ldt, Layout
        layout = Layout(width=800, height=800)
        svg = plot_ldt("luminaire.ldt", code="D53",
                       layout=layout, interp_method="cubic")

    Raster export (requires the ``[export]`` optional dependency)::

        from eulumdat_plot.export import svg_to_png
        png = svg_to_png(svg)
    """
    ldt_path = Path(ldt_path)
    svg_path = Path(svg_path) if svg_path is not None else ldt_path.with_suffix(".svg")

    if layout is None:
        layout = Layout()

    # ------------------------------------------------------------------
    # 1. Read LDT — pyldt expands symmetry; we always get the full matrix.
    # ------------------------------------------------------------------
    ldt = LdtReader.read(ldt_path)

    # ------------------------------------------------------------------
    # 2. Extract C-planes by nearest-angle lookup.
    # ------------------------------------------------------------------
    I_C0   = _get_plane(ldt,   0.0)
    I_C90  = _get_plane(ldt,  90.0)
    I_C180 = _get_plane(ldt, 180.0)
    I_C270 = _get_plane(ldt, 270.0)

    available = [p for p in (I_C0, I_C90, I_C180, I_C270) if p is not None]
    if not available:
        raise ValueError(f"No usable C-plane data found in '{ldt_path}'.")

    r_data_max = float(np.vstack(available).max())

    # ------------------------------------------------------------------
    # 3. Gamma angles + optional resampling.
    # ------------------------------------------------------------------
    g_deg = np.asarray(ldt.header.g_angles, dtype=float)

    if interpolate and g_deg.size > 1:
        g_deg, (I_C0, I_C90, I_C180, I_C270) = _resample(
            g_deg, I_C0, I_C90, I_C180, I_C270,
            step_deg=interp_step_deg,
            method=interp_method,
        )

    # ------------------------------------------------------------------
    # 4. Build NAT curves.
    # ------------------------------------------------------------------
    curves_solid:   List[NatCurve] = []
    curves_dotted:  List[NatCurve] = []
    colors_solid:   List[str]      = []
    colors_dotted:  List[str]      = []
    strokes_solid:  List[float]    = []
    strokes_dotted: List[float]    = []

    def _register(
        arr_right: Optional[np.ndarray],
        arr_left:  Optional[np.ndarray],
        *,
        solid: bool,
        col_right: str = "black",
        col_left:  str = "black",
    ) -> None:
        """Build a NAT pair and append it to the appropriate curve lists."""
        cr, cl = _build_nat_pair(g_deg, arr_right, arr_left)
        for curve, col in ((cr, col_right), (cl, col_left)):
            if curve is None:
                continue
            if solid:
                curves_solid.append(curve)
                colors_solid.append(col)
                strokes_solid.append(layout.stroke_curve_solid)
            else:
                curves_dotted.append(curve)
                colors_dotted.append(col)
                strokes_dotted.append(layout.stroke_curve_dotted)

    if debug:
        # Colour-code each C-plane for visual validation.
        _register(I_C0,  I_C180, solid=True,  col_right="red",   col_left="blue")
        _register(I_C90, I_C270, solid=False, col_right="green", col_left="orange")
    else:
        _register(I_C0,  I_C180, solid=True)
        _register(I_C90, I_C270, solid=False)

    # ------------------------------------------------------------------
    # 5. Render SVG.
    # ------------------------------------------------------------------
    return make_svg(
        curves_solid=curves_solid,
        curves_dotted=curves_dotted,
        r_data_max=r_data_max,
        outfile=svg_path,
        code=code,
        layout=layout,
        debug=debug,
        colors_solid=colors_solid,
        colors_dotted=colors_dotted,
        strokes_solid=strokes_solid,
        strokes_dotted=strokes_dotted,
    )


def plot_ldt_svg(
    ldt_path: str | Path,
    *,
    code: str = "",
    layout: Optional[Layout] = None,
    interpolate: bool = True,
    interp_step_deg: float = 1.0,
    interp_method: str = "linear",
) -> str:
    """
    Same as :func:`plot_ldt` but returns the SVG as a string instead of
    writing to disk.

    Returns
    -------
    str
        SVG document as a string (starts with ``<svg``).
    """
    ldt_path = Path(ldt_path)
    if layout is None:
        layout = Layout()

    ldt = LdtReader.read(ldt_path)

    I_C0   = _get_plane(ldt,   0.0)
    I_C90  = _get_plane(ldt,  90.0)
    I_C180 = _get_plane(ldt, 180.0)
    I_C270 = _get_plane(ldt, 270.0)

    available = [p for p in (I_C0, I_C90, I_C180, I_C270) if p is not None]
    if not available:
        raise ValueError(f"No usable C-plane data found in '{ldt_path}'.")

    r_data_max = float(np.vstack(available).max())

    g_deg = np.asarray(ldt.header.g_angles, dtype=float)
    if interpolate and g_deg.size > 1:
        g_deg, (I_C0, I_C90, I_C180, I_C270) = _resample(
            g_deg, I_C0, I_C90, I_C180, I_C270,
            step_deg=interp_step_deg,
            method=interp_method,
        )

    curves_solid: List[NatCurve]  = []
    curves_dotted: List[NatCurve] = []
    colors_solid:  List[str]      = []
    colors_dotted: List[str]      = []
    strokes_solid:  List[float]   = []
    strokes_dotted: List[float]   = []

    def _register(arr_right, arr_left, *, solid: bool) -> None:
        cr, cl = _build_nat_pair(g_deg, arr_right, arr_left)
        for curve in (cr, cl):
            if curve is None:
                continue
            if solid:
                curves_solid.append(curve)
                colors_solid.append("black")
                strokes_solid.append(layout.stroke_curve_solid)
            else:
                curves_dotted.append(curve)
                colors_dotted.append("black")
                strokes_dotted.append(layout.stroke_curve_dotted)

    _register(I_C0, I_C180, solid=True)
    _register(I_C90, I_C270, solid=False)

    return make_svg_str(
        curves_solid=curves_solid,
        curves_dotted=curves_dotted,
        r_data_max=r_data_max,
        code=code,
        layout=layout,
        colors_solid=colors_solid,
        colors_dotted=colors_dotted,
        strokes_solid=strokes_solid,
        strokes_dotted=strokes_dotted,
    )
