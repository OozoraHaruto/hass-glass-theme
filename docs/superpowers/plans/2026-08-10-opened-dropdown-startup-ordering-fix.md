# Opened Dropdown Startup Ordering Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the existing Frosted Glass opened-menu surface to dropdowns already present inside open shadow roots when `glass-dropdown.js` starts.

**Architecture:** Add a regression test for the pre-existing shadow-root topology, then reorder startup so `sync()` establishes the activation state before the first document traversal. Keep the existing observer, cleanup, reconciliation, and ownership behavior unchanged.

**Tech Stack:** Browser JavaScript ES modules, Node.js built-in test runner, Home Assistant custom properties and open shadow roots.

## Global Constraints

- Apply only to opened dropdown menus already covered by `glass-dropdown.js`.
- Do not add true popup backdrop blur.
- Do not change theme tokens, generated YAML, closed fields, cards, dialogs, or module installation.
- Do not change dynamic insertion, cleanup, restart, custom-element reconciliation, or third-party inline-value ownership behavior.
- Add no dependencies.

---

## File Structure

- Modify `tests/js/glass-dropdown.test.js`: reproduce and guard the pre-existing open-shadow-root startup case.
- Modify `www/glass-dropdown.js`: establish activation before the initial observed-root scan.

### Task 1: Fix initial shadow-root dropdown activation

**Files:**
- Modify: `tests/js/glass-dropdown.test.js:158-180`
- Modify: `www/glass-dropdown.js:107-128`
- Test: `tests/js/glass-dropdown.test.js`

**Interfaces:**
- Consumes: `createDropdownSurfaceController(env)` and theme activation token `--ha-glass-dropdown-surface`.
- Produces: immediate `--wa-color-surface-raised: var(--ha-glass-dropdown-surface)` on eligible `ha-dropdown` elements existing below open shadow roots at startup.

- [ ] **Step 1: Add the failing regression test**

Insert after the existing light-DOM startup test:

```js
test("applies to an existing dropdown inside an open shadow root", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const host = env.element("ha-dialog");
  host.shadowRoot = env.root();
  const dropdown = env.element("ha-dropdown");
  host.shadowRoot.append(dropdown);
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);

  controller.start();

  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
});
```

- [ ] **Step 2: Run the focused test and verify it fails for the diagnosed reason**

Run:

```bash
node --test --test-name-pattern="existing dropdown inside an open shadow root" tests/js/glass-dropdown.test.js
```

Expected: FAIL with actual `""` and expected `"var(--ha-glass-dropdown-surface)"`.

If Node remains unavailable locally, do not claim the RED run occurred. Preserve the test and rely on CI for execution while recording the tooling limitation.

- [ ] **Step 3: Reorder startup minimally**

Change `start()` in `www/glass-dropdown.js` to establish activation before the first traversal:

```js
  const start = () => {
    if (started) return;
    generation += 1;
    started = true;
    sync();
    observeRoot(document);
    themeObserver = new MutationObserver(sync);
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["style"],
    });
  };
```

Do not change `sync()`, `scan()`, `observeRoot()`, or any ownership and cleanup functions.

- [ ] **Step 4: Run the focused test and complete JavaScript suite**

Run:

```bash
node --test --test-name-pattern="existing dropdown inside an open shadow root" tests/js/glass-dropdown.test.js
npm run test:js
```

Expected: focused test passes and the full JavaScript suite passes.

If Node/npm remain unavailable, report both commands as unavailable and do not substitute unrelated tooling.

- [ ] **Step 5: Run unchanged-domain verification**

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_themes.py --check
.venv/bin/python -m yamllint -c .yamllint.yml tokens/ themes/ demo/ .github/
git diff --check
```

Expected: all Python tests pass, generated theme reports 15 current entries, YAML lint exits 0, and the diff has no whitespace errors.

- [ ] **Step 6: Review scope**

Run:

```bash
git diff -- www/glass-dropdown.js tests/js/glass-dropdown.test.js
```

Expected: one regression test and startup call reordering only. Confirm no theme tokens, generated YAML, installation, or unrelated behavior changed.

- [ ] **Step 7: Commit**

Only if commit authorization has been given:

```bash
git add www/glass-dropdown.js tests/js/glass-dropdown.test.js docs/superpowers/specs/2026-08-10-opened-dropdown-startup-ordering-fix-design.md docs/superpowers/plans/2026-08-10-opened-dropdown-startup-ordering-fix.md
git commit -m "fix: activate existing shadow-root dropdowns"
```
