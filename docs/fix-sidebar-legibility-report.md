# Sidebar legibility fix — report

## Bug

User report, Glass theme, light mode: "Sidebar in custom dashboard words are
difficult to read" and "Settings icon can barely be seen."

Root cause (confirmed by recomputing, not just trusting the diagnosis):

- `sidebar-background-color` was set to the **card's** glass fill
  (`glassbuild/variables.py:63`, old code) — e.g. `rgba(255, 255, 255, 0.10)`
  in light-mode "Glass" (non-Lite). A card sits on the theme's own gradient;
  the sidebar sits over arbitrary dashboard content, with no blur behind it
  unless card-mod is installed. At 0.10 alpha the dashboard shows straight
  through.
- `sidebar-icon-color` was `palette["text_secondary"]`, a ~60%-alpha grey,
  which is a large-text/icon-tier color, not really meant to anchor legibility
  on its own.

## Fix

1. **`glassbuild/variables.py`** — `sidebar-background-color` is now built
   from `palette["opaque_surface"]`'s RGB, composited at `LITE_FILL_ALPHA`
   (0.72, imported from `glassbuild.materials`) — the same base+alpha the
   Lite entries already use for the same reason (must stay legible with
   nothing behind it). It is **not** `full.fill` with the alpha merely
   raised — verified below that this distinction matters in dark mode.
2. `sidebar-icon-color` is now `palette["text_primary"]`.
   `sidebar-selected-icon-color` / `sidebar-selected-text-color` are
   untouched (still the accent).
3. **`glassbuild/cardmod.py`** — `_SIDEBAR_TEMPLATE`'s `background: {fill}`
   still uses the card's glass fill, unchanged. That code path only ever
   runs alongside a real `backdrop-filter` on the same `:host` (card-mod is
   installed, blur is present), so the translucent fill stays legible there.
   The module docstring now explains why the two intentionally differ, so a
   future reader doesn't "fix" the discrepancy back into a bug.
4. **`tests/test_contrast.py`** — added 4 parametrized tests × 12
   `ENTRY_NAMES` = 48 new cases, covering `sidebar-text-color` (≥4.5:1),
   `sidebar-icon-color` (≥3.0:1), `sidebar-selected-text-color` (≥3.0:1),
   `sidebar-selected-icon-color` (≥3.0:1) — all measured on the sidebar fill
   composited over `primary-background-color` (not the Lovelace gradient,
   since the sidebar sits outside Lovelace views), using the file's existing
   `_entry_payload` partial-overlay helper.

## Measured contrast, before → after (light / dark)

All entries collapsed to the same per-mode number after the fix, because
`sidebar-background-color`'s base color now equals `primary-background-color`
exactly in every entry (previously it varied by material/weight). Before
numbers below are for the material/mode combination the original diagnosis
cited (non-Lite "Glass"); Lite entries were already close to the fixed values
because Lite's card fill already happened to use the opaque-surface base.

| Metric | Mode | Before | After | Threshold |
|---|---|---|---|---|
| sidebar text | light | 15.38:1 | 15.25:1 | 4.5:1 |
| sidebar text | dark | 15.30:1 | 17.01:1 | 4.5:1 |
| sidebar icon | light | 3.32:1 (best case — see caveat) | 15.25:1 | 3.0:1 |
| sidebar icon | dark | 5.61:1 (best case — see caveat) | 17.01:1 | 3.0:1 |
| selected text/icon (accent) | light | 3.63:1 | 3.60:1 | 3.0:1 |
| selected text/icon (accent) | dark | 4.19:1 | 4.66:1 | 3.0:1 |

**Important caveat on the "before" icon numbers**: those are measured against
`primary-background-color` (the backdrop the new tests use, per the sidebar's
own real fallback surface). The bug report's ~1.1–1.8:1 figures for the old
code were measured against **darker arbitrary dashboard content**, which
`primary-background-color` does not reproduce (see "Mutation-test finding"
below for why this matters).

### CRITICAL check requested: does raising the *existing* white fill's alpha work instead?

No — verified directly, dark mode, `white @ 0.72` alpha vs. the actual fix
(`opaque_surface @ 0.72`):

```
white@0.72 dark surface:  (191, 191, 192, 1.0)  accent contrast: 1.99
opaque@0.72 dark surface: (28, 28, 30, 1.0)     accent contrast: 4.66
```

(My measured number for the white-based approach is 1.99:1, not the 2.46:1
cited in the diagnosis — likely a different backdrop assumption on their
end — but the conclusion is the same and, if anything, worse than claimed:
simply raising the alpha on the existing white fill fails the 3:1 floor
badly in dark mode. Using `opaque_surface` as the base avoids this
entirely.)

## `icon-primary-color` / `state-icon-color`

Measured on the **card** surface over all three gradient stops, both modes,
all entries (both currently map to `palette["text_secondary"]`, untouched by
this fix):

