"""Mapping of merged tokens onto Home Assistant theme variable names.

Keys are written without the leading ``--``; Home Assistant adds it.
Surfaces are grouped per the spec: full material on cards and dialogs, light
material on controls, opaque on dense reading surfaces.
"""

from __future__ import annotations

from typing import Any

from glassbuild.color import parse_rgba, rgba_str
from glassbuild.materials import (
    LIGHT_ALPHA_BONUS,
    SIDEBAR_FILL_ALPHA,
    Material,
    select_fill_alpha,
)


def build_variables(
    merged: dict[str, Any], materials: dict[str, Material]
) -> dict[str, str]:
    """Build the flat HA theme variable map for a single entry."""
    palette = merged["palette"]
    radius = merged["radius"]
    font = merged["font"]
    full = materials["full"]
    light = materials["light"]

    opaque = palette["opaque_surface"]
    opaque_r, opaque_g, opaque_b, _ = parse_rgba(opaque)
    # The sidebar sits over arbitrary dashboard content, not over the theme's
    # own gradient like a card does. With no blur behind it (blur only exists
    # when card-mod is installed -- see cardmod.py), the card's low-alpha
    # glass fill lets that content show straight through, tanking sidebar
    # text/icon contrast. So the sidebar gets its own fill, based on the
    # opaque surface rather than the card's white-based glass -- the latter
    # drops the selected-item accent to ~1.99:1 in dark mode even at high
    # alpha. It uses its own alpha, `SIDEBAR_FILL_ALPHA` (0.94), rather than
    # reusing `LITE_FILL_ALPHA` (0.72): 0.72 is enough for body/icon text but
    # lets the *accent* (the selected nav item) drop as low as ~1.82:1 when
    # composited over a black or white worst case, below the 3:1 floor. See
    # `SIDEBAR_FILL_ALPHA`'s docstring in materials.py for the sweep.
    sidebar_fill = rgba_str(opaque_r, opaque_g, opaque_b, SIDEBAR_FILL_ALPHA)
    # The closed select box has no backdrop-filter behind it (Home Assistant
    # exposes no --mdc-select-backdrop-filter, and card-mod does not reach
    # controls), so the selected value's label has to stay legible over
    # arbitrary dashboard content with nothing to blur the bleed-through --
    # the same no-blur regime as the sidebar above. But where the sidebar
    # uses the opaque surface (it must also lift the accent), the select only
    # carries primary text, so it can stay on the glass/frosted tint and spend
    # the minimum alpha that holds: select_fill_alpha returns the no-blur
    # adversarial legibility floor for this mode's fill_rgb (light ~0.52,
    # dark ~0.83 -- the dark RGB's luminance is too close to white to go as
    # low as light). That trades the opaque look from 6528272 for a frosted
    # pane: translucent in light, near-opaque in dark, legible in both. The
    # glass light.fill stays on the text field below; that was not the
    # reported surface and keeps the glass look.
    fill_rgb = merged["material"]["fill_rgb"]
    select_fill = rgba_str(
        fill_rgb[0], fill_rgb[1], fill_rgb[2], select_fill_alpha(fill_rgb)
    )
    # Hover lifts the fill alpha by LIGHT_ALPHA_BONUS -- the same idiom the light
    # material uses -- so a hovered form field reads heavier, not flat. Disabled
    # clamps to resting: the components dim disabled fields with opacity: 0.5
    # (ha-picker-field, ha-input, ha-textarea), so the fill itself should not move.
    form_fill_hover = rgba_str(
        fill_rgb[0], fill_rgb[1], fill_rgb[2],
        min(1.0, select_fill_alpha(fill_rgb) + LIGHT_ALPHA_BONUS),
    )
    form_fill_disabled = select_fill

    variables: dict[str, str] = {
        # ---- core palette -------------------------------------------------
        "primary-color": palette["accent"],
        "accent-color": palette["accent"],
        "dark-primary-color": palette["accent"],
        "light-primary-color": palette["accent"],
        "primary-text-color": palette["text_primary"],
        "secondary-text-color": palette["text_secondary"],
        "text-primary-color": palette["text_primary"],
        "disabled-text-color": palette["text_disabled"],
        "divider-color": palette["divider"],
        "error-color": palette["error"],
        "warning-color": palette["warning"],
        "success-color": palette["success"],
        "info-color": palette["accent"],
        # ---- backgrounds --------------------------------------------------
        "primary-background-color": opaque,
        "secondary-background-color": opaque,
        "card-background-color": full.fill,
        "lovelace-background": (
            f"linear-gradient(160deg, {palette['background_from']} 0%, "
            f"{palette['background_via']} 52%, {palette['background_to']} 100%)"
        ),
        # ---- cards: full material ------------------------------------------
        "ha-card-background": full.fill,
        "ha-card-border-radius": radius["card"],
        "ha-card-border-width": "1px",
        "ha-card-border-color": full.rim,
        # The specular edge leads, then the drop shadow. Box shadows paint
        # first-listed on top, so the inset edge has to come first or the
        # drop shadow's spread washes it out at the corners. See
        # `Material.edge` in glassbuild/materials.py for why the edge is a
        # shadow pair rather than part of `ha-card-border-color`.
        "ha-card-box-shadow": f"{full.edge}, {merged['shadow']}",
        # ---- dialogs: full material ----------------------------------------
        "ha-dialog-surface-background": full.fill,
        "ha-dialog-border-radius": radius["dialog"],
        "mdc-dialog-scrim-color": "rgba(0, 0, 0, 0.32)",
        # ---- header and sidebar --------------------------------------------
        "app-header-background-color": full.fill,
        "app-header-text-color": palette["text_primary"],
        "sidebar-background-color": sidebar_fill,
        "sidebar-icon-color": palette["text_primary"],
        "sidebar-text-color": palette["text_primary"],
        "sidebar-selected-icon-color": palette["accent"],
        "sidebar-selected-text-color": palette["accent"],
        # ---- controls: light material --------------------------------------
        # ---- form fields: frosted via the modern + legacy hooks ------------
        # The modern ha-select paints from --ha-color-form-background
        # (ha-picker-field.ts), not --mdc-select-fill-color -- so the modern hook is
        # the one that actually frosts the dropdown. input-fill-color is the hub of
        # HA's legacy alias chain (color.globals.ts derives the legacy text-field and
        # table-header fills from it), so retargeting it frosts legacy MDC text
        # fields, expansion panels, config pickers, and calendar/schedule headers too.
        # All five collapse onto the one no-blur legible frosted value; mdc-select-fill
        # stays for legacy selects (never broken). See the 2026-08-04 correction in
        # docs/superpowers/specs/2026-08-02-frosted-select-design.md.
        "input-fill-color": select_fill,
        "input-label-ink-color": palette["text_secondary"],
        "input-dropdown-icon-color": palette["text_secondary"],
        "mdc-text-field-fill-color": select_fill,
        "mdc-select-fill-color": select_fill,
        "ha-color-form-background": select_fill,
        "ha-color-form-background-hover": form_fill_hover,
        "ha-color-form-background-disabled": form_fill_disabled,
        "mdc-theme-primary": palette["accent"],
        "mdc-theme-secondary": palette["accent"],
        "mdc-theme-surface": opaque,
        "mdc-theme-on-surface": palette["text_primary"],
        "ha-switch-checked-background-color": palette["accent"],
        "ha-switch-background-color": palette["text_disabled"],
        "slider-color": palette["accent"],
        "slider-secondary-color": light.fill,
        "icon-primary-color": palette["text_secondary"],
        "state-icon-color": palette["text_secondary"],
        "state-icon-hover-color": palette["accent"],
        # ---- dense reading surfaces: opaque --------------------------------
        "table-row-background-color": opaque,
        "table-row-alternative-background-color": opaque,
        "data-table-background-color": opaque,
        "code-editor-background-color": opaque,
        "markdown-code-background-color": opaque,
        # ---- charts ---------------------------------------------------------
        "energy-grid-consumption-color": palette["accent"],
        "energy-grid-return-color": palette["success"],
        "energy-solar-color": palette["warning"],
        "energy-battery-in-color": palette["scene"],
        "energy-battery-out-color": palette["success"],
        "history-unavailable-color": palette["text_disabled"],
        # ---- scrollbars and type ---------------------------------------------
        "scrollbar-thumb-color": palette["divider"],
        "ha-font-family-body": font["stack"],
        "ha-font-family-heading": font["stack"],
        "ha-font-family-code": font["stack_code"],
        # ---- controls: per-component border radius, all take radius.control -
        "control-button-border-radius": radius["control"],
        "control-slider-border-radius": radius["control"],
        "control-select-border-radius": radius["control"],
        "control-switch-border-radius": radius["control"],
        "control-number-buttons-border-radius": radius["control"],
        "control-select-menu-border-radius": radius["control"],
        "control-select-button-border-radius": radius["control"],
        "ha-assist-chip-container-shape": radius["pill"],
    }

    if full.backdrop is not None:
        # `light` shares the same lite-gating as `full` (see
        # glassbuild/materials.py derive()): both are None together, so one
        # conditional safely covers all seven keys below.
        #
        # Scrims (--ha-dialog-scrim-backdrop-filter, --dialog-backdrop-filter,
        # --ha-bottom-sheet-scrim-backdrop-filter) deliberately get the
        # *light* material's half-blur backdrop, not full: a scrim covers the
        # whole viewport, and full blur there is expensive on tablets.
        variables["ha-card-backdrop-filter"] = full.backdrop
        variables["ha-dialog-surface-backdrop-filter"] = full.backdrop
        variables["app-header-backdrop-filter"] = full.backdrop
        variables["ha-bottom-sheet-surface-backdrop-filter"] = full.backdrop
        variables["ha-dialog-scrim-backdrop-filter"] = light.backdrop
        variables["dialog-backdrop-filter"] = light.backdrop  # legacy alias, set both
        variables["ha-bottom-sheet-scrim-backdrop-filter"] = light.backdrop

        refraction = merged["material"].get("refraction")
        if refraction:
            # An *alternative* chain, not a replacement: nothing in the theme
            # reads this variable. www/glass-refraction.js repoints the four
            # surface variables above at it once it has put the matching
            # `<filter>` in the document, and leaves them alone otherwise.
            #
            # Shipping the whole chain here rather than assembling it in
            # JavaScript keeps every tuning decision in tokens/ -- the module
            # never learns this material's blur radius or luminance remap, it
            # just swaps one variable for another.
            #
            # The url() leads because filter functions apply left to right:
            # displacement has to bend the raw backdrop *before* the blur
            # smooths it, or it would be shuffling an already-flat field.
            #
            # Only the four surface variables get upgraded, never the three
            # scrims -- a scrim covers the whole viewport, and there is no
            # edge there for a rim lens to sit on.
            variables["ha-glass-refraction-backdrop"] = (
                f"url(#{refraction['filter_id']}) {full.backdrop}"
            )
            # The displacement's own tuning, published for the module to read
            # rather than left as literals on its side. Same rule as the blur
            # radius above: a copy in JavaScript that matches the token today
            # goes on matching right up until someone retunes the token, and
            # then diverges silently -- nothing renders differently enough for
            # review to catch it.
            variables["ha-glass-refraction-scale"] = str(refraction["scale"])
            variables["ha-glass-refraction-edge"] = str(refraction["edge_fraction"])

    return variables
