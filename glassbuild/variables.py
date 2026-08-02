"""Mapping of merged tokens onto Home Assistant theme variable names.

Keys are written without the leading ``--``; Home Assistant adds it.
Surfaces are grouped per the spec: full material on cards and dialogs, light
material on controls, opaque on dense reading surfaces.
"""

from __future__ import annotations

from typing import Any

from glassbuild.materials import Material


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
        "ha-card-box-shadow": merged["shadow"],
        # ---- dialogs: full material ----------------------------------------
        "ha-dialog-surface-background": full.fill,
        "ha-dialog-border-radius": radius["dialog"],
        "mdc-dialog-scrim-color": "rgba(0, 0, 0, 0.32)",
        # ---- header and sidebar --------------------------------------------
        "app-header-background-color": full.fill,
        "app-header-text-color": palette["text_primary"],
        "sidebar-background-color": full.fill,
        "sidebar-icon-color": palette["text_secondary"],
        "sidebar-text-color": palette["text_primary"],
        "sidebar-selected-icon-color": palette["accent"],
        "sidebar-selected-text-color": palette["accent"],
        # ---- controls: light material --------------------------------------
        "input-fill-color": light.fill,
        "input-label-ink-color": palette["text_secondary"],
        "input-dropdown-icon-color": palette["text_secondary"],
        "mdc-text-field-fill-color": light.fill,
        "mdc-select-fill-color": light.fill,
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

    return variables
