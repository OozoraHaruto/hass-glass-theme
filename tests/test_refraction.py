"""The compatibility refraction module and its coupling to token metadata.

Real refraction needs an ``feDisplacementMap``, and a ``backdrop-filter``
can only reach one through a *same-document* ``url(#id)`` fragment. Chromium
resolves nothing else: external ``.svg`` files and ``data:`` URIs are both
rejected (Blink bug 109212), and a rejected reference does not degrade to an
unfiltered chain -- per the Filter Effects spec it invalidates every function
in the chain, so the card loses its blur too.

A Home Assistant theme is a YAML variable map and card-mod injects CSS, so
neither can put a ``<filter>`` element in the document. This module is the
only piece that can, which is why it ships as a separate opt-in file rather
than as part of ``themes/glass.yaml``.

These are structural checks on shipped text rather than behavioural tests --
there is no browser or JS runner in this repo. They exist to catch the
failure that no Python test would otherwise see: the module and the tokens
drifting apart on the one string they must agree about.
"""

import re
from pathlib import Path

import pytest

from glassbuild.tokens import load_tokens

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "www" / "glass-refraction.js"


@pytest.fixture(scope="module")
def source() -> str:
    return MODULE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def refraction() -> dict:
    return load_tokens(ROOT)["materials"]["liquid-glass"]["material"]["refraction"]


def test_the_module_ships_in_the_repository():
    assert MODULE.is_file(), f"missing companion module: {MODULE}"


def test_the_module_defines_the_filter_id_the_tokens_reference(source, refraction):
    """The one string the theme and the module must agree on.

    Compatible older YAML emits ``url(#<filter_id>)`` and this module supplies
    the element it points at. The retained token metadata and module are edited
    in different files and languages, so the compatibility ID must stay aligned.
    """
    assert f'id="{refraction["filter_id"]}"' in source


def test_the_filter_actually_displaces(source):
    """Blur scatters light; displacement bends it. Only the latter is lensing.

    Without an ``feDisplacementMap`` this compatibility module would add no
    refraction to older Liquid Glass YAML.
    """
    assert "feDisplacementMap" in source


def test_the_filter_is_referenced_only_as_a_same_document_fragment(source):
    """Anything else silently kills the whole chain in Chromium.

    Checked against the module text because this is exactly the mistake that
    looks correct in review: ``url(/local/glass.svg#glass-refraction)`` is
    valid CSS, resolves in Firefox, and renders an unfiltered card in the one
    engine this feature targets.
    """
    for bad in ("url(data:", "url('data:", 'url("data:', ".svg#"):
        assert bad not in source, f"module references a filter via {bad!r}"


def test_the_module_holds_no_tuning_values_of_its_own(source):
    """Blur radius and luminance remap belong to tokens/, not to JavaScript.

    The module reassigns one CSS variable to another for compatible older YAML.
    If a real blur radius ever appears here, compatibility behavior gains a
    second source of truth and the retained token metadata is no longer
    authoritative.

    Matched with a digit required after the paren so the module stays free to
    *discuss* ``blur()`` in its comments -- which it must, since why CSS blur
    is not refraction is the entire reason the file exists. An unparameterised
    mention is documentation; ``blur(18px)`` is a second source of truth.
    """
    assert not re.search(r"blur\(\s*[\d.]", source)
    assert not re.search(r"saturate\(\s*[\d.]", source)


def test_the_module_checks_the_variable_before_overriding_anything(source):
    """It must no-op on Glass, Frosted Glass, and every non-theme page.

    The override points card backdrops at a compatibility filter. Applied when
    older YAML defines no source variable, it resolves to nothing and strips
    the card's backdrop-filter entirely.
    """
    assert "ha-glass-refraction-backdrop" in source


def test_the_module_takes_its_displacement_tuning_from_the_theme(source, refraction):
    """Same rule as the blur radius: tokens/ is authoritative, not JavaScript.

    ``scale`` and ``edge_fraction`` are tuning values like any other, so the
    module must read them rather than carry its own copy. A literal here that
    happens to match the token today is the failure mode -- it stays matching
    until someone retunes the token, and then diverges silently, because
    nothing renders differently enough to notice in review.
    """
    assert "--ha-glass-refraction-scale" in source
    assert "--ha-glass-refraction-edge" in source
    assert str(refraction["scale"]) not in source
    assert str(refraction["edge_fraction"]) not in source


def test_current_liquid_theme_does_not_activate_the_compatibility_module():
    from glassbuild.emit import build_themes

    entry = build_themes(ROOT)["Liquid Glass Dark"]
    assert "ha-glass-refraction-backdrop" not in entry
    assert "ha-glass-refraction-scale" not in entry
    assert "ha-glass-refraction-edge" not in entry
