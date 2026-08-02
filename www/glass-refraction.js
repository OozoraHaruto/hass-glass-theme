/*
 * glass-refraction.js -- optional companion module for the Liquid Glass
 * theme entries of hass-glass-theme.
 *
 * WHY THIS FILE EXISTS AT ALL
 *
 * Every other material in this theme can only *scatter* light, because CSS
 * gives no way to bend it: `backdrop-filter` has `blur()` and nothing that
 * displaces a pixel. Real refraction needs an SVG `feDisplacementMap`, and a
 * `backdrop-filter` can only reach one through a same-document `url(#id)`
 * fragment. Chromium resolves nothing else -- external `.svg` files and
 * `data:` URIs are both rejected (Blink bug 109212) -- and a rejected
 * reference does not merely skip its own term: per the Filter Effects spec it
 * invalidates the *entire* chain, so the card would lose its blur too.
 *
 * A Home Assistant theme is a YAML map of CSS variables, and card-mod injects
 * CSS rather than markup. Neither can put an element in the document. This
 * module can, which is the whole reason it is a separate file instead of
 * more lines in themes/glass.yaml.
 *
 * INSTALL (optional -- the theme is complete without it)
 *
 *   1. Copy this file to `<config>/www/glass-refraction.js`.
 *   2. Add to configuration.yaml:
 *
 *        frontend:
 *          extra_module_url:
 *            - /local/glass-refraction.js
 *
 *   3. Restart Home Assistant and pick a "Liquid Glass" theme entry.
 *
 * Skip all of it and the Liquid Glass entries still render: they carry an
 * ordinary blur chain of their own, and this module only ever *upgrades*
 * that. There is no broken intermediate state, which is why the theme never
 * references the refraction chain itself.
 *
 * SCOPE
 *
 * Chromium only (Chrome, Edge, the Android companion app's webview). Firefox
 * and Safari get the plain blur, on purpose -- see `blinkResolvesFilterRefs`.
 * Displacement is also genuinely expensive to composite, so this is not
 * something to put on an always-on wall tablet.
 */

