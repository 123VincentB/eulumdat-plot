"""
tests/test_smoke.py — Smoke tests on real LDT samples.

Runs plot_ldt() on every .ldt file found in data/input/ and writes the
resulting SVG to data/output/.  A test passes if no exception is raised
and the output SVG file is non-empty.

Run from the project root:
    pytest tests/test_smoke.py -v
Or for a quick standalone run without pytest:
    python tests/test_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — resolved relative to this file so the script works from any cwd.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
DATA_INPUT   = PROJECT_ROOT / "data" / "input"
DATA_OUTPUT  = PROJECT_ROOT / "data" / "output"
SRC          = PROJECT_ROOT / "src"

# Make sure the local src/ is on the path (no editable install required).
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Import after path setup.
# ---------------------------------------------------------------------------
from eulumdat_plot import plot_ldt, Layout   # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ldt_files() -> list[Path]:
    """Return all .ldt files in data/input/, sorted by name."""
    files = sorted(DATA_INPUT.glob("*.ldt"))
    if not files:
        raise FileNotFoundError(f"No .ldt files found in {DATA_INPUT}")
    return files


def _run_one(ldt_path: Path, layout: Layout) -> tuple[bool, str]:
    """
    Run plot_ldt() on a single file.

    Returns
    -------
    (success, message)
    """
    svg_path = DATA_OUTPUT / ldt_path.with_suffix(".svg").name
    try:
        out = plot_ldt(
            ldt_path,
            svg_path,
            code="",
            layout=layout,
            interpolate=True,
            interp_method="cubic",
        )
        size = out.stat().st_size
        if size == 0:
            return False, f"SVG is empty (0 bytes)"
        return True, f"OK — {size:,} bytes → {out.name}"
    except Exception as exc:
        return False, f"EXCEPTION: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Standalone runner (python tests/test_smoke.py)
# ---------------------------------------------------------------------------

def run_all() -> None:
    files = _ldt_files()
    layout = Layout(width=1181, height=1181)

    passed = 0
    failed = 0
    failures: list[str] = []

    print(f"\n{'─' * 60}")
    print(f"  eulumdat-plot smoke test — {len(files)} files")
    print(f"  Input  : {DATA_INPUT}")
    print(f"  Output : {DATA_OUTPUT}")
    print(f"{'─' * 60}\n")

    for ldt in files:
        success, msg = _run_one(ldt, layout)
        status = "✓" if success else "✗"
        print(f"  {status}  {ldt.name:<40}  {msg}")
        if success:
            passed += 1
        else:
            failed += 1
            failures.append(f"{ldt.name}: {msg}")

    print(f"\n{'─' * 60}")
    print(f"  Results: {passed} passed, {failed} failed / {len(files)} total")
    print(f"{'─' * 60}\n")

    if failures:
        print("Failed files:")
        for f in failures:
            print(f"  • {f}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# pytest interface
# ---------------------------------------------------------------------------

def pytest_generate_tests(metafunc):
    """Parametrize test_single_ldt with all .ldt files."""
    if "ldt_path" in metafunc.fixturenames:
        try:
            files = _ldt_files()
        except FileNotFoundError:
            files = []
        metafunc.parametrize("ldt_path", files, ids=[f.name for f in files])


def test_single_ldt(ldt_path: Path) -> None:
    """Each LDT file must produce a non-empty SVG without raising."""
    layout = Layout(width=1181, height=1181)
    success, msg = _run_one(ldt_path, layout)
    assert success, msg


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_all()
