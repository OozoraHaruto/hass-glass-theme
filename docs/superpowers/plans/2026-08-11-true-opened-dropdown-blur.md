# True Opened Dropdown Blur Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a genuine fixed 40px backdrop blur to opened Glass and Liquid Glass dropdown menus while retaining the existing fill fallback.

**Architecture:** Extend the existing token-gated `ha-dropdown` controller to own one narrowly scoped `<style>` in each eligible dropdown's open shadow root. The style targets `wa-popup::part(popup)` with standard and WebKit-prefixed backdrop filters. Track style ownership independently from the reversible fill override so theme changes, removals, and stop clean up only module-owned state.

**Tech Stack:** Browser JavaScript ES modules, open shadow DOM, CSS shadow parts, Node.js built-in test runner, Home Assistant/WebAwesome custom elements.

## Global Constraints

- Apply only to opened dropdown menus for themes emitting `--ha-glass-dropdown-surface`.
- Use fixed `blur(40px)` for both Glass and Liquid Glass.
- Retain the existing `--wa-color-surface-raised` fill fallback.
- Add no dependencies and do not patch prototypes or inject global CSS.
- Remove only module-owned styles and preserve unrelated shadow-root content.
- Do not change theme tokens, generated YAML, closed fields, cards, dialogs, or installation behavior.
- Accept and document Home Assistant popup stacking and positioning risks.

---

## File Structure

- Modify `tests/js/glass-dropdown.test.js`: extend the fake DOM with element attributes/removal and add blur lifecycle tests.
- Modify `www/glass-dropdown.js`: install, track, and remove owned popup blur styles.
- Modify `README.md`: document true blur, fallback behavior, internal-selector compatibility, and known risks.

### Task 1: Model owned shadow-root styles and add the first failing test

**Files:**
- Modify: `tests/js/glass-dropdown.test.js:5-155`
- Test: `tests/js/glass-dropdown.test.js`

**Interfaces:**
- Fake nodes support `setAttribute`, `getAttribute`, `remove`, and text content sufficiently to inspect module-owned styles.
- Tests identify owned styles through `data-ha-glass-dropdown-blur`.

- [ ] **Step 1: Extend fake nodes minimally**

Add an attribute map and methods to the `root` factory without changing existing tree semantics:

```js
  const root = (localName) => {
    const attributes = new Map();

    return {
      localName,
      children: [],
      parentNode: null,
      host: null,
      textContent: "",
      _shadowRoot: null,
      get shadowRoot() {
        return this._shadowRoot;
      },
      set shadowRoot(value) {
        this._shadowRoot = value;
        if (value) value.host = this;
      },
      style: declaration(),
      setAttribute(name, value) {
        attributes.set(name, String(value));
      },
      getAttribute(name) {
        return attributes.get(name) ?? null;
      },
      get isConnected() {
        if (this === document) return true;
        return Boolean(this.parentNode?.isConnected || this.host?.isConnected);
      },
      append(child) {
        child.parentNode?.remove(child);
        this.children.push(child);
        child.parentNode = this;
      },
      remove(child) {
        if (child === undefined) {
          this.parentNode?.remove(this);
          return;
        }
        this.children = this.children.filter((candidate) => candidate !== child);
        if (child.parentNode === this) child.parentNode = null;
      },
    };
  };
```

Add `document.createElement = (localName) => root(localName)` after constructing `document`.

- [ ] **Step 2: Add an owned-style helper and startup test**

Near the test constants, add:

```js
const BLUR_ATTRIBUTE = "data-ha-glass-dropdown-blur";
const BLUR_RULE = `wa-popup::part(popup) {
  -webkit-backdrop-filter: blur(40px);
  backdrop-filter: blur(40px);
}`;

const ownedBlurStyles = (dropdown) =>
  (dropdown.shadowRoot?.children ?? []).filter(
    (child) => child.getAttribute?.(BLUR_ATTRIBUTE) === "",
  );
```

Replace the existing open-shadow-root startup regression test with a dropdown that has its own open shadow root and assert both fill and blur:

```js
test("applies fill and blur to an existing shadow-root dropdown", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const host = env.element("ha-dialog");
  host.shadowRoot = env.root();
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  host.shadowRoot.append(dropdown);
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);

  controller.start();

  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
  assert.equal(ownedBlurStyles(dropdown).length, 1);
  assert.equal(ownedBlurStyles(dropdown)[0].textContent, BLUR_RULE);
});
```

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```bash
node --test --test-name-pattern="applies fill and blur to an existing shadow-root dropdown" tests/js/glass-dropdown.test.js
```

Expected: FAIL because no owned style exists.

If Node is unavailable, record the exact command failure and do not claim an observed assertion failure.

- [ ] **Step 4: Verify the fake DOM did not break existing tests**

Run:

```bash
npm run test:js
```

Expected before production implementation: the new blur assertion fails; unrelated tests pass. If npm is unavailable, record that limitation.

### Task 2: Install and clean up module-owned blur styles

**Files:**
- Modify: `www/glass-dropdown.js:1-54`
- Modify: `tests/js/glass-dropdown.test.js`
- Test: `tests/js/glass-dropdown.test.js`

**Interfaces:**
- Owned style marker: `data-ha-glass-dropdown-blur`.
- Owned CSS rule: fixed 40px standard and WebKit backdrop filters on `wa-popup::part(popup)`.
- `styled` map tracks dropdown-to-style ownership separately from `changed` fill ownership.

- [ ] **Step 1: Implement minimal style ownership**

Add constants:

```js
const BLUR_ATTRIBUTE = "data-ha-glass-dropdown-blur";
const BLUR_RULE = `wa-popup::part(popup) {
  -webkit-backdrop-filter: blur(40px);
  backdrop-filter: blur(40px);
}`;
```

Add `const styled = new Map();` beside `changed`.

Add helpers:

```js
  const applyBlur = (dropdown) => {
    if (styled.has(dropdown) || !dropdown.shadowRoot) return;
    const style = document.createElement("style");
    style.setAttribute(BLUR_ATTRIBUTE, "");
    style.textContent = BLUR_RULE;
    dropdown.shadowRoot.append(style);
    styled.set(dropdown, style);
  };

  const removeBlur = (dropdown) => {
    const style = styled.get(dropdown);
    if (!style) return;
    style.remove();
    styled.delete(dropdown);
  };
```

Call `applyBlur(dropdown)` from `apply()` even when the fill override is already tracked:

```js
  const apply = (dropdown) => {
    applyBlur(dropdown);
    if (changed.has(dropdown)) return;
    ...
  };
```

Update `clear()` to remove every owned style before clearing fill overrides:

```js
  const clear = () => {
    for (const dropdown of styled.keys()) removeBlur(dropdown);
    for (const [dropdown, previous] of changed) restore(dropdown, previous);
    changed.clear();
  };
```

Update `release()` so every encountered `ha-dropdown` removes both owned states:

```js
    if (node.localName === "ha-dropdown") {
      removeBlur(node);
      if (changed.has(node)) {
        restore(node, changed.get(node));
        changed.delete(node);
      }
    }
```

- [ ] **Step 2: Run the focused startup test and verify GREEN**

Run:

```bash
node --test --test-name-pattern="applies fill and blur to an existing shadow-root dropdown" tests/js/glass-dropdown.test.js
```

Expected: PASS.

- [ ] **Step 3: Add idempotence and fallback tests**

Add tests proving repeated `sync()` does not duplicate styles and a dropdown without a shadow root retains the fill fallback:

```js
test("does not duplicate an owned blur style during repeated sync", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);

  controller.start();
  controller.sync();
  controller.sync();

  assert.equal(ownedBlurStyles(dropdown).length, 1);
});

test("keeps the fill fallback when a dropdown has no open shadow root", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);

  controller.start();

  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
  assert.equal(ownedBlurStyles(dropdown).length, 0);
});
```

Run:

```bash
node --test --test-name-pattern="owned blur style|fill fallback" tests/js/glass-dropdown.test.js
```

Expected: PASS.

- [ ] **Step 4: Add lifecycle and ownership tests**

Add tests for theme deactivation, stop, subtree removal, and unrelated styles. Each creates a dropdown with a shadow root and an unrelated style child, starts active, triggers the lifecycle action, then asserts:

- owned style count becomes zero;
- unrelated style remains attached;
- fill property restoration matches existing behavior.