```
icon-primary-color  dark:  worst 4.79:1 (Frosted Glass, stop (27,22,32))
icon-primary-color light:  worst 3.24:1 (Glass, stop (230,236,246))
state-icon-color    dark:  worst 4.79:1 (Frosted Glass, stop (27,22,32))
state-icon-color   light:  worst 3.24:1 (Glass, stop (230,236,246))
```

Both clear the 3.0:1 floor for non-text content in both modes, with the
tightest margin (3.24:1) in light mode "Glass". **Not changed** — per
instructions, thresholds pass, so no fix was made here.

## Mutation-test finding (read before trusting the new tests blindly)

Per instructions, I reverted each fix individually (fill fixed / icon
reverted, then icon fixed / fill reverted), re-ran the new sidebar tests, and
restored. **Neither mutation caused the new tests to fail.** This is a real,
reproducible finding, not an oversight — reported per "code wins, tell me
rather than writing something false":

```
$ .venv/bin/python -m pytest tests/test_contrast.py -q -k "sidebar_icon"
# with sidebar-icon-color reverted to text_secondary (fill fix in place):
............                                                             [100%]
12 passed, 64 deselected in 0.03s

$ .venv/bin/python -m pytest tests/test_contrast.py -q -k "sidebar"
# with sidebar-background-color reverted to full.fill (icon fix in place):
................................................                         [100%]
48 passed, 28 deselected in 0.04s
```

**Why**: `primary-background-color` is always `palette["opaque_surface"]`
(`variables.py:43`). After the PART 1 fix, `sidebar-background-color`'s base
color is *also* `palette["opaque_surface"]` — the same RGB. Compositing a
color onto a background of the identical RGB produces that same RGB
regardless of the foreground's alpha (`(f·fa + b·ba·(1−fa))/out_a = f` when
`f == b`). So once the fix is in place, the sidebar-over-`primary-background-
color` test surface is mathematically just `opaque_surface` itself,
independent of the 0.72 alpha choice — and `text_secondary` already clears
3:1 against plain `opaque_surface` in both modes (measured: 3.29:1 light,
5.94:1 dark), so reverting the icon color alone can't drop it below the
floor on *this* backdrop. Reverting the fill alone doesn't fail either,
because `text_primary` (kept from the icon fix) has enormous margin
(11.7–17:1) against any surface built from either fill.

This means the four new tests, as specified (backdrop =
`primary-background-color`), cannot detect *this specific* regression shape
with today's palette values — they are not vacuous in general (a
sufficiently bad color, e.g. `text_disabled`, does fail: measured 2.0:1 in
light mode, below 3.0), but they don't catch reverting to `text_secondary`
specifically, nor reverting the fill to the card's glass alpha, because
`primary-background-color` is a moderate-luminance, mode-appropriate
backdrop, not the dark/arbitrary dashboard content the original bug report
was actually about. I implemented exactly what was specified (the
instructions were explicit that the backdrop must be
`primary-background-color`, not the gradient), and the tests are still a
legitimate regression floor for grosser mistakes — but per the instruction
to report honestly rather than fabricate a passing mutation-test, this is
the actual result, not the expected one.

## Test run (final state, both fixes applied)

```
$ .venv/bin/python -m pytest -q
........................................................................ [ 31%]
........................................................................ [ 63%]
........................................................................ [ 94%]
............                                                             [100%]
228 passed in 1.04s
```

(180 pre-existing + 48 new sidebar tests, all passing. Key counts in
`tests/test_variables.py` — `EXPECTED_FULL_KEY_COUNT` / `EXPECTED_LITE_KEY_COUNT`
— are unchanged, since no keys were added or removed, only two values
changed.)

```
$ .venv/bin/python scripts/build_themes.py --check
/Volumes/Documents/code/hass-glass-theme/themes/glass.yaml is up to date (12 entries)
```

```
$ .venv/bin/python -m yamllint -c .yamllint.yml themes/glass.yaml tokens/base.yaml \
    tokens/glass.yaml tokens/frosted-glass.yaml tokens/modes/light.yaml \
    tokens/modes/dark.yaml demo/dashboard.yaml
(no output — clean)
```

## Files changed

- `glassbuild/variables.py` — `sidebar-background-color` now built from
  `palette["opaque_surface"]` at `LITE_FILL_ALPHA`; `sidebar-icon-color` now
  `palette["text_primary"]`.
- `glassbuild/cardmod.py` — docstring updated to explain why
  `card-mod-sidebar-yaml`'s glass fill deliberately differs from the native
  `sidebar-background-color` fallback.
- `tests/test_contrast.py` — 4 new parametrized test functions (48 cases)
  covering sidebar text/icon/selected-text/selected-icon contrast.
- `themes/glass.yaml` — regenerated via `scripts/build_themes.py` (never
  hand-edited).
