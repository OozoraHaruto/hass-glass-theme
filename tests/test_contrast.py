"""WCAG AA contrast checks for every entry.

Text sits on the card fill, which sits on the dashboard gradient. The gradient
is approximated by its three stops (start, middle, and end); body text must
clear 4.5:1 against all three, so the check holds wherever on the gradient a
card lands.
"""

from pathlib import Path

import pytest

from glassbuild.color import composite, contrast_ratio, parse_rgba
from glassbuild.emit import ENTRY_NAMES, build_themes
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
    name = "Glass" if material == "glass" else "Frosted Glass"
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
# never lands on the dashboard gradient, so unlike everything above, its
# backdrop here is `primary-background-color`, not a gradient stop.


def _sidebar_surface(payload: dict[str, str]) -> tuple[int, int, int, float]:
    fill = parse_rgba(payload["sidebar-background-color"])
    backdrop = parse_rgba(payload["primary-background-color"])
    return composite(fill, backdrop)


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_sidebar_text_clears_wcag_aa(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        surface = _sidebar_surface(payload)
        text = parse_rgba(payload["sidebar-text-color"])
        ratio = contrast_ratio(composite(text, surface)[:3], surface[:3])
        assert ratio >= BODY_MIN, (
            f"{name} ({mode}): sidebar text on the sidebar fill is "
            f"{ratio:.2f}:1, need {BODY_MIN}:1"
        )


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_sidebar_icon_clears_large_text_minimum(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        surface = _sidebar_surface(payload)
        icon = parse_rgba(payload["sidebar-icon-color"])
        ratio = contrast_ratio(composite(icon, surface)[:3], surface[:3])
        assert ratio >= LARGE_MIN, (
            f"{name} ({mode}): sidebar icon on the sidebar fill is "
            f"{ratio:.2f}:1, need {LARGE_MIN}:1"
        )


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_sidebar_selected_text_clears_large_text_minimum(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        surface = _sidebar_surface(payload)
        text = parse_rgba(payload["sidebar-selected-text-color"])
        ratio = contrast_ratio(composite(text, surface)[:3], surface[:3])
        assert ratio >= LARGE_MIN, (
            f"{name} ({mode}): sidebar selected text on the sidebar fill is "
            f"{ratio:.2f}:1, need {LARGE_MIN}:1"
        )


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_sidebar_selected_icon_clears_large_text_minimum(themes, name):
    for mode in _mode_for(name):
        payload = _entry_payload(themes, name, mode)
        surface = _sidebar_surface(payload)
        icon = parse_rgba(payload["sidebar-selected-icon-color"])
        ratio = contrast_ratio(composite(icon, surface)[:3], surface[:3])
        assert ratio >= LARGE_MIN, (
            f"{name} ({mode}): sidebar selected icon on the sidebar fill is "
            f"{ratio:.2f}:1, need {LARGE_MIN}:1"
        )
