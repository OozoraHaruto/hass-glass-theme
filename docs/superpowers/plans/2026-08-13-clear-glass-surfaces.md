# Clear Glass Surfaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Glass and Liquid Glass low-opacity, unblurred materials while keeping blur on Frosted Glass and on opened dropdown menus handled by the optional dropdown module.

**Architecture:** Add an explicit material capability that controls whether the generator derives and emits surface backdrop filters. Preserve card-mod styling for full clear entries with a no-filter sidebar template, continue omitting card-mod entirely for Lite entries, and let the existing `full.backdrop is not None` gate keep refraction variables inactive. Regenerate the committed theme and rewrite the README around the resulting material semantics.

**Tech Stack:** Python 3.11+, PyYAML, pytest, generated Home Assistant theme YAML, card-mod CSS strings, dependency-free browser JavaScript, Node 22 test runner, yamllint.

## Global Constraints

- Glass and Liquid Glass keep their current low-opacity fills, rims, specular edges, geometry, colors, and gradient.
- Glass and Liquid Glass emit no native Home Assistant backdrop-filter variables and no card-mod backdrop-filter declarations.
- The optional `glass-dropdown.js` module remains the only blur source for Glass and Liquid Glass and retains its fixed `blur(20px)` popup rule.
- Glass Lite remains the near-opaque no-blur readability, weak-hardware, and compatibility variant.
- Frosted Glass and Frosted Glass Lite behavior stays unchanged.
- Liquid Glass emits no refraction activation or tuning variables; `glass-refraction.js` remains packaged only for compatibility with older generated themes.
- Theme names and the fifteen-entry picker matrix remain unchanged; do not add Liquid Glass Lite.
- Do not hand-edit `themes/glass.yaml`; regenerate it with `python scripts/build_themes.py`.
- Do not add dependencies or comments unrelated to this change.
- Do not commit unless the user explicitly requests it.

## File Structure

- `tokens/glass.yaml`: declares Glass as a clear, no-surface-backdrop material and removes obsolete blur tuning prose/data.
- `tokens/liquid-glass.yaml`: declares Liquid Glass as clear, keeps its rim/edge and dormant refraction metadata, and removes current surface blur tuning.
- `tokens/frosted-glass.yaml`: explicitly declares Frosted Glass as the only surface-backdrop material.
- `tokens/modes/light.yaml`: retains shared mode tuning while removing Glass-specific claims that blur is active.
- `tokens/modes/dark.yaml`: retains shared mode tuning while removing Glass-specific claims that blur is active.
- `glassbuild/materials.py`: derives backdrop chains only for materials that opt in.
- `glassbuild/cardmod.py`: emits either blurred or clear sidebar CSS for full entries, while Lite entries still emit no card-mod keys.
- `glassbuild/emit.py`: passes the explicit Lite flag into card-mod generation and updates the Liquid Glass matrix rationale.
- `glassbuild/variables.py`: updates stale comments; its existing `full.backdrop` gate continues to control native filters and refraction output.
- `tests/test_materials.py`: unit coverage for clear versus blurred derivation.
- `tests/test_token_data.py`: token-schema and material-capability coverage.
- `tests/test_variables.py`: variable-level coverage for clear Glass/Liquid and blurred Frosted Glass.
- `tests/test_cardmod.py`: clear, blurred, and Lite card-mod output coverage.
- `tests/test_emit.py`: complete generated-entry behavior, low-opacity fill, filter absence, Frosted preservation, and unchanged matrix coverage.
- `tests/test_refraction.py`: verifies current Liquid Glass entries do not activate the retained compatibility module.
- `www/glass-refraction.js`: retains compatibility behavior while removing claims that current Liquid Glass activates it.
- `themes/glass.yaml`: regenerated output only.
- `README.md`: authoritative explanation of Glass, Liquid Glass, Lite, Frosted Glass, dropdown blur, card-mod, and dormant refraction.

---

### Task 1: Make Surface Backdrops an Explicit Material Capability

**Files:**
- Modify: `tokens/glass.yaml:1-38`
- Modify: `tokens/liquid-glass.yaml:1-64`
- Modify: `tokens/frosted-glass.yaml:1-13`
- Modify: `tokens/modes/light.yaml:16-31`
- Modify: `tokens/modes/dark.yaml:9-36`
- Modify: `glassbuild/materials.py:1-25,117-131,149-187`
- Test: `tests/test_materials.py:10-151`
- Test: `tests/test_token_data.py:27-160,261-307`

