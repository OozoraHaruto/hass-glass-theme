# hass-glass-theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS-installable Home Assistant theme shipping twelve Apple-inspired glass entries generated from a single token source, validated by GitHub CI/CD.

**Architecture:** YAML token files (`tokens/`) are merged base → material → mode → lite by a Python package (`glassbuild/`), which derives material values, maps them onto Home Assistant theme variables, and emits a single `themes/glass.yaml` containing all twelve entries. A thin CLI (`scripts/build_themes.py`) writes that file; `--check` re-generates and diffs so CI can fail on drift. Generated output is committed so HACS and manual installs need no build step.

**Tech Stack:** Python 3.11+, PyYAML, pytest, yamllint, actionlint, GitHub Actions, HACS.

## Global Constraints

- Python 3.11 or later. Runtime dependency: **PyYAML only**. Dev dependencies: pytest, yamllint.
- Home Assistant theme variable keys are written **without** the leading `--`. HA adds it.
- All twelve entry names exactly as in the entry matrix below. Names are user-visible.
- Lite entries must contain **no** `backdrop-filter` in any form — native variable or card-mod CSS.
- Lite fill alpha floor: **0.72**. Full-material minimum fill alpha floor: **0.10**.
- Light material is **derived, never authored**: blur = half the full radius, fill alpha = full + 0.08.
- No font files are bundled. SF Pro is licensed for Apple platforms only.
- All third-party GitHub Actions pinned to commit SHAs, never tags or `@main`.
- Contrast target: WCAG AA — 4.5:1 body text, 3:1 large text.
- Generated `themes/glass.yaml` is committed. Never hand-edit it.

### Entry matrix

| | Auto | Light | Dark |
|---|---|---|---|
| **Glass** | `Glass` | `Glass Light` | `Glass Dark` |
| **Glass, no blur** | `Glass Lite` | `Glass Light Lite` | `Glass Dark Lite` |
| **Frosted Glass** | `Frosted Glass` | `Frosted Glass Light` | `Frosted Glass Dark` |
| **Frosted, no blur** | `Frosted Glass Lite` | `Frosted Glass Light Lite` | `Frosted Glass Dark Lite` |

### Material tuning table

| Property | Glass | Frosted Glass |
|---|---|---|
| Blur | `8px` | `40px` |
| Saturation | `180%` | `150%` |
| Fill alpha light / dark | `.10` / `.14` | `.55` / `.45` |
| Rim alpha | `.45` | `.20` |
| Lite fill alpha | `.72` | `.72` |

## File Structure

| Path | Responsibility |
|---|---|
| `glassbuild/color.py` | Colour parsing, alpha compositing, WCAG luminance and contrast |
| `glassbuild/tokens.py` | Load token YAML, merge base → material → mode |
| `glassbuild/materials.py` | Derive full / light / lite material values from tuning table |
| `glassbuild/variables.py` | Map a merged token dict onto HA theme variable names |
| `glassbuild/cardmod.py` | Build the card-mod CSS injection block |
| `glassbuild/emit.py` | Assemble the twelve entries, apply `modes:` wrapping |
| `glassbuild/validate.py` | Dangling vars, Lite purity, flat-map shape |
| `scripts/build_themes.py` | CLI: write `themes/glass.yaml`, `--check` for drift |
| `tokens/*.yaml` | Design values — the only files a designer edits |
| `themes/glass.yaml` | GENERATED, committed. Twelve entries |
| `tests/*.py` | pytest suite |
| `demo/dashboard.yaml` | Manual verification dashboard |
| `hacs.json`, `README.md` | HACS packaging and docs |
| `.github/workflows/*` | CI and release |

---

### Task 1: Project scaffolding and colour maths

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.yamllint.yml`, `glassbuild/__init__.py`, `glassbuild/color.py`
- Test: `tests/test_color.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces:
  - `parse_rgba(value: str) -> tuple[int, int, int, float]` — accepts `#RRGGBB`, `#RGB`, `rgba(r,g,b,a)`, `rgb(r,g,b)`
  - `rgba_str(r: int, g: int, b: int, a: float) -> str` — renders `rgba(r, g, b, a)`, alpha to 3 dp, trailing zeros stripped
  - `composite(fg: tuple[int,int,int,float], bg: tuple[int,int,int,float]) -> tuple[int,int,int,float]` — source-over, returns opaque when `bg` alpha is 1.0
  - `relative_luminance(rgb: tuple[int,int,int]) -> float` — WCAG 2.1
  - `contrast_ratio(fg: tuple[int,int,int], bg: tuple[int,int,int]) -> float` — WCAG 2.1, always ≥ 1.0

- [ ] **Step 1: Create the project files**

`pyproject.toml`:

```toml
[project]
name = "hass-glass-theme"
version = "0.1.0"
description = "Apple-inspired glass and frosted glass themes for Home Assistant"
requires-python = ">=3.11"
dependencies = ["PyYAML>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "yamllint>=1.35"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.setuptools]
packages = ["glassbuild"]
```

`.gitignore`:

```
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
*.egg-info/
.superpowers/
actionlint
```

`.superpowers/` holds build-process scratch and must stay ignored. `actionlint` is the
binary Task 12 downloads for local workflow linting.

`.yamllint.yml`:

```yaml
extends: default
rules:
  line-length: disable
  document-start: disable
  comments-indentation: disable
  truthy:
    check-keys: false
  indentation:
    spaces: 2
    indent-sequences: true
ignore: |
  .venv/
```

Create an empty `glassbuild/__init__.py`.

- [ ] **Step 2: Write the failing tests**

`tests/test_color.py`:

```python
import pytest

from glassbuild.color import (
    composite,
    contrast_ratio,
    parse_rgba,
    relative_luminance,
    rgba_str,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("#FFFFFF", (255, 255, 255, 1.0)),
        ("#000", (0, 0, 0, 1.0)),
        ("#007AFF", (0, 122, 255, 1.0)),
        ("rgb(10, 20, 30)", (10, 20, 30, 1.0)),
        ("rgba(10, 20, 30, 0.5)", (10, 20, 30, 0.5)),
        ("rgba(10,20,30,.25)", (10, 20, 30, 0.25)),
    ],
)
def test_parse_rgba(value, expected):
    assert parse_rgba(value) == expected


def test_parse_rgba_rejects_garbage():
    with pytest.raises(ValueError):
        parse_rgba("not-a-colour")


def test_rgba_str_strips_trailing_zeros():
    assert rgba_str(1, 2, 3, 0.5) == "rgba(1, 2, 3, 0.5)"
    assert rgba_str(1, 2, 3, 1.0) == "rgba(1, 2, 3, 1)"
    assert rgba_str(1, 2, 3, 0.125) == "rgba(1, 2, 3, 0.125)"


def test_composite_opaque_foreground_wins():
    assert composite((255, 0, 0, 1.0), (0, 0, 255, 1.0)) == (255, 0, 0, 1.0)


def test_composite_half_alpha_is_midpoint():
    r, g, b, a = composite((255, 255, 255, 0.5), (0, 0, 0, 1.0))
    assert (r, g, b) == (128, 128, 128)
    assert a == 1.0


def test_composite_transparent_foreground_is_noop():
    assert composite((255, 0, 0, 0.0), (0, 0, 255, 1.0)) == (0, 0, 255, 1.0)


def test_relative_luminance_endpoints():
    assert relative_luminance((0, 0, 0)) == pytest.approx(0.0)
    assert relative_luminance((255, 255, 255)) == pytest.approx(1.0)


def test_contrast_ratio_black_on_white_is_21():
    assert contrast_ratio((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0, abs=0.01)


def test_contrast_ratio_is_order_independent():
    a = contrast_ratio((0, 0, 0), (255, 255, 255))
    b = contrast_ratio((255, 255, 255), (0, 0, 0))
    assert a == pytest.approx(b)


def test_contrast_ratio_identical_colours_is_one():
    assert contrast_ratio((80, 80, 80), (80, 80, 80)) == pytest.approx(1.0)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/test_color.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glassbuild.color'`

- [ ] **Step 4: Implement `glassbuild/color.py`**

