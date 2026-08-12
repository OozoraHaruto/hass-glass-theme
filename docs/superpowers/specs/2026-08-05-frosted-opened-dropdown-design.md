# Frosted Opened Dropdown Surface Design

## Goal

Make opened dropdown menus readable in the Glass and Liquid Glass themes by giving them the same opaque-enough tinted surface used by Frosted Glass. The change applies only to the opened options menu. Closed dropdown fields, cards, dialogs, and other themed surfaces remain unchanged.

## Constraint

Home Assistant's `ha-dropdown` assigns `--wa-color-surface-raised` inside its shadow-root `:host` rule from `--card-background-color`. Theme YAML cannot override that assignment independently, and changing `--card-background-color` would also change cards. The popup exposes no supported backdrop-filter theme hook.

The implementation therefore uses an optional frontend module. It does not modify Home Assistant files, inject CSS into shadow roots, or apply `backdrop-filter` to the popup. Avoiding popup blur prevents this feature from adding another stacking context or increasing the risk of Home Assistant's existing dropdown layering bugs.

## Theme Contract

The theme generator emits a new custom property named `ha-glass-dropdown-surface` for every existing Glass and Liquid Glass entry, including light, dark, auto, and Glass Lite variants. Liquid Glass has no Lite variant. Its value is the corresponding mode's Frosted Glass fill.

Frosted Glass entries do not emit this property because their existing `card-background-color` already gives opened menus the desired heavier surface. Third-party themes and unrelated entries do not emit it.

Presence of `--ha-glass-dropdown-surface` is the activation signal. The module does not compare theme names, so renamed entries and auto light/dark transitions continue to work.

## Optional Module

A new module under `www/` follows the installation model used by `glass-refraction.js`.

When active, it finds every `ha-dropdown` element and sets this host-level inline custom property:

```css
--wa-color-surface-raised: var(--ha-glass-dropdown-surface)
```

The inline host value overrides `ha-dropdown`'s internal `:host` declaration while leaving the WebAwesome implementation and popup DOM untouched.

The module observes document mutations so it also handles dropdowns created after startup, including menus opened from dynamically rendered dialogs and views. Discovery traverses newly added elements and reachable open shadow roots because Home Assistant components are commonly nested below them.

The module also observes changes to `document.documentElement`'s inline style, which Home Assistant rewrites on theme and mode changes. On each change it:

1. Reads the computed `--ha-glass-dropdown-surface` value.
2. Applies the override to discovered dropdowns when the value is present.
3. Removes only the module-owned override when the value is absent.

Cleanup is mandatory: switching to Frosted Glass, another bundled theme, or a third-party theme must restore Home Assistant's normal dropdown behavior. The module tracks the dropdowns it changed and does not remove a value that another script replaced after its write.

## Appearance and Safety

The opened menu receives a frosted-tinted background fill but no true backdrop blur. This deliberately prioritizes readable option text and compatibility over optical fidelity.

The implementation does not:

- alter `card-background-color`;
- alter the closed field's `ha-color-form-background`;
- add popup filters or stacking contexts;
- patch Home Assistant or WebAwesome prototypes;
- depend on private shadow-root markup inside `ha-dropdown`.

If the module is absent, fails to load, or the activation token is unavailable, Home Assistant retains its current behavior. The generated themes remain valid and usable without the module.

## Testing

Python tests verify that:

- Glass and Liquid Glass entries emit `ha-glass-dropdown-surface` in every mode and variant;
- the emitted value equals the corresponding Frosted Glass fill;
- Frosted Glass and unrelated entries do not emit the activation token;
- generated `themes/glass.yaml` matches the builder output.

Module tests verify that:

- existing dropdowns receive the override when an eligible theme is active;
- dynamically inserted dropdowns receive it;
- dropdowns nested in reachable open shadow roots are discovered;
- switching light/dark mode updates through the variable reference without stale copied colors;
- switching to an ineligible theme removes module-owned overrides;
- unrelated inline values are not removed;
- repeated synchronization and mutation callbacks are idempotent.

Manual verification uses the demo `input_select` in light and dark modes for Glass, Liquid Glass, and Frosted Glass. It confirms readable opened-menu text, unchanged closed fields and cards, correct cleanup after theme switching, and no regression in menu positioning or clickability.

## Installation

The README documents copying the new module to Home Assistant's `www` directory, adding it under `frontend.extra_module_url`, and restarting Home Assistant. It also states that the module is optional, fill-only, and does not resolve Home Assistant's existing dropdown stacking bugs.
