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
