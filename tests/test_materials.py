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


def test_light_material_halves_the_blur_radius():
    merged = {
        **MERGED,
        "material": {**MERGED["material"], "blur_px": 40, "saturate_pct": 150},
    }
    result = derive(merged, "frosted-glass", lite=False)
    assert result["light"].backdrop == "blur(20px) saturate(150%)"


def test_light_material_truncates_odd_blur():
    merged = {**MERGED, "material": {**MERGED["material"], "blur_px": 9}}
    result = derive(merged, "glass", lite=False)
    assert result["light"].backdrop == "blur(4px) saturate(180%)"


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