**Interfaces:**
- Consumes: merged material token mapping at `merged["material"]`.
- Produces: required Boolean token `material.surface_backdrop`; `derive(merged, material_key, lite) -> dict[str, Material]`, where `Material.backdrop` is non-`None` only when `surface_backdrop` is true and `lite` is false.

- [ ] **Step 1: Add failing material-capability tests**

In `tests/test_materials.py`, add `surface_backdrop: False` to the `MERGED["material"]` fixture and replace the Glass backdrop expectations with explicit clear-surface tests:

```python
def test_clear_material_keeps_low_alpha_without_a_backdrop():
    result = derive(MERGED, "glass", lite=False)
    assert result["full"].fill == "rgba(255, 255, 255, 0.1)"
    assert result["full"].backdrop is None
    assert result["light"].backdrop is None


def test_backdrop_material_diffuses_before_it_tints():
    merged = {
        **MERGED,
        "material": {**MERGED["material"], "surface_backdrop": True},
    }
    result = derive(merged, "frosted-glass", lite=False)
    assert result["full"].backdrop == (
        "blur(8px) saturate(180%) brightness(60%) contrast(110%)"
    )


def test_backdrop_material_light_layer_uses_half_blur():
    merged = {
        **MERGED,
        "material": {
            **MERGED["material"],
            "surface_backdrop": True,
            "blur_px": 40,
            "saturate_pct": 150,
        },
    }
    result = derive(merged, "frosted-glass", lite=False)
    assert result["light"].backdrop == (
        "blur(20px) saturate(150%) brightness(60%) contrast(110%)"
    )
```

Keep the existing Lite fill/edge tests, but ensure they use `surface_backdrop: False` and still expect `backdrop is None`.

- [ ] **Step 2: Add failing token-schema tests**

In `tests/test_token_data.py`, make the required keys conditional and pin the capability matrix:

```python
@pytest.mark.parametrize("material", MATERIALS)
@pytest.mark.parametrize("mode", MODES)
def test_merged_tokens_have_required_keys(tokens, material, mode):
    merged = merge(
        tokens["base"],
        tokens["materials"][material],
        tokens["modes"][mode],
    )
    assert merged["radius"]["card"] == "18px"
    assert merged["material"]["name"] == MATERIAL_NAMES[material]
    assert isinstance(merged["material"]["surface_backdrop"], bool)
    if merged["material"]["surface_backdrop"]:
        assert isinstance(merged["material"]["blur_px"], int)
        assert isinstance(merged["material"]["saturate_pct"], int)
    for key in ("accent", "text_primary", "opaque_surface", "background_from"):
        assert key in merged["palette"]


def test_only_frosted_glass_enables_surface_backdrops(tokens):
    assert tokens["materials"]["glass"]["material"]["surface_backdrop"] is False
    assert (
        tokens["materials"]["liquid-glass"]["material"]["surface_backdrop"]
        is False
    )
    assert (
        tokens["materials"]["frosted-glass"]["material"]["surface_backdrop"]
        is True
    )
```

Replace `test_glass_blur_is_wide_enough_to_diffuse_content` with a Frosted-only assertion:

```python
def test_frosted_blur_is_wide_enough_to_diffuse_content(tokens):
    material = tokens["materials"]["frosted-glass"]["material"]
    assert material["blur_px"] == 40
    assert material["saturate_pct"] == 120
```

Delete or rewrite tests that claim Glass or Liquid Glass must blur, including `test_liquid_glass_still_blurs_enough_to_stand_alone`. Retain tests for their low fill alpha, stronger Liquid rim/edge, refraction metadata structure, and the Frosted tuning values.

- [ ] **Step 3: Run focused tests to verify they fail**

Run:

```bash
python -m pytest tests/test_materials.py tests/test_token_data.py -v
```

Expected: failures because `surface_backdrop` is absent and `derive()` still emits backdrops for every non-Lite material.

- [ ] **Step 4: Add the capability to material tokens**

Set the following exact values:

```yaml
# tokens/glass.yaml
material:
  name: Glass
  surface_backdrop: false
  rim_alpha: 0.45
  edge_scale: 1.0
```

```yaml
# tokens/liquid-glass.yaml
material:
  name: Liquid Glass
  surface_backdrop: false
  rim_alpha: 0.55
  edge_scale: 1.2
  refraction:
    filter_id: glass-refraction
    scale: 14
    edge_fraction: 0.18
```

