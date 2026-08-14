# Glass & Frosted Glass Themes for Home Assistant

Apple-inspired clear and frosted materials for Home Assistant's Lovelace dashboard,
with low-opacity Glass surfaces, an intentionally near-opaque Lite fallback, and
opt-in Frosted backdrop blur.

## What it is

Fifteen theme entries, generated from one token source (`tokens/`) into
`themes/glass.yaml`:

| Material          | Auto                 | Light                      | Dark                      |
| ----------------- | -------------------- | -------------------------- | ------------------------- |
| Glass             | `Glass`              | `Glass Light`              | `Glass Dark`              |
| Glass Lite        | `Glass Lite`         | `Glass Light Lite`         | `Glass Dark Lite`         |
| Frosted Glass     | `Frosted Glass`      | `Frosted Glass Light`      | `Frosted Glass Dark`      |
| Frosted Glass Lite| `Frosted Glass Lite` | `Frosted Glass Light Lite` | `Frosted Glass Dark Lite` |
| Liquid Glass      | `Liquid Glass`       | `Liquid Glass Light`       | `Liquid Glass Dark`       |

- **Glass** uses a low-opacity translucent fill (`0.14` in light mode, `0.16`
  in dark mode), a bright rim, and a directional specular edge. It does not
  apply general backdrop blur.
- **Liquid Glass** is clearer still (`0.11` in light mode, `0.13` in dark
  mode), with a hotter rim and stronger edge. It applies no general backdrop
  blur, and current generated entries do not activate SVG refraction. It has
  no separate Lite entries; `Glass Lite` is the near-opaque fallback.
- **Glass Lite** uses a near-opaque `0.72` surface for readability, weak
  hardware, and compatibility. It is not simply a blur-off version of Glass,
  because Glass is already unblurred.
- **Frosted Glass** uses a high-opacity diffuse fill and `blur(40px)` across
  full surfaces.
- **Frosted Glass Lite** is the near-opaque, no-blur Frosted fallback.
- **Auto** entries follow Home Assistant's light/dark setting. **Light** and
  **Dark** entries pin one mode regardless of that setting.

All materials retain a perimeter rim and a directional inset edge: highlight
along the top and shade along the bottom. These details separate a surface
from its background without requiring blur.

## Install

1. In HACS, add this repository as a custom repository with category **Theme**
   (or install it directly if it is already listed).
2. Make sure your `configuration.yaml` merges the themes directory:
   ```yaml
   frontend:
     themes: !include_dir_merge_named themes
   ```
3. Restart Home Assistant.
4. Open your user profile, scroll to **Theme**, and pick one of the fifteen
   entries above.

For manual installation from a current release archive:

1. Extract `themes/glass.yaml` to `<config>/themes/glass.yaml`.
2. Optionally extract `www/glass-dropdown.js` to
   `<config>/www/glass-dropdown.js` for the opened-menu treatment described
   below.
3. If you use an older generated Liquid Glass theme, optionally extract
   `www/glass-refraction.js` to `<config>/www/glass-refraction.js` for the
   compatibility support described below. Current themes leave it inactive.
4. Configure theme loading and any optional module, then restart Home
   Assistant.

Current release archives contain `themes/glass.yaml`,
`www/glass-dropdown.js`, and `www/glass-refraction.js`.

`hacs.json` sets a floor of Home Assistant **2024.5.0** because Frosted Glass
relies on `--ha-card-backdrop-filter`. Some other variables, including the
bottom-sheet pair and `ha-font-family-*` trio, arrived later. On releases near
the floor those individual variables may no-op and fall back to Home
Assistant defaults; a current Home Assistant release provides the intended
coverage.

## Home Assistant backdrop coverage and optional card-mod

Only the three full **Frosted Glass** entries emit Home Assistant's seven
native backdrop variables:

- `--ha-card-backdrop-filter`
- `--ha-dialog-surface-backdrop-filter`
- `--ha-dialog-scrim-backdrop-filter`
- `--dialog-backdrop-filter` (legacy scrim alias)
- `--ha-bottom-sheet-surface-backdrop-filter`
- `--ha-bottom-sheet-scrim-backdrop-filter`
- `--app-header-backdrop-filter`

