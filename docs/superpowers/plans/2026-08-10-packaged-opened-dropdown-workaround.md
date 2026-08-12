# Packaged Opened Dropdown Workaround Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Include the existing safe opened-dropdown frosted-fill module in every release archive alongside the generated theme.

**Architecture:** A dependency-free Python packaging script creates and validates a ZIP containing repository-relative `themes/` and `www/` paths. The release workflow delegates archive construction to that tested script, while the README documents extraction destinations and the still-required Home Assistant module registration.

**Tech Stack:** Python 3.11+, Python standard-library `zipfile`, pytest, GitHub Actions YAML, Home Assistant theme and frontend module configuration.

## Global Constraints

- Apply only to opened dropdown menus; closed fields, cards, dialogs, theme colors, and blur behavior remain unchanged.
- Package exactly `themes/glass.yaml` and `www/glass-dropdown.js` with repository-relative paths preserved.
- Continue using the existing fill-only module; do not add `backdrop-filter` or change module runtime behavior.
- Do not generate or modify Home Assistant configuration files.
- Module registration through `/local/glass-dropdown.js` under `frontend.extra_module_url` remains manual and optional.
- Add no runtime dependencies.

---

## File Structure

- Create `scripts/package_release.py`: construct and validate the release ZIP from an explicit file manifest.
- Create `tests/test_package_release.py`: verify exact archive paths, content, and missing-input failure behavior.
- Modify `.github/workflows/release.yml`: replace the flattening shell ZIP command with the tested packaging script.
- Modify `tests/test_package_release.py`: guard that the release workflow invokes the packaging script and no longer uses `zip -j`.
- Modify `README.md`: document release-archive extraction and required module registration.

### Task 1: Build and validate the release archive

**Files:**
- Create: `scripts/package_release.py`
- Create: `tests/test_package_release.py`

**Interfaces:**
- Consumes: existing files at `themes/glass.yaml` and `www/glass-dropdown.js`.
- Produces: `build_archive(output: Path, root: Path = ROOT) -> Path`, creating a ZIP whose entries are exactly `themes/glass.yaml` and `www/glass-dropdown.js`.
- Produces: CLI command `python scripts/package_release.py`, writing `dist/hass-glass-theme.zip`.

- [ ] **Step 1: Write failing archive-content tests**

Create `tests/test_package_release.py`:

```python
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.package_release import ARCHIVE_PATHS, ROOT, build_archive


def test_build_archive_preserves_required_paths_and_contents(tmp_path):
    output = tmp_path / "hass-glass-theme.zip"

    result = build_archive(output)

    assert result == output
    with ZipFile(output) as archive:
        assert tuple(archive.namelist()) == tuple(path.as_posix() for path in ARCHIVE_PATHS)
        for relative_path in ARCHIVE_PATHS:
            assert archive.read(relative_path.as_posix()) == (ROOT / relative_path).read_bytes()


def test_build_archive_fails_when_a_required_file_is_missing(tmp_path):
    root = tmp_path / "repository"
    (root / "themes").mkdir(parents=True)
    (root / "themes" / "glass.yaml").write_text("Glass: {}\n", encoding="utf-8")
    output = tmp_path / "hass-glass-theme.zip"

    with pytest.raises(FileNotFoundError, match="www/glass-dropdown.js"):
        build_archive(output, root=root)

    assert not output.exists()
```

- [ ] **Step 2: Run the focused tests and verify the missing-module failure**

Run:

```bash
python -m pytest tests/test_package_release.py -v
```

Expected: test collection fails with `ModuleNotFoundError: No module named 'scripts.package_release'`.

- [ ] **Step 3: Implement the minimal packaging script**

Create `scripts/package_release.py`:

```python
#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "hass-glass-theme.zip"
ARCHIVE_PATHS = (Path("themes/glass.yaml"), Path("www/glass-dropdown.js"))


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
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```bash
python -m pytest tests/test_package_release.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Exercise the packaging CLI and inspect its archive entries**

Run:

```bash
python scripts/package_release.py --output /tmp/hass-glass-theme.zip
python -c 'from zipfile import ZipFile; print("\n".join(ZipFile("/tmp/hass-glass-theme.zip").namelist()))'
```

Expected output:

```text
themes/glass.yaml
www/glass-dropdown.js
```

- [ ] **Step 6: Commit the packaging unit**

Only if commit authorization has been given:

```bash
git add scripts/package_release.py tests/test_package_release.py
git commit -m "build: package dropdown module with releases"
```

### Task 2: Route release publishing through the tested packager

**Files:**
- Modify: `.github/workflows/release.yml:27-30`
- Modify: `tests/test_package_release.py`

**Interfaces:**
- Consumes: `python scripts/package_release.py` from Task 1.
- Produces: `dist/hass-glass-theme.zip` for `softprops/action-gh-release` at `.github/workflows/release.yml:35`.

- [ ] **Step 1: Add a failing workflow wiring test**

Append to `tests/test_package_release.py`:

```python
def test_release_workflow_uses_the_tested_packager():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "python scripts/package_release.py" in workflow
    assert "zip -j" not in workflow
```

