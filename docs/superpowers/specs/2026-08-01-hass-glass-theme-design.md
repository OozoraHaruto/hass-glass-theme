# hass-glass-theme — Design

**Date:** 2026-08-01
**Status:** Approved (design phase)

## Purpose

A Home Assistant theme package providing two Apple-inspired glass materials — a clear
"Glass" and a diffuse "Frosted Glass" — each available in Auto, Light, and Dark, for a
total of six entries in Home Assistant's theme picker. Distributed via HACS, maintained
from a single token source, and validated by GitHub CI/CD.

## Constraints that shape the design

Two facts about Home Assistant drove most of the decisions below.

**Themes are CSS custom properties, not CSS.** A native HA theme can set variables but
cannot declare `backdrop-filter: blur()`, which is what makes frosted glass read as glass
rather than as tinted plastic. Real blur requires CSS injection, which in practice means
the `card-mod` HACS integration and its `card-mod-theme` / `card-mod-root-yaml` theme keys.

**`backdrop-filter` blurs what is behind it.** Home Assistant's default dashboard
background is a flat solid colour, and blurring a flat colour yields the same flat colour.
A glass theme that does not supply its own backdrop produces no visible effect. The theme
therefore ships its own background; this is load-bearing, not decorative.

## Architecture

```
hass-glass-theme/
├─ tokens/
│  ├─ base.yaml            # geometry, type scale, motion, spacing — shared by all six
│  ├─ glass.yaml           # material: blur 8px, low alpha, bright specular rim
│  ├─ frosted-glass.yaml   # material: blur 40px, high alpha, soft diffuse rim
│  └─ modes/
│     ├─ light.yaml        # palette + material tuning for light
│     └─ dark.yaml         # palette + material tuning for dark
├─ scripts/build_themes.py # tokens → themes/*.yaml
├─ tests/                  # pytest: generator, contrast, dangling vars, round-trip
├─ themes/                 # GENERATED, committed to the repo
│  ├─ glass.yaml           # Glass, Glass Light, Glass Dark
│  └─ frosted-glass.yaml   # Frosted Glass, Frosted Glass Light, Frosted Glass Dark
├─ demo/                   # dashboard YAML exercising every themed surface
├─ hacs.json
├─ README.md
└─ .github/
   ├─ workflows/{ci.yml,release.yml}
   └─ dependabot.yml
```

### Why a generator

Six entries share one design system. Maintaining roughly 150 variables across six entries
by hand guarantees drift, and YAML anchors cannot help because every top-level key in an HA
theme file becomes a picker entry — anchor definitions would appear as themes. A generator
gives one place to change a radius or an accent.

Python, because the Home Assistant ecosystem is Python and `pyyaml` is the only dependency
required. A Node generator would add a `package.json` and `node_modules` to a repository
that otherwise ships only YAML, for no benefit.

Generated files are committed so HACS and manual installs work with no build step. CI
re-runs the generator and fails on drift, which keeps the committed output honest.

### Two-layer theme output

Each generated entry carries both layers, so the theme degrades gracefully:

1. **Baseline layer** — standard HA theme variables only. Translucent `rgba` fills and
   gradients. No dependencies; looks deliberate on a bare install.
2. **Upgrade layer** — a `card-mod-theme` key plus `card-mod-root-yaml` /
   `card-mod-card-yaml` blocks carrying the real `backdrop-filter`. Home Assistant ignores
   these keys when card-mod is not installed.

### Auto vs. flat entries

The Auto entries wrap their mode payloads in Home Assistant's `modes: light: / dark:`
block. The Light and Dark entries inline the same payload flat. Because all three derive
from the same token merge, a given mode renders identically whichever entry the user picks.

## Visual system

### Shared tokens (identical across all six entries)

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

### Material tuning — the only axis on which the two themes differ

| Property | Glass | Frosted Glass |
|---|---|---|
| Blur | `blur(8px)` | `blur(40px)` |
| Saturation | `saturate(180%)` | `saturate(150%)` |
| Fill alpha (light / dark) | `.10 / .14` | `.55 / .45` |
| Rim alpha | `.45` (bright) | `.20` (soft) |

The `saturate()` companion to the blur is what makes Apple's materials look alive rather
than muddy: colours behind the glass bloom instead of washing out.

### Open item to verify during implementation

Whether the current Home Assistant frontend exposes a native `backdrop-filter` hook on
`ha-card`. If it does, the baseline layer gains real blur and card-mod becomes purely
additive. If it does not, the baseline layer remains translucent-only as designed. This is
to be checked against the installed HA frontend version, not assumed. Either outcome is
compatible with the architecture above; only the README's description of the bare install
changes.

## UI surface coverage

Governing principle: **material on chrome and containers, opaque on dense reading
surfaces.** This mirrors Apple's own practice — Control Center is glass, an editor pane is
not. Frosting a forty-row data table or a YAML editor destroys legibility.

