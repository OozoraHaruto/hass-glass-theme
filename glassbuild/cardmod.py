"""card-mod CSS injection for surfaces without complete native hooks.

Only Frosted Glass uses Home Assistant's native backdrop-filter variables and
the blurred sidebar template. Clear Glass and Liquid Glass still use card-mod
for fills, borders, type tracking, and transitions, but never emit blur. Lite
entries emit no card-mod keys.

The native sidebar fallback remains near-opaque so text and the selected accent
stay readable without card-mod. The card-mod sidebar can instead use each full
material's own fill and rim. ``card-mod-root-yaml`` and
``card-mod-sidebar-yaml`` are already scoped to ``hui-root`` and ``ha-sidebar``
respectively; the root selector remains tripled so its header styling beats
Home Assistant's edit-mode selector.
"""

from __future__ import annotations

from typing import Any

from glassbuild.materials import Material

_ROOT_TEMPLATE = """\
.: |
  .header.header.header {{
    background: {fill};
    border-bottom: 1px solid {rim};
    letter-spacing: {tracking_headline};
    transition: background {duration} {easing};
  }}
  ha-tab-group {{
    letter-spacing: {tracking_body};
  }}
"""

_BLURRED_SIDEBAR_TEMPLATE = """\
.: |
  :host {{
    backdrop-filter: {backdrop};
    -webkit-backdrop-filter: {backdrop};
    background: {fill};
    border-right: 1px solid {rim};
    transition: background {duration} {easing}, backdrop-filter {duration} {easing};
  }}
  .title {{
    letter-spacing: {tracking_headline};
  }}
  ha-list-item-button {{
    letter-spacing: {tracking_body};
  }}
"""

_CLEAR_SIDEBAR_TEMPLATE = """\
.: |
  :host {{
    background: {fill};
    border-right: 1px solid {rim};
    transition: background {duration} {easing};
  }}
  .title {{
    letter-spacing: {tracking_headline};
  }}
  ha-list-item-button {{
    letter-spacing: {tracking_body};
  }}
"""


def build_cardmod(
    entry_name: str,
    materials: dict[str, Material],
    merged: dict[str, Any],
    *,
    lite: bool,
) -> dict[str, str]:
    """Build card-mod styling for one full entry; Lite entries emit nothing."""
    if lite:
        return {}

    full = materials["full"]
    font = merged["font"]
    motion = merged["motion"]
    fmt_args = {
        "backdrop": full.backdrop,
        "fill": full.fill,
        "rim": full.rim,
        "tracking_headline": font["tracking_headline"],
        "tracking_body": font["tracking_body"],
        "duration": motion["duration"],
        "easing": motion["easing"],
    }
    sidebar_template = (
        _BLURRED_SIDEBAR_TEMPLATE
        if full.backdrop is not None
        else _CLEAR_SIDEBAR_TEMPLATE
    )
    return {
        "card-mod-theme": entry_name,
        "card-mod-root-yaml": _ROOT_TEMPLATE.format(**fmt_args),
        "card-mod-sidebar-yaml": sidebar_template.format(**fmt_args),
    }