```python
"""Colour parsing, compositing, and WCAG contrast maths."""

from __future__ import annotations

import re

RGBA = tuple[int, int, int, float]

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_FUNC_RE = re.compile(
    r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([0-9]*\.?[0-9]+)\s*)?\)$"
)


def parse_rgba(value: str) -> RGBA:
    """Parse ``#RGB``, ``#RRGGBB``, ``rgb(...)``, or ``rgba(...)`` into an RGBA tuple."""
    text = value.strip()

    if _HEX_RE.match(text):
        digits = text[1:]
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        return (
            int(digits[0:2], 16),
            int(digits[2:4], 16),
            int(digits[4:6], 16),
            1.0,
        )

    match = _FUNC_RE.match(text)
    if match:
        r, g, b, a = match.groups()
        return (int(r), int(g), int(b), float(a) if a is not None else 1.0)

    raise ValueError(f"cannot parse colour: {value!r}")


def rgba_str(r: int, g: int, b: int, a: float) -> str:
    """Render an RGBA tuple as CSS, trimming trailing zeros from the alpha."""
    alpha = f"{a:.3f}".rstrip("0").rstrip(".")
    return f"rgba({r}, {g}, {b}, {alpha or '0'})"


def composite(fg: RGBA, bg: RGBA) -> RGBA:
    """Source-over composite of ``fg`` onto ``bg``."""
    fr, fg_, fb, fa = fg
    br, bg_, bb, ba = bg
    out_a = fa + ba * (1.0 - fa)
    if out_a == 0.0:
        return (0, 0, 0, 0.0)

    def channel(f: int, b: int) -> int:
        return round((f * fa + b * ba * (1.0 - fa)) / out_a)

    return (channel(fr, br), channel(fg_, bg_), channel(fb, bb), out_a)


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG 2.1 relative luminance."""

    def linearise(channel: int) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linearise(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    """WCAG 2.1 contrast ratio between two opaque colours."""
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_color.py -v`
Expected: PASS — 15 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore .yamllint.yml glassbuild/ tests/test_color.py
git commit -m "feat: add colour maths and project scaffolding"
```

---

### Task 2: Token loading and merge

**Files:**
- Create: `glassbuild/tokens.py`
- Test: `tests/test_tokens.py`

**Interfaces:**
- Consumes: nothing from Task 1
- Produces:
  - `MATERIALS: tuple[str, ...]` — `("glass", "frosted-glass")`
  - `MODES: tuple[str, ...]` — `("light", "dark")`
  - `load_tokens(root: Path) -> dict[str, dict]` — returns `{"base": ..., "materials": {name: ...}, "modes": {name: ...}}`
  - `merge(base: dict, material: dict, mode: dict) -> dict` — later sources win, nested dicts merged recursively

- [ ] **Step 1: Write the failing tests**

`tests/test_tokens.py`:

```python
import pytest

from glassbuild.tokens import MATERIALS, MODES, load_tokens, merge

REPO_ROOT_MARKER = "tokens"


def test_material_and_mode_names():
    assert MATERIALS == ("glass", "frosted-glass")
    assert MODES == ("light", "dark")


def test_merge_later_sources_win():
    result = merge({"a": 1, "b": 2}, {"b": 3}, {"a": 4})
    assert result == {"a": 4, "b": 3}


def test_merge_is_recursive():
    result = merge({"m": {"x": 1, "y": 2}}, {"m": {"y": 3}}, {})
    assert result == {"m": {"x": 1, "y": 3}}


def test_merge_does_not_mutate_inputs():
    base = {"m": {"x": 1}}
    merge(base, {"m": {"x": 2}}, {})
    assert base == {"m": {"x": 1}}


def test_load_tokens_reads_every_file(tmp_path):
    (tmp_path / "tokens" / "modes").mkdir(parents=True)
    (tmp_path / "tokens" / "base.yaml").write_text("radius: 18px\n")
    (tmp_path / "tokens" / "glass.yaml").write_text("blur: 8px\n")
    (tmp_path / "tokens" / "frosted-glass.yaml").write_text("blur: 40px\n")
    (tmp_path / "tokens" / "modes" / "light.yaml").write_text("bg: white\n")
    (tmp_path / "tokens" / "modes" / "dark.yaml").write_text("bg: black\n")

    tokens = load_tokens(tmp_path)

    assert tokens["base"] == {"radius": "18px"}
    assert tokens["materials"]["glass"] == {"blur": "8px"}
    assert tokens["materials"]["frosted-glass"] == {"blur": "40px"}
    assert tokens["modes"]["light"] == {"bg": "white"}
    assert tokens["modes"]["dark"] == {"bg": "black"}


def test_load_tokens_reports_a_missing_file(tmp_path):
    (tmp_path / "tokens").mkdir()
    (tmp_path / "tokens" / "base.yaml").write_text("radius: 18px\n")
    with pytest.raises(FileNotFoundError):
        load_tokens(tmp_path)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_tokens.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glassbuild.tokens'`

- [ ] **Step 3: Implement `glassbuild/tokens.py`**

```python
"""Loading and merging of the YAML token sources."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

MATERIALS: tuple[str, ...] = ("glass", "frosted-glass")
MODES: tuple[str, ...] = ("light", "dark")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing token file: {path}")
    return yaml.safe_load(path.read_text()) or {}


def load_tokens(root: Path) -> dict[str, Any]:
    """Load every token file under ``root/tokens``."""
    tokens_dir = Path(root) / "tokens"
    return {
        "base": _read(tokens_dir / "base.yaml"),
        "materials": {name: _read(tokens_dir / f"{name}.yaml") for name in MATERIALS},
        "modes": {name: _read(tokens_dir / "modes" / f"{name}.yaml") for name in MODES},
    }


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def merge(*sources: dict[str, Any]) -> dict[str, Any]:
    """Merge token dicts left to right; later sources win. Inputs are not mutated."""
    result: dict[str, Any] = {}
    for source in sources:
        _deep_merge(result, source or {})
    return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_tokens.py -v`
Expected: PASS — 6 passed

- [ ] **Step 5: Commit**

```bash
git add glassbuild/tokens.py tests/test_tokens.py
git commit -m "feat: add token loading and recursive merge"
```

---

### Task 3: Token data files

**Files:**
- Create: `tokens/base.yaml`, `tokens/glass.yaml`, `tokens/frosted-glass.yaml`, `tokens/modes/light.yaml`, `tokens/modes/dark.yaml`
- Test: `tests/test_token_data.py`

**Interfaces:**
- Consumes: `load_tokens`, `merge`, `MATERIALS`, `MODES` from Task 2
- Produces: the token schema every later task reads. Merged token keys: `radius.*`, `shadow`, `font.*`, `motion.*`, `material.*`, `palette.*`.

- [ ] **Step 1: Write the token files**

`tokens/base.yaml`:

```yaml
# Geometry, type, and motion. Shared by all twelve entries.
radius:
  card: 18px
  dialog: 28px
  control: 12px
  pill: 980px

shadow: "0 1px 2px rgba(0, 0, 0, 0.04), 0 8px 32px rgba(0, 0, 0, 0.12)"

font:
  stack: >-
    -apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui,
    "Segoe UI", Roboto, sans-serif
  tracking_headline: "-0.4px"
  tracking_body: "-0.2px"

motion:
  duration: 300ms
  easing: cubic-bezier(0.25, 0.1, 0.25, 1)
```

`tokens/glass.yaml`:

```yaml
# Clear material: minimal blur, high transparency, bright specular rim.
material:
  name: Glass
  blur_px: 8
  saturate_pct: 180
  rim_alpha: 0.45
```

`tokens/frosted-glass.yaml`:

```yaml
# Diffuse material: heavy blur, low transparency, soft rim.
material:
  name: Frosted Glass
  blur_px: 40
  saturate_pct: 150
  rim_alpha: 0.20
```

`tokens/modes/light.yaml`:

```yaml
material:
  fill_rgb: [255, 255, 255]
  fill_alpha_glass: 0.10
  fill_alpha_frosted: 0.55
  rim_rgb: [255, 255, 255]

palette:
  accent: "#007AFF"
  success: "#34C759"
  warning: "#FF9500"
  error: "#FF3B30"
  scene: "#AF52DE"
  text_primary: "#1C1C1E"
  text_secondary: "#3C3C4399"
  text_disabled: "#3C3C4361"
  divider: "rgba(60, 60, 67, 0.18)"
  opaque_surface: "#F2F2F7"
  background_from: "#EEF2F8"
  background_via: "#E6ECF6"
  background_to: "#F7F4FA"
```

`tokens/modes/dark.yaml`:

```yaml
material:
  fill_rgb: [255, 255, 255]
  fill_alpha_glass: 0.14
  fill_alpha_frosted: 0.45
  rim_rgb: [255, 255, 255]

palette:
  accent: "#0A84FF"
  success: "#30D158"
  warning: "#FF9F0A"
  error: "#FF453A"
  scene: "#BF5AF2"
  text_primary: "#FFFFFF"
  text_secondary: "#EBEBF599"
  text_disabled: "#EBEBF561"
  divider: "rgba(84, 84, 88, 0.65)"
  opaque_surface: "#1C1C1E"
  background_from: "#101014"
  background_via: "#16161C"
  background_to: "#1B1620"
```

Note on the dark Lite fill: Lite clamps alpha to 0.72 over a dark background, so `fill_rgb` of white would produce a near-white surface in dark mode. Task 4 handles this by using `opaque_surface` as the Lite fill base rather than `fill_rgb`.

- [ ] **Step 2: Write the failing test**

`tests/test_token_data.py`:

```python
from pathlib import Path

import pytest

from glassbuild.tokens import MATERIALS, MODES, load_tokens, merge

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def tokens():
    return load_tokens(ROOT)


def test_every_token_file_loads(tokens):
    assert set(tokens["materials"]) == set(MATERIALS)
    assert set(tokens["modes"]) == set(MODES)


@pytest.mark.parametrize("material", MATERIALS)
@pytest.mark.parametrize("mode", MODES)
def test_merged_tokens_have_required_keys(tokens, material, mode):
    merged = merge(
        tokens["base"],
        tokens["materials"][material],
        tokens["modes"][mode],
    )
    assert merged["radius"]["card"] == "18px"
    assert merged["material"]["name"] in ("Glass", "Frosted Glass")
    assert isinstance(merged["material"]["blur_px"], int)
    assert isinstance(merged["material"]["saturate_pct"], int)
    for key in ("accent", "text_primary", "opaque_surface", "background_from"):
        assert key in merged["palette"]


def test_tuning_table_values_match_the_spec(tokens):
    assert tokens["materials"]["glass"]["material"]["blur_px"] == 8
    assert tokens["materials"]["glass"]["material"]["saturate_pct"] == 180
    assert tokens["materials"]["glass"]["material"]["rim_alpha"] == 0.45
    assert tokens["materials"]["frosted-glass"]["material"]["blur_px"] == 40
    assert tokens["materials"]["frosted-glass"]["material"]["saturate_pct"] == 150
    assert tokens["materials"]["frosted-glass"]["material"]["rim_alpha"] == 0.20
    assert tokens["modes"]["light"]["material"]["fill_alpha_glass"] == 0.10
    assert tokens["modes"]["light"]["material"]["fill_alpha_frosted"] == 0.55
    assert tokens["modes"]["dark"]["material"]["fill_alpha_glass"] == 0.14
    assert tokens["modes"]["dark"]["material"]["fill_alpha_frosted"] == 0.45
```

- [ ] **Step 3: Run the tests to verify they pass**

Run: `python -m pytest tests/test_token_data.py -v`
Expected: PASS — 7 passed

These tests pass on first run because the data files were written in Step 1. That is intentional: this task's deliverable is data, and the test's job is to pin the spec's tuning table so a later edit cannot silently drift from it.

- [ ] **Step 4: Lint the token files**

Run: `python -m yamllint tokens/`
Expected: no output, exit code 0

- [ ] **Step 5: Commit**

```bash
git add tokens/ tests/test_token_data.py
git commit -m "feat: add design token data files"
```

---

### Task 4: Material derivation

**Files:**
- Create: `glassbuild/materials.py`
- Test: `tests/test_materials.py`

**Interfaces:**
- Consumes: `parse_rgba`, `rgba_str` from Task 1
- Produces:
  - `LITE_FILL_ALPHA: float` — `0.72`
  - `FULL_FILL_ALPHA_FLOOR: float` — `0.10`
  - `LIGHT_ALPHA_BONUS: float` — `0.08`
  - `Material` dataclass with fields `fill: str`, `rim: str`, `backdrop: str | None`
  - `derive(merged: dict, material_key: str, lite: bool) -> dict[str, Material]` — returns `{"full": Material, "light": Material}`

`backdrop` is `None` for Lite. `material_key` is `"glass"` or `"frosted-glass"` and selects which mode alpha applies.

- [ ] **Step 1: Write the failing tests**

`tests/test_materials.py`:

```python
import pytest

from glassbuild.materials import (
    FULL_FILL_ALPHA_FLOOR,
    LIGHT_ALPHA_BONUS,
    LITE_FILL_ALPHA,
    derive,
)

MERGED = {
    "material": {
        "name": "Glass",
        "blur_px": 8,
        "saturate_pct": 180,
        "rim_alpha": 0.45,
        "fill_rgb": [255, 255, 255],
        "fill_alpha_glass": 0.10,
        "fill_alpha_frosted": 0.55,
        "rim_rgb": [255, 255, 255],
    },
    "palette": {"opaque_surface": "#1C1C1E"},
}


def test_constants_match_the_spec():
    assert LITE_FILL_ALPHA == 0.72
    assert FULL_FILL_ALPHA_FLOOR == 0.10
    assert LIGHT_ALPHA_BONUS == 0.08


def test_full_material_uses_the_mode_alpha():
    result = derive(MERGED, "glass", lite=False)
    assert result["full"].fill == "rgba(255, 255, 255, 0.1)"
    assert result["full"].backdrop == "blur(8px) saturate(180%)"
    assert result["full"].rim == "rgba(255, 255, 255, 0.45)"


def test_frosted_selects_its_own_alpha():
    result = derive(MERGED, "frosted-glass", lite=False)
    assert result["full"].fill == "rgba(255, 255, 255, 0.55)"


def test_light_material_is_half_blur_and_bonus_alpha():
    result = derive(MERGED, "glass", lite=False)
    assert result["light"].backdrop == "blur(4px) saturate(180%)"
    assert result["light"].fill == "rgba(255, 255, 255, 0.18)"


def test_light_material_rounds_odd_blur_down():
    merged = {**MERGED, "material": {**MERGED["material"], "blur_px": 40}}
    result = derive(merged, "frosted-glass", lite=False)
    assert result["light"].backdrop == "blur(20px) saturate(150%)"


def test_lite_has_no_backdrop_and_clamped_alpha():
    result = derive(MERGED, "glass", lite=True)
    assert result["full"].backdrop is None
    assert result["light"].backdrop is None
    assert result["full"].fill == "rgba(28, 28, 30, 0.72)"


def test_lite_light_material_also_uses_the_opaque_base():
    result = derive(MERGED, "glass", lite=True)
    assert result["light"].fill == "rgba(28, 28, 30, 0.8)"


def test_full_alpha_below_the_floor_is_rejected():
    merged = {**MERGED, "material": {**MERGED["material"], "fill_alpha_glass": 0.05}}
    with pytest.raises(ValueError, match="below the 0.1 floor"):
        derive(merged, "glass", lite=False)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_materials.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glassbuild.materials'`

- [ ] **Step 3: Implement `glassbuild/materials.py`**

```python
"""Derivation of full, light, and lite material values from the tuning table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from glassbuild.color import parse_rgba, rgba_str

LITE_FILL_ALPHA = 0.72
FULL_FILL_ALPHA_FLOOR = 0.10
LIGHT_ALPHA_BONUS = 0.08


@dataclass(frozen=True)
class Material:
    """One rendered material: its fill, its rim, and its backdrop filter."""

    fill: str
    rim: str
    backdrop: str | None


_ALPHA_KEY = {"glass": "fill_alpha_glass", "frosted-glass": "fill_alpha_frosted"}


def derive(merged: dict[str, Any], material_key: str, lite: bool) -> dict[str, Material]:
    """Build the full and light materials for one material/mode combination."""
    spec = merged["material"]
    blur = int(spec["blur_px"])
    saturate = int(spec["saturate_pct"])
    rim_r, rim_g, rim_b = spec["rim_rgb"]
    rim = rgba_str(rim_r, rim_g, rim_b, float(spec["rim_alpha"]))

    if lite:
        base_r, base_g, base_b, _ = parse_rgba(merged["palette"]["opaque_surface"])
        full_alpha = LITE_FILL_ALPHA
    else:
        base_r, base_g, base_b = spec["fill_rgb"]
        full_alpha = float(spec[_ALPHA_KEY[material_key]])
        if full_alpha < FULL_FILL_ALPHA_FLOOR:
            raise ValueError(
                f"fill alpha {full_alpha} for {material_key} is below the "
                f"{FULL_FILL_ALPHA_FLOOR} floor"
            )

    light_alpha = min(1.0, full_alpha + LIGHT_ALPHA_BONUS)

    return {
        "full": Material(
            fill=rgba_str(base_r, base_g, base_b, full_alpha),
            rim=rim,
            backdrop=None if lite else f"blur({blur}px) saturate({saturate}%)",
        ),
        "light": Material(
            fill=rgba_str(base_r, base_g, base_b, light_alpha),
            rim=rim,
            backdrop=None if lite else f"blur({blur // 2}px) saturate({saturate}%)",
        ),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_materials.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add glassbuild/materials.py tests/test_materials.py
git commit -m "feat: derive full, light, and lite materials from tuning table"
```

---

### Task 5: Home Assistant variable mapping

**Files:**
- Create: `glassbuild/variables.py`
- Test: `tests/test_variables.py`

**Interfaces:**
- Consumes: `Material` and `derive` from Task 4
- Produces: `build_variables(merged: dict, materials: dict[str, Material]) -> dict[str, str]` — the flat HA theme variable map for one entry

- [ ] **Step 1: Write the failing tests**

`tests/test_variables.py`:

```python
from glassbuild.materials import Material, derive
from glassbuild.variables import build_variables

MERGED = {
    "radius": {"card": "18px", "dialog": "28px", "control": "12px", "pill": "980px"},
    "shadow": "0 1px 2px rgba(0, 0, 0, 0.04), 0 8px 32px rgba(0, 0, 0, 0.12)",
    "font": {
        "stack": '-apple-system, system-ui, sans-serif',
        "tracking_headline": "-0.4px",
        "tracking_body": "-0.2px",
    },
    "motion": {"duration": "300ms", "easing": "cubic-bezier(0.25, 0.1, 0.25, 1)"},
    "material": {
        "name": "Glass",
        "blur_px": 8,
        "saturate_pct": 180,
        "rim_alpha": 0.45,
        "fill_rgb": [255, 255, 255],
        "fill_alpha_glass": 0.14,
        "fill_alpha_frosted": 0.45,
        "rim_rgb": [255, 255, 255],
    },
    "palette": {
        "accent": "#0A84FF",
        "success": "#30D158",
        "warning": "#FF9F0A",
        "error": "#FF453A",
        "scene": "#BF5AF2",
        "text_primary": "#FFFFFF",
        "text_secondary": "#EBEBF599",
        "text_disabled": "#EBEBF561",
        "divider": "rgba(84, 84, 88, 0.65)",
        "opaque_surface": "#1C1C1E",
        "background_from": "#101014",
        "background_via": "#16161C",
        "background_to": "#1B1620",
    },
}


def _vars(lite: bool = False) -> dict[str, str]:
    return build_variables(MERGED, derive(MERGED, "glass", lite=lite))


def test_every_value_is_a_string():
    for key, value in _vars().items():
        assert isinstance(key, str), key
        assert isinstance(value, str), key


def test_no_key_starts_with_double_dash():
    assert not [k for k in _vars() if k.startswith("--")]


def test_core_palette_is_mapped():
    v = _vars()
    assert v["primary-color"] == "#0A84FF"
    assert v["accent-color"] == "#0A84FF"
    assert v["primary-text-color"] == "#FFFFFF"
    assert v["error-color"] == "#FF453A"


def test_card_uses_the_full_material():
    v = _vars()
    assert v["ha-card-background"] == "rgba(255, 255, 255, 0.14)"
    assert v["ha-card-backdrop-filter"] == "blur(8px) saturate(180%)"
    assert v["ha-card-border-radius"] == "18px"
    assert v["ha-card-border-color"] == "rgba(255, 255, 255, 0.45)"
    assert v["ha-card-box-shadow"].startswith("0 1px 2px")


def test_dialog_uses_the_native_backdrop_variable():
    v = _vars()
    assert v["ha-dialog-surface-backdrop-filter"] == "blur(8px) saturate(180%)"
    assert v["ha-dialog-border-radius"] == "28px"


def test_dense_surfaces_are_opaque():
    v = _vars()
    assert v["code-editor-background-color"] == "#1C1C1E"
    assert v["data-table-background-color"] == "#1C1C1E"
    assert v["markdown-code-background-color"] == "#1C1C1E"


def test_controls_use_the_light_material():
    v = _vars()
    assert v["input-fill-color"] == "rgba(255, 255, 255, 0.22)"
    assert v["mdc-text-field-fill-color"] == "rgba(255, 255, 255, 0.22)"


def test_background_is_a_gradient():
    v = _vars()
    assert "gradient" in v["lovelace-background"]
    assert "#101014" in v["lovelace-background"]


def test_lite_omits_every_backdrop_filter_key():
    v = _vars(lite=True)
    assert "ha-card-backdrop-filter" not in v
    assert "ha-dialog-surface-backdrop-filter" not in v
    assert not [val for val in v.values() if "backdrop-filter" in val]


def test_lite_still_defines_the_card_background():
    v = _vars(lite=True)
    assert v["ha-card-background"] == "rgba(28, 28, 30, 0.72)"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_variables.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glassbuild.variables'`

- [ ] **Step 3: Implement `glassbuild/variables.py`**

```python
"""Mapping of merged tokens onto Home Assistant theme variable names.

Keys are written without the leading ``--``; Home Assistant adds it.
Surfaces are grouped per the spec: full material on cards and dialogs, light
material on controls, opaque on dense reading surfaces.
"""

from __future__ import annotations

from typing import Any

from glassbuild.materials import Material


def build_variables(
    merged: dict[str, Any], materials: dict[str, Material]
) -> dict[str, str]:
    """Build the flat HA theme variable map for a single entry."""
    palette = merged["palette"]
    radius = merged["radius"]
    font = merged["font"]
    motion = merged["motion"]
    full = materials["full"]
    light = materials["light"]

    opaque = palette["opaque_surface"]

    variables: dict[str, str] = {
        # ---- core palette -------------------------------------------------
        "primary-color": palette["accent"],
        "accent-color": palette["accent"],
        "dark-primary-color": palette["accent"],
        "light-primary-color": palette["accent"],
        "primary-text-color": palette["text_primary"],
        "secondary-text-color": palette["text_secondary"],
        "text-primary-color": palette["text_primary"],
        "disabled-text-color": palette["text_disabled"],
        "divider-color": palette["divider"],
        "error-color": palette["error"],
        "warning-color": palette["warning"],
        "success-color": palette["success"],
        "info-color": palette["accent"],
        # ---- backgrounds --------------------------------------------------
        "primary-background-color": opaque,
        "secondary-background-color": opaque,
        "card-background-color": full.fill,
        "lovelace-background": (
            f"linear-gradient(160deg, {palette['background_from']} 0%, "
            f"{palette['background_via']} 52%, {palette['background_to']} 100%)"
        ),
        # ---- cards: full material ------------------------------------------
        "ha-card-background": full.fill,
        "ha-card-border-radius": radius["card"],
        "ha-card-border-width": "1px",
        "ha-card-border-color": full.rim,
        "ha-card-box-shadow": merged["shadow"],
        # ---- dialogs: full material ----------------------------------------
        "ha-dialog-surface-background": full.fill,
        "ha-dialog-border-radius": radius["dialog"],
        "ha-dialog-scrim-color": "rgba(0, 0, 0, 0.32)",
        "mdc-dialog-scrim-color": "rgba(0, 0, 0, 0.32)",
        # ---- header and sidebar --------------------------------------------
        "app-header-background-color": full.fill,
        "app-header-text-color": palette["text_primary"],
        "sidebar-background-color": full.fill,
        "sidebar-icon-color": palette["text_secondary"],
        "sidebar-text-color": palette["text_primary"],
        "sidebar-selected-icon-color": palette["accent"],
        "sidebar-selected-text-color": palette["accent"],
        # ---- controls: light material --------------------------------------
        "input-fill-color": light.fill,
        "input-ideal-fill-color": light.fill,
        "input-label-ink-color": palette["text_secondary"],
        "input-dropdown-icon-color": palette["text_secondary"],
        "mdc-text-field-fill-color": light.fill,
        "mdc-select-fill-color": light.fill,
        "mdc-theme-primary": palette["accent"],
        "mdc-theme-secondary": palette["accent"],
        "mdc-theme-surface": opaque,
        "mdc-theme-on-surface": palette["text_primary"],
        "switch-checked-color": palette["accent"],
        "switch-unchecked-color": palette["text_disabled"],
        "slider-color": palette["accent"],
        "slider-secondary-color": light.fill,
        "paper-item-icon-color": palette["text_secondary"],
        "paper-item-icon-active-color": palette["accent"],
        "paper-listbox-background-color": opaque,
        "state-icon-color": palette["text_secondary"],
        "state-icon-active-color": palette["warning"],
        # ---- dense reading surfaces: opaque --------------------------------
        "table-row-background-color": opaque,
        "table-row-alternative-background-color": opaque,
        "data-table-background-color": opaque,
        "code-editor-background-color": opaque,
        "markdown-code-background-color": opaque,
        # ---- charts ---------------------------------------------------------
        "energy-grid-consumption-color": palette["accent"],
        "energy-grid-return-color": palette["success"],
        "energy-solar-color": palette["warning"],
        "energy-battery-in-color": palette["scene"],
        "energy-battery-out-color": palette["success"],
        "history-unavailable-color": palette["text_disabled"],
        # ---- scrollbars, type, motion ---------------------------------------
        "scrollbar-thumb-color": palette["divider"],
        "primary-font-family": font["stack"],
        "paper-font-common-base_-_font-family": font["stack"],
        "paper-font-body1_-_font-family": font["stack"],
        "paper-font-headline_-_letter-spacing": font["tracking_headline"],
        "paper-font-body1_-_letter-spacing": font["tracking_body"],
        "ha-transition-duration": motion["duration"],
        "ha-transition-easing": motion["easing"],
        "control-border-radius": radius["control"],
        "ha-chip-border-radius": radius["pill"],
    }

    if full.backdrop is not None:
        variables["ha-card-backdrop-filter"] = full.backdrop
        variables["ha-dialog-surface-backdrop-filter"] = full.backdrop

    return variables
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_variables.py -v`
Expected: PASS — 10 passed

- [ ] **Step 5: Commit**

```bash
git add glassbuild/variables.py tests/test_variables.py
git commit -m "feat: map tokens onto Home Assistant theme variables"
```

---

### Task 6: card-mod injection block

**Files:**
- Create: `glassbuild/cardmod.py`
- Test: `tests/test_cardmod.py`

**Interfaces:**
- Consumes: `Material` from Task 4
- Produces: `build_cardmod(entry_name: str, materials: dict[str, Material]) -> dict[str, str]` — returns `{}` for Lite, otherwise `card-mod-theme` plus `card-mod-root-yaml`

