# Frosted-tinted dropdown — design

> **Date:** 2026-08-02
> **Status:** Approved (brainstormed 2026-08-02), pending implementation
> **Supersedes part of:** the 2026-08-01 spec's "Not themed" line for
> dropdowns, and the closed-box treatment from commit `6528272`
> ("fix: give the dropdown its own opaque fill so backdrop text stops
> showing through").

## Goal

Make the dropdown control read as frosted glass, the way iOS menus do —
translucent, not see-through — instead of the flat-opaque look the closed
box got in `6528272`.

## Two surfaces, and which one this touches

A Home Assistant dropdown is two surfaces:

1. **The closed box** — the control you tap. Its fill is
   `--mdc-select-fill-color`, set by this theme's
   `glassbuild/variables.py`. Fully themeable.
2. **The opened menu** — the popover list of options. It is a webawesome
   `wa-popup` teleported to `<body>`.

This design changes the **closed box**. It leaves the opened menu alone,
because the opened menu is not reachable — see "The opened menu is
unreachable" below.

## The opened menu is unreachable (recorded so it is not re-litigated)

The opened menu's background comes from `--wa-color-surface-raised`, which
`ha-dropdown`'s `:host` rule sets as:

```css
--wa-color-surface-raised: var(
  --card-background-color,
  var(--ha-dialog-surface-background, var(--mdc-theme-surface, #fff))
);
```

Three facts together make it unreachable from a theme:

- `--card-background-color` is **always set** in this theme (to the thin
  glass fill, alpha 0.14/0.16), so the menu reads that value and never
  falls through to `--mdc-theme-surface`. The first link of the chain
  wins.
- `--card-background-color` is shared with actual cards, which have a
  `backdrop-filter` behind them and *need* to stay the thin glass. It
  cannot be raised to frost the menu without undoing the glass-on-cards
  look. So the one variable the menu does read is locked.
- A Home Assistant theme is a flat map of document-level custom
  properties. It cannot override the `:host`-level re-assignment of
  `--wa-color-surface-raised` *inside `ha-dropdown`'s shadow root*, and
  `card-mod-root-yaml` is scoped to `hui-root`'s shadow root — the popup
  is teleported to `<body>`, outside `hui-root`, so no card-mod selector
  reaches it either. (There is no `card-mod-menu-yaml` hook.)

Verified against `src/components/ha-dropdown.ts` on the `dev` branch:
`--wa-color-surface-raised` is the only lever for the menu background
defined in that component; the `wa-popup::part(popup)` rule only sets
`z-index: 200`. No `backdrop-filter` is applied to the popup anywhere in
the component, and webawesome does not read a `--*-backdrop-filter`
theme variable for it — so the real blur half of iOS frost is not
reachable on the opened menu either.

The 2026-08-01 spec already documented the related hard limit that
`backdrop-filter` on surfaces is what *traps* dropdowns in the
layering bug (frontend#20725 / #26113). Injecting blur on the menu
would risk recreating that bug even if it could be reached.

**Consequence:** the opened menu keeps Home Assistant's default
appearance (the thin glass fill via `--card-background-color`). It is
documented in the README as a known, upstream limit — not a tuning gap
in this theme.

## The closed box: frosted tint, not opaque

### Why the raw frosted token alpha does not work here

The frosted material's fill alpha is 0.55 (light) / 0.45 (dark). On a
*card* that is fine, because a 40px `backdrop-filter` blur sits behind
the fill and destroys the backdrop bleed-through before the alpha ever
matters. The closed box has **no blur behind it** (no
`--mdc-select-backdrop-filter` exists; card-mod does not reach
controls), so the tint alone has to keep the selected value's label
legible against arbitrary dashboard content — the same regime as the
sidebar.

The raw frosted alphas fail the no-blur adversarial-backdrop floor:

| mode | frosted alpha | worst case | ratio |
|------|---------------|------------|-------|
| light | 0.55 | over black | 5.06:1 — pass |
| light | 0.55 | over white | 17.01:1 — pass |
| dark  | 0.45 | over black | 14.71:1 — pass |
| dark  | 0.45 | over white | **2.05:1 — fail** |

The dark glass RGB (`90, 90, 94`) is too close in luminance to a white
backdrop to carry white menu text at 0.45. This is the identical failure
the sidebar hit, and it has the same shape of fix: raise the alpha until
the floor clears, accepting that the surface reads heavier than iOS
frost as the price of legibility-without-blur.

### The design

A **frosted-tinted** closed box: use the mode's glass/frosted `fill_rgb`
(`255, 255, 255` light / `90, 90, 94` dark) at the **minimum per-mode
alpha that clears the 4.5:1 adversarial-backdrop floor**:

| mode | fill RGB | alpha | worst-case contrast |
|------|----------|-------|---------------------|
| light | `255, 255, 255` | **0.52** | 4.55:1 (over black) |
| dark  | `90, 90, 94`    | **0.83** | 4.52:1 (over white) |

This replaces the opaque-surface fill at 0.72 from `6528272`. The RGB
moves from the opaque surface (`242,242,247` / `28,28,30`) to the
frosted/glass tint, and the alpha becomes per-mode. Light mode reads as
a genuinely translucent frosted pane; dark mode necessarily stays
near-opaque (0.83) because that is the floor — the asymmetry is the
legibility floor forcing it, not a tuning preference.

## Implementation surface

- `glassbuild/materials.py`: add two constants,
  `SELECT_FILL_ALPHA_LIGHT = 0.52` and `SELECT_FILL_ALPHA_DARK = 0.83`,
  each with a docstring recording the adversarial sweep (worst case and
  the value tried just below that failed), mirroring
  `SIDEBAR_FILL_ALPHA`'s docstring style. Per-mode rather than one
  shared constant because the two floors differ by 0.31 — a single
  value would either fail dark or over-opaque light.
- `glassbuild/variables.py`: `select_fill` uses the mode's
  `material.fill_rgb` (the glass/frosted RGB) with the new per-mode
  alpha, instead of `opaque_surface` + `LITE_FILL_ALPHA`. The
  `input-fill-color` and `mdc-text-field-fill-color` mappings stay on
  `light.fill` (unchanged from `6528272` — the text field was not the
  reported surface and keeps the glass look).
- `glassbuild/emit.py`: no change. `build_variables` already receives
  the merged per-mode tokens, so `fill_rgb` is mode-correct without
  threading a new parameter.

## Tests

- `tests/test_contrast.py::test_select_value_text_clears_wcag_aa`
  (added in `6528272`) is unchanged in shape: primary text over the
  select fill must clear 4.5:1 against the two adversarial backdrops,
  for every entry and mode. It becomes the guard on the *frosted* alpha
  rather than the opaque one. It must still pass — that is the green
  check that the new alphas hold.
- `tests/test_variables.py::test_select_fill_is_opaque_based_not_glass`
  (added in `6528272`) is renamed and rewritten to
  `test_select_fill_is_frosted_tinted`: it pins the select fill to the
  frosted RGB and per-mode alpha (against the dark-mode fixture, which
  is the heavier case) and still asserts it differs from the glass
  `light.fill` the text field uses. The opaque-surface assertion is
  removed — that is exactly what this change reverses.

## Out of scope

- The opened menu's appearance (unreachable — see above).
- `backdrop-filter` on the closed box (would require card-mod reaching
  a control, which it does not; and even on the card, blur is the
  card's, not the box's own).
- The text field and `input-fill-color` — ~~kept on glass, as in
  `6528272`~~. **Reversed 2026-08-04:** the modern frontend unifies every
  form field under `--ha-color-form-background`, so `input-fill-color` and
  `mdc-text-field-fill-color` were retargeted onto the frosted value alongside
  the new hook. See "2026-08-04 correction" below.

## Manual verification

No new demo surface is needed: `demo/dashboard.yaml` already has an
`input_select` row whose closed box exercises this. The reviewer loads
it, steps through the entries light/dark, and confirms the closed box
reads frosted (light) / a heavier near-opaque tint (dark) and that the
selected value's label stays legible over a busy backdrop. The opened
menu is expected to look unchanged (the documented unreachable case).

## 2026-08-04 correction: the real closed-box hook

The "Two surfaces" section above names `--mdc-select-fill-color` as the
closed-box hook. That is wrong for the modern Home Assistant frontend. The
modern `ha-select` paints its closed field from `--ha-color-form-background`
(`ha-picker-field.ts:137`, `ha-combo-box-item { background-color:
var(--ha-color-form-background) }`). `--mdc-select-fill-color` is consumed
only by `color.globals.ts` (a legacy default) and `ha-onboarding.ts` (set to
`none`) — never by the modern select. So the frosted `select_fill` this spec
designed was emitted under an inert key, and the modern dropdown stayed clear
— the bug reported as "for glass and liquid glass the select dropdown is
still clear not frosted."

The override path was verified against a cloned `home-assistant/frontend`
`dev` branch: `themes-mixin` calls `applyThemesOnElement(document.documentElement,
…)`, which turns each theme key into `--${key}` and sets it as an inline
style on `<html>`; inline-on-`<html>` beats the `html { --ha-color-form-background: … }`
default in `semantic.globals.ts`, and the custom property inherits down into
`ha-picker-field`. No component redeclares the variable in its own `:host`
— every hit is a `var()` consumer.

The fix emits `ha-color-form-background` (plus `-hover` lifted by
`LIGHT_ALPHA_BONUS` and `-disabled` clamped to resting) with the same frosted
value, and retargets `input-fill-color` / `mdc-text-field-fill-color` onto it
so the legacy alias chain (legacy text fields, expansion panels, config
pickers, calendar/schedule headers via `--table-header-background-color`)
frosts too. `ha-color-form-background` is a shared form-field token (selects,
text inputs, textareas, time inputs, checkbox hover) — there is no
select-only hook — so frosting it frosts the whole form layer, not just the
dropdown. This reverses the earlier "only the dropdown" scope: that choice
was made when text fields were assumed separately themed, but the modern
frontend unifies every field under this one token, and the theme previously
left it on Home Assistant's flat default. The opened-menu limit above stands
unchanged.
