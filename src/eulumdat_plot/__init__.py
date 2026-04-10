"""
eulumdat-plot — Photometric polar diagram generator for EULUMDAT (.ldt) files.

This package is an extension of ``eulumdat-py`` (``pyldt``).
It reads a ``.ldt`` file and generates a photometric polar diagram in the
style of the Lumtopic software: a square SVG image with a top banner
("LED" / distribution code / "cd / klm") and a polar plot showing the
C0/C180 distribution (solid curve) and C90/C270 distribution (dotted curve).

Quick start
-----------
::

    from eulumdat_plot import plot_ldt

    # Minimal — outputs "luminaire.svg" next to the source file.
    svg = plot_ldt("luminaire.ldt")

    # With distribution code and custom canvas size.
    from eulumdat_plot import Layout
    layout = Layout(width=800, height=800)
    svg = plot_ldt("luminaire.ldt", code="D53", layout=layout)

    # Raster export (requires the ``[export]`` optional dependency).
    from eulumdat_plot.export import svg_to_png, svg_to_jpg
    png = svg_to_png(svg)
    jpg = svg_to_jpg(svg)

Public API
----------
:func:`plot_ldt`
    Main entry point: LDT file → SVG diagram.
:class:`Layout`
    Dataclass holding all visual parameters (sizes, stroke widths, fonts…).
:func:`make_svg`
    Low-level renderer: pre-computed NAT curves → SVG.
    Useful if you need to build curves yourself and bypass the LDT pipeline.
:func:`polar_to_nat`
    Convert polar ``(r, θ)`` to NAT ``(x, y)`` Cartesian coordinates.
"""

from .plot import plot_ldt, plot_ldt_svg
from .renderer import Layout, make_svg, make_svg_str, polar_to_nat

__all__ = [
    "plot_ldt",
    "plot_ldt_svg",
    "Layout",
    "make_svg",
    "make_svg_str",
    "polar_to_nat",
]
