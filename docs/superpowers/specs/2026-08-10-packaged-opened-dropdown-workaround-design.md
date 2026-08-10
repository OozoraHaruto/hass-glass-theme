# Packaged Opened Dropdown Workaround Design

## Goal

Make the existing safe frosted-fill workaround available in every release so users of Glass and Liquid Glass can install it without retrieving a separate source file. This change applies only to opened dropdown menus. Closed fields, cards, dialogs, theme colors, and blur behavior remain unchanged.

## Existing Behavior

Glass and Liquid Glass entries already emit `--ha-glass-dropdown-surface`, using the corresponding Frosted Glass fill. The existing `www/glass-dropdown.js` module applies that value to `--wa-color-surface-raised` on `ha-dropdown` hosts and restores prior behavior when an ineligible theme becomes active.

The release archive currently contains only `themes/glass.yaml`. Consequently, release users do not receive the module that consumes the emitted variable, even though the README instructs them to copy it from the repository.

## Release Packaging

The release workflow will package both files while preserving the repository-relative directories:

- `themes/glass.yaml`
- `www/glass-dropdown.js`

The archive will no longer flatten these files. Preserving `themes/` and `www/` makes each destination explicit and avoids filename ambiguity.

A release validation step will inspect the archive and fail unless both expected paths are present. No Home Assistant configuration file will be generated or modified.

## Installation Contract

The README will direct release-archive users to copy:

- `themes/glass.yaml` into `<config>/themes/`
- `www/glass-dropdown.js` into `<config>/www/`

Users must still register `/local/glass-dropdown.js` under `frontend.extra_module_url`, restart Home Assistant, and hard-refresh stale browser caches when necessary. Home Assistant does not provide a theme package mechanism that can register this module automatically.

The module remains optional. If it is not installed or registered, the YAML themes continue to work, but Glass and Liquid Glass opened menus retain Home Assistant's normal card-derived surface.

## Appearance and Safety

The module continues to apply a heavier translucent Frosted Glass fill without `backdrop-filter`. This avoids introducing a new popup stacking context and does not claim to fix Home Assistant's existing dropdown positioning or layering bugs.

The change does not:

- alter theme-generated surface values;
- alter closed form fields;
- add true popup blur;
- automatically edit `configuration.yaml`;
- change module runtime behavior.

## Testing

Automated validation will verify that the release workflow constructs an archive containing exactly the required theme and module paths. Existing Python and JavaScript tests will continue to validate generated theme values and module behavior.

Repository verification will run:

- the Python test suite;
- the JavaScript module tests;
- generated-theme drift checking;
- YAML linting;
- any release-package validation added with this change.

Manual verification will extract the archive and confirm its paths match the documented Home Assistant destinations.
