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


def test_required_variable_missing_from_one_mode_only_is_not_caught_by_the_union_check(
    themes,
):
    # The required-variable check flattens top-level + modes.light +
    # modes.dark into one namespace and asks only "is this key defined
    # *somewhere*" -- by design, it cannot by itself notice that
    # ha-card-background is missing from modes.light while still present in
    # modes.dark. Confirm that directly: no "required variable" problem is
    # raised for this mutation.
    #
    # This is adjudicated as acceptable, not a gap: the same asymmetry is
    # caught transitively by tests/test_emit.py's
    # `test_auto_entries_match_ha_real_merge_algorithm_against_the_flat_entries`
    # (test_emit.py:121-152), which asserts `{**base, **modes[mode]} == the
    # corresponding flat entry` for both light and dark, for all four Auto
    # pairs. Because the eight flat entries (`Glass Light`, `Glass Dark`,
    # ...) carry no `modes` key at all, each is checked against
    # REQUIRED_VARIABLES entirely on its own by *this* module -- so a
    # variable actually missing from one mode's real payload would show up
    # as a required-variable failure on the corresponding flat entry, or as
    # an equality failure in test_emit.py, well before it could reach this
    # union check. The union check's job is narrower than "catch every
    # per-mode omission"; it does not need to expand to do that.
    broken = _copy(themes)
    broken["Glass"]["modes"]["light"].pop("ha-card-background", None)
    problems = validate(broken)
    assert not any(
        "ha-card-background" in p and "required variable" in p for p in problems
    )


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


def test_var_reference_missing_leading_dashdash_is_reported(themes):
    # `var(primary-color)` -- no leading "--" -- is malformed CSS: it does
    # not reference the custom property `--primary-color` at all, and the
    # browser silently drops it, same silent-failure class as a dangling
    # reference. It must not sneak past the "well-formed var()" regex just
    # because "primary-color" happens to also be a real, defined variable.
    broken = _copy(themes)
    broken["Glass Dark"]["ha-card-background"] = "var(primary-color)"
    problems = validate(broken)
    assert any(
        "Glass Dark" in p and "primary-color" in p and "malformed" in p
        for p in problems
    )


def test_well_formed_var_reference_does_not_trigger_the_malformed_check(themes):
    # Sanity check for the malformed-var() detector's negative lookahead:
    # a correctly-prefixed reference must not also be reported as malformed.
    ok = _copy(themes)
    ok["Glass Dark"]["ha-card-background"] = "var(--primary-color)"
    problems = validate(ok)
    assert not any("malformed" in p for p in problems)


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


def test_modes_key_itself_is_exempt_from_the_string_value_rule(themes):
    # "modes" maps to a dict, not a string -- it is the one key explicitly
    # exempted from the string-value rule. Prove the exemption is targeted
    # rather than a blanket pass: planting a genuine non-string value
    # elsewhere in the same entry must still be caught, while "modes"
    # itself is never flagged as a bad value.
    broken = _copy(themes)
    broken["Glass"]["ha-card-border-radius"] = 12
    problems = validate(broken)
    assert any("ha-card-border-radius" in p for p in problems)
    assert not any("'modes'" in p for p in problems)


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
    # A harmless value -- no "backdrop-filter" or "blur(" substring anywhere
    # in it -- so the only thing that can trip a violation here is the
    # card-mod-key-prefix check itself, not one of the other two conditions
    # riding along for free.
    broken["Glass Lite"]["card-mod-root-yaml"] = "x: harmless\n"
    problems = validate(broken)
    assert any(
        "Glass Lite" in p and "card-mod key" in p for p in problems
    )


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


# ---------------------------------------------------------------------------
# modes shape: malformed modes blocks must be reported, never swallowed
# ---------------------------------------------------------------------------
#
# An earlier version of _mode_payloads() tolerated malformed `modes` shapes
# by silently filtering them out (`if not isinstance(...): return {}` /
# `if isinstance(payload, dict)`), which meant a badly-shaped modes block --
# something HA would apply nothing for -- passed validate() with zero
# problems reported. Confirmed by execution before the fix: modes["light"]
# = "oops" returned []; deleting modes["light"] entirely returned [];
# modes = ["junk"] on an otherwise-flat entry returned []. Each case below
# now must produce a problem naming the entry and the broken shape.


def test_modes_value_that_is_not_a_dict_is_reported(themes):
    broken = _copy(themes)
    broken["Glass"]["modes"] = "oops"
    problems = validate(broken)
    assert any(
        "Glass" in p and "'modes'" in p and "dict" in p for p in problems
    )


def test_modes_value_that_is_a_list_on_an_otherwise_flat_entry_is_reported(themes):
    # "Glass Dark" is a flat entry -- it has no modes key in the real
    # document at all. Bolting a malformed one on is a different edge case
    # from mutating an existing Auto entry's modes block, and is exactly
    # what was confirmed broken by direct execution.
    broken = _copy(themes)
    broken["Glass Dark"]["modes"] = ["junk"]
    problems = validate(broken)
    assert any(
        "Glass Dark" in p and "'modes'" in p and "list" in p for p in problems
    )


def test_modes_payload_that_is_not_a_dict_is_reported(themes):
    broken = _copy(themes)
    broken["Glass"]["modes"]["light"] = "oops"
    problems = validate(broken)
    assert any(
        "Glass" in p and "modes.light" in p and "dict" in p for p in problems
    )


def test_modes_missing_light_key_entirely_is_reported(themes):
    broken = _copy(themes)
    del broken["Glass"]["modes"]["light"]
    problems = validate(broken)
    assert any(
        "Glass" in p and "modes" in p and "'light'" in p for p in problems
    )


def test_modes_missing_dark_key_entirely_is_reported(themes):
    broken = _copy(themes)
    del broken["Glass"]["modes"]["dark"]
    problems = validate(broken)
    assert any(
        "Glass" in p and "modes" in p and "'dark'" in p for p in problems
    )


def test_a_malformed_mode_payload_does_not_prevent_checking_the_other_mode(themes):
    # modes.light is broken; modes.dark is still a well-formed dict and
    # should still be walked/flattened normally rather than the whole entry
    # being abandoned once one malformed shape is found.
    broken = _copy(themes)
    broken["Glass"]["modes"]["light"] = "oops"
    broken["Glass"]["modes"]["dark"]["ha-card-background"] = "var(--nope-not-defined)"
    problems = validate(broken)
    assert any("nope-not-defined" in p for p in problems)


def test_flat_entry_with_no_modes_key_is_not_required_to_have_one(themes):
    # A flat entry (e.g. "Glass Dark" in the real document) legitimately has
    # no "modes" key at all -- that must not, by itself, be reported as a
    # missing 'light'/'dark' shape problem.
    assert "modes" not in themes["Glass Dark"]
    assert validate(themes) == []
