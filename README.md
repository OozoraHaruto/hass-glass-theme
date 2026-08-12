# Glass & Frosted Glass Themes for Home Assistant

Apple-inspired glass themes for Home Assistant's Lovelace dashboard: translucent,
blurred cards and dialogs over a soft gradient background, in two intensities and
two color schemes, each pinnable to light or dark.

## What it is

Twelve theme entries, generated from one token source (`tokens/`) into a single
generated file, `themes/glass.yaml`. Two materials, each in an Auto / Light / Dark
variant, each with a matching Lite twin:

| Material          | Auto              | Light                   | Dark                   |
| ------------------ | ----------------- | ------------------------ | ------------------------ |
| Glass               | `Glass`             | `Glass Light`             | `Glass Dark`             |
| Glass Lite          | `Glass Lite`        | `Glass Light Lite`        | `Glass Dark Lite`        |
| Frosted Glass        | `Frosted Glass`     | `Frosted Glass Light`     | `Frosted Glass Dark`     |
| Frosted Glass Lite  | `Frosted Glass Lite`| `Frosted Glass Light Lite`| `Frosted Glass Dark Lite`|
| Liquid Glass        | `Liquid Glass`      | `Liquid Glass Light`      | `Liquid Glass Dark`      |

- **Glass** (`blur(20px)`) is Apple's *regular* Liquid Glass — translucent, but
  wide enough to diffuse whatever is behind it into a colour field rather than
  leaving it legible through the card. The blur sits where detail stops
  resolving and no further: blur *scatters* light, which is what frosted glass
  does, so pushing it harder to buy legibility just turns glass into frost.
- **Frosted Glass** is a heavier blur (`blur(40px)`) — closer to macOS's thick
  material.
- **Liquid Glass** (`blur(18px)`) is the clearest of the three, and the only one
  that can actually *bend* light rather than scatter it — but only if you also
  install the optional companion module (see **Refraction** below). Without it
  the entry is still a valid, slightly clearer Glass; the refraction is an
  upgrade layered on top, never the thing holding it up. It has no **Lite**
  variants, because Lite drops `backdrop-filter` entirely and that is precisely
  where the refraction lives.
- All three materials remap the backdrop's luminance after blurring it (dark
  mode dims and hardens, light mode lifts and softens) and carry a directional
  specular edge — a highlight along the top, shadow along the bottom — so a
  card reads as a surface in front of the background rather than a hole
  through to it. With no way to refract in plain CSS, a rim brighter than the
  body is what separates glass from frost.
- **Auto** entries follow Home Assistant's light/dark setting; **Light**/**Dark**
  entries pin one mode regardless of the ambient setting.
