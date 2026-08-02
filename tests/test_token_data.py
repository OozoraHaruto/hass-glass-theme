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


MATERIAL_NAMES = {"glass": "Glass", "frosted-glass": "Frosted Glass"}


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
    assert tokens["materials"]["glass"]["material"]["blur_px"] == 8
    assert tokens["materials"]["glass"]["material"]["saturate_pct"] == 180
    assert tokens["materials"]["glass"]["material"]["rim_alpha"] == 0.45
    assert tokens["materials"]["frosted-glass"]["material"]["blur_px"] == 40
    assert tokens["materials"]["frosted-glass"]["material"]["saturate_pct"] == 150
    assert tokens["materials"]["frosted-glass"]["material"]["rim_alpha"] == 0.20
    assert tokens["modes"]["light"]["material"]["fill_alpha_glass"] == 0.10
    assert tokens["modes"]["light"]["material"]["fill_alpha_frosted"] == 0.55
    assert tokens["modes"]["dark"]["material"]["fill_alpha_glass"] == 0.14
    assert tokens["modes"]["dark"]["material"]["fill_alpha_frosted"] == 0.14


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


@pytest.mark.parametrize("mode", MODES)
def test_mode_material_rgb_values_match_the_spec(tokens, mode):
    material = tokens["modes"][mode]["material"]
    assert material["fill_rgb"] == [255, 255, 255]
    assert material["rim_rgb"] == [255, 255, 255]


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
