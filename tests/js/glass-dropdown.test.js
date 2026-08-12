import assert from "node:assert/strict";
import test from "node:test";
import { createDropdownSurfaceController } from "../../www/glass-dropdown.js";

const SOURCE_VARIABLE = "--ha-glass-dropdown-surface";
const TARGET_VARIABLE = "--wa-color-surface-raised";
const OVERRIDE_VALUE = "var(--ha-glass-dropdown-surface)";
const BLUR_ATTRIBUTE = "data-ha-glass-dropdown-blur";
const BLUR_RULE = `wa-popup::part(popup) {
  -webkit-backdrop-filter: blur(20px);
  backdrop-filter: blur(20px);
}`;

const ownedBlurStyles = (dropdown) =>
  (dropdown.shadowRoot?.children ?? []).filter(
    (child) => child.getAttribute?.(BLUR_ATTRIBUTE) === "",
  );

const declaration = () => {
  const properties = new Map();

  return {
    getPropertyValue(name) {
      return properties.get(name)?.value ?? "";
    },
    getPropertyPriority(name) {
      return properties.get(name)?.priority ?? "";
    },
    setProperty(name, value, priority = "") {
      properties.set(name, { value, priority });
    },
    removeProperty(name) {
      const value = properties.get(name)?.value ?? "";
      properties.delete(name);
      return value;
    },
  };
};

const fakeEnvironment = (initialSource) => {
  let source = initialSource;
  const observers = [];
  const definitions = new Map();
  const definitionWaiters = new Map();
  const definitionWaitCounts = new Map();

  class FakeMutationObserver {
    constructor(callback) {
      this.callback = callback;
      this.disconnected = false;
      this.observed = [];
      observers.push(this);
    }

    observe(target, options) {
      this.observed.push({ target, options });
    }

    disconnect() {
      this.disconnected = true;
    }

    emit(records) {
      if (!this.disconnected) this.callback(records);
    }
  }

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
  const documentElement = root("html");
  const document = root(undefined);
  document.createElement = (localName) => root(localName);
  document.head = root(undefined);
  document.documentElement = documentElement;
  document.append(documentElement);
  const customElements = {
    get(localName) {
      return definitions.get(localName);
    },
    whenDefined(localName) {
      definitionWaitCounts.set(
        localName,
        (definitionWaitCounts.get(localName) ?? 0) + 1,
      );
      if (definitions.has(localName)) return Promise.resolve();
      return new Promise((resolve, reject) => {
        const waiters = definitionWaiters.get(localName) ?? [];
        waiters.push({ resolve, reject });
        definitionWaiters.set(localName, waiters);
      });
    },
  };

  return {
    document,
    customElements,
    getComputedStyle(target) {
      assert.equal(target, documentElement);
      return {
        getPropertyValue(name) {
          return name === SOURCE_VARIABLE ? source : "";
        },
      };
    },
    MutationObserver: FakeMutationObserver,
    element: (localName) => root(localName),
    root: () => root(undefined),
    setSource(value) {
      source = value;
    },
    define(localName, upgrade) {
      definitions.set(localName, true);
      upgrade();
      for (const waiter of definitionWaiters.get(localName) ?? []) waiter.resolve();
    },
    rejectDefinition(localName) {
      for (const waiter of definitionWaiters.get(localName) ?? []) {
        waiter.reject(new Error("definition failed"));
      }
      definitionWaiters.delete(localName);
    },
    definitionWaitCount(localName) {
      return definitionWaitCounts.get(localName) ?? 0;
    },
    emitDocumentAddition(node) {
      const observer = observers.find(({ observed }) =>
        observed.some(({ target }) => target === document),
      );
      observer.emit([{ addedNodes: [node], removedNodes: [] }]);
    },
    emitDocumentMutation({ addedNodes = [], removedNodes = [] }) {
      const observer = observers.find(({ observed }) =>
        observed.some(({ target }) => target === document),
      );
      observer.emit([{ addedNodes, removedNodes }]);
    },
    activeObserverCount() {
      return observers.filter((observer) => !observer.disconnected).length;
    },
    observers,
  };
};

test("applies the variable reference to an existing dropdown", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
});

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

test("reinstalls removed owned blur without duplication", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  const removedStyle = ownedBlurStyles(dropdown)[0];
  removedStyle.remove();
  const observer = env.observers.find(({ observed }) =>
    observed.some(({ target }) => target === dropdown.shadowRoot),
  );

  observer.emit([{ addedNodes: [], removedNodes: [removedStyle] }]);

  assert.equal(ownedBlurStyles(dropdown).length, 1);
  assert.notEqual(ownedBlurStyles(dropdown)[0], removedStyle);
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
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
});

