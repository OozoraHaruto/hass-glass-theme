"""Assembly of the theme entries.

Each material x each weight it supports (full, lite) yields three display
entries: an "Auto" entry that follows the browser/HA light-dark setting via a
``modes`` block, plus flat "Light" and "Dark" entries that pin one mode
regardless of the ambient setting.

The matrix is not fully rectangular. Glass and Frosted Glass span both
weights (2 materials x 2 weights x 3 entries = 12); Liquid Glass spans only
the full weight (3 more), for 15 in total -- see ``_NO_LITE`` below for why.
Nothing downstream hardcodes the count: ``ENTRY_NAMES`` is the single source
of truth for which entries exist and in what order.

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

MATERIAL_LABEL = {
    "glass": "Glass",
    "frosted-glass": "Frosted Glass",
    "liquid-glass": "Liquid Glass",
}
_MODE_LABEL = {"light": "Light", "dark": "Dark"}

# Materials that span the mode axis but not the weight axis.
#
# The existing Glass Lite family is the single near-opaque fallback, and the
# approved picker matrix remains unchanged. Liquid Glass therefore has no
# separate Lite variants.
_NO_LITE: frozenset[str] = frozenset({"liquid-glass"})


def _weights(material: str) -> tuple[bool, ...]:
    """The ``lite`` flags this material is built at: both, or full only."""
    return (False,) if material in _NO_LITE else (False, True)


def _entry_names() -> tuple[str, ...]:
    names: list[str] = []
    for material in MATERIALS:
        label = MATERIAL_LABEL[material]
        for lite in _weights(material):
            suffix = " Lite" if lite else ""
            names.append(f"{label}{suffix}")
            names.append(f"{label} Light{suffix}")
            names.append(f"{label} Dark{suffix}")
    return tuple(names)


ENTRY_NAMES: tuple[str, ...] = _entry_names()


def _build_variables_for_mode(
    tokens: dict[str, Any], material: str, mode: str, lite: bool
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Merge tokens and derive materials/variables once for a (material, mode, lite) triple.

    This is the entry-name-*independent* half of an entry's payload: the
    merged tokens, the derived ``Material`` objects, and the flat HA
    variables. It is computed exactly once per (material, mode, lite)
    combination and its outputs are reused for both the flat entry and the
    Auto entry's same-mode payload -- only ``build_cardmod``'s
    ``card-mod-theme`` value differs between those two uses, so only that
    call is repeated (see ``build_themes`` below).
    """
    merged = merge(tokens["base"], tokens["materials"][material], tokens["modes"][mode])
    materials = derive(merged, material, lite=lite)
    variables = build_variables(merged, materials)
    return merged, materials, variables


def build_themes(root: Path) -> dict[str, dict[str, Any]]:
    """Build the complete theme document: fifteen entries keyed by display name.

    Insertion order matches ``ENTRY_NAMES`` exactly -- entries are collected
    into a scratch dict in whatever order is convenient to compute (Light,
    Dark, then Auto per material/weight), then re-keyed into the final dict
    by iterating ``ENTRY_NAMES``, so a caller that serialises this dict
    without sorting still gets the canonical matrix order.
    """
    tokens = load_tokens(root)
    built: dict[str, dict[str, Any]] = {}

    for material in MATERIALS:
        label = MATERIAL_LABEL[material]
        for lite in _weights(material):
            suffix = " Lite" if lite else ""
            auto_name = f"{label}{suffix}"

            mode_payloads: dict[str, dict[str, str]] = {}
            for mode, mode_label in _MODE_LABEL.items():
                merged, materials, variables = _build_variables_for_mode(
                    tokens, material, mode, lite
                )

                flat_name = f"{label} {mode_label}{suffix}"
                flat_cardmod = build_cardmod(flat_name, materials, merged, lite=lite)
                built[flat_name] = {**variables, **flat_cardmod}

                auto_cardmod = build_cardmod(auto_name, materials, merged, lite=lite)
                mode_payloads[mode] = {**variables, **auto_cardmod}

            light_payload = mode_payloads["light"]
            dark_payload = mode_payloads["dark"]
            shared = {
                key: value
                for key, value in light_payload.items()
                if dark_payload.get(key) == value
            }
            built[auto_name] = {
                **shared,
                "modes": {
                    "light": {
                        k: v for k, v in light_payload.items() if k not in shared
                    },
                    "dark": {k: v for k, v in dark_payload.items() if k not in shared},
                },
            }

    return {name: built[name] for name in ENTRY_NAMES}
