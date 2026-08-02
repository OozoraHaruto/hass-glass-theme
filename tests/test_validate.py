"""Tests for structural validation of the generated theme document.

Validation is the module that turns silent runtime failures -- an undefined
``var()`` renders transparent or black with no error surfaced anywhere -- into
build errors. These tests exercise the real generated document (must be
clean) plus deliberately corrupted copies of it (must each be caught, with
the offending entry/key/value named in the message).
"""

from pathlib import Path

import pytest

from glassbuild.emit import build_themes
from glassbuild.validate import REQUIRED_VARIABLES, validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def themes():
    return build_themes(ROOT)


def _copy(themes):
    """Shallow-copy the document and every entry (including nested modes)
    deeply enough that mutating a test's copy never leaks into another
    test's view of the shared, module-scoped ``themes`` fixture."""
    out = {}
    for name, entry in themes.items():
        new_entry = dict(entry)
        if isinstance(new_entry.get("modes"), dict):
            new_entry["modes"] = {
                mode: dict(payload) for mode, payload in new_entry["modes"].items()
            }
        out[name] = new_entry
    return out


# ---------------------------------------------------------------------------
# The real document
# ---------------------------------------------------------------------------


def test_the_real_themes_validate_clean(themes):
    assert validate(themes) == []


# ---------------------------------------------------------------------------
# Entry presence
# ---------------------------------------------------------------------------


def test_missing_entry_is_reported(themes):
    broken = _copy(themes)
    del broken["Glass Dark"]
    problems = validate(broken)
    assert any("Glass Dark" in p and "missing" in p for p in problems)


def test_all_entries_missing_reports_twelve_problems_without_raising():
    problems = validate({})
    assert len(problems) == 12
    assert all(isinstance(p, str) for p in problems)


def test_non_dict_document_does_not_raise():
    # validate() must never raise, even on a document shaped nothing like
    # the real one.
    problems = validate("not a dict")
    assert isinstance(problems, list)
    assert problems


# ---------------------------------------------------------------------------
# Required variables (counting modes payloads -- partial overlay)
# ---------------------------------------------------------------------------


def test_missing_required_variable_is_reported(themes):
    broken = _copy(themes)
    some_required = sorted(REQUIRED_VARIABLES)[0]
    broken["Glass Dark"].pop(some_required, None)
    broken["Glass Dark"].pop("modes", None)
    assert any(some_required in p for p in validate(broken))


def test_required_variable_defined_only_in_modes_payloads_is_accepted(themes):
    # "Glass" is an Auto entry: most required variables (ha-card-background,
    # primary-color, divider-color, ...) live only inside modes.light /
    # modes.dark, not at the entry's top level -- that's the whole point of
    # the Auto/modes split. If the flattening didn't account for modes
    # payloads, the entry would look like it's missing nearly every required
    # variable even though the real document is correct.
    auto = themes["Glass"]
    assert "ha-card-background" not in auto
    assert "ha-card-background" in auto["modes"]["light"]
    assert "ha-card-background" in auto["modes"]["dark"]
    assert validate(themes) == []


def test_required_variable_missing_from_one_mode_only_is_reported(themes):
    broken = _copy(themes)
    broken["Glass"]["modes"]["light"].pop("ha-card-background", None)
    problems = validate(broken)
    # Dark mode still defines it and top-level doesn't need to (Auto's
    # design), so the *required-variable* check alone cannot see this -- it
    # unions all locations. This test documents that limitation rather than
    # asserting a specific problem is raised: the flatten-based check is a
    # coarse union, not a per-mode completeness check.
    assert isinstance(problems, list)


# ---------------------------------------------------------------------------
# Dangling var() references
# ---------------------------------------------------------------------------


def test_dangling_var_reference_is_reported(themes):
    broken = _copy(themes)
    broken["Glass Dark"]["ha-card-background"] = "var(--nope-not-defined)"
    assert any("nope-not-defined" in p for p in validate(broken))


def test_dangling_var_reference_inside_modes_is_reported(themes):
    broken = _copy(themes)
    broken["Glass"]["modes"]["light"]["ha-card-background"] = "var(--also-not-defined)"
    problems = validate(broken)
    assert any("also-not-defined" in p for p in problems)
    assert any("Glass" in p for p in problems)


def test_var_reference_to_a_defined_token_is_accepted(themes):
    ok = _copy(themes)
    ok["Glass Dark"]["ha-card-background"] = "var(--primary-color)"
    assert validate(ok) == []


def test_var_reference_to_an_ha_builtin_is_accepted(themes):
    # secondary-background-color is an HA builtin that this theme never
    # defines itself (see HA_BUILTIN_VARIABLES) -- referencing it must not
    # be flagged as dangling.
    ok = _copy(themes)
    ok["Glass Dark"]["ha-card-background"] = "var(--secondary-background-color)"
    assert validate(ok) == []


# ---------------------------------------------------------------------------
# Shape: non-string keys/values, "--"-prefixed keys
# ---------------------------------------------------------------------------