```yaml
# tokens/frosted-glass.yaml
material:
  name: Frosted Glass
  surface_backdrop: true
  blur_px: 40
  saturate_pct: 120
  rim_alpha: 0.20
  edge_scale: 0.55
```

Remove `blur_px` and `saturate_pct` from Glass and Liquid Glass because current entries must not derive surface backdrops from those values. Rewrite their existing comments so they describe low-opacity fill plus edge separation and do not claim current cards blur or refract. Keep Liquid Glass refraction metadata explicitly described as compatibility metadata for `glass-refraction.js`; current generated entries do not publish its activation variables.

Update `tokens/modes/light.yaml` and `tokens/modes/dark.yaml` comments around `brightness_pct` and `contrast_pct`: these remain shared tuning consumed by Frosted Glass, but the comments must no longer claim Glass or Liquid Glass cards run a blur/remap chain. Keep the numeric values unchanged because changing palette or shared Frosted tuning is outside scope.

- [ ] **Step 5: Gate backdrop derivation on the material capability**

In `glassbuild/materials.py`, avoid reading blur-only keys for clear materials and derive both layers from one gate:

```python
def derive(merged: dict[str, Any], material_key: str, lite: bool) -> dict[str, Material]:
    """Build the full and light materials for one material/mode combination."""
    spec = merged["material"]
    rim_r, rim_g, rim_b = spec["rim_rgb"]
    rim = rgba_str(rim_r, rim_g, rim_b, float(spec["rim_alpha"]))
    edge = _edge(spec)
    uses_backdrop = bool(spec["surface_backdrop"]) and not lite

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
    full_backdrop = None
    light_backdrop = None
    if uses_backdrop:
        blur = int(spec["blur_px"])
        full_backdrop = _backdrop(spec, blur)
        light_backdrop = _backdrop(spec, blur // 2)

    return {
        "full": Material(
            fill=rgba_str(base_r, base_g, base_b, full_alpha),
            rim=rim,
            edge=edge,
            backdrop=full_backdrop,
        ),
        "light": Material(
            fill=rgba_str(base_r, base_g, base_b, light_alpha),
            rim=rim,
            edge=edge,
            backdrop=light_backdrop,
        ),
    }
```

Update the module/class docstrings so fill and edge are universal material parts while backdrop filtering is an opt-in Frosted capability.

- [ ] **Step 6: Run focused tests**

Run:

```bash
python -m pytest tests/test_materials.py tests/test_token_data.py -v
```

Expected: PASS.

- [ ] **Step 7: Inspect the task diff without committing**

Run:

```bash
git diff -- tokens/glass.yaml tokens/liquid-glass.yaml tokens/frosted-glass.yaml tokens/modes/light.yaml tokens/modes/dark.yaml glassbuild/materials.py tests/test_materials.py tests/test_token_data.py
git status --short
```

Expected: only the eight intended source/test files are changed; do not commit.

---

### Task 2: Emit Clear Variables and Preserve Clear card-mod Styling

**Files:**
- Modify: `glassbuild/variables.py:191-237`
- Modify: `glassbuild/cardmod.py:1-167`
- Modify: `glassbuild/emit.py:45-58,76-124`
- Modify: `www/glass-refraction.js:1-43,64-87,203-230`
- Test: `tests/test_variables.py:22-38,86-122,253-359`
- Test: `tests/test_cardmod.py:8-128`
- Test: `tests/test_emit.py:72-246`
- Test: `tests/test_refraction.py:1-127`

**Interfaces:**
- Consumes: `Material.backdrop`, `merged["material"]["surface_backdrop"]`, and the explicit `lite: bool` generated by `glassbuild.emit._weights()`.
- Produces: `build_cardmod(entry_name, materials, merged, *, lite) -> dict[str, str]`; clear full entries receive card-mod fill/border/tracking CSS without filters, Frosted full entries receive the existing blurred CSS, and Lite entries receive `{}`.

- [ ] **Step 1: Write failing variable and generated-entry tests**

In `tests/test_variables.py`, add `surface_backdrop: False` to the fixture and change direct Glass expectations:

```python
def test_clear_card_uses_the_low_opacity_full_material_without_blur():
    v = _vars()
    assert v["ha-card-background"] == "rgba(255, 255, 255, 0.14)"
    assert "ha-card-backdrop-filter" not in v
    assert v["ha-card-border-radius"] == "18px"
    assert v["ha-card-border-color"] == "rgba(255, 255, 255, 0.45)"


def test_clear_dialog_omits_the_native_backdrop_variable():
    v = _vars()
    assert "ha-dialog-surface-backdrop-filter" not in v
    assert v["ha-dialog-border-radius"] == "28px"
```

