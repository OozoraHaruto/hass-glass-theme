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

- **Glass** is a light, subtle blur (`blur(8px)`) — closer to iOS's thin material.
- **Frosted Glass** is a heavier blur (`blur(40px)`) — closer to macOS's thick
  material.
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
4. Open your user profile, scroll to **Theme**, and pick one of the twelve
   entries above.

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

**Remedy:** if either of these bites you, switch to the matching Lite entry
(e.g. `Glass` → `Glass Lite`). Lite entries set no `backdrop-filter` anywhere,
so they don't create the stacking context that traps the dropdown.

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

## Accessibility

Every one of the twelve entries clears WCAG AA against the shipped
`lovelace-background` gradient: body text at 4.5:1, secondary/large text at
3.0:1. This is checked by an automated test suite
(`tests/test_contrast.py`) that composites each entry's card fill and text
color over three sample points along its gradient (start, middle, and end
stop) and asserts the resulting contrast ratio, across all twelve entries and
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