- [ ] **Step 2: Run the workflow test and verify it fails**

Run:

```bash
python -m pytest tests/test_package_release.py::test_release_workflow_uses_the_tested_packager -v
```

Expected: FAIL because `.github/workflows/release.yml` still contains `zip -j` and does not invoke the Python packager.

- [ ] **Step 3: Replace the flattening ZIP command**

Replace `.github/workflows/release.yml:27-30` with:

```yaml
      - name: Package the theme and optional modules
        run: python scripts/package_release.py
```

Keep the existing release upload path `dist/hass-glass-theme.zip` unchanged.

- [ ] **Step 4: Run the package and workflow tests**

Run:

```bash
python -m pytest tests/test_package_release.py -v
```

Expected: all three tests pass.

- [ ] **Step 5: Validate the workflow YAML**

Run the repository's pinned actionlint setup if `actionlint` is available:

```bash
./actionlint -color
```

Expected: exit code 0. If the binary is unavailable locally, rely on the identical pinned CI check in `.github/workflows/ci.yml:21-24` and report that limitation rather than downloading unrequested tooling.

- [ ] **Step 6: Commit the release workflow wiring**

Only if commit authorization has been given:

```bash
git add .github/workflows/release.yml tests/test_package_release.py
git commit -m "ci: preserve module paths in release archive"
```

### Task 3: Document release-archive installation

**Files:**
- Modify: `README.md:46-66`
- Modify: `README.md:127-166`

**Interfaces:**
- Consumes: archive paths `themes/glass.yaml` and `www/glass-dropdown.js` from Task 1.
- Produces: explicit manual-install and opened-menu module setup instructions.

- [ ] **Step 1: Add manual release-archive installation steps**

After the HACS installation list at `README.md:46-57`, add:

```markdown
For manual installation from a release archive:

1. Extract `themes/glass.yaml` to `<config>/themes/glass.yaml`.
2. Extract `www/glass-dropdown.js` to `<config>/www/glass-dropdown.js` if you want the optional opened-menu frosted fill described below.
3. Configure theme loading and the optional module as shown in the relevant sections, then restart Home Assistant.
```

- [ ] **Step 2: Clarify that releases now include the optional module**

Replace the opening sentence at `README.md:156` with:

```markdown
Release archives include the optional module at `www/glass-dropdown.js`. To enable the opened-menu fill workaround:
```

Replace step 1 of that list with:

```markdown
1. Copy the archive's `www/glass-dropdown.js` to `<config>/www/glass-dropdown.js` if it is not already there.
```

Keep the existing `frontend.extra_module_url`, restart, cache, fill-only, and known-bug guidance unchanged.

- [ ] **Step 3: Review the rendered Markdown structure**

Verify that list numbering and fenced YAML remain correctly nested around `README.md:46-66` and `README.md:156-166`.

Expected: the standard HACS path remains first; manual release extraction is clearly separate; `/local/glass-dropdown.js` registration is still mandatory for the workaround.

- [ ] **Step 4: Commit the installation documentation**

Only if commit authorization has been given:

```bash
git add README.md
git commit -m "docs: explain packaged dropdown module setup"
```

### Task 4: Run full repository verification

**Files:**
- Verify only; no planned modifications.

**Interfaces:**
- Consumes: all changes from Tasks 1-3.
- Produces: evidence that packaging, theme generation, JavaScript behavior, YAML, and Python tests remain valid.

- [ ] **Step 1: Check generated theme drift**

Run:

```bash
python scripts/build_themes.py --check
```

Expected: exit code 0 and `themes/glass.yaml is up to date (15 entries)`.

- [ ] **Step 2: Run the full Python test suite**

Run:

```bash
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Run the JavaScript module suite**

Run:

```bash
npm run test:js
```

Expected: all Node tests pass.

- [ ] **Step 4: Run YAML lint**

Run:

```bash
python -m yamllint -c .yamllint.yml tokens/ themes/ demo/ .github/
```

Expected: exit code 0.

- [ ] **Step 5: Build and inspect the final release archive**

Run:

```bash
python scripts/package_release.py
python -c 'from zipfile import ZipFile; archive = ZipFile("dist/hass-glass-theme.zip"); assert archive.namelist() == ["themes/glass.yaml", "www/glass-dropdown.js"]; print("\n".join(archive.namelist()))'
```

Expected output:

```text
themes/glass.yaml
www/glass-dropdown.js
```

- [ ] **Step 6: Inspect repository changes**

Run:

```bash
git status --short
git diff --check
git diff -- scripts/package_release.py tests/test_package_release.py .github/workflows/release.yml README.md
```

Expected: only intended files plus the approved design and plan documents are changed; `git diff --check` exits 0; no generated `dist/` artifact is staged or committed.

- [ ] **Step 7: Request code review**

Invoke `superpowers:requesting-code-review` and review the complete diff against `docs/superpowers/specs/2026-08-10-packaged-opened-dropdown-workaround-design.md`. Resolve any findings, then rerun the affected verification commands before claiming completion.