Replace `test_full_material_includes_every_backdrop_filter_key` with real-token coverage:

```python
@pytest.mark.parametrize("material", ["glass", "liquid-glass"])
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_clear_materials_omit_every_backdrop_filter_key(material, mode):
    tokens = load_tokens(ROOT)
    merged = merge(tokens["base"], tokens["materials"][material], tokens["modes"][mode])
    variables = build_variables(merged, derive(merged, material, lite=False))
    for key in _BACKDROP_FILTER_KEYS:
        assert key not in variables, (material, mode, key)
    assert not [key for key in variables if "backdrop-filter" in key]


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_frosted_material_includes_every_backdrop_filter_key(mode):
    tokens = load_tokens(ROOT)
    merged = merge(
        tokens["base"],
        tokens["materials"]["frosted-glass"],
        tokens["modes"][mode],
    )
    variables = build_variables(
        merged,
        derive(merged, "frosted-glass", lite=False),
    )
    for key in _BACKDROP_FILTER_KEYS:
        assert key in variables, (mode, key)
```

In `tests/test_emit.py`, replace the old Glass-blur and Liquid-refraction assertions with:

```python
_CLEAR_ENTRIES = (
    "Glass",
    "Glass Light",
    "Glass Dark",
    "Liquid Glass",
    "Liquid Glass Light",
    "Liquid Glass Dark",
)


def test_clear_entries_keep_low_opacity_card_fills(themes):
    assert _applied_mode(themes["Glass"], "light")["ha-card-background"] == (
        "rgba(255, 255, 255, 0.14)"
    )
    assert _applied_mode(themes["Glass"], "dark")["ha-card-background"] == (
        "rgba(90, 90, 94, 0.16)"
    )
    assert _applied_mode(themes["Liquid Glass"], "light")["ha-card-background"] == (
        "rgba(255, 255, 255, 0.11)"
    )
    assert _applied_mode(themes["Liquid Glass"], "dark")["ha-card-background"] == (
        "rgba(90, 90, 94, 0.13)"
    )


@pytest.mark.parametrize("name", _CLEAR_ENTRIES)
def test_clear_entries_have_no_backdrop_filter_anywhere(themes, name):
    for key, value in _flatten_entry(themes[name]):
        assert "backdrop-filter" not in key, (name, key)
        assert "backdrop-filter" not in str(value), (name, key, value)
        assert "blur(" not in str(value), (name, key, value)


def test_frosted_keeps_its_existing_blur(themes):
    assert "blur(40px)" in themes["Frosted Glass Dark"]["ha-card-backdrop-filter"]


@pytest.mark.parametrize(
    "name", ["Liquid Glass", "Liquid Glass Light", "Liquid Glass Dark"]
)
def test_current_liquid_entries_do_not_publish_refraction_variables(themes, name):
    values = dict(_flatten_entry(themes[name]))
    assert "ha-glass-refraction-backdrop" not in values
    assert "ha-glass-refraction-scale" not in values
    assert "ha-glass-refraction-edge" not in values
```

Keep the fifteen-entry matrix, no-Liquid-Lite, dropdown activation surface, Glass Lite fill, and Frosted Lite tests.

- [ ] **Step 2: Write failing card-mod tests**

In `tests/test_cardmod.py`, model three states explicitly:

```python
CLEAR = Material(
    fill="rgba(255, 255, 255, 0.14)",
    rim="rgba(255, 255, 255, 0.45)",
    edge=EDGE,
    backdrop=None,
)
FROSTED = Material(
    fill="rgba(255, 255, 255, 0.55)",
    rim="rgba(255, 255, 255, 0.2)",
    edge=EDGE,
    backdrop="blur(40px) saturate(120%) brightness(105%) contrast(96%)",
)
LITE = Material(
    fill="rgba(28, 28, 30, 0.72)",
    rim="rgba(255, 255, 255, 0.45)",
    edge=EDGE,
    backdrop=None,
)
```

Update the helper to pass `lite` explicitly and choose the material:

```python
def _block(
    entry_name: str = "Glass",
    *,
    material: Material = CLEAR,
    lite: bool = False,
) -> dict[str, str]:
    materials = {"full": material, "light": material}
    return build_cardmod(entry_name, materials, MERGED, lite=lite)
```

