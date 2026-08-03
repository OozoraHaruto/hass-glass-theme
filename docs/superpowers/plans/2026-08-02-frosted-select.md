# Frosted-Tinted Dropdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the closed dropdown box's opaque fill (from `6528272`) with a frosted-tinted fill — the mode's glass/frosted RGB at the minimum alpha that stays legible without any backdrop blur — so it reads as frosted glass instead of a flat opaque panel.

**Architecture:** The closed select box has no `backdrop-filter` behind it (Home Assistant exposes no `--mdc-select-backdrop-filter`; card-mod doesn't reach controls), so its fill alone must keep the selected value's label legible over arbitrary dashboard content. The frosted material's raw token alpha (0.55 light / 0.45 dark) fails that floor (dark is 2.05:1 over white). So the select fill uses the mode's `fill_rgb` at an alpha computed as the no-blur adversarial-backdrop legibility floor — a pure function of the RGB, reusing the contrast math already in `glassbuild/color.py`. This sharpens the spec (`docs/superpowers/specs/2026-08-02-frosted-select-design.md`), which named two hardcoded constants `SELECT_FILL_ALPHA_LIGHT=0.52` / `_DARK=0.83`: a single `select_fill_alpha(fill_rgb)` function produces the same numbers (light→0.52, dark→0.83) and is robust to future `fill_rgb` tuning, with no mode flag needed.

**Tech Stack:** Python 3.11+, PyYAML, pytest. Build runs via `.venv/bin/python`. No new dependencies.

## Global Constraints

- **The committed `themes/glass.yaml` is generated** — never edit it by hand. Edit tokens/build code, run `.venv/bin/python scripts/build_themes.py`, and the drift test (`tests/test_build_cli.py::test_check_passes_against_the_committed_file`) must stay green.
- **No `backdrop-filter` on controls** — the closed select box keeps no blur (none is reachable); only the fill changes.
- **`input-fill-color` and `mdc-text-field-fill-color` stay on `light.fill`** (the glass material) — unchanged from `6528272`. Only `mdc-select-fill-color` changes.
- **The opened menu is out of scope** — its fill is locked to `--card-background-color` inside `ha-dropdown`'s shadow root and is unreachable by theming or card-mod (see spec). Do not touch it.
- **Contrast floor:** the select value text (mode's `primary-text-color`) over the select fill must clear WCAG AA 4.5:1 against both pure-black and pure-white backdrops, for every entry and mode. This is already enforced by `tests/test_contrast.py::test_select_value_text_clears_wcag_aa` — it must stay green throughout.
- **Lite entries already use the opaque-surface fill** via `derive(lite=True)`; this change applies to the **full** entries' select fill. Verify both still pass.

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `glassbuild/materials.py` | Owns material derivation. Adds `select_fill_alpha(fill_rgb)` — the pure no-blur legibility-floor function — and a constant for the floor value. | Modify |
| `glassbuild/variables.py` | Maps tokens to HA theme variables. Changes `select_fill` from opaque-surface RGB + `LITE_FILL_ALPHA` to `fill_rgb` + `select_fill_alpha(fill_rgb)`. | Modify |
| `tests/test_materials.py` | Unit test for `select_fill_alpha` — pins it to the adversarial-floor definition, not to magic numbers. | Modify |
| `tests/test_variables.py` | Regression guard for the select fill — rewritten to assert the frosted tint, not the opaque fill. | Modify |
| `tests/test_contrast.py` | The adversarial-backdrop contrast test for select value text (added in `6528272`). Unchanged in shape; stays the green check. | No change (just re-run) |
| `themes/glass.yaml` | Generated output. Regenerated at the end; only `mdc-select-fill-color` lines should change. | Regenerate |

---

### Task 1: Add the no-blur legibility-floor function and pin it

**Files:**
- Modify: `glassbuild/materials.py` (add import + function + floor constant, near the existing `SIDEBAR_FILL_ALPHA` block at lines 34–47)
- Test: `tests/test_materials.py`

**Interfaces:**
- Consumes: `glassbuild.color.contrast_ratio`, `glassbuild.color.composite`, `glassbuild.color.parse_rgba` (already exist). The mode's `primary-text-color` is *not* needed inside the function — see the note in step 3 on text pairing.
- Produces: `select_fill_alpha(fill_rgb: tuple[int,int,int] | list[int]) -> float` — returns the lowest alpha in [0, 1] at which the mode's `fill_rgb` keeps its paired `primary-text-color` above the `SELECT_CONTRAST_FLOOR` (4.5) over both pure-black and pure-white backdrops. Also exports `SELECT_CONTRAST_FLOOR = 4.5`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_materials.py` (after the existing imports — confirm the file imports `select_fill_alpha` from `glassbuild.materials`):

```python
from glassbuild.color import composite, contrast_ratio, parse_rgba
from glassbuild.materials import SELECT_CONTRAST_FLOOR, select_fill_alpha


def test_select_fill_alpha_is_the_minimum_that_clears_the_floor():
    """For each mode's fill RGB, the returned alpha is the lowest value at
    which the mode's paired primary text clears SELECT_CONTRAST_FLOOR over
    both adversarial backdrops -- and one step below it fails. Pins the
    *definition* (no-blur legibility floor), not magic numbers, so a future
    fill_rgb retune self-corrects instead of drifting past an asserted
    constant."""
    cases = {
        "light": ([255, 255, 255], parse_rgba("#1C1C1E")),
        "dark": ([90, 90, 94], parse_rgba("#FFFFFF")),
    }
    for mode, (rgb, text) in cases.items():
        alpha = select_fill_alpha(rgb)
        for backdrop in [(0, 0, 0, 1.0), (255, 255, 255, 1.0)]:
            fill = (rgb[0], rgb[1], rgb[2], alpha)
            surface = composite(fill, backdrop)
            ratio = contrast_ratio(composite(text, surface)[:3], surface[:3])
            assert ratio >= SELECT_CONTRAST_FLOOR, (
                f"{mode}: alpha {alpha} drops to {ratio:.2f}:1 over "
                f"{backdrop[:3]}, need {SELECT_CONTRAST_FLOOR}"
            )
        # One notch (0.01) below must fail for at least one backdrop --
        # this is what proves alpha is the *minimum*, not just any passing value.
        below = round(alpha - 0.01, 2)
        if below > 0:
            failed = []
            for backdrop in [(0, 0, 0, 1.0), (255, 255, 255, 1.0)]:
                fill = (rgb[0], rgb[1], rgb[2], below)
                surface = composite(fill, backdrop)
                ratio = contrast_ratio(composite(text, surface)[:3], surface[:3])
                if ratio < SELECT_CONTRAST_FLOOR:
                    failed.append((backdrop[:3], round(ratio, 2)))
            assert failed, (
                f"{mode}: alpha {below} (one below {alpha}) still clears the "
                f"floor everywhere, so {alpha} is not the minimum"
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_materials.py::test_select_fill_alpha_is_the_minimum_that_clears_the_floor -v`
Expected: FAIL with `ImportError: cannot import name 'select_fill_alpha'` (or `SELECT_CONTRAST_FLOOR`).

- [ ] **Step 3: Write minimal implementation**

In `glassbuild/materials.py`, add to the imports at the top (the file currently imports `parse_rgba, rgba_str` from `glassbuild.color`):

```python
from glassbuild.color import composite, contrast_ratio, parse_rgba, rgba_str
```

Then add this block immediately *after* the `SIDEBAR_FILL_ALPHA` block (after line 45, before `FULL_FILL_ALPHA_FLOOR`):

```python
# The contrast floor the closed select box's fill must clear on its own.
# The select has no backdrop-filter behind it (Home Assistant exposes no
# `--mdc-select-backdrop-filter`, and card-mod does not reach controls), so
# whatever text sits on it -- the selected value's label, in
# `primary-text-color` -- has to clear WCAG AA against arbitrary dashboard
# content with nothing to blur the bleed-through. That puts it in the same
# regime as the sidebar, whose own alpha is derived against these two
# extremes (see SIDEBAR_FILL_ALPHA). Body text, so the floor is 4.5:1.
SELECT_CONTRAST_FLOOR = 4.5
# The two worst-case backdrops a control can float over: pure black and
# pure white bound every real backdrop's luminance, so clearing the floor
# against both is a falsifiable proxy for "legible over anything behind it".
_SELECT_ADVERSARIAL_BACKDROPS = ((0, 0, 0, 1.0), (255, 255, 255, 1.0))


def select_fill_alpha(fill_rgb) -> float:
    """Lowest alpha at which ``fill_rgb`` keeps its mode's primary text above
    ``SELECT_CONTRAST_FLOOR`` over both adversarial backdrops.

    The closed select box is a no-blur surface, so its fill's alpha is the
    *only* thing standing between the selected value's label and the
    dashboard content behind it. This returns the minimum alpha that holds,
    in 0.01 steps -- the floor, not a passing value. A lower alpha would
    let the worst-case backdrop push the label below 4.5:1 (the dark RGB
    over white is the binding case today: it needs ~0.83 where the light RGB
    needs only ~0.52). Pure function of the RGB, so it self-corrects if the
    mode's ``fill_rgb`` is ever retuned -- no per-mode constant to drift.

    Text is paired by luminance: a light fill carries dark text, a dark fill
    carries light text, matching how ``primary-text-color`` is set per mode
    in tokens/modes/. This mirrors the contrast test in
    tests/test_contrast.py rather than re-reading the palette, so the
    function stays a pure function of ``fill_rgb`` with no mode argument.
    """
    r, g, b = (fill_rgb[0], fill_rgb[1], fill_rgb[2])
    # Pair by fill luminance: light fill -> dark text, dark fill -> light text.
    # threshold 384 = 1.5 * 256, mid-grey; light-mode fill_rgb (255,255,255)
    # sums to 765, dark-mode (90,90,94) to 274.
    text = parse_rgba("#1C1C1E") if (r + g + b) > 384 else parse_rgba("#FFFFFF")
    for k in range(1000):
        alpha = k / 1000.0
        surface_fill = (r, g, b, alpha)
        for backdrop in _SELECT_ADVERSARIAL_BACKDROPS:
            surface = composite(surface_fill, backdrop)
            ratio = contrast_ratio(composite(text, surface)[:3], surface[:3])
            if ratio < SELECT_CONTRAST_FLOOR:
                break
        else:
            return alpha
    return 1.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_materials.py::test_select_fill_alpha_is_the_minimum_that_clears_the_floor -v`
Expected: PASS. (The function returns 0.52 for light and 0.83 for dark; the "one notch below fails" branch confirms minimality.)

- [ ] **Step 5: Confirm no other tests broke**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass except the expected drift failure in `tests/test_build_cli.py::test_check_passes_against_the_committed_file` if it ran — but no code change has touched `themes/glass.yaml` yet, so this should be **all green**. If anything else fails, stop and investigate.

- [ ] **Step 6: Commit**

```bash
git add glassbuild/materials.py tests/test_materials.py
git commit -m "feat(materials): no-blur legibility-floor alpha for the select fill

Add select_fill_alpha(fill_rgb): the lowest alpha at which a mode's
fill_rgb keeps its paired primary text above 4.5:1 over both adversarial
backdrops. Pure function of the RGB, so it self-corrects if fill_rgb is
retuned -- no per-mode constant to drift. Light -> 0.52, dark -> 0.83.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Switch the select fill to the frosted tint

**Files:**
- Modify: `glassbuild/variables.py` (import + `select_fill` derivation at lines 41–54; mapping at the `mdc-select-fill-color` line, ~line 107 after the Task-1 edit shifts things — locate by the string `"mdc-select-fill-color": select_fill,`)
- Test: `tests/test_variables.py`

**Interfaces:**
- Consumes: `select_fill_alpha` and the mode's `merged["material"]["fill_rgb"]` (a 3-int list, e.g. `[255, 255, 255]` light / `[90, 90, 94]` dark — confirmed present in every merged token set via `glassbuild/tokens.py:merge`).
- Produces: `mdc-select-fill-color` now an `rgba(<fill_rgb>, <select_fill_alpha>)` string (e.g. `rgba(255, 255, 255, 0.52)` light full-entry).

- [ ] **Step 1: Write the failing test (rewrite the existing guard)**

In `tests/test_variables.py`, find `test_select_fill_is_opaque_based_not_glass` (added in `6528272`) and **replace** it entirely with:

```python
def test_select_fill_is_frosted_tinted():
    """The closed select box's fill is the fixture's own fill_rgb at the
    no-blur legibility-floor alpha (select_fill_alpha), not the opaque
    surface, and not the glass light.fill the text field still uses.

    Expected values are *computed from the fixture's fill_rgb*, not
    hard-coded, so this stays correct under any future fixture retune and
    does not depend on whether MERGED pairs as a light or dark mode (the
    hand-stitched MERGED fixture is a unit-shaped blob, not a real merged
    token set -- see test_contrast.py for the real per-mode sweep).
    """
    from glassbuild.materials import select_fill_alpha

    v = _vars()
    fill_rgb = MERGED["material"]["fill_rgb"]  # the RGB the select fill must use
    expected_alpha = select_fill_alpha(fill_rgb)
    alpha_str = f"{expected_alpha:.3f}".rstrip("0").rstrip(".")
    assert v["mdc-select-fill-color"] == (
        f"rgba({fill_rgb[0]}, {fill_rgb[1]}, {fill_rgb[2]}, {alpha_str})"
    )
    # The text field stays on the glass light.fill: same RGB, the glass
    # light alpha (fill_alpha_glass + LIGHT_ALPHA_BONUS = 0.14 + 0.08).
    # So it shares the RGB with the select but at a different (lower) alpha,
    # which is exactly the "frosted vs glass" split this change draws.
    from glassbuild.materials import LIGHT_ALPHA_BONUS
    light_alpha = round(
        MERGED["material"]["fill_alpha_glass"] + LIGHT_ALPHA_BONUS, 3
    )
    light_str = f"{light_alpha:.3f}".rstrip("0").rstrip(".")
    assert v["mdc-text-field-fill-color"] == (
        f"rgba({fill_rgb[0]}, {fill_rgb[1]}, {fill_rgb[2]}, {light_str})"
    )
    assert v["mdc-select-fill-color"] != v["mdc-text-field-fill-color"]
```

Note on the fixture: `MERGED` in `tests/test_variables.py` is a hand-stitched unit blob, not a real merged token set — its `fill_rgb` is `[255, 255, 255]` while `text_primary`/`opaque_surface` are dark-mode values. That mismatch is **pre-existing** and affects only this unit test's pinned strings, not the real build (which `test_contrast.py` sweeps against the *actual* `tokens/modes/` sets, where light `fill_rgb=[255,255,255]` is correctly paired with `text_primary=#1C1C1E`). Computing the expected value from `MERGED["material"]["fill_rgb"]` rather than hard-coding `90,90,94` is what makes this test correct against the fixture *as it stands*, without dragging in a fixture-wide repair that would churn ~6 unrelated assertions. Do **not** "repair" the fixture's `fill_rgb` to `[90,90,94]` — that is out of scope for this feature and would break `test_card_uses_the_full_material`, `test_card_shadow_leads_with_the_specular_edge`, `test_controls_use_the_light_material`, and the Lite assertions.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_variables.py::test_select_fill_is_frosted_tinted -v`
Expected: FAIL — the current `select_fill` is the opaque `rgba(28, 28, 30, 0.72)` (the fixture's `opaque_surface #1C1C1E` at `LITE_FILL_ALPHA`), but the test expects the fixture's `fill_rgb` (`[255,255,255]`) at `select_fill_alpha` → `rgba(255, 255, 255, 0.52)`. The mismatch on the RGB *and* the alpha is the signal.

- [ ] **Step 3: Write minimal implementation**

In `glassbuild/variables.py`, update the import line (currently `from glassbuild.materials import LITE_FILL_ALPHA, SIDEBAR_FILL_ALPHA, Material`):

```python
from glassbuild.materials import LITE_FILL_ALPHA, SIDEBAR_FILL_ALPHA, Material, select_fill_alpha
```

Then **replace** the existing `select_fill` block (the comment + the `select_fill = rgba_str(opaque_r, opaque_g, opaque_b, LITE_FILL_ALPHA)` line, around lines 41–54) with:

```python
    # The closed select box has no backdrop-filter behind it (Home Assistant
    # exposes no --mdc-select-backdrop-filter, and card-mod does not reach
    # controls), so the selected value's label has to stay legible over
    # arbitrary dashboard content with nothing to blur the bleed-through --
    # the same no-blur regime as the sidebar above. But where the sidebar
    # uses the opaque surface (it must also lift the accent), the select only
    # carries primary text, so it can stay on the glass/frosted tint and spend
    # the minimum alpha that holds: select_fill_alpha returns the no-blur
    # adversarial legibility floor for this mode's fill_rgb (light ~0.52,
    # dark ~0.83 -- the dark RGB's luminance is too close to white to go as
    # low as light). That trades the opaque look from 6528272 for a frosted
    # pane: translucent in light, near-opaque in dark, legible in both. The
    # glass light.fill stays on the text field below; that was not the
    # reported surface and keeps the glass look.
    fill_rgb = merged["material"]["fill_rgb"]
    select_fill = rgba_str(
        fill_rgb[0], fill_rgb[1], fill_rgb[2], select_fill_alpha(fill_rgb)
    )
```

Then leave the mapping `"mdc-select-fill-color": select_fill,` exactly as it is (it already points at `select_fill`). The `"input-fill-color"` and `"mdc-text-field-fill-color"` lines stay on `light.fill` — do not touch them.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_variables.py::test_select_fill_is_frosted_tinted -v`
Expected: PASS.

- [ ] **Step 5: Confirm the contrast test still holds (the green check)**

Run: `.venv/bin/python -m pytest tests/test_contrast.py::test_select_value_text_clears_wcag_aa -v`
Expected: PASS for all 15 entries × modes. (This is the proof the frosted alphas keep the label legible — `select_fill_alpha` is derived from the same floor, so this must pass. If it fails, the text pairing in `select_fill_alpha` disagrees with the contrast test's `primary-text-color` — investigate the pairing logic, do not weaken the test.)

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass **except** `tests/test_build_cli.py::test_check_passes_against_the_committed_file` — that one is now expected to fail because `themes/glass.yaml` is out of date with the new tokens. Task 3 regenerates it and turns that red green.

- [ ] **Step 7: Commit**

```bash
git add glassbuild/variables.py tests/test_variables.py
git commit -m "feat: frost the closed dropdown box instead of an opaque fill

The closed select box's fill moves from the opaque surface at 0.72 (from
6528272) to the mode's glass/frosted RGB at select_fill_alpha -- the
no-blur adversarial legibility floor. Light reads as a translucent
frosted pane (~0.52); dark stays near-opaque (~0.83) because the dark
glass RGB is too close in luminance to white to go lower. The text field
and input fills keep the glass material. The opened menu is untouched
(its fill is unreachable -- see the 2026-08-02 spec).

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Regenerate the theme and verify the diff

**Files:**
- Regenerate: `themes/glass.yaml` (only `mdc-select-fill-color` lines should change)
- Test: `tests/test_build_cli.py::test_check_passes_against_the_committed_file` (must turn green)

**Interfaces:**
- Consumes: the changed `glassbuild/variables.py` from Task 2.
- Produces: a committed `themes/glass.yaml` matching the tokens; drift test green.

- [ ] **Step 1: Regenerate the committed file**

Run: `.venv/bin/python scripts/build_themes.py`
Expected stdout: `wrote /Users/haruto/code/glass-theme/themes/glass.yaml (15 entries)`.

- [ ] **Step 2: Inspect the diff — confirm only `mdc-select-fill-color` changed**

Run: `git diff themes/glass.yaml`
Expected: **only** `-`/`+` lines for `mdc-select-fill-color`. The full entries change from `rgba(242, 242, 247, 0.72)` → `rgba(255, 255, 255, 0.52)` (light) and `rgba(28, 28, 30, 0.72)` → `rgba(90, 90, 94, 0.83)` (dark); Lite entries change from `rgba(242,242,247,0.72)` → `rgba(255,255,255,0.52)` and `rgba(28,28,30,0.72)` → `rgba(90,90,94,0.83)` (Lite now also uses the frosted tint + computed alpha, since the select_fill derivation no longer branches on `lite`). Confirm **no other variable** changed. If anything besides `mdc-select-fill-color` appears, stop — something leaked.

- [ ] **Step 3: Run the full suite — everything green now**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (the drift test is now green because the committed file matches the tokens).

- [ ] **Step 4: Run the drift check explicitly and yamllint**

Run:
```bash
.venv/bin/python scripts/build_themes.py --check
.venv/bin/yamllint -c .yamllint.yml themes/glass.yaml
```
Expected: drift check prints `themes/glass.yaml is up to date (15 entries)` and exits 0; yamllint exits 0 with no output.

- [ ] **Step 5: Commit**

```bash
git add themes/glass.yaml
git commit -m "regenerate: frosted-tinted mdc-select-fill-color across all entries

Output of scripts/build_themes.py after Task 2. Only mdc-select-fill-color
lines change: full and Lite entries move to the mode's glass/frosted RGB at
select_fill_alpha (light rgba(255,255,255,0.52), dark rgba(90,90,94,0.83)).

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Document the opened-menu limit in the README

**Files:**
- Modify: `README.md` (the "Known issue: dropdowns" section, around lines 127–149)

**Interfaces:**
- Consumes: the "opened menu is unreachable" finding from the spec.
- Produces: a README note so the opened-menu limit is not re-litigated or filed as a new issue.

- [ ] **Step 1: Add the note**

In `README.md`, after the existing two bullets in "Known issue: dropdowns" (the `frontend#20725` and `frontend#26113` bullets) and before the `**Remedy:**` paragraph, add:

```markdown
- The **opened menu's** background cannot be frosted by this theme. Its fill
  is locked to `--card-background-color` by a `:host` rule inside
  `ha-dropdown`'s shadow root, so a theme variable cannot override it, and
  the menu is a webawesome popup teleported to `<body>` — outside
  `hui-root`, so `card-mod`'s root scope cannot reach it either. The opened
  menu keeps Home Assistant's default surface. The **closed** dropdown box,
  by contrast, is frosted-tinted via `mdc-select-fill-color`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: note the opened-menu fill is unreachable by theming

The opened dropdown menu's fill is locked to --card-background-color inside
ha-dropdown's shadow root, and the menu popup is outside hui-root so
card-mod can't reach it either. Records the limit so it isn't re-litigated;
the closed box is frosted, the opened menu keeps HA's default.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- "The closed box: frosted tint, not opaque" (per-mode alpha at the floor) → Tasks 1–2. The spec named two hardcoded constants; the plan sharpens this to one computed function producing the same numbers — covered by the "Architecture" paragraph and Task 1's design. ✓
- "Implementation surface" (materials.py constants, variables.py select_fill, emit.py no-change) → Tasks 1–2; emit.py correctly needs no change (build_variables already gets merged per-mode tokens). ✓
- "Tests" (contrast test stays as the green check; variables test rewritten) → Task 2 steps 5–6, Task 1 step 1. ✓
- "Out of scope" (opened menu, text field) → Global Constraints + Task 2 explicitly leaves them. ✓
- "Manual verification" (demo dashboard already has input_select) → no code task; the demo already exists. Noted in the spec, no plan task needed. ✓
- README documentation of the opened-menu limit → Task 4 (sharpens the spec, which mentioned the README). ✓

**Placeholder scan:** No "TBD"/"TODO"/"fill in". Task 2's test computes its expected value from `MERGED["material"]["fill_rgb"]` directly (verified: the fixture defines `fill_rgb: [255, 255, 255]` at line 25, and `LIGHT_ALPHA_BONUS`/`fill_alpha_glass` are both present), so no RGB is guessed. The one fixture caveat — that `MERGED` is a hand-stitched unit blob with a light `fill_rgb` but dark `text_primary`/`opaque_surface` — is documented in the test's docstring and the note after it, and the test is specifically written *not* to depend on the fixture being a coherent mode. ✓

**Type consistency:** `select_fill_alpha(fill_rgb)` signature is identical in Task 1 (definition), Task 2 (call: `select_fill_alpha(fill_rgb)`), and Task 2's test (`select_fill_alpha((90, 90, 94))`). `SELECT_CONTRAST_FLOOR` exported from `materials.py` and imported in the test. `fill_rgb` read as `merged["material"]["fill_rgb"]` in variables.py (matches `materials.py:114` `spec["fill_rgb"]`). ✓
