"""The generated file must match what Home Assistant's theme loader accepts."""

from pathlib import Path

import pytest
import yaml

from glassbuild.emit import ENTRY_NAMES

ROOT = Path(__file__).resolve().parents[1]
THEME_FILE = ROOT / "themes" / "glass.yaml"


@pytest.fixture(scope="module")
def document():
    return yaml.safe_load(THEME_FILE.read_text())


def test_file_parses(document):
    assert isinstance(document, dict)


def test_exactly_the_twelve_entries(document):
    assert set(document) == set(ENTRY_NAMES)


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_entry_is_flat_apart_from_modes(document, name):
    for key, value in document[name].items():
        assert isinstance(key, str)
        if key == "modes":
            assert set(value) == {"light", "dark"}
            for payload in value.values():
                for mode_key, mode_value in payload.items():
                    assert isinstance(mode_key, str)
                    assert isinstance(mode_value, str)
        else:
            assert isinstance(value, str), f"{name}.{key} is {type(value).__name__}"


@pytest.mark.parametrize("name", ENTRY_NAMES)
def test_no_key_carries_the_css_prefix(document, name):
    assert not [k for k in document[name] if k.startswith("--")]


def test_generated_header_is_present():
    assert THEME_FILE.read_text().startswith("# GENERATED FILE")