- **Lite** entries exist for the dropdown bug below and for underpowered wall
  tablets — see [Lite entries](#lite-entries).

## Install

1. In HACS, add this repository as a custom repository with category **Theme**
   (or install it directly if it's already listed).
2. Make sure your `configuration.yaml` merges the themes directory:
   ```yaml
   frontend:
     themes: !include_dir_merge_named themes
   ```
3. Restart Home Assistant.
4. Open your user profile, scroll to **Theme**, and pick one of the fifteen
   entries above.

For manual installation from a release archive:

1. Extract `themes/glass.yaml` to `<config>/themes/glass.yaml`.
2. Extract `www/glass-dropdown.js` to `<config>/www/glass-dropdown.js` if you want the optional opened-menu frosted fill described below.
3. Configure theme loading and the optional module as shown in the relevant sections, then restart Home Assistant.

`hacs.json` sets a floor of Home Assistant **2024.5.0**, since that's roughly
when `--ha-card-backdrop-filter` itself landed. A few of the other variables
this theme sets (the bottom-sheet pair, the `ha-font-family-*` trio) landed
in later releases than that floor — on a Home Assistant version close to
2024.5.0 those specific variables simply no-op rather than error, so the
theme degrades gracefully (missing a blur or falling back to the default
font) instead of breaking. Running a current Home Assistant release avoids
this entirely.

## card-mod is optional

Home Assistant natively exposes seven `backdrop-filter` theme variables, and
this theme sets all seven: `--ha-card-backdrop-filter`,
`--ha-dialog-surface-backdrop-filter`, `--ha-dialog-scrim-backdrop-filter`,
`--dialog-backdrop-filter` (a legacy alias of the scrim variable),
`--ha-bottom-sheet-surface-backdrop-filter`,
`--ha-bottom-sheet-scrim-backdrop-filter`, and `--app-header-backdrop-filter`.

That means **with no card-mod installed at all**, you already get real,
native blur on cards, dialogs (including the more-info dialog), dialog and
bottom-sheet scrims, bottom sheets, and the dashboard header.

[card-mod](https://github.com/thomasloven/lovelace-card-mod) is only needed
for the small handful of surfaces Home Assistant has no theme variable for at
all:

- The **sidebar**'s blur and border — `sidebar-background-color` (the fill)
  is already native and applies with or without card-mod, but there's no
  native `--sidebar-backdrop-filter`, so the blur itself and the border are
  card-mod's job.
- The header's **tab strip** (and a couple of edit-mode-safe touch-ups to the
  header's own fill/border, so they survive Lovelace's edit mode).
- **Letter-spacing**, on the header and the sidebar's title and list items —
  Home Assistant has no letter-spacing theme variable anywhere, so there's no
  native way to set it at all, with or without card-mod.
- **Transition duration/easing** on the surfaces above, for the same reason:
  no native theme variable for motion timing exists either.

If you don't install card-mod, everything above still looks correct except
for two things: the sidebar is **translucent but unblurred** (it already has
its glass-tinted fill natively, just without the blur sitting behind it,
which can look a little washed out rather than opaque), and header/sidebar
type uses default tracking instead of the tightened letter-spacing. Nothing
breaks either way.

## Outside dashboards

`lovelace-background` — the gradient this theme ships — is a Lovelace-view
variable. It only paints behind dashboard views. Settings, Developer Tools,
History, Logbook, and Media Browser are not Lovelace views, so none of them
read it; they fall back to Home Assistant's own `--primary-background-color`,
a flat, near-opaque page color (`#F2F2F7` in light mode, `#1C1C1E` in dark).

A glass card dropped onto a flat page still gets its translucent fill and
blur, but there's no gradient behind it for the blur to catch — a card there
looks like a slightly different flat tint rather than the layered glass
effect you see on a dashboard. On those pages the card's **rim** and
**shadow** do the work of separating it from the page that the gradient does
elsewhere, which is why the light-mode rim is a dark hairline
(`rgba(60, 60, 67, ...)`, matching the palette's divider color) rather than
white: a white rim is invisible against light-mode's light flat pages, the
dashboard gradient included. Dark mode's rim stays white, since it already
reads clearly against dark, low-luminance surfaces everywhere it appears.

If a card still looks flat on these pages, that's expected, not a bug — it's
the same fill and border token used on the dashboard, just without a gradient
underneath to blur.

## Known issue: dropdowns

Two Home Assistant frontend bugs affect any theme that sets
`--ha-card-backdrop-filter`, including this one, and both are closed upstream
as "not planned":

- [frontend#20725](https://github.com/home-assistant/frontend/issues/20725) —
  a dropdown menu (e.g. an `input_select` row) can render *behind* a
  picture-elements card elsewhere on the same view instead of on top of it,
  because the picture-elements card's backdrop-filter creates its own
  stacking context that traps the dropdown's overlay beneath it. Menu items
  become unclickable.
- [frontend#26113](https://github.com/home-assistant/frontend/issues/26113) —
  a dropdown opened from inside a more-info dialog can escape and render
  outside the dialog's bounds instead of staying inside it.
- Theme YAML alone cannot independently override the **opened menu's**
  background. Its fill is locked to `--card-background-color` by a `:host`
  rule inside `ha-dropdown`'s shadow root, and the menu is a webawesome popup
  teleported to `<body>` — outside `hui-root`, so `card-mod`'s root scope
  cannot reach it either. The optional host-level `www/glass-dropdown.js`
  workaround gives opened menus the Frosted Glass fill and injects a fixed
  `blur(20px)` rule into each dropdown's open shadow root when a Glass or
  Liquid Glass entry is active. The fill remains as a fallback if Home
  Assistant changes its internal `wa-popup::part(popup)` structure. It does
  not fix frontend#20725 or frontend#26113. Frosted Glass already uses the
  desired fill and needs no override. The **closed** dropdown box is frosted
  via `ha-color-form-background` — the token the modern `ha-select` reads.
  Because that is a shared form-field token, modern text inputs, textareas,
  and time inputs use the same fill; legacy fields use the aligned
  `input-fill-color` and `mdc-text-field-fill-color` tokens.

Release archives include the optional module at `www/glass-dropdown.js`. To enable the opened-menu workaround:

1. Copy the archive's `www/glass-dropdown.js` to `<config>/www/glass-dropdown.js` if it is not already there.
2. Add to `configuration.yaml`:
   ```yaml
   frontend:
     extra_module_url:
       - /local/glass-dropdown.js
   ```
3. Restart Home Assistant. If the old cached module remains, perform a hard
   browser refresh.

The optional opened-menu workaround is supported on Chromium-based browsers,
not Safari. Safari can lose both its injected Frosted Glass fill and popup blur
after a browser refresh. On Safari, use the normal dropdown styling or switch
to the matching Lite theme instead.

**Remedy for frontend#20725:** switch to the matching Lite entry (e.g. `Glass`
→ `Glass Lite`). Lite entries set no `backdrop-filter` anywhere, so they don't
create the stacking context that traps the dropdown. The optional module does
not replace this workaround.

`demo/dashboard.yaml` includes a picture-elements card next to an
`input_select` dropdown specifically to reproduce the frontend#20725 shape —
see that file for a manual check.

## Lite entries

Lite entries exist for two reasons: to work around the dropdown bug above,
and because `backdrop-filter` is expensive to render continuously on
underpowered wall-mounted tablets.

A Lite entry sets **no `backdrop-filter` anywhere** — no blur on cards,
dialogs, scrims, bottom sheets, or the header. To stay legible without blur,
the main surface fill (cards, dialogs, header, sidebar) is clamped to a
near-opaque `rgba(..., 0.72)` instead.

**Lite entries are not pixel-identical to their full twins.** The full
entries use a much lower alpha (as low as 0.10) that reads as glass only
because of the blur sitting behind it; without that blur, the same low alpha
would look muddy and be hard to read. Lite entries are a deliberately
different, near-solid look built for legibility without blur — not a
"disable blur" toggle on the full entries.

**Lite entries emit no card-mod keys at all** — not even `card-mod-theme`.
If you install card-mod and pick a Lite entry, you will not get sidebar
glass or the tightened letter-spacing described above; card-mod has
nothing to do for a Lite entry, since there's no blur anywhere for it to
add. This is intentional, not a bug, but it can be a surprise if you're
expecting card-mod's touch-ups on every entry uniformly.

## Refraction (optional, Chromium only)

The **Liquid Glass** entries are the only ones that can bend light rather than
just scatter it — and doing that needs one file outside `themes/`.

Plain CSS has no way to refract: `backdrop-filter` gives you `blur()` and
nothing that displaces a pixel. Real refraction needs an SVG
`feDisplacementMap`, and a `backdrop-filter` can only reach one through a
**same-document** `url(#id)` fragment. Chromium resolves nothing else —
external `.svg` files and `data:` URIs are both rejected
([Blink bug 109212](https://issues.chromium.org/issues/41054930)) — and a
rejected reference doesn't just skip its own term: per the Filter Effects
spec it invalidates the *entire* chain, so the card would lose its blur too.

A Home Assistant theme is a YAML map of CSS variables, and card-mod injects
CSS rather than markup. Neither can put an element in the document. Hence
`www/glass-refraction.js`:

1. Copy `www/glass-refraction.js` from this repo to `<config>/www/glass-refraction.js`.
2. Add to `configuration.yaml` (the optional dropdown workaround can be
   registered alongside it):
   ```yaml
   frontend:
     extra_module_url:
       - /local/glass-refraction.js
       - /local/glass-dropdown.js
   ```
3. Restart Home Assistant and pick a **Liquid Glass** entry. If a copied
   module remains cached, perform a hard browser refresh.

**Skipping this is a supported configuration.** The Liquid Glass entries ship
an ordinary blur chain of their own and the module only ever *upgrades* it, by
repointing four surface variables at an alternative chain the theme also
publishes. There is no broken intermediate state — which is exactly why the
theme never references the refraction chain itself, and why the module
disables its own override the moment a non-refractive theme is active.

Caveats, stated plainly:

- **Chromium only** (Chrome, Edge, the Android companion app's webview).
  Firefox and Safari get the plain blur on purpose — see WebKit bug
  [245510](https://bugs.webkit.org/show_bug.cgi?id=245510). The module detects
  the engine by proxy (the Houdini Paint API, which only Blink ships) because
  `CSS.supports` reports on *syntax* and every engine parses `url(#x)` happily
  whether or not it will later resolve it.
- **Not for wall tablets.** Displacing the backdrop is genuinely expensive to
  composite. If a device needs the **Lite** entries, it does not want this.
- The displacement is confined to the outer ~18% of each axis, so it reads as
  the thickness at a card's edge rather than a fish-eye across its face.

## Accessibility

Every one of the fifteen entries clears WCAG AA against the shipped
`lovelace-background` gradient: body text at 4.5:1, secondary/large text at
3.0:1. This is checked by an automated test suite
(`tests/test_contrast.py`) that composites each entry's card fill and text
color over three sample points along its gradient (start, middle, and end
stop) and asserts the resulting contrast ratio, across all fifteen entries and
both light/dark modes where an entry supports both.

The tightest margin among all of those checks is **3.24:1**, for secondary
text in `Glass`/`Glass Light` mode — still clearing the 3.0:1 minimum, but
with less headroom than everywhere else.

`disabled-text-color` is deliberately **not** covered by that suite (its
worst-case ratio is about **1.99:1**, well under 4.5:1). WCAG explicitly
exempts disabled/inactive controls from its contrast requirements, so this is
an intentional gap, not an oversight — but it's worth knowing if you're
auditing this theme against a stricter internal bar than WCAG AA.

**A busy custom wallpaper can break this.** The contrast tests are measured
against the shipped gradient background, not against your actual wallpaper.
If you override `lovelace-background` with a photo (see below), especially a
high-contrast or busy one, text over the translucent card fill can end up
with much worse real-world contrast than the tests certify, particularly on
the low-alpha full-glass entries.

## Custom wallpaper

Override `lovelace-background` from your own theme, layered on top of one of
these (via `!include` and a themes-merge trick, or by copying an entry into
your own theme file):

```yaml
My Custom Glass:
  lovelace-background: center / cover no-repeat url("/local/my-wallpaper.jpg")
```

Because the card fill is translucent, whatever you put here shows through
every glass surface — so busy or low-contrast photos are more likely to hurt
text readability than a plain color or gradient would. See
[Accessibility](#accessibility) above.

## Contributing

`themes/glass.yaml` is a **generated file** — never hand-edit it, your edits
will be silently overwritten the next time someone runs the generator.

To change anything about the theme:

1. Edit the token sources under `tokens/`.
2. Regenerate: `python scripts/build_themes.py`
3. Run the test suite: `python -m pytest`
4. Commit both your token changes and the regenerated `themes/glass.yaml`.

`python scripts/build_themes.py --check` fails without writing anything if
`themes/glass.yaml` has drifted from `tokens/` — useful in CI or as a
pre-commit sanity check.

## License

MIT — see [LICENSE](LICENSE).
