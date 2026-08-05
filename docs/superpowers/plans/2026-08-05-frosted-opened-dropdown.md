# Frosted Opened Dropdown Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give opened `ha-dropdown` menus in Glass and Liquid Glass the Frosted Glass fill without changing cards, closed fields, or Home Assistant internals.

**Architecture:** The Python theme builder publishes a material-gated `ha-glass-dropdown-surface` variable containing the mode's Frosted Glass fill. An optional dependency-free browser ES module detects that variable, observes Home Assistant's dynamic document/open-shadow-root tree, and places a reversible inline `--wa-color-surface-raised: var(--ha-glass-dropdown-surface)` override on `ha-dropdown` hosts.

**Tech Stack:** Python 3.11+, PyYAML, pytest, browser JavaScript ES modules, Node.js built-in test runner, Home Assistant theme custom properties.

## Global Constraints

- Apply only to the opened options menu; closed dropdown fields, cards, dialogs, and other surfaces remain unchanged.
- Glass and Liquid Glass use the corresponding light/dark Frosted Glass fill.
- Do not apply `backdrop-filter`, add a stacking context, patch Home Assistant/WebAwesome prototypes, or inject CSS into component shadow roots.
- Activation is token-based through `--ha-glass-dropdown-surface`; never match Home Assistant theme display names in JavaScript.
- The module is optional and Home Assistant must retain its existing behavior when the module or token is absent.
- Theme changes must remove only module-owned overrides and must preserve values replaced by other code.
- Add no runtime JavaScript dependencies.

---

## File Structure

- Modify `glassbuild/variables.py`: derive and conditionally publish the opened-menu surface token.
- Modify `tests/test_variables.py`: unit-test the material gate and exact Frosted Glass fill.
- Modify `tests/test_emit.py`: test all generated theme entries and auto-mode behavior.
- Create `www/glass-dropdown.js`: optional Home Assistant module, DOM traversal, observation, and reversible override ownership.
- Create `tests/js/glass-dropdown.test.js`: browser-DOM test doubles and behavioral tests for the module.
- Create `package.json`: declare ESM and expose the dependency-free Node test command.
- Modify `.github/workflows/ci.yml`: run JavaScript module tests in CI.
- Modify `README.md`: installation, scope, safety, and known-limit documentation.
- Regenerate `themes/glass.yaml`: publish the new generated variable.

### Task 1: Publish the material-gated dropdown surface token

**Files:**
- Modify: `glassbuild/variables.py:61-75,180-228`
- Modify: `tests/test_variables.py:287-323`
- Test: `tests/test_variables.py`

**Interfaces:**
- Consumes: merged token keys `material.name`, `material.fill_rgb`, and `material.fill_alpha_frosted`.
- Produces: optional theme key `ha-glass-dropdown-surface: str` for materials named `Glass` and `Liquid Glass`.

- [ ] **Step 1: Write failing unit tests for exact value and material gating**

Add tests that build real material/mode combinations rather than extending the hand-built `_vars()` fixture:

```python
@pytest.mark.parametrize("material", ["glass", "liquid-glass"])
@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("lite", [False, True])
def test_glass_materials_publish_the_frosted_dropdown_surface(material, mode, lite):
    tokens = load_tokens(ROOT)
    merged = merge(tokens["base"], tokens["materials"][material], tokens["modes"][mode])
    variables = build_variables(merged, derive(merged, material, lite=lite))
    r, g, b = merged["material"]["fill_rgb"]
    expected = rgba_str(r, g, b, merged["material"]["fill_alpha_frosted"])
    assert variables["ha-glass-dropdown-surface"] == expected


@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("lite", [False, True])
def test_frosted_glass_does_not_publish_a_dropdown_override(mode, lite):
    tokens = load_tokens(ROOT)
    merged = merge(
        tokens["base"], tokens["materials"]["frosted-glass"], tokens["modes"][mode]
    )
    variables = build_variables(merged, derive(merged, "frosted-glass", lite=lite))
    assert "ha-glass-dropdown-surface" not in variables
```

