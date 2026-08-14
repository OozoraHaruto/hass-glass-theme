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


MATERIAL_NAMES = {
    "glass": "Glass",
    "frosted-glass": "Frosted Glass",
    "liquid-glass": "Liquid Glass",
}


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
    assert tokens["materials"]["liquid-glass"]["material"]["surface_backdrop"] is False
    assert tokens["materials"]["frosted-glass"]["material"]["surface_backdrop"] is True


def test_tuning_table_values_match_the_spec(tokens):
    assert tokens["materials"]["glass"]["material"]["rim_alpha"] == 0.45
    assert tokens["materials"]["glass"]["material"]["edge_scale"] == 1.0
    assert tokens["materials"]["liquid-glass"]["material"]["rim_alpha"] == 0.55
    assert tokens["materials"]["liquid-glass"]["material"]["edge_scale"] == 1.2
    assert tokens["materials"]["frosted-glass"]["material"]["rim_alpha"] == 0.20
    assert tokens["materials"]["frosted-glass"]["material"]["edge_scale"] == 0.55
    assert tokens["modes"]["light"]["material"]["fill_alpha_glass"] == 0.14
    assert tokens["modes"]["light"]["material"]["fill_alpha_frosted"] == 0.55
    assert tokens["modes"]["dark"]["material"]["fill_alpha_glass"] == 0.16
    assert tokens["modes"]["dark"]["material"]["fill_alpha_frosted"] == 0.45


def test_frosted_blur_is_wide_enough_to_diffuse_content(tokens):
    material = tokens["materials"]["frosted-glass"]["material"]
    assert material["blur_px"] == 40
    assert material["saturate_pct"] == 120


@pytest.mark.parametrize("mode", MODES)
def test_glass_stays_transparent_enough_to_read_as_glass(tokens, mode):
    """The tint ceiling keeps clear Glass visually distinct from Frosted."""
    alpha = tokens["modes"][mode]["material"]["fill_alpha_glass"]
    assert alpha <= 0.18, f"{mode} glass tints at {alpha}, frosted territory"


@pytest.mark.parametrize("mode", MODES)
def test_glass_is_markedly_clearer_than_frosted(tokens, mode):
    """Two materials that measure nearly the same are one material.

    Whatever the absolute values drift to, the gap has to stay wide enough
    that a user switching entries sees a different surface rather than a
    slightly different one.
    """
    material = tokens["modes"][mode]["material"]
    assert material["fill_alpha_glass"] * 2 <= material["fill_alpha_frosted"]


@pytest.mark.parametrize("mode", MODES)
def test_the_rim_outshines_the_body(tokens, mode):
    """Glass concentrates light at its edge; frost scatters it uniformly.

    Apple draws the same distinction between lensing -- bending and
    concentrating light -- and blur, which only scatters it. Real lensing
    needs a displacement map this material deliberately does without (see
    tokens/liquid-glass.yaml), so the edge does the work instead: a rim
    brighter than the body is the refraction-free signal that a surface is
    glass rather than frost, and it only reads as one while the body stays
    dimmer than the rim.
    """
    material = tokens["modes"][mode]["material"]
    assert material["highlight_alpha"] > material["fill_alpha_glass"]


def test_dark_mode_dims_the_backdrop_without_smothering_it(tokens):
    """Frosted tuning settles the backdrop without erasing it."""
    assert tokens["modes"]["dark"]["material"]["brightness_pct"] >= 75


@pytest.mark.parametrize("mode", MODES)
def test_every_mode_supplies_the_diffusion_and_edge_tokens(tokens, mode):
    material = tokens["modes"][mode]["material"]
    for key in (
        "brightness_pct",
        "contrast_pct",
        "highlight_rgb",
        "highlight_alpha",
        "shade_rgb",
        "shade_alpha",
    ):
        assert key in material, f"{mode} mode is missing {key}"


def test_dark_mode_dims_the_backdrop_and_light_mode_lifts_it(tokens):
    """The luminance remap runs toward each mode's own base, not a shared one.

    Dark mode pulls the backdrop down and hardens it; light mode lifts it and
    softens it. Both land on a flatter field than they started from, which is
    what keeps text legible at a low fill alpha.
    """
    dark = tokens["modes"]["dark"]["material"]
    light = tokens["modes"]["light"]["material"]
    assert dark["brightness_pct"] < 100 < light["brightness_pct"]
    assert light["contrast_pct"] < 100 < dark["contrast_pct"]


def test_base_tokens_match_the_spec(tokens):
    base = tokens["base"]
    assert base["radius"]["card"] == "18px"
    assert base["radius"]["dialog"] == "28px"
    assert base["radius"]["control"] == "12px"
    assert base["radius"]["pill"] == "980px"
    assert base["shadow"] == (
        "0 1px 2px rgba(0, 0, 0, 0.04), 0 8px 32px rgba(0, 0, 0, 0.12)"
    )
    assert base["font"]["stack"] == (
        '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, '
        '"Segoe UI", Roboto, sans-serif'
    )
    assert base["font"]["stack_code"] == (
        'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace'
    )
    assert base["font"]["tracking_headline"] == "-0.4px"
    assert base["font"]["tracking_body"] == "-0.2px"
    assert base["motion"]["duration"] == "300ms"
    assert base["motion"]["easing"] == "cubic-bezier(0.25, 0.1, 0.25, 1)"