Add these assertions:

```python
def test_lite_produces_no_cardmod_keys():
    assert _block("Glass Lite", material=LITE, lite=True) == {}


def test_clear_full_entry_keeps_cardmod_without_backdrop_filter():
    block = _block("Glass")
    assert block["card-mod-theme"] == "Glass"
    assert "backdrop-filter" not in block["card-mod-root-yaml"]
    assert "backdrop-filter" not in block["card-mod-sidebar-yaml"]
    assert "background: rgba(255, 255, 255, 0.14)" in block["card-mod-sidebar-yaml"]
    assert "border-right: 1px solid rgba(255, 255, 255, 0.45)" in block[
        "card-mod-sidebar-yaml"
    ]


def test_frosted_sidebar_keeps_the_backdrop_filter():
    block = _block("Frosted Glass", material=FROSTED)
    assert FROSTED.backdrop in block["card-mod-sidebar-yaml"]
```

Keep YAML shape, header/tab selectors, tracking, motion, and specificity assertions for the clear block.

- [ ] **Step 3: Update the current-theme refraction expectation**

In `tests/test_refraction.py`, keep the structural compatibility checks for the shipped module and token filter ID. Replace `test_the_theme_publishes_the_displacement_tuning` with:

```python
def test_current_liquid_theme_does_not_activate_the_compatibility_module():
    from glassbuild.emit import build_themes

    entry = build_themes(ROOT)["Liquid Glass Dark"]
    assert "ha-glass-refraction-backdrop" not in entry
    assert "ha-glass-refraction-scale" not in entry
    assert "ha-glass-refraction-edge" not in entry
```

Update stale test docstrings that say current theme output points cards at the filter. Also update `www/glass-refraction.js` installation, scope, and activation comments so they identify the module as compatibility support for older Liquid Glass YAML; current entries never define its activation source. Preserve all executable behavior and constants—the compatibility module must remain able to activate when an older theme defines the three source variables.

- [ ] **Step 4: Run focused tests to verify they fail**

Run:

```bash
python -m pytest tests/test_variables.py tests/test_cardmod.py tests/test_emit.py tests/test_refraction.py -v
```

Expected: failures because Glass/Liquid still follow old test assumptions in helper code, `build_cardmod` does not accept `lite`, and clear entries currently lose all card-mod output when their backdrop is `None`.

- [ ] **Step 5: Add clear and blurred sidebar templates**

In `glassbuild/cardmod.py`, retain `_ROOT_TEMPLATE`, rename the existing sidebar template to `_BLURRED_SIDEBAR_TEMPLATE`, and add:

```python
_CLEAR_SIDEBAR_TEMPLATE = """\
.: |
  :host {{
    background: {fill};
    border-right: 1px solid {rim};
    transition: background {duration} {easing};
  }}
  .title {{
    letter-spacing: {tracking_headline};
  }}
  ha-list-item-button {{
    letter-spacing: {tracking_body};
  }}
"""
```

Change the public function to:

```python
def build_cardmod(
    entry_name: str,
    materials: dict[str, Material],
    merged: dict[str, Any],
    *,
    lite: bool,
) -> dict[str, str]:
    """Build card-mod styling for one full entry; Lite entries emit nothing."""
    if lite:
        return {}

    full = materials["full"]
    font = merged["font"]
    motion = merged["motion"]
    fmt_args = {
        "backdrop": full.backdrop,
        "fill": full.fill,
        "rim": full.rim,
        "tracking_headline": font["tracking_headline"],
        "tracking_body": font["tracking_body"],
        "duration": motion["duration"],
        "easing": motion["easing"],
    }
    sidebar_template = (
        _BLURRED_SIDEBAR_TEMPLATE
        if full.backdrop is not None
        else _CLEAR_SIDEBAR_TEMPLATE
    )
    return {
        "card-mod-theme": entry_name,
        "card-mod-root-yaml": _ROOT_TEMPLATE.format(**fmt_args),
        "card-mod-sidebar-yaml": sidebar_template.format(**fmt_args),
    }
```

Rewrite the large module docstring to state:

- only Frosted Glass uses native and sidebar backdrop filters;
- Glass and Liquid Glass still use card-mod for fills, borders, tracking, and transitions but never blur;
- Lite entries emit no card-mod keys;
- the native sidebar fallback remains near-opaque for readability.

- [ ] **Step 6: Pass the Lite flag from the emitter**

