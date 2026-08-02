from pathlib import Path

import pytest

from glassbuild.emit import ENTRY_NAMES, build_themes

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def themes():
    return build_themes(ROOT)


def test_all_twelve_names_present():
    assert len(ENTRY_NAMES) == 12
    assert ENTRY_NAMES == (
        "Glass",
        "Glass Light",
        "Glass Dark",
        "Glass Lite",
        "Glass Light Lite",
        "Glass Dark Lite",
        "Frosted Glass",
        "Frosted Glass Light",
        "Frosted Glass Dark",
        "Frosted Glass Lite",
        "Frosted Glass Light Lite",
        "Frosted Glass Dark Lite",
    )


def test_document_contains_exactly_those_entries(themes):
    assert set(themes) == set(ENTRY_NAMES)


@pytest.mark.parametrize("name", ["Glass", "Frosted Glass", "Glass Lite"])
def test_auto_entries_have_a_modes_block(themes, name):
    assert set(themes[name]["modes"]) == {"light", "dark"}


@pytest.mark.parametrize(
    "name", ["Glass Light", "Glass Dark", "Frosted Glass Light", "Glass Dark Lite"]
)
def test_flat_entries_have_no_modes_block(themes, name):
    assert "modes" not in themes[name]


def test_auto_light_payload_matches_the_flat_light_entry(themes):
    auto_light = themes["Glass"]["modes"]["light"]
    flat = {k: v for k, v in themes["Glass Light"].items() if k != "modes"}
    for key, value in auto_light.items():
        assert flat[key] == value, key


def test_lite_entries_have_no_cardmod_keys(themes):
    for name in ENTRY_NAMES:
        if not name.endswith("Lite"):
            continue
        assert "card-mod-theme" not in themes[name]
        assert "card-mod-root-yaml" not in themes[name]


def test_full_entries_have_cardmod_keys(themes):
    assert themes["Glass"]["card-mod-theme"] == "Glass"
    assert themes["Frosted Glass Dark"]["card-mod-theme"] == "Frosted Glass Dark"


def test_frosted_uses_its_own_blur(themes):
    assert "blur(40px)" in themes["Frosted Glass Dark"]["ha-card-backdrop-filter"]
    assert "blur(8px)" in themes["Glass Dark"]["ha-card-backdrop-filter"]


def test_auto_dark_payload_matches_the_flat_dark_entry(themes):
    # Symmetric with the light-side check above: whichever entry the user
    # picks, a given mode must render identically.
    auto_dark = themes["Glass"]["modes"]["dark"]
    flat = {k: v for k, v in themes["Glass Dark"].items() if k != "modes"}
    for key, value in auto_dark.items():
        assert flat[key] == value, key


def test_lite_entries_have_no_backdrop_filter_anywhere(themes):
    # Load-bearing per the brief: a later task hard-fails the build if any
    # backdrop-filter reaches a Lite entry, whether at the top level or
    # nested inside a modes payload.
    for name in ENTRY_NAMES:
        if not name.endswith("Lite"):
            continue
        entry = themes[name]
        flat_keys = {k for k in entry if k != "modes"}
        assert not any("backdrop-filter" in k for k in flat_keys)
        for mode_payload in entry.get("modes", {}).values():
            assert not any("backdrop-filter" in k for k in mode_payload)