Use existing helpers `env.setSource("")`, `env.emitThemeChange()`, `controller.stop()`, and `env.emitDocumentRemoval(host)` to follow neighboring test conventions.

- [ ] **Step 5: Add delayed-shadow-root reconciliation coverage**

Extend or add a test around the existing custom-element definition behavior:

1. Start with an undefined `ha-dropdown` lacking a shadow root.
2. Confirm fill fallback applies and no owned style exists.
3. Attach `dropdown.shadowRoot = env.root()`.
4. Resolve `env.define("ha-dropdown")` and await the existing microtask helper.
5. Assert exactly one owned blur style exists.

This guards the design requirement that blur is added when the open shadow root becomes available.

- [ ] **Step 6: Run the complete JavaScript suite**

Run:

```bash
npm run test:js
```

Expected: all JavaScript tests pass. If Node/npm is unavailable, report the limitation and ensure CI is relied upon before release.

- [ ] **Step 7: Review runtime scope**

Run:

```bash
git diff -- www/glass-dropdown.js tests/js/glass-dropdown.test.js
```

Expected: owned style lifecycle plus tests only; no global stylesheet, prototype patch, dependency, or theme token changes.

### Task 3: Document true blur and compatibility behavior

**Files:**
- Modify: `README.md:133-178`

**Interfaces:**
- Documents `blur(40px)`, retained fill fallback, internal `wa-popup::part(popup)` targeting, and accepted upstream risks.

- [ ] **Step 1: Replace the fill-only workaround description**

Update `README.md:152-156` to state:

```markdown
  cannot reach it either. The optional `www/glass-dropdown.js` workaround
  gives opened menus the Frosted Glass fill and injects a fixed `blur(40px)`
  rule for `wa-popup::part(popup)` when a Glass or Liquid Glass entry is
  active. The fill remains as a fallback if a Home Assistant version changes
  or does not support that internal popup part. Frosted Glass already uses
  the desired fill and does not activate this override.
```

- [ ] **Step 2: Expand the risk warning after setup**

After the restart/hard-refresh step, add:

```markdown
The popup blur creates its own stacking context and intentionally accepts the
same layering and positioning risks described above. If menus render behind
cards, become unclickable, or escape dialog bounds, use the matching Lite
entry or remove `/local/glass-dropdown.js` from `extra_module_url`. Because
the blur rule targets Home Assistant's internal `wa-popup::part(popup)`
structure, a future frontend update may leave only the fill fallback active.
```

Keep the existing Lite remedy and installation paths accurate; avoid duplicating contradictory guidance.

- [ ] **Step 3: Validate documentation diff**

Run:

```bash
git diff --check -- README.md
git diff -- README.md
```

Expected: no whitespace errors; no fill-only claim remains; installation is unchanged.

### Task 4: Run full verification and review

**Files:**
- Verify only.

- [ ] **Step 1: Run JavaScript tests**

```bash
npm run test:js
```

Expected: all JavaScript tests pass. If unavailable locally, record the exact limitation and require CI evidence before release.

- [ ] **Step 2: Run Python and generated-theme checks**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_themes.py --check
```

Expected: all Python tests pass and 15 generated entries are current.

- [ ] **Step 3: Run lint and whitespace checks**

```bash
.venv/bin/python -m yamllint -c .yamllint.yml tokens/ themes/ demo/ .github/
git diff --check
```

Expected: exit code 0.

- [ ] **Step 4: Inspect final scope**

```bash
git status --short
git diff -- www/glass-dropdown.js tests/js/glass-dropdown.test.js README.md
```

Expected: only runtime, test, documentation, approved design, and plan files changed.

- [ ] **Step 5: Request review**

Invoke `superpowers:requesting-code-review`. Review against `docs/superpowers/specs/2026-08-11-true-opened-dropdown-blur-design.md`, resolve Critical/Important findings, and rerun affected checks.

- [ ] **Step 6: Commit**

Only if commit authorization has been given:

```bash
git add www/glass-dropdown.js tests/js/glass-dropdown.test.js README.md docs/superpowers/specs/2026-08-11-true-opened-dropdown-blur-design.md docs/superpowers/plans/2026-08-11-true-opened-dropdown-blur.md
git commit -m "feat: blur opened dropdown menus"
```