Import `rgba_str` from `glassbuild.color`. Keep the Liquid Glass `lite=True` unit case because `build_variables` supports it even though the emitted entry matrix intentionally does not.

- [ ] **Step 2: Run the focused tests and confirm the missing-token failure**

Run:

```bash
python -m pytest tests/test_variables.py -k dropdown_surface -v
```

Expected: Glass and Liquid Glass cases fail with `KeyError: 'ha-glass-dropdown-surface'`; Frosted Glass cases pass.

- [ ] **Step 3: Implement the smallest conditional token emission**

In `build_variables`, derive the Frosted Glass fill independently of the active material's normal fill:

```python
    frosted_dropdown_fill = rgba_str(
        fill_rgb[0],
        fill_rgb[1],
        fill_rgb[2],
        merged["material"]["fill_alpha_frosted"],
    )
```

After the base `variables` dictionary is built, publish the token only for the two eligible material token names:

```python
    if merged["material"]["name"] in {"Glass", "Liquid Glass"}:
        variables["ha-glass-dropdown-surface"] = frosted_dropdown_fill
```

Do not alter `card-background-color`, `ha-color-form-background`, or any backdrop-filter variable.

- [ ] **Step 4: Update variable-count assertions without weakening them**

Add:

```python
EXPECTED_DROPDOWN_SURFACE_KEY_COUNT = 1
```

Then include that count only when `merged["material"]["name"]` is `Glass` or `Liquid Glass`, alongside the existing full/lite and refraction counts. Add this invariant inside the real-token loop:

```python
eligible = merged["material"]["name"] in {"Glass", "Liquid Glass"}
assert ("ha-glass-dropdown-surface" in v) == eligible
```

- [ ] **Step 5: Run the complete variable test file**

Run:

```bash
python -m pytest tests/test_variables.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit the builder unit**

Only if commit authorization has been given:

```bash
git add glassbuild/variables.py tests/test_variables.py
git commit -m "feat: publish frosted dropdown surface token"
```

### Task 2: Guard the generated theme matrix behavior

**Files:**
- Modify: `tests/test_emit.py:150-207`
- Test: `tests/test_emit.py`

**Interfaces:**
- Consumes: `ha-glass-dropdown-surface` from Task 1 through `build_themes(ROOT)`.
- Produces: matrix-level guarantees for flat and Auto entries.

- [ ] **Step 1: Add helpers that resolve Auto entries the same way Home Assistant does**

Add:

```python
def _applied_mode(entry: dict, mode: str) -> dict:
    base = {key: value for key, value in entry.items() if key != "modes"}
    return {**base, **entry.get("modes", {}).get(mode, {})}
```

- [ ] **Step 2: Add failing matrix tests for eligible and ineligible entries**

Add:

```python
@pytest.mark.parametrize("prefix", ["Glass", "Liquid Glass"])
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_glass_entries_publish_frosted_opened_dropdown_surface(themes, prefix, mode):
    entry = themes[prefix]
    applied = _applied_mode(entry, mode)
    frosted = _applied_mode(themes["Frosted Glass"], mode)
    assert applied["ha-glass-dropdown-surface"] == frosted["card-background-color"]


@pytest.mark.parametrize(
    "name",
    [
        "Frosted Glass",
        "Frosted Glass Light",
        "Frosted Glass Dark",
        "Frosted Glass Lite",
        "Frosted Glass Light Lite",
        "Frosted Glass Dark Lite",
    ],
)
def test_frosted_entries_need_no_opened_dropdown_override(themes, name):
    assert all(
        key != "ha-glass-dropdown-surface"
        for key, _value in _flatten_entry(themes[name])
    )
```

Also add a Glass Lite assertion that compares each mode to the full Frosted Glass fill, not Frosted Glass Lite's opaque fallback:

```python
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_glass_lite_dropdown_still_uses_the_frosted_fill(themes, mode):
    glass_lite = _applied_mode(themes["Glass Lite"], mode)
    frosted = _applied_mode(themes["Frosted Glass"], mode)
    assert glass_lite["ha-glass-dropdown-surface"] == frosted["card-background-color"]
