const SOURCE_VARIABLE = "--ha-glass-dropdown-surface";
const TARGET_VARIABLE = "--wa-color-surface-raised";
const OVERRIDE_VALUE = `var(${SOURCE_VARIABLE})`;

export const createDropdownSurfaceController = ({
  document,
  getComputedStyle,
  MutationObserver,
  customElements,
}) => {
  const changed = new Map();
  const observedRoots = new Map();
  const pendingDefinitions = new Map();
  let themeObserver;
  let active = false;
  let started = false;
  let generation = 0;

  const apply = (dropdown) => {
    if (changed.has(dropdown)) return;
    changed.set(dropdown, {
      value: dropdown.style.getPropertyValue(TARGET_VARIABLE),
      priority: dropdown.style.getPropertyPriority(TARGET_VARIABLE),
    });
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

  const release = (node) => {
    if (node.localName === "ha-dropdown" && changed.has(node)) {
      restore(node, changed.get(node));
      changed.delete(node);
    }
    if (node.shadowRoot) {
      release(node.shadowRoot);
      const observer = observedRoots.get(node.shadowRoot);
      observer?.disconnect();
      observedRoots.delete(node.shadowRoot);
    }
    for (const child of node.children ?? []) release(child);
  };

  const reconcileAfterDefinition = (node) => {
    const { localName } = node;
    if (
      !started ||
      !localName?.includes("-") ||
      node.shadowRoot ||
      !customElements ||
      customElements.get(localName)
    ) {
      return;
    }
    if (pendingDefinitions.has(localName)) return;
    const entry = { generation };
    pendingDefinitions.set(localName, entry);
    customElements
      .whenDefined(localName)
      .then(() => {
        if (started && generation === entry.generation) scan(document);
      })
      .catch(() => {})
      .finally(() => {
        if (pendingDefinitions.get(localName) === entry) {
          pendingDefinitions.delete(localName);
        }
      });
  };

  const scan = (node) => {
    if (node.localName === "ha-dropdown" && active) apply(node);
    if (node.shadowRoot) observeRoot(node.shadowRoot);
    else reconcileAfterDefinition(node);
    for (const child of node.children ?? []) scan(child);
  };

  const observeRoot = (root) => {
    if (observedRoots.has(root)) return;
    const observer = new MutationObserver((records) => {
      const removed = new Set();
      const added = new Set();
      for (const record of records) {
        for (const node of record.removedNodes) removed.add(node);
        for (const node of record.addedNodes) added.add(node);
      }
      for (const node of removed) release(node);
      for (const node of added) scan(node);
    });
    observer.observe(root, { childList: true, subtree: true });
    observedRoots.set(root, observer);
    scan(root);
  };

  const sync = () => {
    if (!started) return;
    active =
      getComputedStyle(document.documentElement)
        .getPropertyValue(SOURCE_VARIABLE)
        .trim() !== "";
    if (active) scan(document);
    else clear();
  };

  const start = () => {
    if (started) return;
    generation += 1;
    started = true;
    observeRoot(document);
    themeObserver = new MutationObserver(sync);
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["style"],
    });
    sync();
  };

  const stop = () => {
    if (!started) return;
    generation += 1;
    started = false;
    themeObserver?.disconnect();
    themeObserver = undefined;
    for (const observer of observedRoots.values()) observer.disconnect();
    observedRoots.clear();
    pendingDefinitions.clear();
    active = false;
    clear();
  };

  return { start, sync, stop };
};

if (typeof document !== "undefined") {
  const start = () =>
    createDropdownSurfaceController({
      document,
      getComputedStyle,
      MutationObserver,
      customElements,
    }).start();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
}