test("applies to dropdowns inserted later into an observed open shadow root", () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const host = env.element("ha-dialog");
  host.shadowRoot = env.root();
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  host.shadowRoot.append(dropdown);
  const observer = env.observers.find(({ observed }) =>
    observed.some(({ target }) => target === host.shadowRoot),
  );
  observer.emit([{ addedNodes: [dropdown], removedNodes: [] }]);
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
  assert.equal(ownedBlurStyles(dropdown).length, 1);
});

test("activates an existing dropdown inside an observed open shadow root", () => {
  const env = fakeEnvironment("");
  const host = env.element("ha-dialog");
  host.shadowRoot = env.root();
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  host.shadowRoot.append(dropdown);
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.setSource("rgba(90, 90, 94, 0.45)");
  const marker = env.element("span");
  host.shadowRoot.append(marker);
  const observer = env.observers.find(({ observed }) =>
    observed.some(({ target }) => target === host.shadowRoot),
  );

  observer.emit([{ addedNodes: [marker], removedNodes: [] }]);

  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
  assert.equal(ownedBlurStyles(dropdown).length, 1);
});

test("discovers an open shadow root attached when a host is defined", async () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const host = env.element("ha-late-host");
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.define("ha-late-host", () => {
    host.shadowRoot = env.root();
    const dropdown = env.element("ha-dropdown");
    host.shadowRoot.append(dropdown);
  });
  await Promise.resolve();
  assert.equal(
    host.shadowRoot.children[0].style.getPropertyValue(TARGET_VARIABLE),
    OVERRIDE_VALUE,
  );
});

test("does not rescan a host removed before definition", async () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const host = env.element("ha-late-host");
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.document.remove(host);
  env.define("ha-late-host", () => {
    host.shadowRoot = env.root();
    host.shadowRoot.append(env.element("ha-dropdown"));
  });
  await Promise.resolve();
  assert.equal(
    host.shadowRoot.children[0].style.getPropertyValue(TARGET_VARIABLE),
    "",
  );
});

test("schedules one handled definition reconciliation per host name", async () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const first = env.element("ha-late-host");
  const second = env.element("ha-late-host");
  env.document.append(first);
  env.document.append(second);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  assert.equal(env.definitionWaitCount("ha-late-host"), 1);
  env.rejectDefinition("ha-late-host");
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(env.definitionWaitCount("ha-late-host"), 1);
});

test("restart ignores stale definition reconciliation", async () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const staleHost = env.element("ha-late-host");
  env.document.append(staleHost);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  controller.stop();
  const currentHost = env.element("ha-late-host");
  env.document.children = [env.document.documentElement, currentHost];
  controller.start();
  assert.equal(env.definitionWaitCount("ha-late-host"), 2);
  env.define("ha-late-host", () => {
    staleHost.shadowRoot = env.root();
    staleHost.shadowRoot.append(env.element("ha-dropdown"));
    currentHost.shadowRoot = env.root();
    currentHost.shadowRoot.append(env.element("ha-dropdown"));
  });
  await Promise.resolve();
  assert.equal(
    staleHost.shadowRoot.children[0].style.getPropertyValue(TARGET_VARIABLE),
    "",
  );
  assert.equal(
    currentHost.shadowRoot.children[0].style.getPropertyValue(TARGET_VARIABLE),
    OVERRIDE_VALUE,
  );
});

test("rejected definition reconciliation can be scheduled again", async () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const host = env.element("ha-late-host");
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.rejectDefinition("ha-late-host");
  await new Promise((resolve) => setImmediate(resolve));
  controller.sync();
  assert.equal(env.definitionWaitCount("ha-late-host"), 2);
  env.define("ha-late-host", () => {
    host.shadowRoot = env.root();
    host.shadowRoot.append(env.element("ha-dropdown"));
  });
  await Promise.resolve();
  assert.equal(
    host.shadowRoot.children[0].style.getPropertyValue(TARGET_VARIABLE),
    OVERRIDE_VALUE,
  );
});

test("repeated shadow-host removal restores values and disconnects observers", () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const controller = createDropdownSurfaceController(env);
  controller.start();
  const baselineObservers = env.activeObserverCount();
  for (let index = 0; index < 3; index += 1) {
    const host = env.element("ha-dialog");
    host.shadowRoot = env.root();
    const dropdown = env.element("ha-dropdown");
    dropdown.style.setProperty(TARGET_VARIABLE, "pink", "important");
    host.shadowRoot.append(dropdown);
    env.document.append(host);
    env.emitDocumentAddition(host);
    assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
    env.document.remove(host);
    env.emitDocumentMutation({ removedNodes: [host] });
    assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "pink");
    assert.equal(dropdown.style.getPropertyPriority(TARGET_VARIABLE), "important");
    assert.equal(env.activeObserverCount(), baselineObservers);
  }
});