(() => {
  "use strict";

  // Must match `refraction.filter_id` in tokens/liquid-glass.yaml.
  // tests/test_refraction.py pins the two together, because a rename on one
  // side alone is silent at runtime and takes the blur down with it.
  const FILTER_MARKUP = `
    <filter id="glass-refraction"
            x="-10%" y="-10%" width="120%" height="120%"
            color-interpolation-filters="sRGB"
            filterUnits="objectBoundingBox"
            primitiveUnits="userSpaceOnUse">
      <feImage result="map" preserveAspectRatio="none"
               x="0" y="0" width="100%" height="100%" href="__MAP__"/>
      <feDisplacementMap in="SourceGraphic" in2="map"
                         scale="__SCALE__"
                         xChannelSelector="R" yChannelSelector="G"/>
    </filter>`;

  // The variable the theme defines and this module switches to. Its presence
  // is also how we detect that a Liquid Glass entry is the active theme --
  // no theme-name matching anywhere, so renaming an entry cannot break this.
  const SOURCE_VARIABLE = "--ha-glass-refraction-backdrop";

  // The displacement's tuning, published by the theme from
  // tokens/liquid-glass.yaml. Read rather than duplicated: a copy here that
  // matches the token today keeps matching until someone retunes the token,
  // and then diverges silently. There are deliberately no fallback literals
  // -- if these are absent then no refractive theme is active, and the right
  // response is to install nothing at all.
  const SCALE_VARIABLE = "--ha-glass-refraction-scale";
  const EDGE_VARIABLE = "--ha-glass-refraction-edge";

  // The four *surface* backdrop variables, and deliberately not the three
  // scrim ones. A scrim covers the whole viewport: it has no edge for a rim
  // lens to sit on, and displacing it full-screen is the most expensive
  // thing this filter could possibly be asked to do.
  const TARGET_VARIABLES = [
    "--ha-card-backdrop-filter",
    "--ha-dialog-surface-backdrop-filter",
    "--app-header-backdrop-filter",
    "--ha-bottom-sheet-surface-backdrop-filter",
  ];

  /*
   * The displacement map.
   *
   * `feDisplacementMap` reads two channels as absolute directions -- here R
   * for x and G for y -- where 128 is "no shift", 0 is a full shift one way
   * and 255 a full shift the other. So the map is two independent ramps that
   * have to occupy different channels of the same image.
   *
   * They are drawn as two full-size rects and combined with `screen`
   * blending, which is what lets each keep its own channel: screening a
   * pure-red image over a pure-green one yields (R, G, 0) with neither
   * disturbing the other. Adding them would clip; screening cannot, since
   * each channel is non-zero in only one layer.
   *
   * The gradients hold flat at the neutral midpoint (#800000 / #008000)
   * across the middle of each axis, so only the outer `edge` fraction bends
   * at all. That is the difference between a rim lens and a fish-eye: a real
   * pane's thickness is visible at its border, not across its face. Stops
   * are fractions rather than pixels so the band tracks the element -- the
   * same map serves a full-width table and a small badge.
   */
  const mapImage = (edge) => {
    const near = edge.toFixed(3);
    const far = (1 - edge).toFixed(3);
    const ramp = (id, x2, y2, lo, mid, hi) =>
      `<linearGradient id="${id}" x1="0" y1="0" x2="${x2}" y2="${y2}">` +
      `<stop offset="0" stop-color="${lo}"/>` +
      `<stop offset="${near}" stop-color="${mid}"/>` +
      `<stop offset="${far}" stop-color="${mid}"/>` +
      `<stop offset="1" stop-color="${hi}"/>` +
      `</linearGradient>`;

    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" ` +
      `viewBox="0 0 100 100" preserveAspectRatio="none">` +
      `<defs>` +
      ramp("h", 1, 0, "#000000", "#800000", "#ff0000") +
      ramp("v", 0, 1, "#000000", "#008000", "#00ff00") +
      `</defs>` +
      `<rect width="100" height="100" fill="url(#h)"/>` +
      `<rect width="100" height="100" fill="url(#v)" ` +
      `style="mix-blend-mode:screen"/>` +
      `</svg>`;

    return "data:image/svg+xml," + encodeURIComponent(svg);
  };

  /*
   * Whether this engine resolves SVG filter references in `backdrop-filter`.
   *
   * There is no direct feature test for it: `CSS.supports` reports on syntax,
   * and every engine parses `url(#x)` happily whether or not it will later
   * resolve it. So this proxies on the engine instead, via the Houdini Paint
   * API -- shipped in Blink, implemented in neither Gecko nor WebKit. It is a
   * correlation rather than a real capability check, which is unsatisfying,
   * but the failure it guards against is severe and one-directional: getting
   * this wrong in the permissive direction strips the backdrop-filter off
   * every card in the theme, while getting it wrong in the strict direction
   * costs an engine its refraction and nothing else.
   */
  const blinkResolvesFilterRefs = () =>
    typeof CSS !== "undefined" &&
    typeof CSS.supports === "function" &&
    CSS.supports("background-image", "paint(id)");

  let styleSheet = null;

  const installFilter = (scale, edge) => {
    if (document.querySelector("svg[data-glass-refraction]")) return;

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("data-glass-refraction", "");
    svg.setAttribute("aria-hidden", "true");
    // Zero-sized and out of flow: this element is a definition, never a
    // rendered thing. Left in normal flow it would add a scroll region to
    // every HA view.
    svg.setAttribute(
      "style",
      "position:absolute;width:0;height:0;overflow:hidden;pointer-events:none",
    );
    svg.innerHTML = FILTER_MARKUP.replace("__MAP__", mapImage(edge)).replace(
      "__SCALE__",
      String(scale),
    );
    document.body.appendChild(svg);
  };

  /*
   * The override lives in a stylesheet rather than in inline styles, for two
   * reasons that both come down to staying out of Home Assistant's way.
   *
   * HA applies a theme by writing CSS variables onto `documentElement`'s
   * inline style. Writing ours there too would mean fighting it for the same
   * slot on every theme change, and -- since we watch that attribute to
   * notice those changes -- our own writes would retrigger the observer.
   * A separate sheet is untouched by HA, so toggling `disabled` is the whole
   * of our state, and `!important` is what lets a stylesheet rule outrank the
   * inline values HA sets.
   */
  const ensureSheet = () => {
    if (styleSheet) return styleSheet;
    const style = document.createElement("style");
    style.setAttribute("data-glass-refraction", "");
    style.textContent =
      "html{" +
      TARGET_VARIABLES.map(
        (name) => `${name}:var(${SOURCE_VARIABLE}) !important;`,
      ).join("") +
      "}";
    document.head.appendChild(style);
    styleSheet = style;
    return style;
  };

  /*
   * Enable the override only while a theme that defines the source variable
   * is active.
   *
   * This is not an optimisation. `var()` on an undefined custom property is
   * invalid at computed-value time, which makes the whole declaration
   * `unset` -- so leaving the sheet enabled under Glass, Frosted Glass, or
   * any third-party theme would strip those themes' backdrop-filter entirely
   * rather than simply not helping them.
   */
  const sync = () => {
    const styles = getComputedStyle(document.documentElement);
    const read = (name) => styles.getPropertyValue(name).trim();

    const declared = read(SOURCE_VARIABLE);
    const scale = Number(read(SCALE_VARIABLE));
    const edge = Number(read(EDGE_VARIABLE));
    const active =
      declared !== "" && Number.isFinite(scale) && edge > 0 && edge < 0.5;

    // Installed here rather than at startup, and only once a refractive theme
    // is actually active: the filter's tuning comes from that theme, and
    // there is nothing sensible to build the element out of before one is
    // applied. It also means an install that never selects Liquid Glass
    // never grows the extra element.
    if (active) installFilter(scale, edge);
    ensureSheet().disabled = !active;
  };

  const start = () => {
    if (!blinkResolvesFilterRefs()) return;

    sync();

    // HA rewrites documentElement's inline custom properties whenever the
    // theme, or the light/dark mode within an Auto entry, changes. That
    // attribute mutation is the signal; we never write there ourselves, so
    // this cannot feed back on itself.
    new MutationObserver(sync).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["style"],
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
