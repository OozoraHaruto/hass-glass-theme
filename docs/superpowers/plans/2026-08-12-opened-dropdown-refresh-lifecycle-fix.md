# Opened Dropdown Refresh Lifecycle Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep opened-dropdown fill and blur active after a Home Assistant browser refresh even when the theme activation token appears after the startup retries.

**Architecture:** Reuse the controller's existing document and open-shadow-root mutation observers as event-driven synchronization signals, so late theme activation no longer depends on a fixed timeout. Restore per-dropdown blur ownership by installing one narrowly scoped style in each `ha-dropdown` open shadow root while retaining the reversible host fill override.

**Tech Stack:** Browser JavaScript ES modules, open shadow DOM, CSS shadow parts, `MutationObserver`, Node.js built-in test runner.

## Global Constraints

- Limit runtime changes to `www/glass-dropdown.js` and tests to `tests/js/glass-dropdown.test.js`.
- Keep the activation token `--ha-glass-dropdown-surface` and fill target `--wa-color-surface-raised` unchanged.
- Keep the existing fixed `blur(20px)` strength with standard and WebKit-prefixed declarations.
- Add no dependencies, permanent polling, prototype patches, generated theme changes, or installation changes.
- Preserve fill restoration, third-party inline values, dynamic insertion, custom-element reconciliation, moved-subtree handling, and observer cleanup.
- Own and remove only styles marked `data-ha-glass-dropdown-blur` that this controller creates.
- Do not commit implementation changes unless the user separately authorizes an implementation commit.

---

## File Structure

- Modify `tests/js/glass-dropdown.test.js`: model per-dropdown owned styles and cover refresh-order late activation, idempotence, fallback, and cleanup.
- Modify `www/glass-dropdown.js`: synchronize on observed DOM mutations and own blur styles inside dropdown shadow roots.
- Verify `docs/superpowers/specs/2026-08-12-opened-dropdown-refresh-lifecycle-fix-design.md`: use as the acceptance criteria; no further documentation change is required.

### Task 1: Activate After Late Theme Propagation

**Files:**
- Modify: `tests/js/glass-dropdown.test.js:135-182,511-518`
- Modify: `www/glass-dropdown.js:111-125`
- Test: `tests/js/glass-dropdown.test.js`

**Interfaces:**
- Consumes: `createDropdownSurfaceController(env)`, `env.setSource(value)`, and `env.emitDocumentAddition(node)`.
- Produces: every observed child-list mutation batch re-evaluates `--ha-glass-dropdown-surface`; activation scans the connected document exactly through `sync()`.

- [ ] **Step 1: Write the failing refresh-order regression test**

Add this test near the existing activation-token tests:

```js
test("activates after a DOM mutation when the theme token arrives late", () => {
  const env = fakeEnvironment("");
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.setSource("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  env.document.append(dropdown);

  env.emitDocumentAddition(dropdown);

  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
});
```

The test intentionally does not call `controller.sync()`: it reproduces a refreshed page where the token appears after startup and a normal frontend insertion is the next observable lifecycle event.

- [ ] **Step 2: Run the focused test to verify RED**

Run:

```bash
node --test --test-name-pattern="activates after a DOM mutation when the theme token arrives late" tests/js/glass-dropdown.test.js
```

Expected: FAIL because the current mutation callback calls `scan(node)` while `active` is still `false`, leaving `--wa-color-surface-raised` empty.

- [ ] **Step 3: Make observed DOM batches synchronize activation**

Replace the body of the observer callback in `observeRoot()` with:

```js
    const observer = new MutationObserver((records) => {
      const removed = new Set();
      for (const record of records) {
        for (const node of record.removedNodes) removed.add(node);
      }
      for (const node of removed) release(node);
      sync();
    });
```

Do not retain a separate added-node scan. When active, `sync()` already scans the connected document and all reachable open shadow roots; when inactive, it clears owned state. Releasing removed nodes first preserves detached-subtree restoration and observer cleanup.

- [ ] **Step 4: Run focused lifecycle tests**

Run:

