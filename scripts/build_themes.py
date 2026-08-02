#!/usr/bin/env python3
"""Generate ``themes/glass.yaml`` from the token sources.

Usage:
    python scripts/build_themes.py            # write the file
    python scripts/build_themes.py --check    # fail if the committed file drifts
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from glassbuild.emit import build_themes  # noqa: E402
from glassbuild.validate import validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "themes" / "glass.yaml"

HEADER = """\
# GENERATED FILE -- DO NOT EDIT.
# Produced by scripts/build_themes.py from the token sources in tokens/.
# Edit the tokens and re-run the generator instead.
"""


def render(themes: dict) -> str:
    """Render the theme document as deterministic YAML text.

    ``sort_keys=False`` is deliberate: ``build_themes()`` returns entries in
    ``ENTRY_NAMES`` order (Glass, Glass Light, Glass Dark, ... Frosted Glass
    Dark Lite) so the Home Assistant theme picker lists them in that logical
    matrix order rather than alphabetically. Determinism still holds because
    ``build_themes()`` constructs its dicts deterministically from the token
    sources -- it does not depend on sorting to be reproducible.
    """
    body = yaml.safe_dump(
        themes,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=100,
    )
    return HEADER + body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed file matches the tokens; do not write",
    )
    args = parser.parse_args(argv)

    themes = build_themes(ROOT)

    problems = validate(themes)
    if problems:
        print("Theme validation failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    rendered = render(themes)

    if args.check:
        if not OUTPUT.is_file():
            print(f"{OUTPUT} does not exist; run the generator", file=sys.stderr)
            return 1
        current = OUTPUT.read_text(encoding="utf-8")
        if current != rendered:
            print(f"{OUTPUT} is out of date with tokens/:", file=sys.stderr)
            diff = difflib.unified_diff(
                current.splitlines(keepends=True),
                rendered.splitlines(keepends=True),
                fromfile="committed",
                tofile="generated",
            )
            sys.stderr.writelines(diff)
            return 1
        print(f"{OUTPUT} is up to date ({len(themes)} entries)")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(themes)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
