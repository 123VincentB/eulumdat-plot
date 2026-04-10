# Changelog

All notable changes to `eulumdat-plot` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.3] — 2026-04-10

### Added
- `plot_ldt_svg()` — same pipeline as `plot_ldt()` but returns the SVG as a
  string instead of writing to disk; intended for inline HTML embedding
- `make_svg_str()` — low-level counterpart to `make_svg()`, returns SVG string
  via `dwg.tostring()` without any file I/O
- `renderer.py`: internal `_build_drawing()` helper factored out to avoid
  code duplication between `make_svg()` and `make_svg_str()`

---

## [1.0.2] — 2026

### Fixed
- README image size

---

## [1.0.1] — 2026

### Fixed
- README images for PyPI rendering

---

## [1.0.0] — 2026

### Added
- `plot_ldt()` — main public API: EULUMDAT `.ldt` → SVG polar diagram
- `Layout` dataclass — all visual parameters in one place
- `Layout.for_size(n)` — proportional scaling from 1181 px reference
- `make_svg()` — low-level SVG renderer, decoupled from LDT parsing
- `polar_to_nat()` — polar to NAT Cartesian coordinate conversion
- `svg_to_png()` / `svg_to_jpg()` — raster export via `vl-convert-python`
  (cross-platform, no native DLL required)
- Optional I(γ) resampling: linear (`numpy`) and cubic spline (`scipy`)
- Dynamic radial scale: 3–6 concentric circles with round values
- Dominant-hemisphere detection for automatic scale label placement
- Debug mode: colour-coded C-planes for visual validation
- SVG clip path: curves and grid clipped to the plot area
- Smoke tests: 46 real EULUMDAT files, all ISYM types (0–4)
- Scaling tests: proportionality and pixel-exact PNG export

### Architecture
- `plot.py` — LDT reading and C-plane extraction via `eulumdat-py`;
  ISYM handling fully delegated to `pyldt.LdtReader`
- `renderer.py` — pure SVG generation, no LDT dependency
- `export.py` — raster export, lazy dependency loading

---

## [0.0.1] — 2026

### Added
- Initial stub published on PyPI to reserve the package name.
