"""WCAG AA contrast checks for every entry.

Text sits on the card fill, which sits on the dashboard gradient. The gradient
is approximated by its three stops (start, middle, and end); body text must
clear 4.5:1 against all three, so the check holds wherever on the gradient a
card lands.
"""

from pathlib import Path

import pytest

from glassbuild.color import composite, contrast_ratio, parse_rgba
from glassbuild.emit import ENTRY_NAMES, MATERIAL_LABEL, build_themes
from glassbuild.tokens import MATERIALS, MODES, load_tokens, merge

ROOT = Path(__file__).resolve().parents[1]

BODY_MIN = 4.5
LARGE_MIN = 3.0


def _gradient_stops(mode: str) -> list[tuple[int, int, int, float]]:
    tokens = load_tokens(ROOT)
    palette = merge(tokens["base"], tokens["modes"][mode])["palette"]
    return [
        parse_rgba(palette[key])
        for key in ("background_from", "background_via", "background_to")
    ]


def _entry_payload(themes: dict, name: str, mode: str) -> dict[str, str]:
    entry = themes[name]
    flat = {k: v for k, v in entry.items() if k != "modes"}
    if "modes" in entry:
        flat.update(entry["modes"][mode])
    return flat


def _mode_for(name: str) -> list[str]:
    if " Light" in name:
        return ["light"]
    if " Dark" in name:
        return ["dark"]
    return list(MODES)


@pytest.fixture(scope="module")
def themes():
    return build_themes(ROOT)


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_body_text_clears_wcag_aa(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        card = parse_rgba(payload["ha-card-background"])
        text = parse_rgba(payload["primary-text-color"])
        for stop in _gradient_stops(mode):
            surface = composite(card, stop)
            composited_text = composite(text, surface)
            ratio = contrast_ratio(composited_text[:3], surface[:3])
            assert ratio >= BODY_MIN, (
                f"{name} ({mode}): primary text on card over {stop[:3]} "
                f"is {ratio:.2f}:1, need {BODY_MIN}:1"
            )


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_secondary_text_clears_large_text_minimum(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        card = parse_rgba(payload["ha-card-background"])
        text = parse_rgba(payload["secondary-text-color"])
        for stop in _gradient_stops(mode):
            surface = composite(card, stop)
            composited_text = composite(text, surface)
            ratio = contrast_ratio(composited_text[:3], surface[:3])
            assert ratio >= LARGE_MIN, (
                f"{name} ({mode}): secondary text is {ratio:.2f}:1, "
                f"need {LARGE_MIN}:1"
            )


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("material", MATERIALS)
def test_accent_clears_large_text_minimum_on_the_card(themes, material, mode):
    # Looked up rather than branched on. This was `"Glass" if material ==
    # "glass" else "Frosted Glass"`, which silently stopped covering anything
    # new the moment a third material was added: liquid-glass fell into the
    # else and re-tested Frosted Glass, so the parametrisation grew a case
    # while the assertions covered one fewer material than before.
    name = MATERIAL_LABEL[material]
    payload = _entry_payload(themes, name, mode)
    card = parse_rgba(payload["ha-card-background"])
    accent = parse_rgba(payload["primary-color"])
    for stop in _gradient_stops(mode):
        surface = composite(card, stop)
        ratio = contrast_ratio(composite(accent, surface)[:3], surface[:3])
        assert ratio >= LARGE_MIN, (
            f"{name} ({mode}): accent is {ratio:.2f}:1, need {LARGE_MIN}:1"
        )


# ---- sidebar ---------------------------------------------------------------
#
# The sidebar sits outside Lovelace views entirely -- it is not a card and
# never lands on the dashboard gradient. It also isn't limited to a bounded
# set of gradient stops the way a card is: it sits over *arbitrary* dashboard
# content, which nothing here can enumerate. So instead of a specific
# backdrop, these tests use the two adversarial extremes -- pure black and
# pure white -- that bound every possible backdrop's luminance. Clearing the
# thresholds against both is a real (falsifiable) proxy for "legible over
# arbitrary content behind it": weakening the fill alpha or the text/icon
# colours pushes one of the two extremes below the floor.
_ADVERSARIAL_BACKDROPS: list[tuple[int, int, int, float]] = [
    (0, 0, 0, 1.0),
    (255, 255, 255, 1.0),
]


def _sidebar_surfaces(payload: dict[str, str]) -> list[tuple[int, int, int, float]]:
    fill = parse_rgba(payload["sidebar-background-color"])
    return [composite(fill, backdrop) for backdrop in _ADVERSARIAL_BACKDROPS]


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_sidebar_text_clears_wcag_aa(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        text = parse_rgba(payload["sidebar-text-color"])
        for surface in _sidebar_surfaces(payload):
            ratio = contrast_ratio(composite(text, surface)[:3], surface[:3])
            assert ratio >= BODY_MIN, (
                f"{name} ({mode}): sidebar text on the sidebar fill over "
                f"{surface[:3]} is {ratio:.2f}:1, need {BODY_MIN}:1"
            )


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_sidebar_icon_clears_large_text_minimum(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        icon = parse_rgba(payload["sidebar-icon-color"])
        for surface in _sidebar_surfaces(payload):
            ratio = contrast_ratio(composite(icon, surface)[:3], surface[:3])
            assert ratio >= LARGE_MIN, (
                f"{name} ({mode}): sidebar icon on the sidebar fill over "
                f"{surface[:3]} is {ratio:.2f}:1, need {LARGE_MIN}:1"
            )


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_sidebar_selected_text_clears_large_text_minimum(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        text = parse_rgba(payload["sidebar-selected-text-color"])
        for surface in _sidebar_surfaces(payload):
            ratio = contrast_ratio(composite(text, surface)[:3], surface[:3])
            assert ratio >= LARGE_MIN, (
                f"{name} ({mode}): sidebar selected text on the sidebar "
                f"fill over {surface[:3]} is {ratio:.2f}:1, need {LARGE_MIN}:1"
            )


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_sidebar_selected_icon_clears_large_text_minimum(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        icon = parse_rgba(payload["sidebar-selected-icon-color"])
        for surface in _sidebar_surfaces(payload):
            ratio = contrast_ratio(composite(icon, surface)[:3], surface[:3])
            assert ratio >= LARGE_MIN, (
                f"{name} ({mode}): sidebar selected icon on the sidebar "
                f"fill over {surface[:3]} is {ratio:.2f}:1, need {LARGE_MIN}:1"
            )
