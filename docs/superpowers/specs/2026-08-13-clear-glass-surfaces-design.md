# Clear Glass Surface Design

## Goal

Make Glass and Liquid Glass clear, low-opacity materials without backdrop blur on cards or other general Home Assistant surfaces. Preserve blur only for opened dropdown menus through the optional `glass-dropdown.js` module.

Keep Glass Lite as the no-blur, near-opaque readability and compatibility variant. Leave Frosted Glass and Frosted Glass Lite behavior unchanged.

## Material Semantics

The theme families will have distinct purposes:

- **Glass:** low-opacity fill, bright rim and specular edge, no backdrop blur.
- **Liquid Glass:** lower-opacity fill, stronger rim and specular edge, no backdrop blur or SVG refraction.
- **Glass Lite:** near-opaque fill, no backdrop blur; intended for readability, weak hardware, and compatibility.
- **Frosted Glass:** high-opacity diffuse fill with backdrop blur.
- **Frosted Glass Lite:** near-opaque fallback without backdrop blur.

Liquid Glass keeps its current visual distinction from Glass through its lower body alpha, hotter rim, and larger specular edge. Its optional SVG refraction cannot remain enabled because refraction is implemented through `backdrop-filter`, which would violate the no-blur/no-filter surface requirement.

## Theme Generation

Backdrop generation will become material-aware rather than treating every non-Lite material alike.

For Glass and Liquid Glass, generated entries will retain their current low-opacity fills, borders, shadows, geometry, colors, and background gradient, but will emit none of the seven native Home Assistant backdrop-filter variables:

- `ha-card-backdrop-filter`
- `ha-dialog-surface-backdrop-filter`
- `app-header-backdrop-filter`
- `ha-bottom-sheet-surface-backdrop-filter`
- `ha-dialog-scrim-backdrop-filter`
- `dialog-backdrop-filter`
- `ha-bottom-sheet-scrim-backdrop-filter`

Their card-mod sidebar CSS will also omit `backdrop-filter` and `-webkit-backdrop-filter`. No general surface under these themes will receive blur.

Liquid Glass entries will stop emitting the refraction backdrop and activation variables, and `glass-refraction.js` will therefore remain inactive. The module may stay packaged for compatibility with older generated themes, but current Liquid Glass entries will not activate it.

Glass Lite remains unchanged: it emits no backdrop filters and uses its existing near-opaque surface fill. Frosted Glass continues to emit its full 40px surface backdrop chain and half-strength scrim chain. Frosted Glass Lite remains its no-blur near-opaque counterpart.

## Dropdown Behavior

Glass and Liquid Glass entries will continue to publish `ha-glass-dropdown-surface`. The optional `glass-dropdown.js` module will remain the sole source of blur for these themes.

When enabled, the module will continue to:

- apply the Frosted Glass fill to opened dropdown menus;
- inject its fixed 20px `backdrop-filter` into each eligible `ha-dropdown` shadow root;
- clean up its fill and blur when an ineligible theme becomes active;
- leave closed dropdown fields without backdrop blur.

This exception is scoped to opened dropdown popups and does not restore blur to cards, dialogs, headers, sidebars, sheets, or scrims.

## Documentation

The README will stop describing Glass and Liquid Glass as natively blurred materials. It will state clearly that:

- Glass and Liquid Glass use low-opacity fills, rims, and specular edges without general surface blur;
- the optional dropdown module is the only blur source for those themes;
- Glass Lite is intentionally more opaque for readability, low-powered hardware, and compatibility rather than merely being a duplicate no-blur edition;
- Frosted Glass is the material to select when diffuse backdrop blur is desired;
- Liquid Glass no longer activates SVG refraction because that effect requires `backdrop-filter`;
- existing Home Assistant dropdown stacking issues caused by card backdrop filters do not apply to Glass or Liquid Glass cards after this change, while the optional opened-dropdown blur can still create a popup-local stacking context.

Installation, theme names, and the number of picker entries remain unchanged.

## Testing

Tests will verify that:

- every Glass and Liquid Glass entry omits all native backdrop-filter variables;
- Glass and Liquid Glass retain their current low-opacity card fills;
- Glass and Liquid Glass card-mod output contains no backdrop-filter declaration;
- current Liquid Glass entries omit refraction activation variables;
- Glass Lite retains its near-opaque fills and emits no backdrop-filter variables;
- Frosted Glass retains its existing fill and backdrop chains;
- Frosted Glass Lite remains unblurred;
- Glass and Liquid Glass still publish the dropdown activation surface;
- the dropdown JavaScript suite continues to prove popup-local blur, lifecycle cleanup, and theme gating;
- generated YAML has no drift and remains valid.

Manual verification will compare Glass, Liquid Glass, Glass Lite, and Frosted Glass on the demo dashboard, confirm that only opened dropdown menus blur under Glass and Liquid Glass, and confirm that cards remain translucent but unblurred.

## Scope

This change does not rename or remove themes, add Liquid Glass Lite variants, alter Frosted Glass behavior, change dropdown blur strength, or add blur to closed form fields. It does not attempt to reproduce true optical refraction without `backdrop-filter`.
