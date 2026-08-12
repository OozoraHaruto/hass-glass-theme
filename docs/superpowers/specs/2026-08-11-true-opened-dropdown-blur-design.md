# True Opened Dropdown Blur Design

## Goal

Give opened dropdown menus genuine Frosted Glass blur when a Glass or Liquid Glass theme is active. The popup uses a fixed `blur(40px)` effect while retaining the existing heavier translucent fill as a compatibility fallback.

## Technical Constraint

The current module can change the opened menu color through `--wa-color-surface-raised` because WebAwesome consumes that property. Home Assistant exposes no equivalent theme or WebAwesome custom property for popup `backdrop-filter`, so assigning another host variable alone cannot create blur.

The blur declaration must be added inside each `ha-dropdown` open shadow root, where a scoped rule can target `wa-popup::part(popup)`. Body-level CSS cannot cross the shadow boundary. Global prototype patching is rejected because it is more fragile and affects unrelated components.

## Module Behavior

When `--ha-glass-dropdown-surface` activates the module, each eligible `ha-dropdown` continues to receive the existing reversible inline `--wa-color-surface-raised` override.

The module also installs one owned style element in that dropdown's shadow root. Its rule targets only the popup part:

```css
wa-popup::part(popup) {
  -webkit-backdrop-filter: blur(40px);
  backdrop-filter: blur(40px);
}
```

The style is idempotent: repeated scans must neither duplicate it nor replace unrelated styles. The module tracks only styles it creates.

If the expected `wa-popup` structure or part is unavailable in a Home Assistant version, the rule is inert and the current heavier fill remains visible. The module does not treat unsupported blur as an error.

## Lifecycle and Ownership

On an ineligible theme, module stop, or removal of an owned dropdown subtree, the module removes only its own style element and restores only its own fill override. It must not remove or rewrite third-party shadow-root styles.

Existing startup ordering, dynamic insertion, open-shadow-root observation, delayed custom-element definition handling, restart behavior, and third-party inline-variable ownership remain intact.

If a dropdown initially lacks a shadow root, existing custom-element reconciliation will revisit it after definition. The blur style is installed when an open shadow root becomes available.

## Compatibility and Risk

Applying `backdrop-filter` creates a stacking context and may trigger or worsen Home Assistant's documented dropdown layering and positioning bugs. This behavior is explicitly accepted for Glass and Liquid Glass opened menus. The matching Lite themes remain the compatibility remedy where blur causes unclickable or misplaced popups.

Both standard and WebKit-prefixed declarations are emitted for browser compatibility.

## Testing

JavaScript tests will verify:

- active startup adds the fill override and exactly one owned blur style;
- repeated scans remain idempotent;
- dynamically inserted dropdowns receive blur;
- dropdowns whose shadow roots appear after custom-element definition receive blur;
- theme deactivation and `stop()` remove owned blur styles;
- removed subtrees release owned styles;
- unrelated shadow-root styles remain untouched;
- fill fallback behavior remains unchanged.

The fake DOM will model shadow-root style insertion, lookup, and removal without adding dependencies. Existing Python, generated-theme, YAML, and packaging tests remain unchanged.

## Documentation

The README will replace the current fill-only claim with an explicit description of the fixed 40px popup blur, retained fill fallback, internal-selector compatibility limitation, and stacking/positioning risks. Installation remains unchanged.

## Non-Goals

- No changes to closed fields, cards, dialogs, or generated theme values.
- No automatic Home Assistant configuration changes.
- No blur for Frosted Glass entries, which do not activate this module.
- No attempt to fix upstream popup stacking or positioning bugs.