Those variables provide Frosted Glass blur on cards, dialogs, dialog and
bottom-sheet scrims, bottom sheets, and the dashboard header without
card-mod. **Glass** and **Liquid Glass** intentionally emit none of these
native backdrop-filter keys.

[card-mod](https://github.com/thomasloven/lovelace-card-mod) remains optional.
For every full entry, it adds:

- header and sidebar material fills and borders;
- tightened header, tab, sidebar-title, and sidebar-item tracking; and
- material transition timing.

Glass and Liquid Glass card-mod sidebar CSS is clear and unblurred. Frosted
Glass card-mod sidebar CSS retains blur because Home Assistant has no native
sidebar backdrop variable. Without card-mod, the native sidebar uses a
near-opaque compatibility fill rather than the material-specific card-mod
fill, while the header and other theme variables still apply normally.

Lite entries emit no card-mod keys at all, including `card-mod-theme`. This is
intentional: choosing a Lite entry does not apply card-mod's optional surface
or typography refinements.

## Outside dashboards

`lovelace-background`, the bundled gradient, only paints Lovelace views.
Settings, Developer Tools, History, Logbook, and Media Browser instead use
Home Assistant's flat `--primary-background-color` (`#F2F2F7` in light mode
and `#1C1C1E` in dark mode).

Glass and Liquid Glass cards remain low-opacity and unblurred on both the
bundled gradients and flat pages. On flat pages they may look subtler because
there is no gradient beneath them, but their rim, directional edge, and shadow
still provide separation. The light-mode rim uses a dark hairline so it
remains visible on light flat pages; the dark-mode rim remains white.

A busy custom wallpaper can reduce legibility. Clear fills preserve backdrop
detail rather than diffusing it, so high-contrast content can remain visible
through a card and compete with its text.

## Known issue: dropdowns

Two closed Home Assistant frontend issues affect dropdown behavior:

- [frontend#20725](https://github.com/home-assistant/frontend/issues/20725): a
  dropdown can render behind a picture-elements card because a card-level
  `--ha-card-backdrop-filter` creates a stacking context.
- [frontend#26113](https://github.com/home-assistant/frontend/issues/26113): a
  dropdown opened inside a more-info dialog can escape the dialog bounds.

The card-level stacking problem applies to full Frosted Glass, which emits
`--ha-card-backdrop-filter`; it does not apply to Glass or Liquid Glass cards,
which emit no card backdrop filter. The second issue is a separate Home
Assistant popup behavior.

Theme YAML cannot independently style an opened menu. Its surface is inside
`ha-dropdown`'s shadow root and the webawesome popup is teleported outside
`hui-root`, beyond card-mod's root scope. The optional
`www/glass-dropdown.js` module supplies the workaround for Glass and Liquid
Glass entries:

- it gives opened menus the Frosted Glass fill, retained as a fallback if Home
  Assistant changes the popup's internal structure;
- it applies a fixed `blur(20px)` only to the popup part inside each dropdown
  shadow root; this is the only blur source for Glass and Liquid Glass;
- that popup-local blur can still create a stacking context local to the
  opened popup; and
- it does not fix frontend#20725 or frontend#26113.

Closed fields remain frosted-tinted but unblurred. The modern field fill comes
from `ha-color-form-background`; legacy fields use the aligned
`input-fill-color` and `mdc-text-field-fill-color` values. Because the modern
token is shared, text inputs, textareas, and time inputs receive the same
legible frosted tint.

Current release archives include the optional dropdown module. To enable it:

1. Copy `www/glass-dropdown.js` to `<config>/www/glass-dropdown.js`.
2. Add it to `configuration.yaml`:
   ```yaml
   frontend:
     extra_module_url:
       - /local/glass-dropdown.js
   ```
3. Restart Home Assistant. If a cached copy remains, perform a hard browser
   refresh.

The workaround is supported on Chromium-based browsers, not Safari. Safari
can lose the injected fill and popup blur after a browser refresh; use normal
dropdown styling or a Lite entry there.

Switching from Frosted Glass to Glass or Liquid Glass removes card-filter
stacking contexts. Switching to a matching Lite entry also chooses a
near-opaque readability surface; because Liquid Glass has no Lite family, use
`Glass Lite` as its fallback. The optional dropdown module does not replace
those choices.

`demo/dashboard.yaml` places a picture-elements card beside an `input_select`
to reproduce the frontend#20725 layout for manual testing.

## Lite entries

Lite exists for readability, weak hardware, and compatibility. Lite entries
emit no native backdrop-filter variables and no card-mod keys. Their card,
dialog, and header surfaces use a deliberately near-opaque `0.72` fill; the
native sidebar uses an even stronger compatibility fill to preserve text,
icon, and selected-accent contrast over arbitrary dashboard content.

For Glass, the defining difference is the near-opaque fill, not backdrop
removal: full Glass is already unblurred. Frosted Glass Lite additionally
removes the full Frosted material's backdrop filter. Both Lite families retain
the rim, directional edge, and ordinary shadow without the continuous
compositing cost of full-surface blur.

Lite entries are therefore not pixel-identical blur toggles. Choose one when
clear backdrop detail hurts readability, a wall tablet struggles with visual
effects, or a backdrop-filter stacking context causes compatibility trouble.

## Refraction compatibility

Current Liquid Glass entries do not define any of the activation variables
used by `glass-refraction.js`:

- `--ha-glass-refraction-backdrop`
- `--ha-glass-refraction-scale`
- `--ha-glass-refraction-edge`

The module therefore stays inactive with current generated themes. Installing
it does **not** upgrade current Liquid Glass.

Release archives retain `www/glass-refraction.js` solely for users of older
generated Liquid Glass YAML that published all three variables. Users
retaining such older YAML can extract the compatibility file to
`<config>/www/glass-refraction.js`, register `/local/glass-refraction.js` under
`frontend.extra_module_url`, and restart Home Assistant. Current themes leave
the packaged module inactive.

True SVG displacement requires a same-document `url(#id)` inside a
`backdrop-filter` chain. That requirement is incompatible with the current
no-filter Liquid Glass contract, so current themes deliberately publish no
refraction activation. The compatibility path targets Chromium; unsupported
engines leave older themes on their original fallback behavior.

## Accessibility

Automated contrast tests cover every one of the fifteen entries against the
three stops in the bundled `lovelace-background` gradient. They require body
text to clear 4.5:1 and secondary, accent, icon, and other large-text uses to
clear 3.0:1. Sidebar and form-field tests additionally composite their fills
over black and white adversarial backdrops.

Disabled controls are not held to the normal text contrast threshold because
WCAG exempts disabled and inactive controls. If your project uses a stricter
internal standard, audit those colors separately.

The tests certify the shipped gradient, not arbitrary wallpaper. A busy,
low-contrast, or high-contrast photo can reduce real-world readability,
especially through low-opacity Glass and Liquid Glass surfaces.

## Custom wallpaper

Override `lovelace-background` from your own theme, layered on top of one of
these entries through your preferred themes merge, or copy an entry into your
own theme file:

```yaml
My Custom Glass:
  lovelace-background: center / cover no-repeat url("/local/my-wallpaper.jpg")
```

Clear materials preserve wallpaper detail. Prefer simple, low-contrast images
and verify text readability on every card location and mode.

## Contributing

`themes/glass.yaml` is generated. Do not hand-edit it: the next generator run
will overwrite those changes.

To change the theme:

1. Edit the token sources under `tokens/`.
2. Regenerate with `python scripts/build_themes.py`.
3. Run the test suite with `python -m pytest`.
4. Include both token changes and the regenerated `themes/glass.yaml` in the
   same change.

`python scripts/build_themes.py --check` verifies generated output without
writing files and fails if `themes/glass.yaml` has drifted from `tokens/`.

## License

MIT — see [LICENSE](LICENSE).
