# Opened Dropdown Refresh Lifecycle Fix Design

## Goal

Keep the opened-dropdown Frosted Glass fill and backdrop blur active after a Home Assistant browser refresh, including when the theme token becomes available after the dropdown module's current startup retries.

## Root Cause

The module activates only when `--ha-glass-dropdown-surface` is present in the computed style of `document.documentElement`. On a browser refresh, the extra module can start before Home Assistant has finished applying theme CSS. The immediate, animation-frame, and 500 ms sync attempts can all run before the token appears.

The theme observer watches only `document.documentElement`'s inline `style` attribute. If the late token arrives through a stylesheet or another frontend lifecycle path, no observed root-style mutation occurs. DOM observers continue discovering nodes but call only `scan()`, which cannot activate the controller. The controller therefore remains inactive for the page lifetime, so both the fill override and blur disappear until Home Assistant restarts or another observed theme mutation occurs.

The current blur rule is also installed in `document.head`. Its `wa-popup::part(popup)` selector cannot cross into an `ha-dropdown` shadow root, so a newly loaded page cannot reliably apply true popup blur. The earlier per-dropdown shadow-root design used the correct CSS scope.

## Design

### Event-Driven Late Activation

Every observed child-list mutation batch will first call `sync()` rather than only scanning added nodes. Home Assistant necessarily creates and upgrades frontend elements while completing a refreshed page, so these existing mutation signals provide bounded, event-driven opportunities to reread the computed theme token without permanent polling or additional fixed delays.

`sync()` will continue to own activation and deactivation. When active, it scans the document, which covers newly added nodes as well as dropdowns that existed before the token appeared. The mutation callback will not separately scan additions after `sync()`, avoiding duplicate traversal. Removal cleanup remains explicit so detached dropdowns regain prior inline values and owned observers are disconnected.

The animation-frame and 500 ms fallback syncs can remain as inexpensive startup fast paths. Correctness will no longer depend on either delay.

### Shadow-Root Blur Ownership

The controller will own at most one blur style per `ha-dropdown`, installed inside that dropdown's open shadow root. The style will target `wa-popup::part(popup)` with the existing 20 px standard and WebKit-prefixed backdrop filters.

Blur ownership will be tracked independently from fill ownership. Repeated syncs will not duplicate styles. Theme deactivation, controller stop, and subtree removal will remove only styles created by this controller. Dropdowns without an open shadow root will retain the fill fallback and can receive blur when later custom-element reconciliation exposes the root.

No global popup stylesheet or prototype patch will be used.

## Data Flow

1. The module starts and immediately reads the activation token.
2. It observes the document, discovered open shadow roots, and root theme-style changes.
3. If the token is initially absent, the controller stays inactive without modifying dropdowns.
4. A later frontend child-list mutation invokes `sync()`.
5. Once the computed token is present, `sync()` activates and scans all known open roots.
6. Each `ha-dropdown` receives the reversible fill variable and, when it has an open shadow root, one owned blur style.
7. Later mutations repeat synchronization, allowing theme deactivation or delayed activation while preserving cleanup semantics.

## Alternatives Rejected

- **More fixed timeouts:** simple but still fails whenever theme propagation exceeds the chosen delay.
- **Permanent interval polling:** reliable eventually, but wastes work for the entire Home Assistant session and complicates shutdown.
- **Global blur CSS:** cannot reliably cross the `ha-dropdown` shadow boundary.

## Testing

JavaScript regression tests will verify:

- startup with an absent token followed by a normal DOM mutation after the token appears activates both fill and blur without an explicit test-only `sync()` call;
- the blur style is installed inside the dropdown shadow root rather than `document.head`;
- repeated sync and mutation batches do not duplicate owned styles;
- theme deactivation removes owned blur and restores fill values;
- removed subtrees release both owned styles and fill overrides;
- dropdowns without open shadow roots retain the fill fallback;
- existing startup, custom-element definition, movement, restart, and third-party ownership tests remain passing.

The complete JavaScript suite, Python suite, generated-theme drift check, YAML lint, and any configured static checks will run before completion.

## Scope

This change is limited to `www/glass-dropdown.js` and its JavaScript tests. It does not alter generated theme tokens, theme YAML, installation configuration, blur strength, closed fields, cards, dialogs, or Home Assistant internals.
