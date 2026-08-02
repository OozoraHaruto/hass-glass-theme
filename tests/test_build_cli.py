import os
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


# Inline script executed in a fresh subprocess so PYTHONHASHSEED can be
# forced to a specific value per run. Calling render() twice in one process
# (as test_render_is_deterministic does) can never observe hash-seed-driven
# ordering flake, because a single process only ever has one hash seed.
_HASH_SEED_PROBE = """
import sys
sys.path.insert(0, {root!r})
from pathlib import Path
from glassbuild.emit import build_themes
from scripts.build_themes import render
sys.stdout.write(render(build_themes(Path({root!r}))))
"""


def test_render_is_deterministic_across_process_hash_seeds():
    code = _HASH_SEED_PROBE.format(root=str(ROOT))
    outputs = []
    for seed in ("0", "1", "2", "3"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, result.stderr
        outputs.append(result.stdout)
    assert len(set(outputs)) == 1, "render() output differs across PYTHONHASHSEED values"


def test_committed_file_parses_and_has_every_entry():
    document = yaml.safe_load((ROOT / "themes" / "glass.yaml").read_text(encoding="utf-8"))
    assert set(document) == set(ENTRY_NAMES)
    assert len(document) == len(ENTRY_NAMES) == 15


def test_committed_file_entry_order_matches_entry_names():
    # sort_keys=False is deliberate (see render()): ENTRY_NAMES order must
    # survive into the emitted YAML so the HA theme picker lists entries in
    # the logical matrix order rather than alphabetically.
    document = yaml.safe_load((ROOT / "themes" / "glass.yaml").read_text(encoding="utf-8"))
    assert list(document) == list(ENTRY_NAMES)


def test_render_includes_the_generated_file_header():
    from scripts.build_themes import HEADER, render

    assert render(build_themes(ROOT)).startswith(HEADER)


def test_committed_file_starts_with_the_generated_file_header():
    text = (ROOT / "themes" / "glass.yaml").read_text(encoding="utf-8")
    assert text.startswith("# GENERATED FILE -- DO NOT EDIT.")


def test_check_fails_when_the_file_drifts(monkeypatch, tmp_path):
    # Exercises --check's comparison logic against a throwaway copy rather
    # than the real committed themes/glass.yaml: a hard kill mid-test must
    # never leave the shippable artifact corrupted.
    import scripts.build_themes as build_themes_module

    copy = tmp_path / "glass.yaml"
    copy.write_text(
        build_themes_module.render(build_themes(ROOT)) + "\nGlass Drifted:\n  primary-color: '#000000'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build_themes_module, "OUTPUT", copy)

    assert build_themes_module.main(["--check"]) == 1


def test_validation_failure_blocks_the_write(monkeypatch):
    # If validate() ever moved below the write (or were skipped), an invalid
    # document could reach disk -- this is the constraint that stops a
    # broken theme from shipping. Mocking build_themes() (not validate()
    # itself) to return a genuinely invalid document -- missing 11 of 12
    # required entries and carrying a dangling var() reference -- means the
    # real validate() does the flagging, and a premature write would leave
    # visibly different (corrupted) bytes on disk, not just a duplicate of
    # the valid content. That makes the byte-identity assertion below
    # actually load-bearing, rather than trivially true regardless of
    # write/validate ordering.
    import scripts.build_themes as build_themes_module

    target = ROOT / "themes" / "glass.yaml"
    original_bytes = target.read_bytes()

    monkeypatch.setattr(
        build_themes_module,
        "build_themes",
        lambda root: {"Bogus Entry": {"primary-color": "var(--totally-undefined)"}},
    )

    try:
        result = build_themes_module.main([])
        assert result == 1
        assert target.read_bytes() == original_bytes
    finally:
        # Defensive: even though a correct implementation never reaches the
        # write when validation fails, guarantee the committed file is
        # untouched regardless.
        if target.read_bytes() != original_bytes:
            target.write_bytes(original_bytes)
