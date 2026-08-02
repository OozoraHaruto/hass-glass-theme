import subprocess
import sys
from pathlib import Path

import yaml

from glassbuild.emit import ENTRY_NAMES, build_themes

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_themes.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_check_passes_against_the_committed_file():
    result = _run("--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_render_is_deterministic():
    from scripts.build_themes import render

    assert render(build_themes(ROOT)) == render(build_themes(ROOT))


def test_committed_file_parses_and_has_twelve_entries():
    document = yaml.safe_load((ROOT / "themes" / "glass.yaml").read_text())
    assert set(document) == set(ENTRY_NAMES)


def test_committed_file_entry_order_matches_entry_names():
    # sort_keys=False is deliberate (see render()): ENTRY_NAMES order must
    # survive into the emitted YAML so the HA theme picker lists entries in
    # the logical matrix order rather than alphabetically.
    document = yaml.safe_load((ROOT / "themes" / "glass.yaml").read_text())
    assert list(document) == list(ENTRY_NAMES)


def test_check_fails_when_the_file_drifts(tmp_path):
    target = ROOT / "themes" / "glass.yaml"
    original = target.read_text()
    try:
        target.write_text(original + "\nGlass Drifted:\n  primary-color: '#000000'\n")
        assert _run("--check").returncode == 1
    finally:
        target.write_text(original)
