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


def test_document_insertion_order_matches_entry_names(themes):
    # A later task serialises this dict without sorting its keys, so
    # insertion order must be the canonical matrix order, not just the set
    # of keys.
    assert list(themes) == list(ENTRY_NAMES)


@pytest.mark.parametrize("name", ["Glass", "Frosted Glass", "Glass Lite"])
def test_auto_entries_have_a_modes_block(themes, name):
    assert set(themes[name]["modes"]) == {"light", "dark"}


@pytest.mark.parametrize(
    "name", ["Glass Light", "Glass Dark", "Frosted Glass Light", "Glass Dark Lite"]
)
def test_flat_entries_have_no_modes_block(themes, name):
    assert "modes" not in themes[name]


def _flatten_entry(entry: dict) -> list[tuple[str, object]]:
    """All (key, value) pairs in an entry: its top level plus, for Auto
    entries, both of its nested ``modes`` payloads. Purity checks (no
    card-mod, no backdrop-filter) must hold everywhere a Lite entry could
    hide a value, not just at the top level.
    """
    pairs = [(k, v) for k, v in entry.items() if k != "modes"]
    for mode_payload in entry.get("modes", {}).values():
        pairs.extend(mode_payload.items())
    return pairs


_CARDMOD_KEYS = {"card-mod-theme", "card-mod-root-yaml", "card-mod-sidebar-yaml"}


def test_lite_entries_have_no_cardmod_keys(themes):
    for name in ENTRY_NAMES:
        if not name.endswith("Lite"):
            continue
        keys = {k for k, _ in _flatten_entry(themes[name])}
        assert not keys & _CARDMOD_KEYS, (name, keys & _CARDMOD_KEYS)


def test_full_entries_have_cardmod_keys(themes):
    assert themes["Glass"]["card-mod-theme"] == "Glass"
    assert themes["Frosted Glass Dark"]["card-mod-theme"] == "Frosted Glass Dark"


def test_frosted_uses_its_own_blur(themes):
    assert "blur(40px)" in themes["Frosted Glass Dark"]["ha-card-backdrop-filter"]
    assert "blur(28px)" in themes["Glass Dark"]["ha-card-backdrop-filter"]


def test_lite_entries_have_no_backdrop_filter_anywhere(themes):
    # Load-bearing per the brief: a later task hard-fails the build if any
    # backdrop-filter reaches a Lite entry. Checks both key names AND values
    # (a value could carry "backdrop-filter:" or a blur() function inside a
    # card-mod CSS blob without the key itself being named that), and walks
    # nested modes payloads as well as the top level.
    for name in ENTRY_NAMES:
        if not name.endswith("Lite"):
            continue
        for key, value in _flatten_entry(themes[name]):
            assert "backdrop-filter" not in key, (name, key)
            text = str(value)
            assert "backdrop-filter" not in text, (name, key, value)
            assert "blur(" not in text, (name, key, value)


def test_auto_entries_match_ha_real_merge_algorithm_against_the_flat_entries(themes):
    # Reviewer finding: this test replaces a since-deleted pair,
    # `test_auto_light_payload_matches_the_flat_light_entry` and
    # `test_auto_dark_payload_matches_the_flat_dark_entry`, which only
    # iterated the `modes` payload, so a value hoisted to the top level (or
    # wrongly *not* hoisted) would never be checked -- that's exactly the
    # shape of bug the original dark-frozen card-mod implementation had, and
    # it would have passed both of those tests. Deleted rather than kept
    # side by side: everything they checked (Glass auto vs. Glass Light /
    # Glass Dark, one direction only) is a strict subset of what this test
    # checks (all four Auto/Lite pairs, both modes, full dict equality in
    # both directions via HA's real merge algorithm), so keeping them added
    # no coverage, only a slower, weaker duplicate to maintain. This test
    # applies HA's actual runtime algorithm confirmed in
    # src/common/dom/apply_themes_on_element.ts:120-130 -- `{...base,
    # ...modes[mode]}` -- and asserts the result equals the corresponding
    # flat entry exactly.
    #
    # `card-mod-theme` is excluded because it is each entry's own
    # self-reference name (the Auto entry's card-mod-theme is intentionally
    # its own name, e.g. "Glass", not "Glass Light"/"Glass Dark") --
    # verified by hand that it is the ONLY key that differs for any pair
    # below; every other key, including the mode-dependent card-mod CSS
    # blobs, must match exactly.
    pairs = [
        ("Glass", "Glass Light", "Glass Dark"),
        ("Glass Lite", "Glass Light Lite", "Glass Dark Lite"),
        ("Frosted Glass", "Frosted Glass Light", "Frosted Glass Dark"),
        ("Frosted Glass Lite", "Frosted Glass Light Lite", "Frosted Glass Dark Lite"),
    ]
    for auto_name, flat_light, flat_dark in pairs:
        entry = themes[auto_name]
        base = {k: v for k, v in entry.items() if k != "modes"}
        for mode, flat_name in (("light", flat_light), ("dark", flat_dark)):
            applied = {**base, **entry["modes"][mode]}
            expected = dict(themes[flat_name])
            applied.pop("card-mod-theme", None)
            expected.pop("card-mod-theme", None)
            assert applied == expected, f"{auto_name} {mode}"
