"""Assembly of the twelve theme entries.

Each material (glass, frosted-glass) x each weight (full, lite) yields three
display entries: an "Auto" entry that follows the browser/HA light-dark
setting via a ``modes`` block, plus flat "Light" and "Dark" entries that pin
one mode regardless of the ambient setting. That's 2 materials x 2 weights x
3 entries = 12.

The Auto entry's ``modes.light``/``modes.dark`` payloads are built the same
way as the flat entries -- same merged tokens, same derived materials, same
``build_variables``/``build_cardmod`` calls -- so a value that happens to be
identical between light and dark (most of the geometry, font, and motion
tokens) is hoisted to the Auto entry's top level, and only the values that
actually differ per mode are left inside ``modes``. This keeps the Auto
entry compact and, more importantly, keeps it *correct*: whichever entry a
user picks, a given mode must render identically, and computing both mode
payloads in full (rather than special-casing which keys are "known" to vary)
is what guarantees that -- card-mod's header fill happens to depend on the
mode-specific material alpha, so it varies too and must follow the same
split as everything else.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from glassbuild.cardmod import build_cardmod
from glassbuild.materials import derive
from glassbuild.tokens import MATERIALS, load_tokens, merge
from glassbuild.variables import build_variables

_LABEL = {"glass": "Glass", "frosted-glass": "Frosted Glass"}
_MODE_LABEL = {"light": "Light", "dark": "Dark"}


def _entry_names() -> tuple[str, ...]:
    names: list[str] = []
    for material in MATERIALS:
        label = _LABEL[material]
        for suffix in ("", " Lite"):
            names.append(f"{label}{suffix}")
            names.append(f"{label} Light{suffix}")
            names.append(f"{label} Dark{suffix}")
    return tuple(names)


ENTRY_NAMES: tuple[str, ...] = _entry_names()


def _mode_payload(
    tokens: dict[str, Any], material: str, mode: str, lite: bool, entry_name: str
) -> dict[str, str]:
    """Build one entry's flat payload: HA variables plus (if applicable) card-mod keys.

    ``entry_name`` only affects the ``card-mod-theme`` value inside the
    card-mod block (see ``glassbuild/cardmod.py``) -- everything else is a
    pure function of the merged tokens and derived materials, so it is safe
    to call this twice with the same tokens/mode but different names (once
    for a flat entry, once for the Auto entry's same-mode payload) and expect
    every other key to come back byte-identical.
    """
    merged = merge(tokens["base"], tokens["materials"][material], tokens["modes"][mode])
    materials = derive(merged, material, lite=lite)
    variables = build_variables(merged, materials)
    cardmod = build_cardmod(entry_name, materials, merged)
    return {**variables, **cardmod}


def build_themes(root: Path) -> dict[str, dict[str, Any]]:
    """Build the complete theme document: twelve entries keyed by display name."""
    tokens = load_tokens(root)
    themes: dict[str, dict[str, Any]] = {}

    for material in MATERIALS:
        label = _LABEL[material]
        for lite in (False, True):
            suffix = " Lite" if lite else ""
            auto_name = f"{label}{suffix}"

            auto_mode_payloads: dict[str, dict[str, str]] = {}
            for mode, mode_label in _MODE_LABEL.items():
                flat_name = f"{label} {mode_label}{suffix}"
                themes[flat_name] = _mode_payload(tokens, material, mode, lite, flat_name)
                auto_mode_payloads[mode] = _mode_payload(
                    tokens, material, mode, lite, auto_name
                )

            light_payload = auto_mode_payloads["light"]
            dark_payload = auto_mode_payloads["dark"]
            shared = {
                key: value
                for key, value in light_payload.items()
                if dark_payload.get(key) == value
            }
            themes[auto_name] = {
                **shared,
                "modes": {
                    "light": {k: v for k, v in light_payload.items() if k not in shared},
                    "dark": {k: v for k, v in dark_payload.items() if k not in shared},
                },
            }

    return themes