test("removal preserves a third-party replacement", () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  dropdown.style.setProperty(TARGET_VARIABLE, "orange");
  env.document.remove(dropdown);
  env.emitDocumentMutation({ removedNodes: [dropdown] });
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "orange");
});

test("a moved subtree remains observed and reapplies its dropdown", () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const host = env.element("ha-dialog");
  host.shadowRoot = env.root();
  const dropdown = env.element("ha-dropdown");
  dropdown.style.setProperty(TARGET_VARIABLE, "pink");
  host.shadowRoot.append(dropdown);
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  const observerCount = env.activeObserverCount();
  env.document.remove(host);
  env.document.append(host);
  env.emitDocumentMutation({ addedNodes: [host], removedNodes: [host] });
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
  assert.equal(env.activeObserverCount(), observerCount);
  const later = env.element("ha-dropdown");
  host.shadowRoot.append(later);
  const observer = env.observers.find(
    ({ disconnected, observed }) =>
      !disconnected && observed.some(({ target }) => target === host.shadowRoot),
  );
  observer.emit([{ addedNodes: [later], removedNodes: [] }]);
  assert.equal(later.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
});

test("a removed dropdown is restored and reapplied when reinserted", () => {
  const env = fakeEnvironment("rgba(90, 90, 94, 0.45)");
  const dropdown = env.element("ha-dropdown");
  dropdown.style.setProperty(TARGET_VARIABLE, "pink", "important");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.document.remove(dropdown);
  env.emitDocumentMutation({ removedNodes: [dropdown] });
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "pink");
  env.document.append(dropdown);
  env.emitDocumentAddition(dropdown);
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), OVERRIDE_VALUE);
  env.document.remove(dropdown);
  env.emitDocumentMutation({ removedNodes: [dropdown] });
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "pink");
  assert.equal(dropdown.style.getPropertyPriority(TARGET_VARIABLE), "important");
});

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

test("removes its override when the activation token disappears", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.setSource("");
  controller.sync();
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "");
});

test("restores a prior inline value when its own override is still installed", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  dropdown.style.setProperty(TARGET_VARIABLE, "pink", "important");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  env.setSource("");
  controller.sync();
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "pink");
  assert.equal(dropdown.style.getPropertyPriority(TARGET_VARIABLE), "important");
});

test("does not erase a value another script writes after activation", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  dropdown.style.setProperty(TARGET_VARIABLE, "orange");
  env.setSource("");
  controller.sync();
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "orange");
});

test("active sync preserves a value another script writes after activation", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  dropdown.style.setProperty(TARGET_VARIABLE, "orange");
  controller.sync();
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "orange");
});

test("repeated sync preserves the original inline value", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  dropdown.style.setProperty(TARGET_VARIABLE, "pink", "important");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  controller.sync();
  env.setSource("");
  controller.sync();
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "pink");
  assert.equal(dropdown.style.getPropertyPriority(TARGET_VARIABLE), "important");
});

test("stop disconnects every observer and cleans owned values", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const host = env.element("ha-dialog");
  host.shadowRoot = env.root();
  const dropdown = env.element("ha-dropdown");
  dropdown.shadowRoot = env.root();
  host.shadowRoot.append(dropdown);
  env.document.append(host);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  controller.stop();
  controller.stop();
  assert.ok(env.observers.length >= 3);
  assert.ok(env.observers.every((observer) => observer.disconnected));
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "");
  assert.equal(ownedBlurStyles(dropdown).length, 0);
  const laterDropdown = env.element("ha-dropdown");
  env.document.append(laterDropdown);
  env.emitDocumentAddition(laterDropdown);
  assert.equal(laterDropdown.style.getPropertyValue(TARGET_VARIABLE), "");
});

test("sync is a no-op after stop", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  controller.stop();
  controller.sync();
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "");
});

test("does not apply while the activation token is absent", () => {
  const env = fakeEnvironment("   ");
  const dropdown = env.element("ha-dropdown");
  env.document.append(dropdown);
  const controller = createDropdownSurfaceController(env);
  controller.start();
  assert.equal(dropdown.style.getPropertyValue(TARGET_VARIABLE), "");
});

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
  assert.equal(ownedBlurStyles(dropdown).length, 1);
});

test("start is idempotent", () => {
  const env = fakeEnvironment("rgba(255, 255, 255, 0.55)");
  const controller = createDropdownSurfaceController(env);
  controller.start();
  const observerCount = env.observers.length;
  controller.start();
  assert.equal(env.observers.length, observerCount);
});
