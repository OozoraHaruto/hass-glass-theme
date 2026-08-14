import re

import yaml

from glassbuild.cardmod import build_cardmod
from glassbuild.materials import Material

EDGE = "inset 0 1px 0 0 rgba(255, 255, 255, 0.28), inset 0 -1px 0 0 rgba(0, 0, 0, 0.22)"

CLEAR = Material(
    fill="rgba(255, 255, 255, 0.14)",
    rim="rgba(255, 255, 255, 0.45)",
    edge=EDGE,
    backdrop=None,
)
FROSTED = Material(
    fill="rgba(255, 255, 255, 0.55)",
    rim="rgba(255, 255, 255, 0.2)",
    edge=EDGE,
    backdrop="blur(40px) saturate(120%) brightness(105%) contrast(96%)",
)
LITE = Material(
    fill="rgba(28, 28, 30, 0.72)",
    rim="rgba(255, 255, 255, 0.45)",
    edge=EDGE,
    backdrop=None,
)

MERGED = {
    "font": {
        "stack": "-apple-system, system-ui, sans-serif",
        "tracking_headline": "-0.4px",
        "tracking_body": "-0.2px",
    },
    "motion": {"duration": "300ms", "easing": "cubic-bezier(0.25, 0.1, 0.25, 1)"},
}


def _block(
    entry_name: str = "Glass",
    *,
    material: Material = CLEAR,
    lite: bool = False,
) -> dict[str, str]:
    materials = {"full": material, "light": material}
    return build_cardmod(entry_name, materials, MERGED, lite=lite)


def _rule_body(css: str, selector: str) -> str:
    """Extract the declaration block for a live (uncommented-enough) rule.

    A plain substring check would also pass against a selector sitting inside
    a CSS comment, or one with no declarations at all. This requires an
    actual "selector { ... }" pair and hands back what's between the braces,
    so callers can assert real declarations landed inside it.
    """
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, f"no live rule for {selector!r} in:\n{css}"
    return match.group(1)


def test_lite_produces_no_cardmod_keys():
    assert _block("Glass Lite", material=LITE, lite=True) == {}


def test_clear_full_entry_keeps_cardmod_without_backdrop_filter():
    block = _block("Glass")
    assert block["card-mod-theme"] == "Glass"
    assert "backdrop-filter" not in block["card-mod-root-yaml"]
    assert "backdrop-filter" not in block["card-mod-sidebar-yaml"]
    assert "background: rgba(255, 255, 255, 0.14)" in block["card-mod-sidebar-yaml"]
    assert (
        "border-right: 1px solid rgba(255, 255, 255, 0.45)"
        in block["card-mod-sidebar-yaml"]
    )


def test_frosted_sidebar_keeps_the_backdrop_filter():
    block = _block("Frosted Glass", material=FROSTED)
    assert FROSTED.backdrop in block["card-mod-sidebar-yaml"]


def test_theme_name_is_echoed():
    block = _block("Glass")
    assert block["card-mod-theme"] == "Glass"


def test_root_yaml_is_valid_yaml_with_only_the_root_key():
    # card-mod interprets any key other than "." as a further shadow-piercing
    # selector, so a stray non-"." key would be silently reinterpreted rather
    # than raise -- isinstance(dict) alone would not catch that.
    block = _block()
    parsed = yaml.safe_load(block["card-mod-root-yaml"])
    assert isinstance(parsed, dict)
    assert list(parsed) == ["."]


def test_sidebar_yaml_is_valid_yaml_with_only_the_root_key():
    block = _block()
    parsed = yaml.safe_load(block["card-mod-sidebar-yaml"])
    assert isinstance(parsed, dict)
    assert list(parsed) == ["."]


def test_root_yaml_covers_the_header_and_tabs():
    # card-mod-root-yaml is already scoped to hui-root's own shadow root
    # (see src/patch/hui-root.ts: apply_card_mod(this, "root")), so the
    # header and its tab strip are reached with plain selectors -- no
    # ha-panel-lovelace$/hui-root$ prefix needed. `ha-tabs` was removed
    # from the frontend; the current element is `ha-tab-group`.
    css = _block()["card-mod-root-yaml"]
    for selector in (".header", "ha-tab-group"):
        assert selector in css


def test_header_rule_is_live_and_no_longer_sets_backdrop_filter():
    # .header's backdrop-filter is now native (--app-header-backdrop-filter,
    # glassbuild/variables.py) -- this rule must supply only what HA has no
    # variable for. The selector is tripled to specificity (0,3,0) so it
    # still wins over hui-root's own ".edit-mode .header" rule (0,2,0).
    css = _block()["card-mod-root-yaml"]
    body = _rule_body(css, ".header.header.header")
    assert "background: rgba(255, 255, 255, 0.14)" in body
    assert "border-bottom: 1px solid rgba(255, 255, 255, 0.45)" in body
    assert "letter-spacing: -0.4px" in body
    assert "backdrop-filter" not in body


def test_sidebar_yaml_covers_the_sidebar():
    # card-mod-sidebar-yaml is scoped to ha-sidebar's own shadow root
    # directly (see src/patch/ha-sidebar.ts: apply_card_mod(this, "sidebar")).
    # It is NOT reachable through card-mod-root-yaml/ha-drawer$ -- there is no
    # native sidebar backdrop-filter variable, so this is the only route.
    css = _block()["card-mod-sidebar-yaml"]
    for selector in (":host", ".title", "ha-list-item-button"):
        assert selector in css


def test_clear_sidebar_yaml_omits_the_backdrop_filter():
    assert "backdrop-filter" not in _block()["card-mod-sidebar-yaml"]


def test_letter_spacing_tracking_tokens_appear():
    block = _block()
    combined = "".join(block.values())
    assert "-0.4px" in combined
    assert "-0.2px" in combined


def test_motion_tokens_appear():
    block = _block()
    combined = "".join(block.values())
    assert "300ms" in combined
    assert "cubic-bezier(0.25, 0.1, 0.25, 1)" in combined