- [ ] **Step 1: Write the failing tests**

`tests/test_cardmod.py`:

```python
import yaml

from glassbuild.cardmod import build_cardmod
from glassbuild.materials import Material

FULL = Material(
    fill="rgba(255, 255, 255, 0.14)",
    rim="rgba(255, 255, 255, 0.45)",
    backdrop="blur(8px) saturate(180%)",
)
LITE = Material(fill="rgba(28, 28, 30, 0.72)", rim="rgba(255, 255, 255, 0.45)", backdrop=None)


def test_lite_produces_no_cardmod_keys():
    assert build_cardmod("Glass Lite", {"full": LITE, "light": LITE}) == {}


def test_theme_name_is_echoed():
    block = build_cardmod("Glass", {"full": FULL, "light": FULL})
    assert block["card-mod-theme"] == "Glass"


def test_root_yaml_is_valid_yaml():
    block = build_cardmod("Glass", {"full": FULL, "light": FULL})
    assert isinstance(yaml.safe_load(block["card-mod-root-yaml"]), dict)


def test_root_yaml_covers_the_non_native_surfaces():
    block = build_cardmod("Glass", {"full": FULL, "light": FULL})
    css = block["card-mod-root-yaml"]
    for selector in ("ha-sidebar", ".header", "ha-tabs", "ha-more-info-dialog"):
        assert selector in css


def test_root_yaml_carries_the_backdrop_filter():
    block = build_cardmod("Glass", {"full": FULL, "light": FULL})
    assert "blur(8px) saturate(180%)" in block["card-mod-root-yaml"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_cardmod.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glassbuild.cardmod'`

- [ ] **Step 3: Implement `glassbuild/cardmod.py`**

```python
"""card-mod CSS injection for surfaces with no native backdrop-filter hook.

Home Assistant natively supports ``--ha-card-backdrop-filter`` and
``--ha-dialog-surface-backdrop-filter``. Everything else -- header, sidebar,
tabs, menus, tooltips, toasts, quick bar -- needs card-mod. The ``$`` suffix
in card-mod selectors pierces a shadow root.
"""

from __future__ import annotations

from glassbuild.materials import Material

_ROOT_TEMPLATE = """\
ha-drawer$: |
  ha-sidebar {{
    backdrop-filter: {backdrop};
    -webkit-backdrop-filter: {backdrop};
    background: {fill};
    border-right: 1px solid {rim};
  }}
ha-panel-lovelace$ hui-root$: |
  .header {{
    backdrop-filter: {backdrop};
    -webkit-backdrop-filter: {backdrop};
    background: {fill};
    border-bottom: 1px solid {rim};
  }}
  ha-tabs {{
    background: transparent;
  }}
ha-more-info-dialog$: |
  .content {{
    background: transparent;
  }}
"""


def build_cardmod(entry_name: str, materials: dict[str, Material]) -> dict[str, str]:
    """Build the card-mod block for one entry. Returns ``{}`` for Lite entries."""
    full = materials["full"]
    if full.backdrop is None:
        return {}

    return {
        "card-mod-theme": entry_name,
        "card-mod-root-yaml": _ROOT_TEMPLATE.format(
            backdrop=full.backdrop,
            fill=full.fill,
            rim=full.rim,
        ),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_cardmod.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: Verify the selectors against card-mod's documentation**

The shadow-root paths above follow card-mod's documented `element$: |` syntax, but the exact
element nesting changes with Home Assistant frontend releases and cannot be confirmed from
the Python tests alone. Open
<https://github.com/thomasloven/lovelace-card-mod/blob/master/README.md> and confirm each of
`ha-drawer`, `ha-panel-lovelace`, `hui-root`, and `ha-more-info-dialog` is still the correct
path for header, sidebar, tabs, and dialog styling. Adjust `_ROOT_TEMPLATE` and the selector
list in `test_root_yaml_covers_the_non_native_surfaces` together if anything has moved.

Record the outcome in the commit message. This is re-verified visually in Task 11.

- [ ] **Step 6: Commit**

```bash
git add glassbuild/cardmod.py tests/test_cardmod.py
git commit -m "feat: add card-mod injection for non-native surfaces"
```

---

### Task 7: Entry assembly

**Files:**
- Create: `glassbuild/emit.py`
- Test: `tests/test_emit.py`

**Interfaces:**
- Consumes: `load_tokens`, `merge`, `MATERIALS`, `MODES` (Task 2); `derive` (Task 4); `build_variables` (Task 5); `build_cardmod` (Task 6)
- Produces:
  - `ENTRY_NAMES: tuple[str, ...]` — all twelve names, in matrix order
  - `build_themes(root: Path) -> dict[str, dict]` — the complete theme document

Auto entries carry shared variables at the top level plus a `modes` key holding the light and dark payloads. Light and Dark entries are flat, with no `modes` key.

- [ ] **Step 1: Write the failing tests**

`tests/test_emit.py`:

```python
from pathlib import Path

import pytest

from glassbuild.emit import ENTRY_NAMES, build_themes

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def themes():
    return build_themes(ROOT)


def test_all_twelve_names_present():
    assert len(ENTRY_NAMES) == 12
    assert ENTRY_NAMES == (
        "Glass",
        "Glass Light",
        "Glass Dark",
        "Glass Lite",
        "Glass Light Lite",
        "Glass Dark Lite",
        "Frosted Glass",
        "Frosted Glass Light",
        "Frosted Glass Dark",
        "Frosted Glass Lite",
        "Frosted Glass Light Lite",
        "Frosted Glass Dark Lite",
    )


def test_document_contains_exactly_those_entries(themes):
    assert set(themes) == set(ENTRY_NAMES)


@pytest.mark.parametrize("name", ["Glass", "Frosted Glass", "Glass Lite"])
def test_auto_entries_have_a_modes_block(themes, name):
    assert set(themes[name]["modes"]) == {"light", "dark"}


@pytest.mark.parametrize(
    "name", ["Glass Light", "Glass Dark", "Frosted Glass Light", "Glass Dark Lite"]
)
def test_flat_entries_have_no_modes_block(themes, name):
    assert "modes" not in themes[name]


def test_auto_light_payload_matches_the_flat_light_entry(themes):
    auto_light = themes["Glass"]["modes"]["light"]
    flat = {k: v for k, v in themes["Glass Light"].items() if k != "modes"}
    for key, value in auto_light.items():
        assert flat[key] == value, key


def test_lite_entries_have_no_cardmod_keys(themes):
    for name in ENTRY_NAMES:
        if not name.endswith("Lite"):
            continue
        assert "card-mod-theme" not in themes[name]
        assert "card-mod-root-yaml" not in themes[name]


def test_full_entries_have_cardmod_keys(themes):
    assert themes["Glass"]["card-mod-theme"] == "Glass"
    assert themes["Frosted Glass Dark"]["card-mod-theme"] == "Frosted Glass Dark"


