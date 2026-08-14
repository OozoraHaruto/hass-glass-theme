from pathlib import Path

import pytest

from glassbuild.color import rgba_str
from glassbuild.materials import derive
from glassbuild.tokens import MATERIALS, MODES, load_tokens, merge
from glassbuild.variables import build_variables

ROOT = Path(__file__).resolve().parents[1]

MERGED = {
    "radius": {"card": "18px", "dialog": "28px", "control": "12px", "pill": "980px"},
    "shadow": "0 1px 2px rgba(0, 0, 0, 0.04), 0 8px 32px rgba(0, 0, 0, 0.12)",
    "font": {
        "stack": "-apple-system, system-ui, sans-serif",
        "stack_code": "ui-monospace, SFMono-Regular, monospace",
        "tracking_headline": "-0.4px",
        "tracking_body": "-0.2px",
    },
    "motion": {"duration": "300ms", "easing": "cubic-bezier(0.25, 0.1, 0.25, 1)"},
    "material": {
        "name": "Glass",
        "surface_backdrop": False,
        "blur_px": 8,
        "saturate_pct": 180,
        "rim_alpha": 0.45,
        "edge_scale": 1.0,
        "fill_rgb": [255, 255, 255],
        "fill_alpha_glass": 0.14,
        "fill_alpha_frosted": 0.45,
        "rim_rgb": [255, 255, 255],
        "brightness_pct": 60,
        "contrast_pct": 110,
        "highlight_rgb": [255, 255, 255],
        "highlight_alpha": 0.28,
        "shade_rgb": [0, 0, 0],
        "shade_alpha": 0.22,
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


def test_code_font_family_is_monospace_and_distinct_from_body():
    v = _vars()
    assert v["ha-font-family-code"] == "ui-monospace, SFMono-Regular, monospace"
    assert v["ha-font-family-body"] == "-apple-system, system-ui, sans-serif"
    assert v["ha-font-family-code"] != v["ha-font-family-body"]


def test_clear_card_uses_the_low_opacity_full_material_without_blur():
    v = _vars()
    assert v["ha-card-background"] == "rgba(255, 255, 255, 0.14)"
    assert "ha-card-backdrop-filter" not in v
    assert v["ha-card-border-radius"] == "18px"
    assert v["ha-card-border-color"] == "rgba(255, 255, 255, 0.45)"


def test_card_shadow_leads_with_the_specular_edge():
    """The inset edge has to precede the drop shadow.

    Box shadows paint first-to-last with the *first* on top, so an edge
    listed after the drop shadow would be painted under it and lose its
    crispness at the corners.
    """
    v = _vars()
    assert v["ha-card-box-shadow"] == (
        "inset 0 1px 0 0 rgba(255, 255, 255, 0.28), "
        "inset 0 -1px 0 0 rgba(0, 0, 0, 0.22), "
        "0 1px 2px rgba(0, 0, 0, 0.04), 0 8px 32px rgba(0, 0, 0, 0.12)"
    )


def test_lite_cards_keep_the_specular_edge():
    v = _vars(lite=True)
    assert "ha-card-backdrop-filter" not in v
    assert v["ha-card-box-shadow"].startswith("inset 0 1px 0 0")


def test_clear_dialog_omits_the_native_backdrop_variable():
    v = _vars()
    assert "ha-dialog-surface-backdrop-filter" not in v
    assert v["ha-dialog-border-radius"] == "28px"


def test_dense_surfaces_are_opaque():
    v = _vars()
    assert v["code-editor-background-color"] == "#1C1C1E"
    assert v["data-table-background-color"] == "#1C1C1E"
    assert v["markdown-code-background-color"] == "#1C1C1E"


def test_controls_use_the_light_material():
    """The glass light.fill survives on the slider's secondary track (it sits
    over the card's blurred backdrop, so it can stay translucent), but the
    form-field keys no longer use it -- they collapsed onto the frosted
    select_fill (see test_legacy_form_fields_share_the_frosted_value). This
    test pins the one place the glass fill did survive, so a future retarget
    does not silently drop the light material from controls entirely.
    """
    v = _vars()
    assert v["slider-secondary-color"] == "rgba(255, 255, 255, 0.22)"
    # Form fields are no longer glass -- they are the frosted value now.
    assert v["input-fill-color"] != "rgba(255, 255, 255, 0.22)"
    assert v["mdc-text-field-fill-color"] != "rgba(255, 255, 255, 0.22)"


def test_select_fill_is_frosted_tinted():
    """The closed select box's fill is the fixture's own fill_rgb at the
    no-blur legibility-floor alpha (select_fill_alpha), not the opaque
    surface. The form-field keys (input-fill-color, mdc-text-field-fill-color,
    ha-color-form-background) now share that same frosted value -- the
    glass-vs-frosted split moved to cards vs form fields, so the text field
    no longer stays on the glass light.fill.

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
    # The form-field keys collapsed onto the one frosted value: the text field
    # now carries the same no-blur legible fill as the select, not the glass
    # light.fill it used before. The glass look survives on the card
    # (ha-card-background) and slider-secondary, which still read light.fill.
    assert v["mdc-text-field-fill-color"] == v["mdc-select-fill-color"]
    assert v["input-fill-color"] == v["mdc-select-fill-color"]
    assert v["ha-color-form-background"] == v["mdc-select-fill-color"]


def test_modern_form_fields_are_frosted_via_the_real_hook():
    """The modern ha-select (and modern text inputs/textareas/time inputs)
    paint from --ha-color-form-background, NOT --mdc-select-fill-color. The
    theme must emit that key with the frosted form-fill value, or the modern
    dropdown renders Home Assistant's flat default and stays clear -- the bug
    this change fixes. Verified against home-assistant/frontend dev:
    ha-picker-field.ts:137 `background-color: var(--ha-color-form-background)`;
    mdc-select-fill-color is consumed only by color.globals.ts (legacy default)
    and ha-onboarding.ts (set to none), never by the modern select.
    """
    from glassbuild.materials import select_fill_alpha

    v = _vars()
    fill_rgb = MERGED["material"]["fill_rgb"]
    expected = (
        f"rgba({fill_rgb[0]}, {fill_rgb[1]}, {fill_rgb[2]}, "
        f"{f'{select_fill_alpha(fill_rgb):.3f}'.rstrip('0').rstrip('.')})"
    )
    assert v["ha-color-form-background"] == expected
    # The modern hook carries the SAME frosted value as the legacy select key.
    assert v["ha-color-form-background"] == v["mdc-select-fill-color"]


def test_form_field_hover_is_lifted_and_disabled_clamps_to_resting():
    """Hover lifts the fill alpha by LIGHT_ALPHA_BONUS (the codebase's existing
    idiom, shared with the light-material bonus) so a hovered field reads
    heavier, not flat. Disabled clamps back to resting -- the components dim
    disabled fields with opacity: 0.5 (ha-picker-field.ts:131-133,
    ha-input.ts:459, ha-textarea.ts:286), so the fill itself should not move.
    """
    from glassbuild.materials import LIGHT_ALPHA_BONUS, select_fill_alpha

    v = _vars()
    fill_rgb = MERGED["material"]["fill_rgb"]
    rest = select_fill_alpha(fill_rgb)
    hover = min(1.0, rest + LIGHT_ALPHA_BONUS)
    fmt = lambda a: f"{a:.3f}".rstrip("0").rstrip(".")
    assert v["ha-color-form-background-hover"] == (
        f"rgba({fill_rgb[0]}, {fill_rgb[1]}, {fill_rgb[2]}, {fmt(hover)})"
    )
    assert v["ha-color-form-background-disabled"] == (
        f"rgba({fill_rgb[0]}, {fill_rgb[1]}, {fill_rgb[2]}, {fmt(rest)})"
    )


def test_legacy_form_fields_share_the_frosted_value():
    """input-fill-color is the hub of HA's legacy alias chain (color.globals.ts
    derives --table-header-background-color, --mdc-text-field-fill-color, and
    --mdc-select-fill-color from var(--input-fill-color)), so retargeting it
    frosts legacy MDC text fields, expansion panels, config-panel pickers, and
    calendar/schedule headers. It and mdc-text-field-fill-color must carry the
    frosted value, not the see-through glass light.fill (0.22/0.24) they use
    today -- that was the original 'too transparent' complaint on surfaces the
    user never named.
    """
    from glassbuild.materials import select_fill_alpha

    v = _vars()
    fill_rgb = MERGED["material"]["fill_rgb"]
    expected = (
        f"rgba({fill_rgb[0]}, {fill_rgb[1]}, {fill_rgb[2]}, "
        f"{f'{select_fill_alpha(fill_rgb):.3f}'.rstrip('0').rstrip('.')})"
    )
    assert v["input-fill-color"] == expected
    assert v["mdc-text-field-fill-color"] == expected
    assert v["input-fill-color"] == v["ha-color-form-background"]


def test_background_is_a_gradient():
    v = _vars()
    assert "gradient" in v["lovelace-background"]
    assert "#101014" in v["lovelace-background"]


_BACKDROP_FILTER_KEYS = (
    "ha-card-backdrop-filter",
    "ha-dialog-surface-backdrop-filter",
    "app-header-backdrop-filter",
    "ha-bottom-sheet-surface-backdrop-filter",
    "ha-dialog-scrim-backdrop-filter",
    "dialog-backdrop-filter",
    "ha-bottom-sheet-scrim-backdrop-filter",
)


def test_lite_omits_every_backdrop_filter_key():
    v = _vars(lite=True)
    for key in _BACKDROP_FILTER_KEYS:
        assert key not in v, key
    assert not [key for key in v if "backdrop-filter" in key]


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


def test_lite_still_defines_the_card_background():
    v = _vars(lite=True)
    assert v["ha-card-background"] == "rgba(28, 28, 30, 0.72)"


@pytest.mark.parametrize("material", ["glass", "liquid-glass"])
@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("lite", [False, True])
def test_glass_materials_publish_the_frosted_dropdown_surface(material, mode, lite):
    tokens = load_tokens(ROOT)
    merged = merge(tokens["base"], tokens["materials"][material], tokens["modes"][mode])
    variables = build_variables(merged, derive(merged, material, lite=lite))
    r, g, b = merged["material"]["fill_rgb"]
    expected = rgba_str(r, g, b, merged["material"]["fill_alpha_frosted"])
    assert variables["ha-glass-dropdown-surface"] == expected


@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("lite", [False, True])
def test_frosted_glass_does_not_publish_a_dropdown_override(mode, lite):
    tokens = load_tokens(ROOT)
    merged = merge(
        tokens["base"], tokens["materials"]["frosted-glass"], tokens["modes"][mode]
    )
    variables = build_variables(merged, derive(merged, "frosted-glass", lite=lite))
    assert "ha-glass-dropdown-surface" not in variables


EXPECTED_BASE_KEY_COUNT = 74
EXPECTED_BACKDROP_FILTER_KEY_COUNT = 7
EXPECTED_DROPDOWN_SURFACE_KEY_COUNT = 1


def test_real_tokens_produce_valid_variables_for_every_combination():
    tokens = load_tokens(ROOT)
    for material in MATERIALS:
        for mode in MODES:
            merged = merge(
                tokens["base"], tokens["materials"][material], tokens["modes"][mode]
            )
            for lite in (False, True):
                v = build_variables(merged, derive(merged, material, lite=lite))
                for key, value in v.items():
                    assert isinstance(key, str), (material, mode, lite, key)
                    assert isinstance(value, str), (material, mode, lite, key)
                    assert not key.startswith("--"), (material, mode, lite, key)
                eligible = merged["material"]["name"] in {"Glass", "Liquid Glass"}
                uses_backdrop = (
                    bool(merged["material"]["surface_backdrop"]) and not lite
                )
                dropdown_surface_count = (
                    EXPECTED_DROPDOWN_SURFACE_KEY_COUNT if eligible else 0
                )
                backdrop_filter_count = (
                    EXPECTED_BACKDROP_FILTER_KEY_COUNT if uses_backdrop else 0
                )
                expected = (
                    EXPECTED_BASE_KEY_COUNT
                    + dropdown_surface_count
                    + backdrop_filter_count
                )
                assert len(v) == expected, (material, mode, lite, sorted(v))
                assert ("ha-glass-dropdown-surface" in v) == eligible
                assert "ha-glass-refraction-backdrop" not in v
                assert "ha-glass-refraction-scale" not in v
                assert "ha-glass-refraction-edge" not in v