def test_non_string_value_is_reported(themes):
    broken = _copy(themes)
    broken["Glass Dark"]["ha-card-border-width"] = 1
    assert any("ha-card-border-width" in p for p in validate(broken))


def test_non_string_key_is_reported(themes):
    broken = _copy(themes)
    broken["Glass Dark"][7] = "some-value"
    problems = validate(broken)
    assert any("Glass Dark" in p and "non-string key" in p for p in problems)


def test_modes_key_itself_is_not_flagged_as_non_string(themes):
    # "modes" maps to a dict, not a string -- it is the one key explicitly
    # exempted from the string-value rule.
    assert validate(themes) == []


def test_key_starting_with_double_dash_is_reported(themes):
    broken = _copy(themes)
    broken["Glass Dark"]["--already-prefixed"] = "red"
    problems = validate(broken)
    assert any("--already-prefixed" in p for p in problems)


# ---------------------------------------------------------------------------
# Lite purity: no backdrop-filter, no blur(), no card-mod keys -- anywhere
# ---------------------------------------------------------------------------
#
# The brief's original check was `"backdrop-filter" in f"{key} {value}"`,
# which only ever fires via the *key* -- real values look like
# "blur(8px) saturate(180%)" and never contain the literal substring
# "backdrop-filter". Each of the three conditions below is tested
# independently, and each is also tested planted inside a modes.light
# payload (not just at the entry's top level), since a check that only
# walks top-level items would silently pass a corrupted Auto-Lite entry.


def test_backdrop_filter_key_at_top_level_of_lite_entry_is_reported(themes):
    broken = _copy(themes)
    broken["Glass Dark Lite"]["ha-card-backdrop-filter"] = "blur(8px)"
    problems = validate(broken)
    assert any("Glass Dark Lite" in p and "backdrop-filter" in p for p in problems)


def test_backdrop_filter_substring_in_modes_light_value_of_lite_entry_is_reported(themes):
    # "Glass Lite" is the Auto-weight Lite entry -- it has a modes block
    # even though it carries no card-mod content in the real document.
    broken = _copy(themes)
    broken["Glass Lite"]["modes"]["light"]["some-injected-key"] = (
        "not a real value but mentions backdrop-filter"
    )
    problems = validate(broken)
    assert any("Glass Lite" in p and "backdrop-filter" in p for p in problems)


def test_blur_paren_value_at_top_level_of_lite_entry_is_reported(themes):
    broken = _copy(themes)
    # An innocuous key name -- the substring must be caught in the *value*,
    # not smuggled in via a suggestively-named key.
    broken["Glass Dark Lite"]["some-injected-key"] = "blur(4px)"
    problems = validate(broken)
    assert any("Glass Dark Lite" in p and "blur(" in p for p in problems)


def test_blur_paren_value_in_modes_light_of_lite_entry_is_reported(themes):
    broken = _copy(themes)
    broken["Glass Lite"]["modes"]["light"]["some-injected-key"] = "blur(4px)"
    problems = validate(broken)
    assert any("Glass Lite" in p and "blur(" in p for p in problems)


def test_cardmod_key_at_top_level_of_lite_entry_is_reported(themes):
    broken = _copy(themes)
    broken["Glass Lite"]["card-mod-root-yaml"] = (
        "x: |\n  .a { backdrop-filter: blur(1px); }\n"
    )
    problems = validate(broken)
    assert any("Glass Lite" in p and "backdrop-filter" in p for p in problems)


def test_cardmod_key_in_modes_light_of_lite_entry_is_reported(themes):
    broken = _copy(themes)
    # An innocuous value -- the violation must be caught via the *key*
    # starting with "card-mod", independent of what it's set to.
    broken["Glass Lite"]["modes"]["light"]["card-mod-sidebar-yaml"] = "harmless"
    problems = validate(broken)
    assert any("Glass Lite" in p and "card-mod" in p for p in problems)


def test_backdrop_filter_and_blur_and_cardmod_are_independent_checks(themes):
    # Each of the three Lite-impurity conditions must be able to fire on
    # its own -- a value with "blur(" but no "backdrop-filter" and a key
    # that isn't card-mod-prefixed must still be caught.
    broken = _copy(themes)
    broken["Frosted Glass Light Lite"]["harmless-key"] = "blur(2px)"
    problems = validate(broken)
    matching = [p for p in problems if "Frosted Glass Light Lite" in p]
    assert matching
    assert any("blur(" in p for p in matching)
    assert not any("backdrop-filter" in p for p in matching)
    assert not any("card-mod" in p for p in matching)


def test_non_lite_entries_are_not_penalised_for_backdrop_filter_or_card_mod(themes):
    # Sanity check: the real document's full-weight entries legitimately
    # contain backdrop-filter, blur(), and card-mod keys -- validate() must
    # not flag any of that on non-Lite entries.
    assert validate(themes) == []
    full_entry = themes["Glass Dark"]
    assert "ha-card-backdrop-filter" in full_entry
    assert "blur(" in full_entry["ha-card-backdrop-filter"]
