"""Structural validation of the generated theme document.

An undefined ``var()`` in a Home Assistant theme fails silently at runtime --
the surface renders transparent or black with no error anywhere. This module
turns that class of failure, plus a handful of other shapes that Home
Assistant or card-mod would otherwise swallow silently, into build errors.

``validate()`` never raises and never prints: it always returns a (possibly
empty) list of human-readable problem strings, even when handed a document
that looks nothing like the real one.

Home Assistant's ``modes`` block is a *partial overlay*: a mode's payload is
spread on top of the entry's top-level keys, not used in isolation (confirmed
against the frontend source). So a variable "counts" as defined for an entry
if it appears at the top level, in ``modes.light``, or in ``modes.dark`` --
the checks below flatten across all three before asking "is this defined?".
"""

from __future__ import annotations

import re
from typing import Any

from glassbuild.emit import ENTRY_NAMES

_VAR_RE = re.compile(r"var\(\s*--([a-zA-Z0-9_-]+)")
# A var() call whose argument does *not* start with "--" -- malformed CSS
# that HA/the browser silently drops at runtime, same failure class as a
# dangling reference.
_MALFORMED_VAR_RE = re.compile(r"var\(\s*(?!--)([a-zA-Z0-9_-]+)")

_REQUIRED_MODE_KEYS = ("light", "dark")

# Every one of these has been verified to exist as a real HA theme variable
# consumed by the frontend. A required variable may legitimately be defined
# at an entry's top level, inside a modes payload, or both.
REQUIRED_VARIABLES: frozenset[str] = frozenset(
    {
        "primary-color",
        "accent-color",
        "primary-text-color",
        "secondary-text-color",
        "divider-color",
        "primary-background-color",
        "card-background-color",
        "ha-card-background",
        "ha-card-border-radius",
        "ha-card-box-shadow",
        "app-header-background-color",
        "sidebar-background-color",
        "lovelace-background",
    }
)

# Variables Home Assistant defines itself (in its own base theme / frontend
# CSS) that this theme is free to reference via var() without ever setting
# them itself.
HA_BUILTIN_VARIABLES: frozenset[str] = frozenset(
    {
        "primary-color",
        "accent-color",
        "primary-text-color",
        "secondary-text-color",
        "primary-background-color",
        "secondary-background-color",
        "card-background-color",
        "divider-color",
        "disabled-text-color",
    }
)


def _check_modes_shape(
    name: str, entry: dict[str, Any], problems: list[str]
) -> dict[str, dict[str, Any]]:
    """Validate the shape of ``entry["modes"]``, if present, appending to ``problems``.

    A flat entry (no ``modes`` key at all) is not required to have one --
    that's a legitimate shape. But once ``modes`` is present, malformed
    shapes are structural bugs, not something to silently tolerate: HA
    applies nothing for a mode whose payload isn't a mapping, and a ``modes``
    block missing ``light`` or ``dark`` entirely means that mode falls back
    to whatever's at the top level (which may be nothing at all for the
    keys that were meant to vary by mode). Every such shape is reported here
    rather than filtered out.

    Returns the subset of modes payloads that *are* dicts, for the rest of
    validation to keep working against -- one malformed mode payload
    shouldn't prevent checking the other, well-formed one.
    """
    if "modes" not in entry:
        return {}

    modes = entry["modes"]
    if not isinstance(modes, dict):
        problems.append(
            f"{name}: 'modes' is a {type(modes).__name__}, expected a dict"
        )
        return {}

    valid_payloads: dict[str, dict[str, Any]] = {}
    for mode, payload in modes.items():
        if not isinstance(payload, dict):
            problems.append(
                f"{name}: modes.{mode} is a {type(payload).__name__}, expected a dict"
            )
            continue
        valid_payloads[mode] = payload

    for required_mode in _REQUIRED_MODE_KEYS:
        if required_mode not in modes:
            problems.append(f"{name}: 'modes' is missing required key {required_mode!r}")

    return valid_payloads


def _flatten(
    entry: dict[str, Any], mode_payloads: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Union an entry's top level with both modes payloads into one namespace.

    Used only to answer "is this key defined somewhere in this entry?" --
    exact overlay precedence (mode-over-top-level) doesn't matter for that
    question, only membership does.
    """
    flat = {k: v for k, v in entry.items() if k != "modes"}
    for payload in mode_payloads.values():
        flat.update(payload)
    return flat


def _iter_locations(entry: dict[str, Any], mode_payloads: dict[str, dict[str, Any]]):
    """Yield (location, key, value) across the top level and both modes payloads."""
    for key, value in entry.items():
        if key == "modes":
            continue
        yield "top-level", key, value
    for mode, payload in mode_payloads.items():
        for key, value in payload.items():
            yield f"modes.{mode}", key, value


def validate(themes: Any) -> list[str]:
    """Return a list of human-readable problems. Empty means the document is valid.

    Never raises and never prints, regardless of what ``themes`` contains.
    """
    problems: list[str] = []

    if not isinstance(themes, dict):
        return [
            f"theme document is a {type(themes).__name__}, expected a dict of entries"
        ]

    for name in ENTRY_NAMES:
        if name not in themes:
            problems.append(f"{name}: entry is missing from the document")

    for name, raw_entry in themes.items():
        if not isinstance(raw_entry, dict):
            problems.append(
                f"{name}: entry is a {type(raw_entry).__name__}, expected a dict"
            )
            continue

        entry = raw_entry
        mode_payloads = _check_modes_shape(name, entry, problems)
        flat = _flatten(entry, mode_payloads)
        is_lite = name.endswith("Lite")

        for required in sorted(REQUIRED_VARIABLES):
            if required not in flat:
                problems.append(
                    f"{name}: required variable {required!r} is not defined "
                    "(checked top level and both modes payloads)"
                )

        for location, key, value in _iter_locations(entry, mode_payloads):
            if not isinstance(key, str):
                problems.append(f"{name} ({location}): non-string key {key!r}")
                continue

            if key.startswith("--"):
                problems.append(
                    f"{name} ({location}): key {key!r} must not start with '--' "
                    "(Home Assistant adds the prefix itself)"
                )

            if is_lite and key.startswith("card-mod"):
                problems.append(
                    f"{name} ({location}): Lite entry must not contain a "
                    f"card-mod key ({key!r})"
                )

            if not isinstance(value, str):
                problems.append(
                    f"{name} ({location}): value of {key!r} is "
                    f"{type(value).__name__}, expected str"
                )
                continue

            for reference in _VAR_RE.findall(value):
                if reference not in flat and reference not in HA_BUILTIN_VARIABLES:
                    problems.append(
                        f"{name} ({location}): {key!r} references undefined "
                        f"variable '--{reference}'"
                    )

            for malformed in _MALFORMED_VAR_RE.findall(value):
                problems.append(
                    f"{name} ({location}): {key!r} has a malformed var() "
                    f"reference {malformed!r} (missing leading '--')"
                )

            if is_lite:
                if "backdrop-filter" in key or "backdrop-filter" in value:
                    problems.append(
                        f"{name} ({location}): Lite entry must not contain "
                        f"'backdrop-filter' (found via {key!r})"
                    )
                if "blur(" in key or "blur(" in value:
                    problems.append(
                        f"{name} ({location}): Lite entry must not contain "
                        f"'blur(' (found via {key!r})"
                    )

    return problems