def test_light_mode_material_rgb_values_match_the_spec(tokens):
    # The rim is a dark hairline in light mode ([60, 60, 67], matching the
    # palette's divider hue) -- a white rim is invisible both on the
    # dashboard gradient and on the flat --primary-background-color page
    # background used outside dashboards. The fill stays white: it's the
    # frosted material tint, not the edge.
    material = tokens["modes"]["light"]["material"]
    assert material["fill_rgb"] == [255, 255, 255]
    assert material["rim_rgb"] == [60, 60, 67]


def test_dark_mode_material_rgb_values_match_the_spec(tokens):
    # The dark-mode fill tints dark ([90, 90, 94], i.e. #5A5A5E) -- a white
    # fill in dark mode composites to mid-grey against the dark gradient and
    # collapses contrast against light dark-mode text. The rim stays white:
    # it's the specular highlight, not the fill.
    material = tokens["modes"]["dark"]["material"]
    assert material["fill_rgb"] == [90, 90, 94]
    assert material["rim_rgb"] == [255, 255, 255]


@pytest.mark.parametrize("mode", MODES)
def test_the_specular_edge_is_white_over_black_in_both_modes(tokens, mode):
    """A lit pane catches light on top and falls into shadow underneath.

    That is true of a physical edge regardless of the ambient appearance, so
    unlike `rim_rgb` -- which flips to a dark hairline in light mode because a
    white *perimeter* is invisible there -- the highlight/shade pair keeps the
    same two colours in both modes. Only the alphas differ.
    """
    material = tokens["modes"][mode]["material"]
    assert material["highlight_rgb"] == [255, 255, 255]
    assert material["shade_rgb"] == [0, 0, 0]


def test_light_mode_leans_on_the_highlight_and_dark_mode_on_the_shade(tokens):
    dark = tokens["modes"]["dark"]["material"]
    light = tokens["modes"]["light"]["material"]
    assert light["highlight_alpha"] > dark["highlight_alpha"]
    assert dark["shade_alpha"] > light["shade_alpha"]


def test_light_palette_matches_the_spec(tokens):
    palette = tokens["modes"]["light"]["palette"]
    assert palette["accent"] == "#007AFF"
    assert palette["success"] == "#34C759"
    assert palette["warning"] == "#FF9500"
    assert palette["error"] == "#FF3B30"
    assert palette["scene"] == "#AF52DE"
    assert palette["text_primary"] == "#1C1C1E"
    assert palette["text_secondary"] == "#3C3C4399"
    assert palette["text_disabled"] == "#3C3C4361"
    assert palette["divider"] == "rgba(60, 60, 67, 0.18)"
    assert palette["opaque_surface"] == "#F2F2F7"
    assert palette["background_from"] == "#EEF2F8"
    assert palette["background_via"] == "#E6ECF6"
    assert palette["background_to"] == "#F7F4FA"


def test_dark_palette_matches_the_spec(tokens):
    palette = tokens["modes"]["dark"]["palette"]
    assert palette["accent"] == "#0A84FF"
    assert palette["success"] == "#30D158"
    assert palette["warning"] == "#FF9F0A"
    assert palette["error"] == "#FF453A"
    assert palette["scene"] == "#BF5AF2"
    assert palette["text_primary"] == "#FFFFFF"
    assert palette["text_secondary"] == "#EBEBF599"
    assert palette["text_disabled"] == "#EBEBF561"
    assert palette["divider"] == "rgba(84, 84, 88, 0.65)"
    assert palette["opaque_surface"] == "#1C1C1E"
    assert palette["background_from"] == "#101014"
    assert palette["background_via"] == "#16161C"
    assert palette["background_to"] == "#1B1620"


def test_liquid_glass_is_the_third_material(tokens):
    assert "liquid-glass" in tokens["materials"]
    assert tokens["materials"]["liquid-glass"]["material"]["name"] == "Liquid Glass"


def test_liquid_glass_declares_a_refraction_block(tokens):
    """Compatibility metadata retains the companion module's structure."""
    refraction = tokens["materials"]["liquid-glass"]["material"]["refraction"]
    assert refraction["filter_id"] == "glass-refraction"
    assert isinstance(refraction["scale"], int)
    assert refraction["scale"] > 0


def test_only_liquid_glass_declares_refraction_metadata(tokens):
    for material in ("glass", "frosted-glass"):
        assert "refraction" not in tokens["materials"][material]["material"]


@pytest.mark.parametrize("mode", MODES)
def test_liquid_glass_is_the_clearest_of_the_three(tokens, mode):
    """Its lower tint and stronger edge distinguish it from clear Glass."""
    material = tokens["modes"][mode]["material"]
    assert material["fill_alpha_liquid"] < material["fill_alpha_glass"]
