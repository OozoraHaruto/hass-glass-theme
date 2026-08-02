import yaml

from glassbuild.cardmod import build_cardmod
from glassbuild.materials import Material

FULL = Material(
    fill="rgba(255, 255, 255, 0.14)",
    rim="rgba(255, 255, 255, 0.45)",
    backdrop="blur(8px) saturate(180%)",
)
LITE = Material(fill="rgba(28, 28, 30, 0.72)", rim="rgba(255, 255, 255, 0.45)", backdrop=None)

MERGED = {
    "font": {
        "stack": "-apple-system, system-ui, sans-serif",
        "tracking_headline": "-0.4px",
        "tracking_body": "-0.2px",
    },
    "motion": {"duration": "300ms", "easing": "cubic-bezier(0.25, 0.1, 0.25, 1)"},
}


def _block(entry_name: str = "Glass", lite: bool = False) -> dict[str, str]:
    materials = {"full": LITE, "light": LITE} if lite else {"full": FULL, "light": FULL}
    return build_cardmod(entry_name, materials, MERGED)


def test_lite_produces_no_cardmod_keys():
    assert _block("Glass Lite", lite=True) == {}


def test_theme_name_is_echoed():
    block = _block("Glass")
    assert block["card-mod-theme"] == "Glass"


def test_root_yaml_is_valid_yaml():
    block = _block()
    assert isinstance(yaml.safe_load(block["card-mod-root-yaml"]), dict)


def test_sidebar_yaml_is_valid_yaml():
    block = _block()
    assert isinstance(yaml.safe_load(block["card-mod-sidebar-yaml"]), dict)


def test_more_info_yaml_is_valid_yaml():
    block = _block()
    assert isinstance(yaml.safe_load(block["card-mod-more-info-yaml"]), dict)


def test_root_yaml_covers_the_header_and_tabs():
    # card-mod-root-yaml is already scoped to hui-root's own shadow root
    # (see src/patch/hui-root.ts: apply_card_mod(this, "root")), so the
    # header and its tab strip are reached with plain selectors -- no
    # ha-panel-lovelace$/hui-root$ prefix needed. `ha-tabs` was removed
    # from the frontend; the current element is `ha-tab-group`.
    css = _block()["card-mod-root-yaml"]
    for selector in (".header", "ha-tab-group"):
        assert selector in css


def test_sidebar_yaml_covers_the_sidebar():
    # card-mod-sidebar-yaml is scoped to ha-sidebar's own shadow root
    # directly (see src/patch/ha-sidebar.ts: apply_card_mod(this, "sidebar")).
    # It is NOT reachable through card-mod-root-yaml/ha-drawer$.
    css = _block()["card-mod-sidebar-yaml"]
    for selector in (":host", ".title", "ha-list-item-button"):
        assert selector in css


def test_more_info_yaml_covers_the_dialog_content():
    # card-mod-more-info-yaml is applied to the light-DOM children of the
    # <ha-dialog> inside ha-more-info-dialog's shadow root (shadow=false in
    # src/patch/ha-more-info-dialog.ts), so plain selectors for slotted
    # content like `.content` and `.title` (slot="headerTitle") work.
    css = _block()["card-mod-more-info-yaml"]
    for selector in (".content", ".title"):
        assert selector in css


def test_root_yaml_carries_the_backdrop_filter():
    assert "blur(8px) saturate(180%)" in _block()["card-mod-root-yaml"]


def test_sidebar_yaml_carries_the_backdrop_filter():
    assert "blur(8px) saturate(180%)" in _block()["card-mod-sidebar-yaml"]


def test_lite_never_carries_a_backdrop_filter_key():
    # Load-bearing: a later task hard-fails the build if any backdrop-filter
    # reaches a Lite entry.
    assert _block("Glass Lite", lite=True) == {}


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
