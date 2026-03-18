# 01 — Basic usage

`eulumdat-plot` generates publication-ready photometric polar diagrams
from EULUMDAT (`.ldt`) files — suitable for product datasheets and PDF
or online documentation.

> For scientific / interactive plots with axis labels and legends,
> see the [eulumdat-py polar diagram example](https://github.com/123VincentB/eulumdat-py/blob/main/examples/02_polar_diagram.md).

---

## Minimal

```python
from eulumdat_plot import plot_ldt

svg = plot_ldt("luminaire.ldt")
# → luminaire.svg  (next to the source file)
```

---

## With a distribution code

The `code` parameter is displayed in the centre of the top banner.

```python
svg = plot_ldt("luminaire.ldt", code="D53")
```

---

## Custom output path

```python
svg = plot_ldt("luminaire.ldt", "output/diagram.svg", code="D53")
```

---

## Interpolation

EULUMDAT files typically store I(γ) at 5° steps.  Resampling to 1°
produces visibly smoother curves.

```python
# Linear interpolation — default, always available
svg = plot_ldt("luminaire.ldt", interpolate=True, interp_method="linear")

# Cubic spline — smoother result, requires:
# pip install "eulumdat-plot[cubic]"
svg = plot_ldt("luminaire.ldt", interpolate=True, interp_method="cubic")

# Disable — plot raw data points only
svg = plot_ldt("luminaire.ldt", interpolate=False)
```

---

## Debug mode

Colour-codes each C-plane to validate symmetry expansion visually:
C0 → red, C180 → blue, C90 → green, C270 → orange.

```python
svg = plot_ldt("luminaire.ldt", debug=True)
```

---

## Diagram conventions

| Element | Description |
|---|---|
| Solid curve | C0 / C180 plane pair |
| Dotted curve | C90 / C270 plane pair |
| Radial scale | cd/klm, dynamic (3–6 circles) |
| Banner left | LED |
| Banner centre | `code` parameter |
| Banner right | cd / klm |
| γ = 0° | Nadir (bottom of diagram) |
| γ = 180° | Zenith (top of diagram) |