```bash
node --test --test-name-pattern="activates after a DOM mutation|inserted later|removed dropdown|moved subtree|repeated shadow-host removal" tests/js/glass-dropdown.test.js
```

Expected: PASS. The late token activates through the mutation, later insertions are discovered through the full scan, and removal/movement cleanup remains intact.

- [ ] **Step 5: Inspect the isolated runtime diff**

Run:

```bash
git diff --check -- www/glass-dropdown.js tests/js/glass-dropdown.test.js
git diff -- www/glass-dropdown.js tests/js/glass-dropdown.test.js
```

Expected: no whitespace errors; the only runtime behavior change is mutation-triggered `sync()`.

### Task 2: Restore Shadow-Root Popup Blur

**Files:**
- Modify: `tests/js/glass-dropdown.test.js:8-17,194-209,419-527`
- Modify: `www/glass-dropdown.js:16-75,128-140`
- Test: `tests/js/glass-dropdown.test.js`

**Interfaces:**
- Consumes: active `ha-dropdown` elements discovered by `scan(node)`.
- Produces: `applyBlur(dropdown)` installs one owned `<style data-ha-glass-dropdown-blur>` in `dropdown.shadowRoot`; `removeBlur(dropdown)` removes only that owned style.
- Ownership state: `Map<HTMLElement, HTMLStyleElement>` named `styled`, independent of the existing `changed` fill map.

- [ ] **Step 1: Change the test helper to inspect dropdown shadow roots**

Replace `ownedBlurStyle` with:

```js
const ownedBlurStyles = (dropdown) =>
  (dropdown.shadowRoot?.children ?? []).filter(
    (child) => child.getAttribute?.(BLUR_ATTRIBUTE) === "",
  );
```

This models the CSS scope required for `wa-popup::part(popup)` to reach the popup.

- [ ] **Step 2: Write the failing shadow-scope startup test**

Replace the current `"applies fill and blur to an existing shadow-root dropdown"` test with:

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
  assert.equal(
    env.document.head.children.some(
      (child) => child.getAttribute?.(BLUR_ATTRIBUTE) === "",
    ),
    false,
  );
});
```

- [ ] **Step 3: Run the shadow-scope test to verify RED**

Run:

```bash
node --test --test-name-pattern="applies fill and blur to an existing shadow-root dropdown" tests/js/glass-dropdown.test.js
```

Expected: FAIL because the current controller installs the owned style in `document.head`, leaving `ownedBlurStyles(dropdown).length` equal to `0`.

- [ ] **Step 4: Add per-dropdown blur ownership**

In `createDropdownSurfaceController`, add `styled` beside `changed` and replace the global `blurStyle`, `applyBlur()`, and `removeBlur()` state with:

```js
  const changed = new Map();
  const styled = new Map();
