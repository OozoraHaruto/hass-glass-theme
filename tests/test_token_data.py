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
    assert isinstance(merged["material"]["blur_px"], int)
    assert isinstance(merged["material"]["saturate_pct"], int)
    for key in ("accent", "text_primary", "opaque_surface", "background_from"):
        assert key in merged["palette"]


def test_tuning_table_values_match_the_spec(tokens):
    assert tokens["materials"]["glass"]["material"]["blur_px"] == 20
    assert tokens["materials"]["glass"]["material"]["saturate_pct"] == 140
    assert tokens["materials"]["glass"]["material"]["rim_alpha"] == 0.45
    assert tokens["materials"]["glass"]["material"]["edge_scale"] == 1.0
    assert tokens["materials"]["frosted-glass"]["material"]["blur_px"] == 40
    assert tokens["materials"]["frosted-glass"]["material"]["saturate_pct"] == 120
    assert tokens["materials"]["frosted-glass"]["material"]["rim_alpha"] == 0.20
    assert tokens["materials"]["frosted-glass"]["material"]["edge_scale"] == 0.55
    assert tokens["modes"]["light"]["material"]["fill_alpha_glass"] == 0.14
    assert tokens["modes"]["light"]["material"]["fill_alpha_frosted"] == 0.55
    assert tokens["modes"]["dark"]["material"]["fill_alpha_glass"] == 0.16
    assert tokens["modes"]["dark"]["material"]["fill_alpha_frosted"] == 0.45


def test_glass_blur_is_wide_enough_to_diffuse_content(tokens):
    """Enough diffusion to destroy detail behind the card -- and no more.

    At the original 8px the backdrop kept its shapes and stayed legible
    straight through the card. But blur is a *scattering* operation, and
    scattering is what frosted glass does: pushed far enough it flattens the
    backdrop into a milky field no amount of low tint can rescue. 16px is the
    floor where detail reliably stops resolving; the ceiling is a judgement
    call left to the tuning table rather than pinned here.
    """
    for material in MATERIALS:
        blur = tokens["materials"][material]["material"]["blur_px"]
        assert blur >= 16, f"{material} blurs at {blur}px, too little to diffuse"


def test_saturation_never_amplifies_the_backdrop(tokens):
    """Apple's materials compress chroma toward neutral; they don't boost it.

    Anything much above 100% pulls the eye to what's *behind* the card rather
    than what's on it -- the web-glassmorphism trope this theme is not.
    """
    for material in MATERIALS:
        saturate = tokens["materials"][material]["material"]["saturate_pct"]
        assert 100 <= saturate <= 140, f"{material} saturates at {saturate}%"


@pytest.mark.parametrize("mode", MODES)
def test_glass_stays_transparent_enough_to_read_as_glass(tokens, mode):
    """The tint ceiling is what stops Glass sliding back into Frosted.

    Legibility on this material is bought by diffusion -- the blur and the
    luminance remap -- not by tint. Reaching for the fill alpha to fix a
    legibility complaint is the wrong lever, and doing exactly that (0.30
    dark / 0.26 light) produced a material indistinguishable from frosted.
    Apple made the same mistake in iOS 26 beta 3 and reverted it in beta 4.
    """
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
    """A hard dim is a scattering operation in disguise.

    brightness(60%) crushed everything behind the card toward black, which
    reads as milk rather than as depth however low the fill alpha goes. The
    remap should settle the backdrop *behind* the surface, not erase it.
    """
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
    """The block is what makes this material *refractive* rather than named so.

    ``glassbuild/variables.py`` gates the extra refraction variable on the
    presence of this block, not on the material's name -- so a material that
    grows one becomes refractive and a material that loses one stops being,
    with no name matching anywhere in the build.
    """
    refraction = tokens["materials"]["liquid-glass"]["material"]["refraction"]
    assert refraction["filter_id"] == "glass-refraction"
    assert isinstance(refraction["scale"], int)
    assert refraction["scale"] > 0


def test_only_liquid_glass_refracts(tokens):
    for material in ("glass", "frosted-glass"):
        assert "refraction" not in tokens["materials"][material]["material"]


@pytest.mark.parametrize("mode", MODES)
def test_liquid_glass_is_the_clearest_of_the_three(tokens, mode):
    """Its whole reason to exist is being clearer than Glass.

    It can afford to be: the lensed rim concentrates light where a flat
    material has to spend tint to separate itself from its backdrop. If this
    ever inverts, the entry is just Glass with extra install steps.
    """
    material = tokens["modes"][mode]["material"]
    assert material["fill_alpha_liquid"] < material["fill_alpha_glass"]


@pytest.mark.parametrize("mode", MODES)
def test_liquid_glass_still_blurs_enough_to_stand_alone(tokens, mode):
    """The refraction is an upgrade, not a load-bearing part of legibility.

    Most installs will never load the companion module, so the entry has to
    be a usable material on blur alone. That is why ``blur_px`` here sits
    near Glass's rather than near zero: a genuinely clear pane plus no
    displacement is an unreadable card, not a transparent one.
    """
    blur = tokens["materials"]["liquid-glass"]["material"]["blur_px"]
    assert blur >= 16
