# 02 — Scaling, raster export, and batch processing

---

## Proportional scaling with `Layout.for_size()`

All visual parameters — stroke widths, font sizes, margins, dash patterns —
scale proportionally from the 1181 px reference.

```python
from eulumdat_plot import plot_ldt, Layout

# 600 × 600 px — compact format for datasheets
svg = plot_ldt("luminaire.ldt", layout=Layout.for_size(600))

# 1181 × 1181 px — reference size (default)
svg = plot_ldt("luminaire.ldt", layout=Layout.for_size(1181))

# 2362 × 2362 px — high resolution for print
svg = plot_ldt("luminaire.ldt", layout=Layout.for_size(2362))
```

`Layout.for_size(1181)` is identical to `Layout()`.

---

## Fine-tuning individual parameters

```python
layout = Layout.for_size(800)
layout.stroke_curve_solid  = 12.0   # thicker main curve
layout.stroke_curve_dotted = 8.0
layout.font_size_header    = 56.0

svg = plot_ldt("luminaire.ldt", layout=layout)
```

---

## Raster export — PNG and JPEG

Requires: `pip install "eulumdat-plot[export]"`

```python
from eulumdat_plot import plot_ldt, Layout
from eulumdat_plot.export import svg_to_png, svg_to_jpg

svg = plot_ldt("luminaire.ldt", layout=Layout.for_size(1181))

# PNG
png = svg_to_png(svg, size_px=600)
# → luminaire.png

# JPEG
jpg = svg_to_jpg(svg, size_px=600, quality=95)
# → luminaire.jpg

# Custom output path
png = svg_to_png(svg, "output/diagram_600.png", size_px=600)
```

The export size is **independent** of the SVG canvas size: a 1181 px SVG
can be exported at any resolution without regenerating it.

```python
# One SVG → multiple raster sizes
for size in [300, 600, 1181]:
    svg_to_png(svg, f"output/diagram_{size}px.png", size_px=size)
```

---

## Batch processing

Process all `.ldt` files in a directory and export SVG + PNG:

```python
from pathlib import Path
from eulumdat_plot import plot_ldt, Layout
from eulumdat_plot.export import svg_to_png

input_dir  = Path("data/input")
output_dir = Path("data/output")
output_dir.mkdir(exist_ok=True)

layout = Layout.for_size(1181)

for ldt_file in sorted(input_dir.glob("*.ldt")):
    svg = plot_ldt(
        ldt_file,
        output_dir / ldt_file.with_suffix(".svg").name,
        layout=layout,
    )
    svg_to_png(svg, output_dir / ldt_file.with_suffix(".png").name, size_px=600)
    print(f"✓  {ldt_file.name}")
```

---

## Complete pipeline

```python
from pathlib import Path
from eulumdat_plot import plot_ldt, Layout
from eulumdat_plot.export import svg_to_png, svg_to_jpg

ldt_file   = Path("luminaire.ldt")
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

svg = plot_ldt(
    ldt_file,
    output_dir / "diagram.svg",
    code="D53",
    layout=Layout.for_size(1181),
    interpolate=True,
    interp_method="cubic",   # requires: pip install "eulumdat-plot[cubic]"
)

# Multiple PNG sizes from the same SVG
for size in [300, 600, 1181]:
    svg_to_png(svg, output_dir / f"diagram_{size}px.png", size_px=size)

# JPEG for web
svg_to_jpg(svg, output_dir / "diagram.jpg", size_px=600, quality=95)
```
