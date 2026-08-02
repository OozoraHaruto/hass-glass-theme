# hass-glass-theme — Design

**Date:** 2026-08-01
**Status:** Implemented — see "Amended during execution" blockquotes throughout
**Revision:** 3 — amended 2026-08-02, after implementation, to correct claims execution
disproved: the native `backdrop-filter` variable count (two → seven), the card-mod surface
list (narrowed to what actually shipped and is feasible), success criteria 3 and 5, and the
background wording. This is the authoritative account of the design as shipped; the
original rationale is kept and superseded in place via blockquotes rather than deleted, so
the change history stays honest. The companion implementation plan
(`docs/superpowers/plans/2026-08-01-hass-glass-theme.md`) is a historical execution record
and was not similarly rewritten — this spec is authoritative where the two disagree.
**Revision 2** — the two open items from revision 1 were researched and resolved; findings
changed the layout, the card-mod story, and the entry count. See "Resolved research" below.

## Purpose

A Home Assistant theme package providing two Apple-inspired glass materials — a clear
"Glass" and a diffuse "Frosted Glass" — each in Auto, Light, and Dark, plus a no-blur
"Lite" twin of each: **twelve entries** in Home Assistant's theme picker. Distributed via
HACS, maintained from a single token source, and validated by GitHub CI/CD.

## Resolved research

Revision 1 carried two open questions. Both were checked against upstream sources and both
changed the design.

### Native `backdrop-filter` support: confirmed present

Home Assistant's frontend exposes native theme variables that apply a backdrop filter with
no card-mod involved:

- `--ha-card-backdrop-filter` — on `ha-card`, in use since approximately 2024.5
- `--ha-dialog-surface-backdrop-filter` — on dialog surfaces

Consequence: a bare install with no card-mod gets **real blur on cards and dialogs**.
card-mod is demoted from "required for any glass effect" to "required only for surfaces
with no native hook" — header, sidebar, view tabs, menus, tooltips, toasts, quick bar.

> **Amended during execution (2026-08-02).** This was wrong, discovered while building
> `glassbuild/variables.py`. Home Assistant exposes **seven** native `backdrop-filter`
> theme variables, not two, and this theme sets all seven (verified against
> `glassbuild/variables.py`, which gates all seven on a single `if full.backdrop is not
> None:` block):
>
> - `--ha-card-backdrop-filter` — cards
> - `--ha-dialog-surface-backdrop-filter` — dialog surfaces, including the more-info dialog
> - `--ha-dialog-scrim-backdrop-filter` — the dialog scrim (backdrop behind the dialog)
> - `--dialog-backdrop-filter` — legacy alias of the scrim variable, set to the same value
> - `--ha-bottom-sheet-surface-backdrop-filter` — bottom sheets (mobile-width dialogs)
> - `--ha-bottom-sheet-scrim-backdrop-filter` — the bottom-sheet scrim
> - `--app-header-backdrop-filter` — the dashboard header
>
> The consequence below is correspondingly larger: a bare install with no card-mod gets
> real blur on cards, dialogs, both scrims, bottom sheets, **and the header**. card-mod's
> job shrinks further than this section originally said — see "card-mod scope: corrected"
> under UI surface coverage below for what's actually left for it to do.

### Both native variables break dropdown layering

Each variable creates a CSS stacking context, and Home Assistant renders dropdown overlays
outside the theme root DOM. Two independent upstream reports:

- [frontend#20725](https://github.com/home-assistant/frontend/issues/20725) —
  `ha-card-backdrop-filter` renders dropdowns *behind* picture-elements cards, unclickable.
  Regression between 2024.4.4 and 2024.5.1.
- [frontend#26113](https://github.com/home-assistant/frontend/issues/26113) —
  `ha-dialog-surface-backdrop-filter` makes dropdowns escape the more-info dialog.

**Both are closed as not planned** — stale-botted rather than fixed. Treat as permanent.

Independent corroboration: the most widely used theme in this space,
[wessamlauf/homeassistant-frosted-glass-themes](https://github.com/wessamlauf/homeassistant-frosted-glass-themes),
hit the same class of bug and ships **"Lite" no-blur editions** as its documented answer —
for the dropdown breakage and for low-end-hardware lag, the same performance concern raised
in "Accepted trade-offs" below. Two upstream issues plus a shipping theme converging on the
same mitigation is strong evidence, so this design adopts it.

### HACS permits exactly one theme file per repository

From [the HACS theme publishing docs](https://www.hacs.xyz/docs/publish/theme/): *"There is
only one theme configuration file (one directory under `ROOT_OF_THE_REPO/themes/`) per
repository (if you have more, only the first one will be managed.)"*

The revision-1 two-file layout is therefore invalid. All entries collapse into a single
`themes/glass.yaml`. Entry *count within* that file is unconstrained, which is what makes
twelve entries cost nothing but generated lines.

GitHub releases are **optional** for HACS — it falls back to scanning the default branch.
Releases are still shipped, for a versioned update path and pinnable rollback.

## Constraints that shape the design

**`backdrop-filter` blurs what is behind it.** Home Assistant's default dashboard background
is a flat solid colour, and blurring a flat colour yields the same flat colour. A glass
theme that does not supply its own backdrop produces no visible effect. The theme therefore
ships its own background; this is load-bearing, not decorative.

**Native theme variables cover cards and dialogs only.** Everything else — header, sidebar,
tabs, menus, tooltips, toasts, quick bar — has no native hook and needs card-mod's
`card-mod-theme` / `card-mod-root-yaml` CSS injection to receive a material.

> **Amended during execution (2026-08-02).** Wrong on two counts. First, native coverage is
> wider: it's cards, dialogs (both surface and scrim), bottom sheets (both surface and
> scrim), **and the header** — seven variables total, not two (see the amendment above).
> Second, of what's left, only the sidebar and the header's tab strip actually have a
> card-mod hook that works; menus, tooltips, toasts, and the quick bar were never
> implemented, and at least one of them (`ha-toast`) turned out not to be feasible at all —
> it uses a hardcoded colour and is not themeable via card-mod or theme variables. See
> "card-mod scope: corrected" under UI surface coverage below.

## Architecture

```
hass-glass-theme/
├─ tokens/
│  ├─ base.yaml            # geometry, type scale, motion, spacing — shared by all twelve
│  ├─ glass.yaml           # material: blur 8px, low alpha, bright specular rim
│  ├─ frosted-glass.yaml   # material: blur 40px, high alpha, soft diffuse rim
│  └─ modes/
│     ├─ light.yaml        # palette + material tuning for light
│     └─ dark.yaml         # palette + material tuning for dark
├─ scripts/build_themes.py # tokens → themes/glass.yaml
├─ tests/                  # pytest: generator, contrast, dangling vars, round-trip
├─ themes/
│  └─ glass.yaml           # GENERATED, committed — all twelve entries (HACS: one file only)
├─ demo/                   # dashboard YAML exercising every themed surface
├─ hacs.json
├─ README.md
└─ .github/
   ├─ workflows/{ci.yml,release.yml}
   └─ dependabot.yml
```

### Why a generator

Twelve entries share one design system. Maintaining roughly 150 variables across twelve
entries by hand guarantees drift, and YAML anchors cannot help because every top-level key
in an HA theme file becomes a picker entry — anchor definitions would appear as themes. A
generator gives one place to change a radius or an accent.

Python, because the Home Assistant ecosystem is Python and `pyyaml` is the only dependency
required. A Node generator would add a `package.json` and `node_modules` to a repository
that otherwise ships only YAML, for no benefit.

The generated file is committed so HACS and manual installs work with no build step. CI
re-runs the generator and fails on drift, keeping the committed output honest.

### Entry matrix

| | Auto | Light | Dark |
|---|---|---|---|
| **Glass** | Glass | Glass Light | Glass Dark |
| **Glass, no blur** | Glass Lite | Glass Light Lite | Glass Dark Lite |
| **Frosted Glass** | Frosted Glass | Frosted Glass Light | Frosted Glass Dark |
| **Frosted, no blur** | Frosted Glass Lite | Frosted Glass Light Lite | Frosted Glass Dark Lite |

Auto entries wrap their mode payloads in Home Assistant's `modes: light: / dark:` block.
Light and Dark entries inline the same payload flat. All three derive from the same token
merge, so a given mode renders identically whichever entry the user picks.

### Material layers

Each non-Lite entry applies its material in two layers:

1. **Native layer** — `--ha-card-backdrop-filter` and
   `--ha-dialog-surface-backdrop-filter`, plus standard translucent `rgba` fills, rim, and
   shadow variables. Real blur on cards and dialogs with zero dependencies.
2. **card-mod layer** — `card-mod-theme` plus `card-mod-root-yaml` / `card-mod-card-yaml`
   blocks extending the material to header, sidebar, tabs, menus, tooltips, toasts, and
   quick bar. Home Assistant ignores these keys when card-mod is absent.

> **Amended during execution (2026-08-02).** The native layer is seven variables, not two —
> it also covers both dialog scrims, both bottom-sheet variables, and the header (see the
> amendments above). The card-mod layer is correspondingly narrower than described: it
> extends the material to the **sidebar** (fill, blur, and border — there is no native
> `--sidebar-backdrop-filter`) and to the header's **tab strip**, plus letter-spacing and
> transition timing on both, since Home Assistant has no theme variable for either of those
> anywhere. It does **not** reach menus, tooltips, toasts, or the quick bar — those were
> never implemented; see "card-mod scope: corrected" under UI surface coverage.

### Lite entries

Lite entries emit **no** `backdrop-filter` — neither native variable, and no card-mod blur
rules. They are generated from the same tokens with blur disabled, so palette, geometry,
type, motion, and accent are identical to their full twins.

Because an unblurred translucent surface sits directly on an unpredictable backdrop, Lite
**clamps fill alpha to a minimum of `0.72`**. Lite is therefore not pixel-identical to its
full twin, and the README will say so plainly rather than claiming otherwise: it is the same
design system rendered on a near-opaque surface instead of a blurred one.

Lite exists for three documented cases: the dropdown bugs above, low-end tablet
performance, and users who simply prefer flat surfaces.

## Visual system

### Shared tokens (identical across all twelve entries)

| Token | Value | Rationale |
|---|---|---|
| Card radius | `18px` | iOS card geometry |
| Dialog radius | `28px` | iOS sheet geometry |
| Control radius | `12px` | inner controls |
| Pill radius | `980px` | fully rounded chips and toggles |
| Shadow | `0 1px 2px rgba(0,0,0,.04), 0 8px 32px rgba(0,0,0,.12)` | Apple's two-part contact + ambient shadow |
| Specular rim | `1px` inset top highlight, fading to transparent by 50% | light catching the glass edge |
| Accent | `#007AFF` light / `#0A84FF` dark | iOS system blue |
| Semantic colours | iOS system green / orange / red / purple | on, warning, alert, scene states |
| Font stack | `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, "Segoe UI", Roboto, sans-serif` | real SF Pro on Apple devices, clean fallback elsewhere |
| Tracking | `-0.4px` headline, `-0.2px` body | SF's optical tracking |
| Motion | `300ms cubic-bezier(.25,.1,.25,1)` | Apple's standard ease |

SF Pro is licensed for Apple platforms only and is therefore not bundled. The system stack
resolves to genuine SF Pro on macOS, iOS, and iPadOS — where most HA dashboards are viewed —
and falls back cleanly elsewhere. No font files are shipped and no licence is violated.

### Background

The theme supplies a layered CSS mesh gradient as the default `lovelace-background`. Pure
CSS: no image files, no bandwidth cost, and it gives `backdrop-filter` something to blur.
The README documents a one-line override for users who prefer their own wallpaper.

> **Amended during execution (2026-08-02).** "Layered CSS mesh gradient" overstates what
> shipped. It's a single three-stop `linear-gradient(160deg, background_from 0%,
> background_via 52%, background_to 100%)` (see `glassbuild/variables.py`,
> `lovelace-background`) — not a layered mesh (multiple overlapping radial/conic gradients
> at different angles, the CSS technique the term "mesh gradient" refers to). The rest of
> the rationale holds: it's still pure CSS, no image files, and it still gives
> `backdrop-filter` something to blur. Also applies only to Lovelace dashboard views — see
> the README's "Outside dashboards" section for pages that don't read it.

### Material tuning — the only axis on which the two materials differ

| Property | Glass | Frosted Glass |
|---|---|---|
| Blur | `blur(8px)` | `blur(40px)` |
| Saturation | `saturate(180%)` | `saturate(150%)` |
| Fill alpha (light / dark) | `.10 / .14` | `.55 / .45` |
| Rim alpha | `.45` (bright) | `.20` (soft) |
| Lite fill alpha | `.72` (clamped) | `.72` (clamped) |

The `saturate()` companion to the blur is what makes Apple's materials look alive rather
than muddy: colours behind the glass bloom instead of washing out.

## UI surface coverage

Governing principle: **material on chrome and containers, opaque on dense reading
surfaces.** This mirrors Apple's own practice — Control Center is glass, an editor pane is
not. Frosting a forty-row data table or a YAML editor destroys legibility.

**Full material, native** (no card-mod required)
All `ha-card` cards and card headers; more-info dialogs; all `ha-dialog`s and their headers.

**Full material, card-mod required**
App header and toolbar; sidebar and sidebar items; view tabs; badges; sections-view
containers; overflow menus and dropdowns; quick-bar / search dialog; toasts; tooltips; FAB.

> **Amended during execution (2026-08-02) — card-mod scope: corrected.** Both lists above
> are wrong about what's native versus what needed card-mod, and the second list describes
> work that was never implemented and, for at least one item, cannot be. Corrected:
>
> **Full material, native** (no card-mod required) — all `ha-card` cards and card headers;
> more-info dialogs; all `ha-dialog`s and their headers, plus both dialog scrims; bottom
> sheets, surface and scrim; **and the app header** (fill, blur, and text color — the
> header's own backdrop-filter is native via `--app-header-backdrop-filter`).
>
> **card-mod required, and shipped** — only two surfaces, plus two cross-cutting style
> properties Home Assistant has no theme variable for at all:
> - The **sidebar**'s blur and border (its fill is native; there's no
>   `--sidebar-backdrop-filter`, so card-mod supplies the blur itself).
> - The header's **tab strip** background.
> - **Letter-spacing** on the header and the sidebar's title/list items.
> - **Transition duration/easing** on the header and sidebar.
>
> **Not themed, and why** — the original list named app header/toolbar (now native, see
> above), view tabs (shipped, see above), badges, sections-view containers, overflow menus
> and dropdowns, quick-bar/search dialog, toasts, tooltips, and the FAB. None of the
> remaining eight (badges, sections-view containers, menus, dropdowns, quick bar, toasts,
> tooltips, FAB) were implemented. They fall back to Home Assistant's default, unstyled
> appearance. At least one is not a scoping choice but a hard limit: `ha-toast` renders with
> a hardcoded color and exposes no theme variable or card-mod hook, so it cannot be glassed
> by this theme regardless of effort spent. The others were simply out of scope for what
> shipped — a future revision could pursue card-mod selectors for them, but none currently
> exist in `glassbuild/cardmod.py`.

**Light material** — derived from each material's full values as: blur at half the full
radius (Glass `blur(4px)`, Frosted `blur(20px)`), fill alpha `+0.08` above the full-material
value, same rim, no separate shadow. Computed by the generator from the tuning table rather
than authored separately, so the two materials cannot drift apart.

Tile-card features; entity rows; buttons (`mwc-button`, `ha-icon-button`); toggles,
sliders, and `ha-control-*` controls; chips; text fields, selects, comboboxes, checkboxes,
radios.

**Opaque or near-opaque** (legibility takes precedence)
`ha-data-table` rows; CodeMirror and YAML editors; Developer Tools output; logbook and
history lists; markdown card body; automation and script editor graph nodes.

**Themed via variables but not glassed** (these have their own rendering paths)
Charts — energy, history, statistics: axis, grid, and series colours; map card; login page;
scrollbars, styled thin and translucent.

### Accepted trade-offs

**Dropdown layering.** Confirmed upstream and unfixed
([#20725](https://github.com/home-assistant/frontend/issues/20725),
[#26113](https://github.com/home-assistant/frontend/issues/26113)). Dialog blur is enabled
by default because the effect is central to the look and the bug only manifests for
dropdowns inside more-info dialogs. Users who hit it switch to the corresponding Lite entry;
the README documents the symptom, the cause, and that remedy explicitly, so an affected user
recognises it immediately rather than assuming the theme is broken.

**Performance.** `backdrop-filter` is GPU-expensive and compounds per layer. On
wall-mounted tablets — Fire HD, older iPads — a dashboard of thirty blurred cards will
stutter. Mitigation: blur is applied only to the layers listed above and is never nested;
the Lite entries exist as the documented remedy.

**Contrast.** Translucent surfaces place text on an unpredictable backdrop, a genuine WCAG
risk. Mitigation: the surface fill *is* the scrim — each material defines a minimum fill
alpha below which the generator refuses to emit, and light-mode fill alphas are tuned so
body text composited over fill-over-gradient clears 4.5:1, verified by test rather than by
eye. No separate text-shadow layer is used; a shadow would mask insufficient contrast rather
than fix it, and would defeat the contrast test. A user who sets a busy photo wallpaper can
still break contrast; the README states this plainly.

## CI/CD

### `ci.yml` — on every pull request and push to `main`

| Job | Action | Fails when |
|---|---|---|
| `lint` | `yamllint` over `tokens/` and `themes/`; `actionlint` over the workflows | malformed YAML, tabs, bad indentation |
| `drift` | `build_themes.py --check` | committed `themes/glass.yaml` does not match generator output |
| `validate` | custom Python check | any of the twelve entries missing; a required HA variable undefined; a `var(--x)` reference resolving to neither a defined token nor a known HA builtin; malformed colour values; **any `backdrop-filter` present in a Lite entry** |
| `hacs` | `hacs/action` with `CATEGORY: theme` | repository is not installable via HACS |

The dangling-variable check in `validate` is the highest-value job: an undefined `var()` in
an HA theme fails silently at runtime, rendering transparent or black with no error surfaced
anywhere.

`home-assistant/actions/hassfest` is deliberately **not** used. It validates custom
integrations via `manifest.json` and has nothing to check in a theme repository. The HACS
action is the correct and sufficient validator.

### `release.yml` — on `v*` tags

Re-runs `drift` and `validate`, zips `themes/`, and publishes a GitHub Release with notes
generated from conventional commits. Releases are optional for HACS but give users a
versioned update path and a pinnable rollback.

### Supply chain

All third-party actions are pinned to commit SHAs, with Dependabot configured to bump them.
An unpinned `@main` action is a supply-chain hole in a repository strangers install.

## Testing

### Automated (pytest, executed by `ci.yml`)

- **Generator unit tests** — token merge precedence (base → material → mode → lite); all
  twelve entries emitted under the correct names; `modes:` present on the Auto entries and
  absent on the flat ones; material alphas and blur radii match the tuning table.
- **Lite purity test** — no Lite entry contains a `backdrop-filter` in any form, native or
  card-mod, and every Lite fill alpha is at least `0.72`. This is the test that keeps the
  documented remedy actually remedial.
- **Contrast tests** — composite each text token's `rgba` over the shipped background
  gradient and assert WCAG AA: 4.5:1 body, 3:1 large text. Run for all twelve entries; Lite
  is checked against the raw gradient with no blur softening.
- **Dangling-variable test** — the `validate` check expressed as a test as well as a lint
  step.
- **Round-trip test** — the generated file re-parses as valid YAML, and every entry is a
  flat string-to-string mapping, which is what HA's theme loader requires.

### Manual (documented checklist)

A `demo/` dashboard YAML exercising every surface listed under UI surface coverage: one of
each card type, a data table, a more-info dialog, the YAML editor, a chart, and — because it
is the known failure mode — a picture-elements card with a dropdown. The reviewer loads it
in real Home Assistant and steps through all twelve entries, light and dark, with and
without card-mod.

### Explicitly rejected approaches

**Playwright against a dockerised Home Assistant.** Home Assistant's frontend DOM changes
across releases, so such a suite would break for reasons unrelated to this theme; pinning HA
to an old version to keep it green would test the wrong thing.

**A standalone HTML harness mimicking HA components.** It would drift from real HA and
produce false confidence, which is worse than no test at all.

The generator logic and the contrast arithmetic are what genuinely merit automation. Visual
verification is a human step, and the demo dashboard exists to make that step fast.

## Success criteria

1. Twelve entries appear in the Home Assistant theme picker under the names in the entry
   matrix.
2. On a bare install with no card-mod, cards and dialogs show real blur via the native
   variables.
3. With card-mod installed, the header, sidebar, tabs, menus, tooltips, toasts, and quick
   bar also show the material.
4. Lite entries contain no `backdrop-filter` anywhere and remain legible, verified by test.
5. Every surface listed under UI surface coverage is themed — none falls back to HA defaults
   or renders unstyled.
6. Body text clears WCAG AA against the shipped background for all twelve entries, verified
   by test.
7. `ci.yml` passes on a clean checkout; `release.yml` produces an installable release.
8. The repository installs via HACS as a custom repository.

> **Amended during execution (2026-08-02).** Criteria 3 and 5 are unmet as originally
> written and are rewritten below to describe what actually shipped, rather than left
> standing as aspirational. Criteria 1, 2, 4, 6, 7, and 8 are unaffected and hold as
> written — all are verified by the test suite or by CI directly.
>
> 3. With no card-mod installed, cards, dialogs (surface and scrim), bottom sheets
>    (surface and scrim), and the header already show the material natively (criterion 2,
>    extended — see the native-variable amendment above). With card-mod additionally
>    installed, the sidebar and the header's tab strip also show the material, and the
>    header/sidebar pick up tightened letter-spacing and themed transition timing. card-mod
>    does **not** extend the material to menus, tooltips, toasts, or the quick bar — those
>    were never implemented (`ha-toast` specifically cannot be, per the UI surface coverage
>    amendment above).
> 5. Every surface listed under "Full material, native" and "card-mod required, and
>    shipped" in the corrected UI surface coverage section is themed. Surfaces listed under
>    "Not themed, and why" fall back to Home Assistant's default appearance by design, not
>    by omission discovered after the fact — this criterion no longer claims blanket
>    coverage of every surface named in the original UI-surface-coverage table.