```

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

Call blur installation before the fill map's idempotence return:

```js
  const apply = (dropdown) => {
    applyBlur(dropdown);
    if (changed.has(dropdown)) return;
```

This permits a dropdown that first received only the fill fallback to receive blur later when its shadow root appears.

- [ ] **Step 5: Update blur cleanup paths**

Replace `clear()` with:

```js
  const clear = () => {
    for (const dropdown of styled.keys()) removeBlur(dropdown);
    for (const [dropdown, previous] of changed) restore(dropdown, previous);
    changed.clear();
  };
```

Replace the opening dropdown branch in `release()` with:

```js
  const release = (node) => {
    if (node.localName === "ha-dropdown") {
      removeBlur(node);
      if (changed.has(node)) {
        restore(node, changed.get(node));
        changed.delete(node);
      }
    }
```

Remove `applyBlur()` from `sync()`, leaving active synchronization as:

```js
    if (active) {
      scan(document);
    } else {
      clear();
    }
```

This removes the global style lifecycle and keeps blur ownership aligned with each dropdown.

- [ ] **Step 6: Run the shadow-scope startup test to verify GREEN**

Run:

```bash
node --test --test-name-pattern="applies fill and blur to an existing shadow-root dropdown" tests/js/glass-dropdown.test.js
```

Expected: PASS with one style in the dropdown shadow root and none in `document.head`.

- [ ] **Step 7: Add idempotence and fill-fallback tests**

Add:

```js
test("does not duplicate blur during repeated sync and mutations", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();

  controller.sync();
  env.emitDocumentAddition(dropdown);

  assert.equal(ownedBlurStyles(dropdown).length, 1);
});

test("keeps the fill fallback without an open dropdown shadow root", () => {
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
node --test --test-name-pattern="does not duplicate blur|keeps the fill fallback" tests/js/glass-dropdown.test.js
```

Expected: PASS.

- [ ] **Step 8: Add deactivation and subtree-removal cleanup tests**

Add:

```js
test("theme deactivation removes owned dropdown blur", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  const unrelated = env.element("style");
  dropdown.shadowRoot.append(unrelated);
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();

  env.setSource("");
  controller.sync();

  assert.equal(ownedBlurStyles(dropdown).length, 0);
  assert.equal(dropdown.shadowRoot.children.includes(unrelated), true);
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "");
});

test("removed subtrees release owned dropdown blur", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const host = env.element("ha-dialog");
  host.shadowRoot = env.root();
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  host.shadowRoot.append(dropdown);
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);
  controller.start();

  env.document.remove(host);
  env.emitDocumentMutation({ removedNodes: [host] });

  assert.equal(ownedBlurStyles(dropdown).length, 0);
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "");
});
```

Run:

```bash
node --test --test-name-pattern="theme deactivation removes owned dropdown blur|removed subtrees release owned dropdown blur" tests/js/glass-dropdown.test.js
```

Expected: PASS; unrelated shadow-root content remains attached.

- [ ] **Step 9: Strengthen the late-activation regression to include blur**

In Task 1's `"activates after a DOM mutation when the theme token arrives late"` test, add after the fill assertion:

```js
  assert.equal(ownedBlurStyles(dropdown).length, 1);
```

Run:

```bash
node --test --test-name-pattern="activates after a DOM mutation when the theme token arrives late" tests/js/glass-dropdown.test.js
```

Expected: PASS, proving one event activates both fill and correctly scoped blur after refresh ordering.

### Task 3: Full Verification and Scope Review

**Files:**
- Verify: `www/glass-dropdown.js`
- Verify: `tests/js/glass-dropdown.test.js`
- Verify: `docs/superpowers/specs/2026-08-12-opened-dropdown-refresh-lifecycle-fix-design.md`

**Interfaces:**
- Consumes: the completed controller and regression suite.
- Produces: evidence that JavaScript behavior, Python theme generation, YAML, and repository formatting remain valid.

- [ ] **Step 1: Run the complete JavaScript suite**

Run:

```bash
npm run test:js
```

Expected: all JavaScript tests pass.

- [ ] **Step 2: Run Python tests and generated-theme drift check**

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_themes.py --check
```

Expected: all Python tests pass and `themes/glass.yaml` is current.

- [ ] **Step 3: Run YAML lint and whitespace checks**

Run:

```bash
.venv/bin/python -m yamllint -c .yamllint.yml tokens/ themes/ demo/ .github/
git diff --check
```

Expected: both commands exit with status `0`.

No JavaScript lint or typecheck script is configured in `package.json`; the Node test suite is the configured JavaScript static/runtime check.

- [ ] **Step 4: Inspect final scope**

Run:

```bash
git status --short
git diff -- www/glass-dropdown.js tests/js/glass-dropdown.test.js
git diff 26171eb --stat
```

Expected: implementation changes are limited to the runtime module, JavaScript tests, and this plan; the approved design commit remains unchanged. No token, generated YAML, package, or installation files are modified.

- [ ] **Step 5: Request code review**

Invoke `superpowers:requesting-code-review` and review the implementation against `docs/superpowers/specs/2026-08-12-opened-dropdown-refresh-lifecycle-fix-design.md`. Resolve all Critical and Important findings, then rerun every affected command from Steps 1-3.

- [ ] **Step 6: Prepare, but do not create, an implementation commit**

Run:

```bash
git diff --check
git status --short
```

Expected: verified implementation changes remain uncommitted unless the user explicitly authorizes a separate implementation commit.
