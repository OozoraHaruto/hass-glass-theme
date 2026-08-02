"""card-mod CSS injection for surfaces with no native theme-variable hook.

Home Assistant natively supports **seven** backdrop-filter theme variables
(all set in ``glassbuild/variables.py``, gated on ``full.backdrop is not
None``): ``--ha-card-backdrop-filter``, ``--ha-dialog-surface-backdrop-filter``,
``--app-header-backdrop-filter``, ``--ha-bottom-sheet-surface-backdrop-filter``,
``--ha-dialog-scrim-backdrop-filter``, ``--dialog-backdrop-filter`` (legacy
alias of the scrim variable), and ``--ha-bottom-sheet-scrim-backdrop-filter``.
Between them, cards, dialogs (including the more-info dialog's inner
``ha-dialog`` -- CSS custom properties inherit through shadow-DOM boundaries,
so the variable reaches it even though it's nested inside
``ha-adaptive-dialog``'s own shadow root), the header, and bottom sheets all
get their glass natively. None of this module's job.

What's left, with no native hook at all, is what this module covers:

- The **sidebar**'s backdrop-filter and fill -- there is no
  ``--sidebar-backdrop-filter`` variable.
- The header's **tab strip** styling.
- **letter-spacing** and **transition duration/easing** -- Home Assistant has
  no theme variable for either, anywhere.

card-mod exposes hooks for these as dedicated ``card-mod-<thing>(-yaml)``
theme variables, each already scoped to a specific element -- it does **not**
work by piercing down from some shared root with ``$`` chains. Verified
directly against thomasloven/lovelace-card-mod's source (README-themes.md and
src/patch/*.ts, cloned locally) plus the Home Assistant frontend source (also
cloned locally):

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

  This rule's ``background`` is the card's *glass* fill (``full.fill``),
  which deliberately differs from ``--sidebar-background-color`` in
  ``glassbuild/variables.py`` (the opaque-surface-based fill used as the
  native fallback). That is not an inconsistency to "fix" -- it is two
  different answers to two different questions. This card-mod rule only
  ever fires alongside a real ``backdrop-filter`` on the same ``:host``
  (see ``_SIDEBAR_TEMPLATE`` below; the whole block is skipped for Lite,
  which has no blur), so the low-alpha glass fill stays legible: blur
  softens whatever dashboard content is behind it before the fill's alpha
  ever gets a chance to expose it. ``--sidebar-background-color`` has no
  such backdrop -- Home Assistant defines no ``--sidebar-backdrop-filter``
  variable, and blur only exists at all when card-mod is installed -- so it
  must be legible standing alone against arbitrary dashboard content, which
  is why it uses the same opaque base + alpha as the Lite materials instead
  of the card's glass fill.

There is deliberately **no** ``card-mod-more-info-yaml`` here (an earlier
version of this module had one). It was removed after verifying it can never
fire: card-mod's ``src/patch/ha-more-info-dialog.ts`` does
``this.shadowRoot.querySelector("ha-dialog")`` and bails (``if (!haDialog)
return``) if that's null. But the frontend's ``ha-more-info-dialog.ts`` no
longer renders ``<ha-dialog>`` directly -- it renders ``<ha-adaptive-dialog>``
(confirmed in frontend source), which nests its own ``<ha-dialog>`` inside
*its own separate* shadow root (``ha-adaptive-dialog.ts``). A shallow
``querySelector`` on ``ha-more-info-dialog``'s shadow root cannot see through
that second shadow boundary, so ``haDialog`` is always ``null`` and the patch
silently never applies -- the key would have parsed as valid YAML and passed
a naive substring test while doing nothing at runtime. Nothing is lost by
dropping it: the more-info dialog's surface is already glassed by the native
``--ha-dialog-surface-backdrop-filter`` variable (see above).

``ha-tabs`` (named in the card-mod theme cookbook's older examples, and in
the original brief for this task) no longer exists anywhere in the current
frontend source -- it does not appear in a single ``.ts`` file. It has been
replaced by ``ha-tab-group``.

On the ``.header.header.header`` selector in ``_ROOT_TEMPLATE``: the header's
own backdrop-filter is native (``--app-header-backdrop-filter``, set in
``glassbuild/variables.py``), so this rule only supplies what HA has no
variable for -- fill, border, and type tracking. The selector is tripled to
reach specificity (0,3,0), which beats hui-root's own ``.edit-mode .header``
rule (0,2,0), so the glass fill survives edit mode regardless of style-tag
order.
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
    }
