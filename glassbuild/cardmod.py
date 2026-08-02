"""card-mod CSS injection for surfaces with no native theme-variable hook.

Home Assistant natively supports ``--ha-card-backdrop-filter`` and
``--ha-dialog-surface-backdrop-filter`` (see ``glassbuild/variables.py``), and
nothing else. Everything else this theme needs to glass -- the header/tab
strip, the sidebar, and the more-info dialog body -- has no theme variable
and must be reached with card-mod's per-surface theme hooks instead.

card-mod exposes those hooks as dedicated ``card-mod-<thing>(-yaml)`` theme
variables, each already scoped to a specific element -- it does **not** work
by piercing down from some shared root with ``$`` chains. Verified directly
against thomasloven/lovelace-card-mod's source (README-themes.md and
src/patch/*.ts, cloned locally) plus the Home Assistant frontend source
(also cloned locally):

- ``card-mod-root-yaml`` is applied to ``hui-root``'s *own* shadow root
  (card-mod's ``src/patch/hui-root.ts`` calls
  ``apply_card_mod(this, "root")`` on the ``hui-root`` element itself, shadow
  DOM target by default). ``hui-root.ts`` renders its header markup --
  including a literal ``<div class="header">`` and, since the tab strip was
  migrated off ``paper-tabs``/``ha-tabs``, a ``<ha-tab-group>`` -- directly in
  its own template, so both are reachable with a plain selector once already
  scoped there. No ``ha-panel-lovelace$ hui-root$`` prefix is needed or
  correct: root-yaml is already inside hui-root.
- ``card-mod-sidebar-yaml`` is applied to ``ha-sidebar``'s *own* shadow root
  (``src/patch/ha-sidebar.ts``: ``apply_card_mod(this, "sidebar")``, called
  directly on the ``ha-sidebar`` element -- not reachable via
  ``ha-drawer$: | ha-sidebar {...}`` from root-yaml, since ha-sidebar is a
  sibling custom element inside ``home-assistant-main``, not a descendant of
  hui-root). ``:host`` is the sidebar surface itself; ``.title`` and
  ``ha-list-item-button`` are real classes/elements in ``ha-sidebar.ts``'s
  render output.
- ``card-mod-more-info-yaml`` is applied to the light-DOM children of the
  ``<ha-dialog>`` inside ``ha-more-info-dialog``'s shadow root
  (``src/patch/ha-more-info-dialog.ts`` calls ``apply_card_mod(haDialog,
  "more-info", ..., false)`` -- the trailing ``false`` selects
  the element itself rather than its shadow root, i.e. light DOM). The
  dialog's ``.content`` wrapper and its ``.title`` (``slot="headerTitle"``)
  are both slotted light-DOM children of ``ha-dialog`` and so are reachable
  with plain selectors here.

``ha-tabs`` (named in the card-mod theme cookbook's older examples, and in
the original brief for this task) no longer exists anywhere in the current
frontend source -- it does not appear in a single ``.ts`` file. It has been
replaced by ``ha-tab-group``.
"""

from __future__ import annotations

from typing import Any

from glassbuild.materials import Material

_ROOT_TEMPLATE = """\
.: |
  .header {{
    backdrop-filter: {backdrop};
    -webkit-backdrop-filter: {backdrop};
    background: {fill};
    border-bottom: 1px solid {rim};
    letter-spacing: {tracking_headline};
    transition: background {duration} {easing}, backdrop-filter {duration} {easing};
  }}
  ha-tab-group {{
    background: transparent;
    letter-spacing: {tracking_body};
  }}
"""

_SIDEBAR_TEMPLATE = """\
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

_MORE_INFO_TEMPLATE = """\
.: |
  .content {{
    background: transparent;
    letter-spacing: {tracking_body};
  }}
  .title {{
    letter-spacing: {tracking_headline};
  }}
"""


def build_cardmod(
    entry_name: str, materials: dict[str, Material], merged: dict[str, Any]
) -> dict[str, str]:
    """Build the card-mod block for one entry.

    Returns ``{}`` for Lite entries (``materials["full"].backdrop is None``):
    Lite has no backdrop-filter anywhere, and therefore no card-mod-injected
    glass surfaces to describe, so no card-mod keys are emitted at all.
    """
    full = materials["full"]
    if full.backdrop is None:
        return {}

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

    return {
        "card-mod-theme": entry_name,
        "card-mod-root-yaml": _ROOT_TEMPLATE.format(**fmt_args),
        "card-mod-sidebar-yaml": _SIDEBAR_TEMPLATE.format(**fmt_args),
        "card-mod-more-info-yaml": _MORE_INFO_TEMPLATE.format(**fmt_args),
    }
