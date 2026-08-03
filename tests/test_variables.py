from pathlib import Path

from glassbuild.materials import derive
from glassbuild.tokens import MATERIALS, MODES, load_tokens, merge
from glassbuild.variables import build_variables

ROOT = Path(__file__).resolve().parents[1]

MERGED = {
    "radius": {"card": "18px", "dialog": "28px", "control": "12px", "pill": "980px"},
    "shadow": "0 1px 2px rgba(0, 0, 0, 0.04), 0 8px 32px rgba(0, 0, 0, 0.12)",
    "font": {
        "stack": '-apple-system, system-ui, sans-serif',
        "stack_code": "ui-monospace, SFMono-Regular, monospace",
        "tracking_headline": "-0.4px",
        "tracking_body": "-0.2px",
    },
    "motion": {"duration": "300ms", "easing": "cubic-bezier(0.25, 0.1, 0.25, 1)"},
    "material": {
        "name": "Glass",
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


def test_card_uses_the_full_material():
    v = _vars()
    assert v["ha-card-background"] == "rgba(255, 255, 255, 0.14)"
    assert v["ha-card-backdrop-filter"] == (
        "blur(8px) saturate(180%) brightness(60%) contrast(110%)"
    )
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


def test_dialog_uses_the_native_backdrop_variable():
    v = _vars()
    assert v["ha-dialog-surface-backdrop-filter"] == (
        "blur(8px) saturate(180%) brightness(60%) contrast(110%)"
    )
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


def test_full_material_includes_every_backdrop_filter_key():
    v = _vars(lite=False)
    full_backdrop = "blur(8px) saturate(180%) brightness(60%) contrast(110%)"
    # light material: half blur, same diffusion terms
    scrim_backdrop = "blur(4px) saturate(180%) brightness(60%) contrast(110%)"
    assert v["ha-card-backdrop-filter"] == full_backdrop
    assert v["ha-dialog-surface-backdrop-filter"] == full_backdrop
    assert v["app-header-backdrop-filter"] == full_backdrop
    assert v["ha-bottom-sheet-surface-backdrop-filter"] == full_backdrop
    assert v["ha-dialog-scrim-backdrop-filter"] == scrim_backdrop
    assert v["dialog-backdrop-filter"] == scrim_backdrop
    assert v["ha-bottom-sheet-scrim-backdrop-filter"] == scrim_backdrop


def test_lite_still_defines_the_card_background():
    v = _vars(lite=True)
    assert v["ha-card-background"] == "rgba(28, 28, 30, 0.72)"


# 71 base keys + 7 conditional backdrop-filter keys (full material only).
EXPECTED_FULL_KEY_COUNT = 78
EXPECTED_LITE_KEY_COUNT = 71
# ...plus the three --ha-glass-refraction-* keys (the alternative backdrop
# chain, and the displacement scale and edge fraction the companion module
# reads), for a full material whose tuning table carries a `refraction`
# block. Counted from the same token data the build reads rather than from a
# list of material names, so this stays a check on the *rule* ("a refraction
# block adds exactly these keys, and only on full") rather than on today's
# roster of materials.
EXPECTED_REFRACTION_KEY_COUNT = 3


def test_real_tokens_produce_valid_variables_for_every_combination():
    tokens = load_tokens(ROOT)
    for material in MATERIALS:
        for mode in MODES:
            merged = merge(tokens["base"], tokens["materials"][material], tokens["modes"][mode])
            for lite in (False, True):
                v = build_variables(merged, derive(merged, material, lite=lite))
                for key, value in v.items():
                    assert isinstance(key, str), (material, mode, lite, key)
                    assert isinstance(value, str), (material, mode, lite, key)
                    assert not key.startswith("--"), (material, mode, lite, key)
                refracts = "refraction" in merged["material"]
                if lite:
                    expected = EXPECTED_LITE_KEY_COUNT
                else:
                    expected = EXPECTED_FULL_KEY_COUNT + (
                        EXPECTED_REFRACTION_KEY_COUNT if refracts else 0
                    )
                assert len(v) == expected, (material, mode, lite, sorted(v))
                # Lite has no backdrop-filter at all, so there is nothing for
                # a displacement to run in front of -- the refraction
                # variable must not survive the lite gate even for a material
                # that declares one.
                assert ("ha-glass-refraction-backdrop" in v) == (refracts and not lite)
