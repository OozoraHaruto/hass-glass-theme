#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "hass-glass-theme.zip"
ARCHIVE_PATHS = (
    Path("themes/glass.yaml"),
    Path("www/glass-dropdown.js"),
    Path("www/glass-refraction.js"),
)


def build_archive(output: Path, root: Path = ROOT) -> Path:
    missing = [path for path in ARCHIVE_PATHS if not (root / path).is_file()]
    if missing:
        joined = ", ".join(path.as_posix() for path in missing)
        raise FileNotFoundError(f"missing release files: {joined}")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    temporary.unlink(missing_ok=True)

    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
            for relative_path in ARCHIVE_PATHS:
                archive.write(root / relative_path, relative_path.as_posix())

        with ZipFile(temporary) as archive:
            actual = tuple(archive.namelist())
        expected = tuple(path.as_posix() for path in ARCHIVE_PATHS)
        if actual != expected:
            raise RuntimeError(f"release archive entries differ: {actual!r}")

        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = build_archive(args.output)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