```

- [ ] **Step 3: Run focused emit tests**

Run:

```bash
python -m pytest tests/test_emit.py -k "dropdown or auto_entries_match" -v
```

Expected: pass after Task 1; failures indicate incorrect gating, value derivation, or Auto hoisting.

- [ ] **Step 4: Run the entire emit test file**

Run:

```bash
python -m pytest tests/test_emit.py -v
```

Expected: all tests pass, including exact Auto-versus-flat equivalence.

- [ ] **Step 5: Commit the matrix guard**

Only if commit authorization has been given:

```bash
git add tests/test_emit.py
git commit -m "test: guard opened dropdown theme matrix"
```

### Task 3: Build the optional reversible Home Assistant module

**Files:**
- Create: `www/glass-dropdown.js`
- Create: `tests/js/glass-dropdown.test.js`
- Create: `package.json`

**Interfaces:**
- Consumes: computed root variable `--ha-glass-dropdown-surface` and `ha-dropdown` host elements.
- Produces: `createDropdownSurfaceController(environment)` with `start()`, `sync()`, and `stop()` methods; browser auto-start; reversible inline host variable `--wa-color-surface-raised`.

- [ ] **Step 1: Add zero-dependency JavaScript test configuration**

Create `package.json`:

```json
{
  "private": true,
  "type": "module",
  "scripts": {
    "test:js": "node --test tests/js/*.test.js"
  }
}
```

No lockfile is needed because there are no npm dependencies and no install command is required.

- [ ] **Step 2: Write the controller behavioral tests first**

Create test doubles in `tests/js/glass-dropdown.test.js` for:

```js
import assert from "node:assert/strict";
import test from "node:test";
import { createDropdownSurfaceController } from "../../www/glass-dropdown.js";
```

The fake environment must provide `document.documentElement`, a tree whose nodes expose `localName`, `children`, `shadowRoot`, and a CSS-style declaration object implementing `getPropertyValue`, `getPropertyPriority`, `setProperty`, and `removeProperty`. Its fake `MutationObserver` stores callbacks and exposes a test-only `emit(records)` method.

Cover these exact behaviors:

```js
test("applies the variable reference to an existing dropdown", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  assert.equal(
    dropdown.style.getPropertyValue("--wa-color-surface-raised"),
    "var(--ha-glass-dropdown-surface)",
  );
});


test("applies to dropdowns inserted later and inside open shadow roots", () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const controller = createDropdownSurfaceController(env);
  controller.start();
  const host = env.element("ha-dialog");
  host.shadowRoot = env.root();
  const dropdown = env.element("ha-dropdown");
  host.shadowRoot.append(dropdown);
  env.document.append(host);
  env.emitDocumentAddition(host);
  assert.equal(
    dropdown.style.getPropertyValue("--wa-color-surface-raised"),
    "var(--ha-glass-dropdown-surface)",
  );
});


test("removes its override when the activation token disappears", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.setSource("");
  controller.sync();
  assert.equal(dropdown.style.getPropertyValue("--wa-color-surface-raised"), "");
});


test("restores a prior inline value when its own override is still installed", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  dropdown.style.setProperty("--wa-color-surface-raised", "pink", "important");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.setSource("");
  controller.sync();
  assert.equal(dropdown.style.getPropertyValue("--wa-color-surface-raised"), "pink");
  assert.equal(dropdown.style.getPropertyPriority("--wa-color-surface-raised"), "important");
});


