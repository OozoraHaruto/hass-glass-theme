from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.package_release import ARCHIVE_PATHS, ROOT, build_archive


def test_build_archive_preserves_required_paths_and_contents(tmp_path):
    output = tmp_path / "hass-glass-theme.zip"

    result = build_archive(output)

    assert result == output
    with ZipFile(output) as archive:
        assert tuple(archive.namelist()) == tuple(
            path.as_posix() for path in ARCHIVE_PATHS
        )
        for relative_path in ARCHIVE_PATHS:
            assert (
                archive.read(relative_path.as_posix())
                == (ROOT / relative_path).read_bytes()
            )


def test_build_archive_fails_when_a_required_file_is_missing(tmp_path):
    root = tmp_path / "repository"
    (root / "themes").mkdir(parents=True)
    (root / "themes" / "glass.yaml").write_text("Glass: {}\n", encoding="utf-8")
    output = tmp_path / "hass-glass-theme.zip"

    with pytest.raises(FileNotFoundError, match="www/glass-dropdown.js"):
        build_archive(output, root=root)

    assert not output.exists()


def test_release_workflow_uses_the_tested_packager():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "python scripts/package_release.py" in workflow
    assert "zip -j" not in workflow
