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
    motion = merged["motion"]
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
        "ha-dialog-scrim-color": "rgba(0, 0, 0, 0.32)",
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
        "input-ideal-fill-color": light.fill,
        "input-label-ink-color": palette["text_secondary"],
        "input-dropdown-icon-color": palette["text_secondary"],
        "mdc-text-field-fill-color": light.fill,
        "mdc-select-fill-color": light.fill,
        "mdc-theme-primary": palette["accent"],
        "mdc-theme-secondary": palette["accent"],
        "mdc-theme-surface": opaque,
        "mdc-theme-on-surface": palette["text_primary"],
        "switch-checked-color": palette["accent"],
        "switch-unchecked-color": palette["text_disabled"],
        "slider-color": palette["accent"],
        "slider-secondary-color": light.fill,
        "paper-item-icon-color": palette["text_secondary"],
        "paper-item-icon-active-color": palette["accent"],
        "paper-listbox-background-color": opaque,
        "state-icon-color": palette["text_secondary"],
        "state-icon-active-color": palette["warning"],
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
        # ---- scrollbars, type, motion ---------------------------------------
        "scrollbar-thumb-color": palette["divider"],
        "primary-font-family": font["stack"],
        "paper-font-common-base_-_font-family": font["stack"],
        "paper-font-body1_-_font-family": font["stack"],
        "paper-font-headline_-_letter-spacing": font["tracking_headline"],
        "paper-font-body1_-_letter-spacing": font["tracking_body"],
        "ha-transition-duration": motion["duration"],
        "ha-transition-easing": motion["easing"],
        "control-border-radius": radius["control"],
        "ha-chip-border-radius": radius["pill"],
    }

    if full.backdrop is not None:
        variables["ha-card-backdrop-filter"] = full.backdrop
        variables["ha-dialog-surface-backdrop-filter"] = full.backdrop

    return variables