test("does not erase a value another script writes after activation", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  dropdown.style.setProperty("--wa-color-surface-raised", "orange");
  env.setSource("");
  controller.sync();
  assert.equal(dropdown.style.getPropertyValue("--wa-color-surface-raised"), "orange");
});
```

Add tests proving repeated `sync()` is idempotent, `stop()` disconnects every observer and cleans owned values, and no value is applied while the activation token is absent.

- [ ] **Step 3: Run JavaScript tests and confirm the missing-module failure**

Run:

```bash
node --test tests/js/glass-dropdown.test.js
```

Expected: fail because `www/glass-dropdown.js` does not exist.

- [ ] **Step 4: Implement the dependency-injected controller**

Create `www/glass-dropdown.js` with these constants and API:

```js
const SOURCE_VARIABLE = "--ha-glass-dropdown-surface";
const TARGET_VARIABLE = "--wa-color-surface-raised";
const OVERRIDE_VALUE = `var(${SOURCE_VARIABLE})`;

export const createDropdownSurfaceController = ({
  document,
  getComputedStyle,
  MutationObserver,
}) => {
  const changed = new Map();
  const observedRoots = new Map();
  let themeObserver;
  let active = false;
```

Implement ownership as a `Map<Element, { value: string, priority: string }>`:

```js
  const apply = (dropdown) => {
    if (!changed.has(dropdown)) {
      changed.set(dropdown, {
        value: dropdown.style.getPropertyValue(TARGET_VARIABLE),
        priority: dropdown.style.getPropertyPriority(TARGET_VARIABLE),
      });
    }
    dropdown.style.setProperty(TARGET_VARIABLE, OVERRIDE_VALUE);
  };

  const restore = (dropdown, previous) => {
    if (dropdown.style.getPropertyValue(TARGET_VARIABLE) !== OVERRIDE_VALUE) return;
    if (previous.value === "") {
      dropdown.style.removeProperty(TARGET_VARIABLE);
    } else {
      dropdown.style.setProperty(TARGET_VARIABLE, previous.value, previous.priority);
    }
  };

  const clear = () => {
    for (const [dropdown, previous] of changed) restore(dropdown, previous);
    changed.clear();
  };
```

Implement recursive light-DOM/open-shadow-root discovery without reading private dropdown internals:

```js
  const scan = (node) => {
    if (node.localName === "ha-dropdown" && active) apply(node);
    if (node.shadowRoot) observeRoot(node.shadowRoot);
    for (const child of node.children ?? []) scan(child);
  };

  const observeRoot = (root) => {
    if (observedRoots.has(root)) return;
    const observer = new MutationObserver((records) => {
      for (const record of records) {
        for (const node of record.addedNodes) scan(node);
      }
    });
    observer.observe(root, { childList: true, subtree: true });
    observedRoots.set(root, observer);
    scan(root);
  };
```

Resolve the source token only to decide activation; keep the applied value as a CSS `var()` reference so Auto light/dark changes cannot leave a copied stale color:

```js
  const sync = () => {
    active = getComputedStyle(document.documentElement)
      .getPropertyValue(SOURCE_VARIABLE)
      .trim() !== "";
    if (active) scan(document);
    else clear();
  };
```

`start()` observes the document, synchronizes immediately, and watches only the root `style` attribute. `stop()` disconnects the theme observer and all root observers, clears the maps, and restores owned values. Make both methods idempotent.

Auto-start only in a real browser:

```js
if (typeof document !== "undefined") {
  const start = () =>
    createDropdownSurfaceController({ document, getComputedStyle, MutationObserver }).start();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
}
```

- [ ] **Step 5: Run JavaScript behavioral tests**

Run:

```bash
npm run test:js
```

Expected: all tests pass with no package installation.

- [ ] **Step 6: Commit the optional module**

Only if commit authorization has been given:

```bash
git add package.json www/glass-dropdown.js tests/js/glass-dropdown.test.js
git commit -m "feat: frost opened dropdown menus"
```

### Task 4: Run module tests in CI

**Files:**
- Modify: `.github/workflows/ci.yml:37-49`
- Test: `.github/workflows/ci.yml`, `tests/js/glass-dropdown.test.js`

**Interfaces:**
- Consumes: `npm run test:js` from Task 3.
- Produces: CI coverage on the repository's supported Node runtime.

- [ ] **Step 1: Add a JavaScript test job**

Add a separate job so Python's version matrix remains unchanged:

```yaml
  test-js:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262  # v4
      - uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020  # v4
        with:
          node-version: "22"
      - run: npm run test:js
```

Before implementation, confirm the pinned `actions/setup-node` SHA is already trusted by repository policy or replace it with the current reviewed v4 SHA; do not use an unpinned action tag.

- [ ] **Step 2: Run local JavaScript tests and YAML lint**

Run:

```bash
npm run test:js
python -m yamllint .github/workflows/ci.yml
```

Expected: both commands pass.

- [ ] **Step 3: Commit CI coverage**

Only if commit authorization has been given:

```bash
git add .github/workflows/ci.yml
git commit -m "ci: test dropdown companion module"
```

### Task 5: Regenerate the theme and document installation

**Files:**
- Modify: `README.md:127-164,200-220,280-299`
- Modify generated: `themes/glass.yaml`
- Test: `tests/test_build_cli.py`, complete test suite

**Interfaces:**
- Consumes: token emission from Task 1 and module filename from Task 3.
- Produces: distributable generated YAML and user-facing installation instructions.

- [ ] **Step 1: Regenerate the committed theme**

Run:

```bash
python scripts/build_themes.py
```

Expected: `themes/glass.yaml` is rewritten with `ha-glass-dropdown-surface` under Glass and Liquid Glass mode payloads/flat entries, and nowhere under Frosted Glass.

- [ ] **Step 2: Add focused generated-file assertions**

Extend `tests/test_build_cli.py` with:

```python
def test_committed_file_scopes_the_opened_dropdown_surface():
    document = yaml.safe_load((ROOT / "themes" / "glass.yaml").read_text(encoding="utf-8"))
    assert "ha-glass-dropdown-surface" in document["Glass Light"]
    assert "ha-glass-dropdown-surface" in document["Liquid Glass Dark"]
    assert "ha-glass-dropdown-surface" not in document["Frosted Glass Light"]
```

- [ ] **Step 3: Update dropdown documentation accurately**

Revise the known-issue section so it no longer says the opened menu cannot be changed at all. State precisely:

- Theme YAML alone cannot independently override the opened menu.
- `www/glass-dropdown.js` is an optional host-level workaround for Glass and Liquid Glass.
- It changes fill only, adds no blur/filter, and does not fix Home Assistant issues `frontend#20725` or `frontend#26113`.
- Frosted Glass already uses the desired fill and needs no override.

Add installation commands alongside the refraction module instructions:

```yaml
frontend:
  extra_module_url:
    - /local/glass-dropdown.js
```

Document copying `www/glass-dropdown.js` to `<config>/www/glass-dropdown.js`, restarting Home Assistant, and performing a hard browser refresh if the old cached module remains.

- [ ] **Step 4: Run generated-file drift and focused tests**

Run:

```bash
python scripts/build_themes.py --check
python -m pytest tests/test_emit.py tests/test_variables.py tests/test_build_cli.py -v
npm run test:js
```

Expected: all pass; drift reports all 15 entries up to date.

- [ ] **Step 5: Run repository lint, type-adjacent checks, and full tests**

Run:

```bash
python -m yamllint tokens/ themes/ demo/ .github/
python -m pytest -v
npm run test:js
```

Expected: all commands pass. This repository has no configured Python static type checker or JavaScript type checker; do not invent one during this focused change.

- [ ] **Step 6: Manually verify in Home Assistant**

Copy the module, register it under `frontend.extra_module_url`, restart Home Assistant, and use `demo/dashboard.yaml` to verify:

1. Glass Light/Dark and Liquid Glass Light/Dark opened menus use the Frosted Glass fill.
2. Closed fields and cards retain their prior appearance.
3. Frosted Glass remains unchanged.
4. Switching to a third-party theme removes the override.
5. Dropdown positioning, item clicking, and the documented picture-elements stacking reproduction are no worse than before.

- [ ] **Step 7: Commit generated output and documentation**

Only if commit authorization has been given:

```bash
git add README.md themes/glass.yaml tests/test_build_cli.py
git commit -m "docs: install frosted dropdown module"
```