def test_frosted_uses_its_own_blur(themes):
    assert "blur(40px)" in themes["Frosted Glass Dark"]["ha-card-backdrop-filter"]
    assert "blur(8px)" in themes["Glass Dark"]["ha-card-backdrop-filter"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_emit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glassbuild.emit'`

- [ ] **Step 3: Implement `glassbuild/emit.py`**

```python
"""Assembly of the twelve theme entries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from glassbuild.cardmod import build_cardmod
from glassbuild.materials import derive
from glassbuild.tokens import MATERIALS, load_tokens, merge
from glassbuild.variables import build_variables

_LABEL = {"glass": "Glass", "frosted-glass": "Frosted Glass"}


def _entry_names() -> tuple[str, ...]:
    names: list[str] = []
    for material in MATERIALS:
        label = _LABEL[material]
        for suffix in ("", " Lite"):
            names.append(f"{label}{suffix}")
            names.append(f"{label} Light{suffix}")
            names.append(f"{label} Dark{suffix}")
    return tuple(names)


ENTRY_NAMES: tuple[str, ...] = _entry_names()


def _payload(tokens: dict[str, Any], material: str, mode: str, lite: bool) -> dict[str, str]:
    merged = merge(tokens["base"], tokens["materials"][material], tokens["modes"][mode])
    return build_variables(merged, derive(merged, material, lite=lite))


def build_themes(root: Path) -> dict[str, dict[str, Any]]:
    """Build the complete theme document: twelve entries keyed by display name."""
    tokens = load_tokens(root)
    themes: dict[str, dict[str, Any]] = {}

    for material in MATERIALS:
        label = _LABEL[material]
        for lite in (False, True):
            suffix = " Lite" if lite else ""
            light = _payload(tokens, material, "light", lite)
            dark = _payload(tokens, material, "dark", lite)

            auto_name = f"{label}{suffix}"
            shared = {k: v for k, v in dark.items() if light.get(k) == v}
            auto: dict[str, Any] = dict(shared)
            auto.update(build_cardmod(auto_name, derive(
                merge(tokens["base"], tokens["materials"][material], tokens["modes"]["dark"]),
                material,
                lite=lite,
            )))
            auto["modes"] = {
                "light": {k: v for k, v in light.items() if k not in shared},
                "dark": {k: v for k, v in dark.items() if k not in shared},
            }
            themes[auto_name] = auto

            for mode_label, payload, mode_key in (
                ("Light", light, "light"),
                ("Dark", dark, "dark"),
            ):
                name = f"{label} {mode_label}{suffix}"
                entry: dict[str, Any] = dict(payload)
                entry.update(build_cardmod(name, derive(
                    merge(
                        tokens["base"],
                        tokens["materials"][material],
                        tokens["modes"][mode_key],
                    ),
                    material,
                    lite=lite,
                )))
                themes[name] = entry

    return themes
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_emit.py -v`
Expected: PASS — 14 passed

- [ ] **Step 5: Commit**

```bash
git add glassbuild/emit.py tests/test_emit.py
git commit -m "feat: assemble twelve theme entries with modes wrapping"
```

---

### Task 8: Validation

**Files:**
- Create: `glassbuild/validate.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `ENTRY_NAMES` from Task 7
- Produces:
  - `REQUIRED_VARIABLES: frozenset[str]`
  - `HA_BUILTIN_VARIABLES: frozenset[str]`
  - `validate(themes: dict) -> list[str]` — returns human-readable problems; empty list means valid

Checks: all twelve entries present; required variables defined in every entry (counting `modes` payloads); no `var(--x)` reference to an undefined, non-builtin variable; every value a string except the `modes` key; no `backdrop-filter` anywhere in a Lite entry.

- [ ] **Step 1: Write the failing tests**

`tests/test_validate.py`:

```python
from pathlib import Path

import pytest

from glassbuild.emit import build_themes
from glassbuild.validate import REQUIRED_VARIABLES, validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def themes():
    return build_themes(ROOT)


def test_the_real_themes_validate_clean(themes):
    assert validate(themes) == []


def test_missing_entry_is_reported(themes):
    broken = dict(themes)
    del broken["Glass Dark"]
    problems = validate(broken)
    assert any("Glass Dark" in p and "missing" in p for p in problems)


def test_missing_required_variable_is_reported(themes):
    broken = {name: dict(entry) for name, entry in themes.items()}
    some_required = sorted(REQUIRED_VARIABLES)[0]
    broken["Glass Dark"].pop(some_required, None)
    broken["Glass Dark"].pop("modes", None)
    assert any(some_required in p for p in validate(broken))


def test_dangling_var_reference_is_reported(themes):
    broken = {name: dict(entry) for name, entry in themes.items()}
    broken["Glass Dark"]["ha-card-background"] = "var(--nope-not-defined)"
    assert any("nope-not-defined" in p for p in validate(broken))


def test_var_reference_to_a_defined_token_is_accepted(themes):
    ok = {name: dict(entry) for name, entry in themes.items()}
    ok["Glass Dark"]["ha-card-background"] = "var(--primary-color)"
    assert validate(ok) == []


def test_backdrop_filter_in_a_lite_entry_is_reported(themes):
    broken = {name: dict(entry) for name, entry in themes.items()}
    broken["Glass Dark Lite"]["ha-card-backdrop-filter"] = "blur(8px)"
    assert any("Glass Dark Lite" in p and "backdrop-filter" in p for p in validate(broken))


def test_cardmod_backdrop_in_a_lite_entry_is_reported(themes):
    broken = {name: dict(entry) for name, entry in themes.items()}
    broken["Glass Lite"]["card-mod-root-yaml"] = "x: |\n  .a { backdrop-filter: blur(1px); }\n"
    assert any("Glass Lite" in p and "backdrop-filter" in p for p in validate(broken))


def test_non_string_value_is_reported(themes):
    broken = {name: dict(entry) for name, entry in themes.items()}
    broken["Glass Dark"]["ha-card-border-width"] = 1
    assert any("ha-card-border-width" in p for p in validate(broken))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glassbuild.validate'`

- [ ] **Step 3: Implement `glassbuild/validate.py`**

```python
"""Structural validation of the generated theme document.

An undefined ``var()`` in a Home Assistant theme fails silently at runtime --
the surface renders transparent or black with no error anywhere. This module
turns that class of failure into a build error.
"""

from __future__ import annotations

import re
from typing import Any

from glassbuild.emit import ENTRY_NAMES

_VAR_RE = re.compile(r"var\(\s*--([a-zA-Z0-9_-]+)")

REQUIRED_VARIABLES: frozenset[str] = frozenset(
    {
        "primary-color",
        "accent-color",
        "primary-text-color",
        "secondary-text-color",
        "divider-color",
        "primary-background-color",
        "card-background-color",
        "ha-card-background",
        "ha-card-border-radius",
        "ha-card-box-shadow",
        "app-header-background-color",
        "sidebar-background-color",
        "lovelace-background",
    }
)

HA_BUILTIN_VARIABLES: frozenset[str] = frozenset(
    {
        "primary-color",
        "accent-color",
        "primary-text-color",
        "secondary-text-color",
        "primary-background-color",
        "secondary-background-color",
        "card-background-color",
        "divider-color",
        "disabled-text-color",
    }
)


def _flatten(entry: dict[str, Any]) -> dict[str, Any]:
    """Merge an entry's top level with both mode payloads into one namespace."""
    flat = {k: v for k, v in entry.items() if k != "modes"}
    for payload in (entry.get("modes") or {}).values():
        flat.update(payload)
    return flat


def _iter_values(entry: dict[str, Any]):
    for key, value in entry.items():
        if key == "modes":
            for payload in (value or {}).values():
                yield from payload.items()
        else:
            yield key, value


def validate(themes: dict[str, Any]) -> list[str]:
    """Return a list of problems. An empty list means the document is valid."""
    problems: list[str] = []

    for name in ENTRY_NAMES:
        if name not in themes:
            problems.append(f"{name}: entry is missing from the document")

    for name, entry in themes.items():
        flat = _flatten(entry)
        is_lite = name.endswith("Lite")

        for required in sorted(REQUIRED_VARIABLES):
            if required not in flat:
                problems.append(f"{name}: required variable {required!r} is not defined")

        for key, value in _iter_values(entry):
            if not isinstance(key, str):
                problems.append(f"{name}: non-string key {key!r}")
                continue
            if not isinstance(value, str):
                problems.append(
                    f"{name}: value of {key!r} is {type(value).__name__}, expected str"
                )
                continue
            if key.startswith("--"):
                problems.append(f"{name}: key {key!r} must not start with '--'")
            for reference in _VAR_RE.findall(value):
                if reference not in flat and reference not in HA_BUILTIN_VARIABLES:
                    problems.append(
                        f"{name}: {key!r} references undefined variable "
                        f"'--{reference}'"
                    )
            if is_lite and "backdrop-filter" in f"{key} {value}":
                problems.append(
                    f"{name}: Lite entry must not contain backdrop-filter "
                    f"(found in {key!r})"
                )

    return problems
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_validate.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add glassbuild/validate.py tests/test_validate.py
git commit -m "feat: add dangling-var, Lite purity, and shape validation"
```

---

### Task 9: Build CLI and generated theme file

**Files:**
- Create: `scripts/build_themes.py`, `themes/glass.yaml` (generated)
- Test: `tests/test_build_cli.py`

**Interfaces:**
- Consumes: `build_themes` (Task 7), `validate` (Task 8)
- Produces:
  - `render(themes: dict) -> str` — deterministic YAML text with a generated-file header
  - `main(argv: list[str] | None = None) -> int` — exit 0 on success, 1 on drift or validation failure

- [ ] **Step 1: Write the failing tests**

`tests/test_build_cli.py`:

```python
import subprocess
import sys
from pathlib import Path

import yaml

from glassbuild.emit import ENTRY_NAMES, build_themes

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_themes.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_check_passes_against_the_committed_file():
    result = _run("--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_render_is_deterministic():
    from scripts.build_themes import render

    assert render(build_themes(ROOT)) == render(build_themes(ROOT))


def test_committed_file_parses_and_has_twelve_entries():
    document = yaml.safe_load((ROOT / "themes" / "glass.yaml").read_text())
    assert set(document) == set(ENTRY_NAMES)


def test_check_fails_when_the_file_drifts(tmp_path):
    target = ROOT / "themes" / "glass.yaml"
    original = target.read_text()
    try:
        target.write_text(original + "\nGlass Drifted:\n  primary-color: '#000000'\n")
        assert _run("--check").returncode == 1
    finally:
        target.write_text(original)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_build_cli.py -v`
Expected: FAIL — the script does not exist

- [ ] **Step 3: Implement `scripts/build_themes.py`**

```python
#!/usr/bin/env python3
"""Generate ``themes/glass.yaml`` from the token sources.

Usage:
    python scripts/build_themes.py            # write the file
    python scripts/build_themes.py --check    # fail if the committed file drifts
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from glassbuild.emit import build_themes  # noqa: E402
from glassbuild.validate import validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "themes" / "glass.yaml"

HEADER = """\
# GENERATED FILE -- DO NOT EDIT.
# Produced by scripts/build_themes.py from the token sources in tokens/.
# Edit the tokens and re-run the generator instead.
"""


def render(themes: dict) -> str:
    """Render the theme document as deterministic YAML text."""
    body = yaml.safe_dump(
        themes,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        width=100,
    )
    return HEADER + body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed file matches the tokens; do not write",
    )
    args = parser.parse_args(argv)

    themes = build_themes(ROOT)

    problems = validate(themes)
    if problems:
        print("Theme validation failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    rendered = render(themes)

    if args.check:
        if not OUTPUT.is_file():
            print(f"{OUTPUT} does not exist; run the generator", file=sys.stderr)
            return 1
        current = OUTPUT.read_text()
        if current != rendered:
            print(f"{OUTPUT} is out of date with tokens/:", file=sys.stderr)
            diff = difflib.unified_diff(
                current.splitlines(keepends=True),
                rendered.splitlines(keepends=True),
                fromfile="committed",
                tofile="generated",
            )
            sys.stderr.writelines(diff)
            return 1
        print(f"{OUTPUT} is up to date ({len(themes)} entries)")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered)
    print(f"wrote {OUTPUT} ({len(themes)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Generate the theme file**

Run: `python scripts/build_themes.py`
Expected: `wrote /Volumes/Documents/code/hass-glass-theme/themes/glass.yaml (12 entries)`

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_build_cli.py -v`
Expected: PASS — 4 passed

- [ ] **Step 6: Lint the generated file**

Run: `python -m yamllint themes/`
Expected: no output, exit code 0

If yamllint objects to the generated formatting, adjust `.yamllint.yml` rather than
hand-editing `themes/glass.yaml` — that file is generated and any manual edit will be
reverted by the next build and caught by `--check`.

- [ ] **Step 7: Commit**

```bash
git add scripts/build_themes.py themes/glass.yaml tests/test_build_cli.py
git commit -m "feat: add build CLI and generate themes/glass.yaml"
```

---

### Task 10: Contrast and round-trip test suites

**Files:**
- Create: `tests/test_contrast.py`, `tests/test_roundtrip.py`

**Interfaces:**
- Consumes: `composite`, `parse_rgba`, `contrast_ratio` (Task 1); `build_themes`, `ENTRY_NAMES` (Task 7)
- Produces: no importable API — these are the spec's acceptance tests

- [ ] **Step 1: Write the contrast tests**

`tests/test_contrast.py`:

```python
"""WCAG AA contrast checks for every entry.

Text sits on the card fill, which sits on the dashboard gradient. The gradient
is approximated by its darkest and lightest stops; body text must clear 4.5:1
against both, so the check holds wherever on the gradient a card lands.
"""

from pathlib import Path

import pytest

from glassbuild.color import composite, contrast_ratio, parse_rgba
from glassbuild.emit import ENTRY_NAMES, build_themes
from glassbuild.tokens import MATERIALS, MODES, load_tokens, merge

ROOT = Path(__file__).resolve().parents[1]

BODY_MIN = 4.5
LARGE_MIN = 3.0


def _gradient_stops(mode: str) -> list[tuple[int, int, int, float]]:
    tokens = load_tokens(ROOT)
    palette = merge(tokens["base"], tokens["modes"][mode])["palette"]
    return [
        parse_rgba(palette[key])
        for key in ("background_from", "background_via", "background_to")
    ]


def _entry_payload(themes: dict, name: str, mode: str) -> dict[str, str]:
    entry = themes[name]
    flat = {k: v for k, v in entry.items() if k != "modes"}
    if "modes" in entry:
        flat.update(entry["modes"][mode])
    return flat


def _mode_for(name: str) -> list[str]:
    if " Light" in name:
        return ["light"]
    if " Dark" in name:
        return ["dark"]
    return list(MODES)


@pytest.fixture(scope="module")
def themes():
    return build_themes(ROOT)


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_body_text_clears_wcag_aa(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        card = parse_rgba(payload["ha-card-background"])
        text = parse_rgba(payload["primary-text-color"])
        for stop in _gradient_stops(mode):
            surface = composite(card, stop)
            composited_text = composite(text, surface)
            ratio = contrast_ratio(composited_text[:3], surface[:3])
            assert ratio >= BODY_MIN, (
                f"{name} ({mode}): primary text on card over {stop[:3]} "
                f"is {ratio:.2f}:1, need {BODY_MIN}:1"
            )


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_secondary_text_clears_large_text_minimum(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        card = parse_rgba(payload["ha-card-background"])
        text = parse_rgba(payload["secondary-text-color"])
        for stop in _gradient_stops(mode):
            surface = composite(card, stop)
            composited_text = composite(text, surface)
            ratio = contrast_ratio(composited_text[:3], surface[:3])
            assert ratio >= LARGE_MIN, (
                f"{name} ({mode}): secondary text is {ratio:.2f}:1, "
                f"need {LARGE_MIN}:1"
            )


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("material", MATERIALS)
def test_accent_clears_large_text_minimum_on_the_card(themes, material, mode):
    name = "Glass" if material == "glass" else "Frosted Glass"
    payload = _entry_payload(themes, name, mode)
    card = parse_rgba(payload["ha-card-background"])
    accent = parse_rgba(payload["primary-color"])
    for stop in _gradient_stops(mode):
        surface = composite(card, stop)
        ratio = contrast_ratio(composite(accent, surface)[:3], surface[:3])
        assert ratio >= LARGE_MIN, (
            f"{name} ({mode}): accent is {ratio:.2f}:1, need {LARGE_MIN}:1"
        )
```

- [ ] **Step 2: Run the contrast tests**

Run: `python -m pytest tests/test_contrast.py -v`
Expected: PASS — 28 passed

If a case fails, **fix the token values, not the threshold.** The usual remedy is raising
`fill_alpha_*` for the failing mode in `tokens/modes/*.yaml` so the card fill masks more of
the gradient, then re-running `python scripts/build_themes.py`. Lowering `BODY_MIN` defeats
the purpose of the test.

- [ ] **Step 3: Write the round-trip tests**

`tests/test_roundtrip.py`:

```python
"""The generated file must match what Home Assistant's theme loader accepts."""

from pathlib import Path

import pytest
import yaml

from glassbuild.emit import ENTRY_NAMES

ROOT = Path(__file__).resolve().parents[1]
THEME_FILE = ROOT / "themes" / "glass.yaml"


@pytest.fixture(scope="module")
def document():
    return yaml.safe_load(THEME_FILE.read_text())


def test_file_parses(document):
    assert isinstance(document, dict)


def test_exactly_the_twelve_entries(document):
    assert set(document) == set(ENTRY_NAMES)


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_entry_is_flat_apart_from_modes(document, name):
    for key, value in document[name].items():
        assert isinstance(key, str)
        if key == "modes":
            assert set(value) == {"light", "dark"}
            for payload in value.values():
                for mode_key, mode_value in payload.items():
                    assert isinstance(mode_key, str)
                    assert isinstance(mode_value, str)
        else:
            assert isinstance(value, str), f"{name}.{key} is {type(value).__name__}"


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_no_key_carries_the_css_prefix(document, name):
    assert not [k for k in document[name] if k.startswith("--")]


def test_generated_header_is_present():
    assert THEME_FILE.read_text().startswith("# GENERATED FILE")
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS — all tests green across every file

- [ ] **Step 5: Commit**

```bash
git add tests/test_contrast.py tests/test_roundtrip.py
git commit -m "test: add WCAG contrast and theme-loader round-trip suites"
```

---

### Task 11: HACS packaging, README, and demo dashboard

**Files:**
- Create: `hacs.json`, `README.md`, `LICENSE`, `demo/dashboard.yaml`

**Interfaces:**
- Consumes: the twelve entry names from Task 7
- Produces: nothing importable

- [ ] **Step 1: Create `hacs.json`**

```json
{
  "name": "Glass & Frosted Glass Themes",
  "content_in_root": false,
  "render_readme": true,
  "homeassistant": "2024.5.0"
}
```

The `homeassistant` floor is 2024.5.0 because `--ha-card-backdrop-filter` landed in that
release; on anything older the native layer silently does nothing.

- [ ] **Step 2: Create `demo/dashboard.yaml`**

```yaml
# Manual verification dashboard. Copy into a Lovelace view in raw config mode
# and step through all twelve entries in light and dark, with and without card-mod.
views:
  - title: Glass Demo
    type: sections
    sections:
      - type: grid
        cards:
          - type: entities
            title: Entities and controls
            entities:
              - input_boolean.demo_toggle
              - input_number.demo_slider
              - input_select.demo_dropdown
              - input_text.demo_text
          - type: tile
            entity: light.demo_light
            features:
              - type: light-brightness
          - type: button
            entity: script.demo_script
      - type: grid
        cards:
          - type: markdown
            title: Markdown and code
            content: |
              Body text on glass. Inline `code` and a block:

              ```yaml
              key: value
              ```
          - type: history-graph
            entities:
              - sensor.demo_temperature
          - type: statistic
            entity: sensor.demo_temperature
            stat_type: mean
      - type: grid
        cards:
          # Known failure mode: frontend#20725 puts dropdowns behind
          # picture-elements when ha-card-backdrop-filter is set. Open the
          # dropdown below on a non-Lite entry to check whether it is affected.
          - type: picture-elements
            image: /local/demo-floorplan.png
            elements:
              - type: state-badge
                entity: light.demo_light
                style:
                  top: 40%
                  left: 40%
          - type: logbook
            entities:
              - light.demo_light
```

- [ ] **Step 3: Create `LICENSE`**

Write an MIT licence text with copyright year 2026. Include the standard MIT permission and
warranty-disclaimer paragraphs verbatim.

- [ ] **Step 4: Write `README.md`**

The README must contain, as separate sections:

1. **What it is** — twelve entries, the entry matrix table from the Global Constraints above.
2. **Install** — HACS custom repository (category: Theme), then
   `themes: !include_dir_merge_named themes` in `configuration.yaml`, then restart, then
   pick the theme in user profile settings.
3. **card-mod is optional** — state plainly that cards and dialogs blur natively with no
   dependency, and that installing card-mod additionally blurs the header, sidebar, tabs,
   menus, tooltips, toasts, and quick bar.
4. **Known issue: dropdowns** — link
   <https://github.com/home-assistant/frontend/issues/20725> and
   <https://github.com/home-assistant/frontend/issues/26113>, describe both symptoms
   (dropdowns behind picture-elements cards; dropdowns escaping more-info dialogs), state
   that both are closed as not planned upstream, and give the remedy: switch to the
   matching Lite entry.
5. **Lite entries** — explain they contain no blur, are the fix for the dropdown issue and
   for sluggish wall tablets, and state plainly that they are **not** pixel-identical to
   their full twins: the fill is near-opaque at 0.72 alpha instead of blurred.
6. **Custom wallpaper** — show overriding `lovelace-background`, and warn that a busy photo
   can break text contrast because the shipped gradient is what the contrast tests are
   measured against.
7. **Contributing** — edit `tokens/`, run `python scripts/build_themes.py`, run
   `python -m pytest`, never hand-edit `themes/glass.yaml`.

- [ ] **Step 5: Verify the theme loads in real Home Assistant**

Copy `themes/glass.yaml` into a Home Assistant instance's `config/themes/`, add
`themes: !include_dir_merge_named themes` to `configuration.yaml`, restart, and confirm:

1. All twelve entries appear in the profile theme picker under the matrix names.
2. Cards and dialogs blur without card-mod installed.
3. With card-mod installed, header and sidebar blur too — this is the visual confirmation of
   the selectors verified against the docs in Task 6 Step 5. If a surface is unstyled, fix
   `_ROOT_TEMPLATE` in `glassbuild/cardmod.py` and re-run the generator.
4. Lite entries show no blur anywhere and remain readable.
5. Load `demo/dashboard.yaml` and open the picture-elements dropdown to check the
   frontend#20725 symptom.

Record what you observed, including anything that did not work, in the commit message.

- [ ] **Step 6: Commit**

```bash
git add hacs.json README.md LICENSE demo/
git commit -m "docs: add HACS manifest, README, licence, and demo dashboard"
```

---

### Task 12: CI and release workflows

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.github/dependabot.yml`

**Interfaces:**
- Consumes: `scripts/build_themes.py --check` (Task 9), the pytest suite (Tasks 1-10)
- Produces: nothing importable

- [ ] **Step 1: Resolve the action SHAs**

Every third-party action must be pinned to a commit SHA, never a tag. Resolve each with:

```bash
gh api repos/actions/checkout/commits/v4 --jq .sha
gh api repos/actions/setup-python/commits/v5 --jq .sha
gh api repos/hacs/action/commits/main --jq .sha
gh api repos/softprops/action-gh-release/commits/v2 --jq .sha
```

Substitute the results for the `<SHA-...>` placeholders in the next two steps. Leave the
`# vN` trailing comments so Dependabot can still track the version.

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<SHA-checkout>  # v4
      - uses: actions/setup-python@<SHA-setup-python>  # v5
        with:
          python-version: "3.11"
      - run: pip install yamllint
      - run: yamllint tokens/ themes/ demo/ .github/
      - name: Install actionlint
        run: |
          bash <(curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash)
      - run: ./actionlint -color

  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<SHA-checkout>  # v4
      - uses: actions/setup-python@<SHA-setup-python>  # v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - name: Fail if themes/glass.yaml drifts from tokens/
        run: python scripts/build_themes.py --check

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@<SHA-checkout>  # v4
      - uses: actions/setup-python@<SHA-setup-python>  # v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: python -m pytest -v

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<SHA-checkout>  # v4
      - uses: hacs/action@<SHA-hacs-action>  # main
        with:
          category: theme
```

The `validate` job from the spec is folded into `test`: `validate()` runs both as a unit
suite (`tests/test_validate.py`) and as a hard gate inside `build_themes.py --check`, so a
third job invoking the same function would add CI time without adding coverage.

- [ ] **Step 3: Create `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<SHA-checkout>  # v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@<SHA-setup-python>  # v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"

      - name: Verify the tagged tree is buildable and valid
        run: |
          python scripts/build_themes.py --check
          python -m pytest -q

      - name: Package the themes
        run: |
          mkdir -p dist
          zip -j dist/hass-glass-theme.zip themes/glass.yaml

      - name: Publish the release
        uses: softprops/action-gh-release@<SHA-gh-release>  # v2
        with:
          files: dist/hass-glass-theme.zip
          generate_release_notes: true
          fail_on_unmatched_files: true
```

- [ ] **Step 4: Create `.github/dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: weekly
    commit-message:
      prefix: "ci"
  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
    commit-message:
      prefix: "build"
```

- [ ] **Step 5: Validate the workflows locally**

Run:

```bash
python -m yamllint .github/
bash <(curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash) \
  && ./actionlint -color
```

Expected: both clean. Confirm no `uses:` line references a tag or `@main` rather than a SHA:

```bash
grep -rn "uses:" .github/workflows/ | grep -v "@[0-9a-f]\{40\}"
```

Expected: no output.

- [ ] **Step 6: Run the whole suite once more**

Run: `python -m pytest -v && python scripts/build_themes.py --check`
Expected: all tests pass, and the generator reports the file is up to date.

- [ ] **Step 7: Commit**

```bash
rm -f actionlint
git add .github/
git commit -m "ci: add lint, drift, test, and HACS workflows plus release automation"
```

- [ ] **Step 8: Push and confirm CI is green**

```bash
git push -u origin main
gh run watch
```

Expected: all four `ci.yml` jobs pass. Do not treat this task as complete until the run is
green — a workflow that has never executed is not verified.

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: colour maths and contrast → Tasks 1
and 10; token generator and merge → Tasks 2-4; twelve-entry matrix and `modes` wrapping →
Task 7; native `ha-card-backdrop-filter` and `ha-dialog-surface-backdrop-filter` → Task 5;
card-mod for non-native surfaces → Task 6; Lite purity → Tasks 4, 5, 6, and 8; single
`themes/glass.yaml` → Task 9; dangling-var and shape validation → Task 8; round-trip → Task
10; HACS packaging, README caveats, demo dashboard → Task 11; CI, release, Dependabot,
SHA pinning → Task 12.

**Two deliberate departures from the spec, both narrowing duplicated work rather than
dropping scope:**

1. The spec lists `validate` as a fourth CI job. It is folded into `test`, because
   `validate()` already runs as a unit suite and as a gate inside `--check`; a third
   invocation would add CI time without coverage. Both call sites are still enforced.
2. The spec says every entry is "a flat string-to-string mapping." That is true except for
   the `modes` key, which HA requires to be nested. `tests/test_roundtrip.py` encodes the
   accurate rule: flat strings everywhere, with `modes` the single permitted nesting.

**Placeholder scan.** The only unresolved tokens are the four `<SHA-...>` action pins,
which Task 12 Step 1 resolves with exact `gh api` commands before use, and the demo
dashboard's `input_*`/`sensor.demo_*` entity IDs, which are necessarily
instance-specific. Task 6 Step 5 and Task 11 Step 5 are verification steps against live
systems, not deferred work.

**Type consistency.** `Material(fill, rim, backdrop)` is constructed in `materials.derive`
and consumed unchanged by `variables.build_variables` and `cardmod.build_cardmod`.
`build_themes(root)` returns the dict that `validate`, `render`, and every test consume.
`ENTRY_NAMES` is defined once in `emit.py` and imported by `validate.py` and three test
modules. `LITE_FILL_ALPHA`, `FULL_FILL_ALPHA_FLOOR`, and `LIGHT_ALPHA_BONUS` are defined
once in `materials.py` and asserted against the spec in `tests/test_materials.py`.

**One risk worth naming.** Task 10's contrast tests are the most likely to fail on first
run — Glass in light mode sets fill alpha to 0.10, which masks very little of the gradient.
That is the test doing its job. The remedy is written into Task 10 Step 2: raise the token
alpha and regenerate; do not lower the threshold.