In `glassbuild/emit.py`, update both calls:

```python
flat_cardmod = build_cardmod(flat_name, materials, merged, lite=lite)
...
auto_cardmod = build_cardmod(auto_name, materials, merged, lite=lite)
```

Rewrite `_NO_LITE` comments so Liquid Glass lacks Lite variants because the existing Glass Lite family is the single near-opaque fallback and the approved picker matrix remains unchanged—not because current Liquid Glass refraction lives in a backdrop filter.

- [ ] **Step 7: Confirm variable/refraction gating needs no new branch**

In `glassbuild/variables.py`, keep the existing:

```python
if full.backdrop is not None:
```

This now naturally emits the seven native backdrop variables only for full Frosted Glass. Because the refraction block is nested inside this gate, current Liquid Glass entries emit none of `ha-glass-refraction-backdrop`, `ha-glass-refraction-scale`, or `ha-glass-refraction-edge`.

Update comments at `glassbuild/variables.py:191-237` to state this behavior and avoid claims that every full material has a backdrop. Do not add a second material-name branch.

- [ ] **Step 8: Run focused tests**

Run:

```bash
python -m pytest tests/test_variables.py tests/test_cardmod.py tests/test_emit.py tests/test_refraction.py -v
```

Expected: PASS.

- [ ] **Step 9: Run the complete Python suite before leaving generator code**

Run:

```bash
python -m pytest -v
```

Expected: PASS with zero failures. If stale blur assumptions fail elsewhere, update only assertions/documentation that conflict with the approved material semantics; do not weaken Frosted, Lite, dropdown, contrast, validation, or matrix coverage.

- [ ] **Step 10: Inspect the task diff without committing**

Run:

```bash
git diff -- glassbuild/variables.py glassbuild/cardmod.py glassbuild/emit.py www/glass-refraction.js tests/test_variables.py tests/test_cardmod.py tests/test_emit.py tests/test_refraction.py
git status --short
```

Expected: only intended generator/test changes plus Task 1 files and the approved spec/plan are present; do not commit.

---

### Task 3: Regenerate and Verify the Shipped Theme YAML

**Files:**
- Modify by generator only: `themes/glass.yaml`
- Test: `tests/test_build_cli.py`
- Test: `tests/test_roundtrip.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `build_themes(root) -> dict[str, dict[str, Any]]` and the updated tokens/generator.
- Produces: committed generated artifact containing the unchanged fifteen entry names and the new clear-surface output.

- [ ] **Step 1: Regenerate the theme**

Run:

```bash
python scripts/build_themes.py
```

Expected: `themes/glass.yaml` is rewritten from source tokens.

- [ ] **Step 2: Check the generated diff for the required boundaries**

Run:

```bash
git diff -- themes/glass.yaml
```

Verify all of the following in the diff:

- Glass and Liquid Glass keep `card-background-color` and `ha-card-background` at `0.14/0.16` and `0.11/0.13` respectively.
- Glass and Liquid Glass remove all seven backdrop-filter keys.
- Glass and Liquid Glass sidebar card-mod CSS remains present but contains no `backdrop-filter` declaration.
- Liquid Glass removes all three `ha-glass-refraction-*` variables.
- Glass and Liquid Glass retain `ha-glass-dropdown-surface`.
- Glass Lite remains near-opaque and unblurred.
- Frosted Glass keeps its 40px full blur and 20px scrim blur.
- Frosted Glass Lite remains unblurred.
- No entry is added, removed, or renamed.

- [ ] **Step 3: Run drift and generated-document tests**

Run:

```bash
python scripts/build_themes.py --check
python -m pytest tests/test_build_cli.py tests/test_roundtrip.py tests/test_validate.py tests/test_emit.py -v
```

Expected: the drift check exits 0 and all tests pass.

- [ ] **Step 4: Parse the generated YAML explicitly**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml

themes = yaml.safe_load(Path("themes/glass.yaml").read_text())
assert len(themes) == 15
assert themes["Glass Light"]["ha-card-background"] == "rgba(255, 255, 255, 0.14)"
assert "ha-card-backdrop-filter" not in themes["Glass Light"]
assert "ha-card-backdrop-filter" not in themes["Liquid Glass Light"]
assert "blur(40px)" in themes["Frosted Glass Light"]["ha-card-backdrop-filter"]
assert themes["Glass Light Lite"]["ha-card-background"] == "rgba(242, 242, 247, 0.72)"
print("generated theme boundaries verified")
PY
```

