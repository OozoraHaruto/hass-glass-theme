# Opened Dropdown Startup Ordering Fix Design

## Goal

Ensure the existing `glass-dropdown.js` workaround applies its Frosted Glass surface to `ha-dropdown` elements that already exist inside open shadow roots when the module starts.

## Root Cause

The controller starts with `active` set to false. `start()` observes and scans the document before `sync()` reads `--ha-glass-dropdown-surface`. Existing shadow roots are therefore scanned while inactive, so their dropdowns are not changed.

After activation, `sync()` scans the document again, but `observeRoot()` returns immediately for every shadow root registered during the first scan. Existing dropdowns below those roots are never revisited. Dropdowns inserted later work because their scan occurs after activation.

## Fix

`start()` will read the activation token before calling `observeRoot(document)`. The initial document and shadow-root traversal will therefore run with the correct active state and apply the existing host override immediately.

The theme observer will still be installed during startup, and later `sync()` calls will retain their current responsibility for theme changes. Dynamic insertion, cleanup, restart, custom-element reconciliation, and third-party inline-value ownership remain unchanged.

The implementation will not add repeated rescanning of all observed roots. Correct startup ordering removes the missed initial state without adding ongoing traversal cost.

## Testing

Add a regression test that constructs an open shadow root containing an `ha-dropdown` before controller startup. With the current implementation, the target inline property remains empty. After the fix, it equals `var(--ha-glass-dropdown-surface)` immediately after `start()`.

Run the complete JavaScript suite where Node is available, plus the existing Python tests, generated-theme drift check, and YAML lint. Manual verification will load the module in Home Assistant with Glass or Liquid Glass active, confirm the target property appears on existing shadow-root dropdown hosts, and confirm the opened menu uses the heavier Frosted Glass fill.

## Non-Goals

- No true popup backdrop blur.
- No changes to theme tokens or generated YAML.
- No changes to closed fields, cards, dialogs, or module installation.
- No changes to Home Assistant or WebAwesome internals.
