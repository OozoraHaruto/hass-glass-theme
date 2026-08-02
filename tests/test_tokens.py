import pytest

from glassbuild.tokens import MATERIALS, MODES, load_tokens, merge


def test_material_and_mode_names():
    assert MATERIALS == ("glass", "frosted-glass")
    assert MODES == ("light", "dark")


def test_merge_later_sources_win():
    result = merge({"a": 1, "b": 2}, {"b": 3}, {"a": 4})
    assert result == {"a": 4, "b": 3}


def test_merge_is_recursive():
    result = merge({"m": {"x": 1, "y": 2}}, {"m": {"y": 3}}, {})
    assert result == {"m": {"x": 1, "y": 3}}


def test_merge_does_not_mutate_inputs():
    base = {"m": {"x": 1}}
    merge(base, {"m": {"x": 2}}, {})
    assert base == {"m": {"x": 1}}


def test_load_tokens_reads_every_file(tmp_path):
    (tmp_path / "tokens" / "modes").mkdir(parents=True)
    (tmp_path / "tokens" / "base.yaml").write_text("radius: 18px\n")
    (tmp_path / "tokens" / "glass.yaml").write_text("blur: 8px\n")
    (tmp_path / "tokens" / "frosted-glass.yaml").write_text("blur: 40px\n")
    (tmp_path / "tokens" / "modes" / "light.yaml").write_text("bg: white\n")
    (tmp_path / "tokens" / "modes" / "dark.yaml").write_text("bg: black\n")

    tokens = load_tokens(tmp_path)

    assert tokens["base"] == {"radius": "18px"}
    assert tokens["materials"]["glass"] == {"blur": "8px"}
    assert tokens["materials"]["frosted-glass"] == {"blur": "40px"}
    assert tokens["modes"]["light"] == {"bg": "white"}
    assert tokens["modes"]["dark"] == {"bg": "black"}


def test_load_tokens_reports_a_missing_file(tmp_path):
    (tmp_path / "tokens").mkdir()
    (tmp_path / "tokens" / "base.yaml").write_text("radius: 18px\n")
    with pytest.raises(FileNotFoundError):
        load_tokens(tmp_path)
