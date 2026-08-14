import pytest

from glassbuild.color import composite, contrast_ratio, parse_rgba
from glassbuild.materials import (
    FULL_FILL_ALPHA_FLOOR,
    LIGHT_ALPHA_BONUS,
    LITE_FILL_ALPHA,
    SELECT_CONTRAST_FLOOR,
    derive,
    select_fill_alpha,
)

MERGED = {
    "material": {
        "name": "Glass",
        "surface_backdrop": False,
        "blur_px": 8,
        "saturate_pct": 180,
        "rim_alpha": 0.45,
        "edge_scale": 1.0,
        "fill_rgb": [255, 255, 255],
        "fill_alpha_glass": 0.10,
        "fill_alpha_frosted": 0.55,
        "rim_rgb": [255, 255, 255],
        "brightness_pct": 60,
        "contrast_pct": 110,
        "highlight_rgb": [255, 255, 255],
        "highlight_alpha": 0.28,
        "shade_rgb": [0, 0, 0],
        "shade_alpha": 0.22,
    },
    "palette": {"opaque_surface": "#1C1C1E"},
}


def test_constants_match_the_spec():
    assert LITE_FILL_ALPHA == 0.72
    assert FULL_FILL_ALPHA_FLOOR == 0.10
    assert LIGHT_ALPHA_BONUS == 0.08


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


def test_frosted_selects_its_own_alpha():
    result = derive(MERGED, "frosted-glass", lite=False)
    assert result["full"].fill == "rgba(255, 255, 255, 0.55)"


def test_light_material_uses_bonus_alpha():
    result = derive(MERGED, "glass", lite=False)
    assert result["light"].fill == "rgba(255, 255, 255, 0.18)"


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


# ---- the specular edge -----------------------------------------------------


def test_edge_is_a_directional_inset_pair():
    """Highlight on the top edge, shade on the bottom -- never one flat rim."""
    result = derive(MERGED, "glass", lite=False)
    assert result["full"].edge == (
        "inset 0 1px 0 0 rgba(255, 255, 255, 0.28), "
        "inset 0 -1px 0 0 rgba(0, 0, 0, 0.22)"
    )


def test_edge_scale_softens_a_diffuse_material():
    merged = {**MERGED, "material": {**MERGED["material"], "edge_scale": 0.55}}
    result = derive(merged, "glass", lite=False)
    assert result["full"].edge == (
        "inset 0 1px 0 0 rgba(255, 255, 255, 0.154), "
        "inset 0 -1px 0 0 rgba(0, 0, 0, 0.121)"
    )


def test_light_material_shares_the_full_edge():
    result = derive(MERGED, "glass", lite=False)
    assert result["light"].edge == result["full"].edge


def test_lite_keeps_the_edge_despite_having_no_backdrop():
    """The edge is a box-shadow, not a backdrop-filter -- it costs Lite nothing."""
    result = derive(MERGED, "glass", lite=True)
    assert result["full"].backdrop is None
    assert result["full"].edge == (
        "inset 0 1px 0 0 rgba(255, 255, 255, 0.28), "
        "inset 0 -1px 0 0 rgba(0, 0, 0, 0.22)"
    )


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


# ---- the closed select box's no-blur legibility floor --------------------


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
