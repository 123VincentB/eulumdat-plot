# eulumdat-plot

[![PyPI](https://img.shields.io/pypi/v/eulumdat-plot)](https://pypi.org/project/eulumdat-plot/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/eulumdat-plot)](https://pypi.org/project/eulumdat-plot/)
[![License: MIT](https://img.shields.io/github/license/123VincentB/eulumdat-plot)](https://github.com/123VincentB/eulumdat-plot/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19096110.svg)](https://doi.org/10.5281/zenodo.19096110)

Photometric polar diagram generator for EULUMDAT (`.ldt`) files —
designed for **product datasheets and publication-ready documents**.

Reads a `.ldt` file and produces a **Lumtopic-style SVG**: a square image
with a top banner and a polar candela distribution diagram showing the
C0/C180 (solid) and C90/C270 (dotted) curves, scaled to fill the plot area.

> **For scientific / interactive plots** (matplotlib, axis labels, legends),
> see the
> [eulumdat-py examples](https://github.com/123VincentB/eulumdat-py/blob/main/examples/02_polar_diagram.md).

Part of the [`eulumdat-*`](https://github.com/123VincentB) ecosystem, built
on top of [`eulumdat-py`](https://pypi.org/project/eulumdat-py/).

---

<img src="https://raw.githubusercontent.com/123VincentB/eulumdat-plot/main/docs/img/sample_01.png" width="360"> <img src="https://raw.githubusercontent.com/123VincentB/eulumdat-plot/main/docs/img/sample_02.png" width="360">

---

## Features

- Reads any EULUMDAT file — all symmetry types (ISYM 0–4) handled by `eulumdat-py`
- Generates a **publication-ready SVG** polar diagram (Lumtopic style)
- Dynamic radial scale (3–6 concentric circles, round values)
- Dominant-hemisphere detection for automatic scale label placement
- Proportional scaling via `Layout.for_size(n)` — one parameter controls everything
- Optional I(γ) interpolation (linear or cubic spline) for smooth curves
- Optional raster export to **PNG** and **JPEG** (cross-platform, no native DLL)
- Debug mode for visual validation of C-plane assignment

## Installation

Core package (SVG generation only):

```bash
pip install eulumdat-plot
```

With raster export (PNG / JPEG):

```bash
pip install "eulumdat-plot[export]"
```

With cubic spline interpolation:

```bash
pip install "eulumdat-plot[cubic]"
```

Everything:

```bash
pip install "eulumdat-plot[full]"
```

## Quick start

```python
from eulumdat_plot import plot_ldt

# Generate an SVG next to the source file
svg = plot_ldt("luminaire.ldt")

# With a distribution code in the banner centre
svg = plot_ldt("luminaire.ldt", code="D53")
```

## Scaling

All visual parameters (stroke widths, font sizes, margins) scale
proportionally from the 1181 px reference with a single call:

```python
from eulumdat_plot import plot_ldt, Layout

svg = plot_ldt("luminaire.ldt", layout=Layout.for_size(600))
```

## Raster export

```python
from eulumdat_plot import plot_ldt, Layout
from eulumdat_plot.export import svg_to_png, svg_to_jpg

svg = plot_ldt("luminaire.ldt", layout=Layout.for_size(1181))
png = svg_to_png(svg, size_px=600)
jpg = svg_to_jpg(svg, size_px=600, quality=95)
```

The export size is independent of the SVG canvas size.

## API reference

### `plot_ldt()`

```python
def plot_ldt(
    ldt_path: str | Path,
    svg_path: str | Path | None = None,
    *,
    code: str = "",
    layout: Layout | None = None,
    interpolate: bool = True,
    interp_step_deg: float = 1.0,
    interp_method: str = "linear",
    debug: bool = False,
) -> Path
```

| Parameter         | Default           | Description                                  |
| ----------------- | ----------------- | -------------------------------------------- |
| `ldt_path`        | —                 | Source `.ldt` file                           |
| `svg_path`        | same name, `.svg` | Output SVG path                              |
| `code`            | `""`              | Distribution code shown in the banner centre |
| `layout`          | `Layout()`        | Visual parameters                            |
| `interpolate`     | `True`            | Resample I(γ) before plotting                |
| `interp_step_deg` | `1.0`             | Angular step for resampling (degrees)        |
| `interp_method`   | `"linear"`        | `"linear"` or `"cubic"` (requires scipy)     |
| `debug`           | `False`           | Colour-code C-planes for visual validation   |

### `Layout.for_size()`

```python
Layout.for_size(size_px: int) -> Layout
```

Creates a `Layout` with all dimensions scaled proportionally from the
1181 px reference. `Layout.for_size(1181)` is identical to `Layout()`.

### `svg_to_png()` / `svg_to_jpg()`

```python
svg_to_png(svg_path, png_path=None, *, size_px=1181, background="#FFFFFF") -> Path
svg_to_jpg(svg_path, jpg_path=None, *, size_px=1181, background="#FFFFFF", quality=95) -> Path
```

Requires `pip install "eulumdat-plot[export]"`.

## Examples

| File                                                                   | Description                              |
| ---------------------------------------------------------------------- | ---------------------------------------- |
| [`examples/01_basic_usage.md`](examples/01_basic_usage.md)             | Generate an SVG from a `.ldt` file       |
| [`examples/02_resize_and_export.md`](examples/02_resize_and_export.md) | Scaling, raster export, batch processing |

## Project structure

```
eulumdat-plot/
├── data/
│   ├── input/          # sample .ldt files (ISYM 0–4)
│   └── output/         # generated SVG / PNG / JPEG
├── docs/
│   └── img/
│       └── sample_01.svg
├── examples/
│   ├── 01_basic_usage.md
│   └── 02_resize_and_export.md
├── src/
│   └── eulumdat_plot/
│       ├── __init__.py
│       ├── plot.py     # public API — LDT → SVG pipeline
│       ├── renderer.py # SVG renderer + Layout dataclass
│       └── export.py   # raster export (PNG / JPEG)
├── tests/
│   ├── test_smoke.py   # 46 real LDT files, all ISYM types
│   └── test_scaling.py # Layout.for_size() proportionality
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## EULUMDAT ecosystem

| Package                                                            | Status  | Description                                  |
| ------------------------------------------------------------------ | ------- | -------------------------------------------- |
| [`eulumdat-py`](https://pypi.org/project/eulumdat-py/)             | v0.1.4  | Read / write EULUMDAT files                  |
| [`eulumdat-symmetry`](https://pypi.org/project/eulumdat-symmetry/) | v1.0.0  | Symmetrise EULUMDAT files                    |
| `eulumdat-plot`                                                    | v1.0.0  | Photometric polar diagram — **this package** |
| `eulumdat-luminance`                                               | planned | Luminance table cd/m² (γ 55°–85°)            |
| `eulumdat-ugr`                                                     | planned | UGR calculation (CIE 117, CIE 190)           |

## Requirements

- Python ≥ 3.9
- `eulumdat-py` ≥ 1.0.0
- `numpy` ≥ 1.21
- `svgwrite` ≥ 1.4
- *(optional)* `vl-convert-python` ≥ 1.6 + `Pillow` ≥ 9.0 — raster export
- *(optional)* `scipy` ≥ 1.7 — cubic spline interpolation

## License

MIT — © 2024 [123VincentB](https://github.com/123VincentB)