Expected: `generated theme boundaries verified`.

- [ ] **Step 5: Inspect status without committing**

Run:

```bash
git status --short
git diff --stat
```

Expected: `themes/glass.yaml` is modified alongside the intended source, test, spec, and plan files; do not commit.

---

### Task 4: Rewrite README Material and Compatibility Guidance

**Files:**
- Modify: `README.md:1-44`
- Modify: `README.md:65-108`
- Modify: `README.md:110-131`
- Modify: `README.md:133-213`
- Modify: `README.md:215-263`
- Test: `tests/test_package_release.py`

**Interfaces:**
- Consumes: final generated behavior from Tasks 1-3.
- Produces: user-facing explanation consistent with the theme YAML and optional modules.

- [ ] **Step 1: Rewrite the introduction and material list**

Replace claims that all cards/dialogs are blurred with a concise distinction:

```markdown
Apple-inspired clear and frosted materials for Home Assistant's Lovelace dashboard,
with low-opacity Glass surfaces, an intentionally near-opaque Lite fallback, and
opt-in Frosted backdrop blur.
```

Describe the families exactly:

- **Glass:** low-opacity translucent fill (`0.14` light / `0.16` dark), bright rim and directional specular edge, no general backdrop blur.
- **Liquid Glass:** lower-opacity fill (`0.11` light / `0.13` dark), hotter rim and stronger edge, no general backdrop blur and no current SVG refraction activation.
- **Glass Lite:** near-opaque `0.72` surface for readability, weak hardware, and compatibility; not simply a blur toggle because Glass is already unblurred.
- **Frosted Glass:** high-opacity diffuse fill with 40px full-surface blur.
- **Frosted Glass Lite:** near-opaque no-blur fallback.

Keep the existing fifteen-entry table and Auto/Light/Dark explanation.

- [ ] **Step 2: Correct Home Assistant and card-mod coverage**

Rewrite the version/card-mod section so it says:

- Home Assistant’s backdrop variables are emitted only by Frosted Glass full entries.
- Glass and Liquid Glass use no native backdrop-filter keys.
- card-mod remains optional and adds header/sidebar fills, borders, tracking, and transitions to full entries.
- Glass/Liquid sidebar card-mod CSS is clear and unblurred.
- Frosted sidebar card-mod CSS retains blur because Home Assistant has no native sidebar backdrop variable.
- Lite entries still emit no card-mod keys.
- Home Assistant 2024.5.0 remains the floor because Frosted Glass relies on the card backdrop variable.

- [ ] **Step 3: Correct outside-dashboard and dropdown guidance**

State that Glass and Liquid Glass cards remain low-opacity and unblurred on both gradients and flat pages; their rim and edge provide separation. Warn that busy wallpaper can reduce legibility because the clear fill does not diffuse backdrop content.

Rewrite the dropdown issue section so:

- card-level stacking bugs from `--ha-card-backdrop-filter` apply to Frosted Glass, not Glass or Liquid Glass;
- the optional `glass-dropdown.js` module is the only blur source for Glass/Liquid;
- its blur is scoped to opened popup shadow roots and can still create a popup-local stacking context;
- it keeps its Frosted fill fallback and fixed 20px blur;
- closed fields remain frosted-tinted but unblurred;
- switching to Glass/Liquid removes card-filter stacking contexts; switching to Lite additionally chooses a near-opaque readability surface.

- [ ] **Step 4: Rewrite Lite and refraction sections**

The Lite section must explicitly say that Lite exists for readability, weak hardware, and compatibility. Its defining difference from Glass is the near-opaque fill, not backdrop removal.

Replace the active Refraction installation instructions with a compatibility note:

- current Liquid Glass entries do not define `--ha-glass-refraction-backdrop`, `--ha-glass-refraction-scale`, or `--ha-glass-refraction-edge`;
- therefore `glass-refraction.js` stays inactive with current themes;
- it remains in archives only for users of older generated Liquid Glass themes;
- true SVG displacement requires `backdrop-filter`, so it is incompatible with the current no-filter Liquid Glass contract.

Do not tell users that installing `glass-refraction.js` upgrades current Liquid Glass.

- [ ] **Step 5: Search README for stale claims**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("README.md").read_text()
for stale in (
    "Glass (`blur(20px)`)",
    "Liquid Glass (`blur(18px)`)",
    "The Liquid Glass entries are the only ones that can bend light",
    "The full entries use a much lower alpha (as low as 0.10) that reads as glass only because of the blur",
):
    assert stale not in text, stale