**Full material** (blur + rim + shadow)
App header and toolbar; sidebar and sidebar items; view tabs; all `ha-card` cards; card
headers; badges; sections-view containers; more-info dialogs; all `ha-dialog`s and their
headers; overflow menus and dropdowns; quick-bar / search dialog; toasts; tooltips; FAB.

**Light material** — derived from each theme's full material as: blur at half the full
radius (Glass `blur(4px)`, Frosted `blur(20px)`), fill alpha `+0.08` above the full-material
value, same rim and no separate shadow. These are computed by the generator from the tuning
table rather than authored separately, so the two materials cannot drift apart.

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

**Performance.** `backdrop-filter` is GPU-expensive and compounds per layer. On
wall-mounted tablets — Fire HD, older iPads — a dashboard of thirty blurred cards will
stutter. Mitigation: blur is applied only to the layers listed under "full material" and is
never nested. The README documents dropping to the Frosted variant's cheaper single-pass
blur, or to the baseline no-card-mod install, on weak hardware.

**Contrast.** Translucent surfaces place text on an unpredictable backdrop, a genuine WCAG
risk. Mitigation: the surface fill *is* the scrim — each material defines a minimum fill
alpha below which the generator refuses to emit, and light-mode fill alphas are tuned so
body text composited over fill-over-gradient clears 4.5:1, verified by test rather than by
eye. No separate text-shadow layer is used; a shadow would mask insufficient contrast
rather than fix it, and would defeat the contrast test. A user who sets a busy photo wallpaper can still break contrast; the README
states this plainly.

## CI/CD

### `ci.yml` — on every pull request and push to `main`

| Job | Action | Fails when |
|---|---|---|
| `lint` | `yamllint` over `tokens/` and `themes/`; `actionlint` over the workflows | malformed YAML, tabs, bad indentation |
| `drift` | `build_themes.py --check` | committed `themes/*.yaml` do not match generator output |
| `validate` | custom Python check | any of the six entries missing; a required HA variable undefined; a `var(--x)` reference resolving to neither a defined token nor a known HA builtin; malformed colour values |
| `hacs` | `hacs/action` with `CATEGORY: theme` | repository is not installable via HACS |

The dangling-variable check in `validate` is the highest-value job: an undefined `var()` in
an HA theme fails silently at runtime, rendering transparent or black with no error
surfaced anywhere.

`home-assistant/actions/hassfest` is deliberately **not** used. It validates custom
integrations via `manifest.json` and has nothing to check in a theme repository. The HACS
action is the correct and sufficient validator.

### `release.yml` — on `v*` tags

Re-runs `drift` and `validate`, zips `themes/`, and publishes a GitHub Release with notes
generated from conventional commits. This provides HACS users a versioned update path.

### Supply chain

All third-party actions are pinned to commit SHAs, with Dependabot configured to bump them.
An unpinned `@main` action is a supply-chain hole in a repository strangers install.

### Open item to verify during implementation

Whether the HACS `theme` category supports a repository shipping two files in `themes/`
rather than one. If only a single file per repository is tracked, the fallback is one
`glass-themes.yaml` containing all six entries — identical themes from identical tokens,
merely one output file instead of two. Nothing above this point in the design changes.

## Testing

### Automated (pytest, executed by `ci.yml`)

- **Generator unit tests** — token merge precedence (base → material → mode); all six
  entries emitted under the correct names; `modes:` present on the Auto pair and absent on
  the flat four; material alphas and blur radii match the tuning table.
- **Contrast tests** — composite each text token's `rgba` over the shipped background
  gradient and assert WCAG AA compliance: 4.5:1 for body text, 3:1 for large text.
- **Dangling-variable test** — the `validate` check expressed as a test as well as a lint
  step.
- **Round-trip test** — every generated file re-parses as valid YAML, and every entry is a
  flat string-to-string mapping, which is what HA's theme loader requires.

### Manual (documented checklist)

A `demo/` dashboard YAML exercising every surface listed under UI surface coverage: one of
each card type, a data table, a more-info dialog, the YAML editor, a chart. The reviewer
loads it in a real Home Assistant instance and steps through all six entries, in light and
dark, with and without card-mod installed.

### Explicitly rejected approaches

**Playwright against a dockerised Home Assistant.** Home Assistant's frontend DOM changes
across releases, so such a suite would break for reasons unrelated to this theme; pinning HA
to an old version to keep it green would test the wrong thing.

**A standalone HTML harness mimicking HA components.** It would drift from real HA and
produce false confidence, which is worse than no test at all.

The generator logic and the contrast arithmetic are what genuinely merit automation. Visual
verification is a human step, and the demo dashboard exists to make that step fast.

## Success criteria

1. Six entries appear in the Home Assistant theme picker with the specified names.
2. With card-mod installed, every surface under "full material" shows real blur.
3. Without card-mod, the theme still renders as a coherent, deliberate design.
4. Every surface listed under UI surface coverage is themed — none falls back to HA
   defaults or renders unstyled.
5. Body text clears WCAG AA against the shipped background, verified by test.
6. `ci.yml` passes on a clean checkout; `release.yml` produces an installable release.
7. The repository installs via HACS as a custom repository.