print("stale README claims removed")
PY
```

Expected: `stale README claims removed`.

- [ ] **Step 6: Run documentation-adjacent tests**

Run:

```bash
python -m pytest tests/test_package_release.py tests/test_emit.py tests/test_refraction.py -v
```

Expected: PASS. If packaging tests assert module contents, keep both optional JavaScript files packaged; only README semantics change.

- [ ] **Step 7: Inspect README diff without committing**

Run:

```bash
git diff -- README.md
git status --short
```

Expected: all material, card-mod, dropdown, Lite, and refraction sections agree with generated output; do not commit.

---

### Task 5: Final Automated and Manual Verification

**Files:**
- Verify only; modify earlier files only if a check exposes a requirement mismatch.

**Interfaces:**
- Consumes: complete implementation and generated artifact.
- Produces: fresh evidence that tests, lint, drift, and documented behavior agree.

- [ ] **Step 1: Run the full Python test suite**

Run:

```bash
python -m pytest -v
```

Expected: zero failures.

- [ ] **Step 2: Run generated-theme drift verification**

Run:

```bash
python scripts/build_themes.py --check
```

Expected: exit 0 with no generated diff.

- [ ] **Step 3: Run YAML lint**

Run:

```bash
yamllint tokens/ themes/ demo/ .github/
```

Expected: exit 0. If `yamllint` is unavailable, install project development dependencies with `python -m pip install -e ".[dev]"` and rerun.

- [ ] **Step 4: Run JavaScript tests**

Run:

```bash
npm run test:js
```

Expected: all dropdown lifecycle and popup-blur tests pass. If Node/npm is unavailable in the environment, report that limitation explicitly rather than claiming JavaScript verification passed.

- [ ] **Step 5: Run a final generated-output invariant check**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml

themes = yaml.safe_load(Path("themes/glass.yaml").read_text())
clear = [
    "Glass",
    "Glass Light",
    "Glass Dark",
    "Liquid Glass",
    "Liquid Glass Light",
    "Liquid Glass Dark",
]
for name in clear:
    entry = themes[name]
    values = [(k, v) for k, v in entry.items() if k != "modes"]
    for payload in entry.get("modes", {}).values():
        values.extend(payload.items())
    for key, value in values:
        assert "backdrop-filter" not in key, (name, key)
        assert "backdrop-filter" not in str(value), (name, key)
        assert "blur(" not in str(value), (name, key)

assert themes["Glass Light"]["ha-card-background"] == "rgba(255, 255, 255, 0.14)"
assert themes["Glass Dark"]["ha-card-background"] == "rgba(90, 90, 94, 0.16)"
assert themes["Liquid Glass Light"]["ha-card-background"] == "rgba(255, 255, 255, 0.11)"
assert themes["Liquid Glass Dark"]["ha-card-background"] == "rgba(90, 90, 94, 0.13)"
assert themes["Glass Light Lite"]["ha-card-background"] == "rgba(242, 242, 247, 0.72)"
assert "blur(40px)" in themes["Frosted Glass Light"]["ha-card-backdrop-filter"]
assert "blur(40px)" in themes["Frosted Glass Dark"]["ha-card-backdrop-filter"]
print("clear, Lite, and Frosted invariants verified")
PY
```

Expected: `clear, Lite, and Frosted invariants verified`.

- [ ] **Step 6: Inspect the complete diff and repository status**

Run:

```bash
git diff --check
git diff --stat
git status --short
```

Expected: no whitespace errors, no unrelated files, no secrets, and no commit created.

- [ ] **Step 7: Perform Home Assistant visual verification when available**

Using `demo/dashboard.yaml`, verify:

1. Glass and Liquid Glass cards remain translucent but do not diffuse or blur the gradient behind them.
2. Their dialogs, headers, sidebars, sheets, and scrims have no backdrop blur.
3. Glass Lite is visibly more opaque than Glass and remains unblurred.
4. Frosted Glass retains diffuse card/dialog/header/sidebar blur.
5. With `glass-dropdown.js` enabled, an opened dropdown under Glass or Liquid Glass alone receives Frosted fill and 20px popup blur.
6. Closing the dropdown leaves cards and closed fields unblurred.
7. Switching themes removes dropdown-owned styles according to the existing lifecycle behavior.

If a Home Assistant instance is unavailable, report manual visual verification as outstanding; do not infer it from unit tests.
