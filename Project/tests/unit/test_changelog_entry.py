"""The release notes come from CHANGELOG.md.

The release workflow runs ``scripts/release/changelog_entry.py`` for the
tagged version and publishes its output as the GitHub Release notes, which
the in-app Updates tab shows. These tests pin the extraction, and one of
them is the gate that keeps the two files in step: while ``Project/version.py``
names a version with no entry, the suite fails, so a release-bound PR cannot
merge without its notes.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "release" / "changelog_entry.py"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
VERSION_FILE = REPO_ROOT / "Project" / "version.py"

if not SCRIPT.exists():  # the release bundle ships Project/ without the repo root
    pytest.skip("not running inside the repository", allow_module_level=True)

spec = importlib.util.spec_from_file_location("changelog_entry", SCRIPT)
changelog_entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(changelog_entry)

SAMPLE = """# Changelog

Newest first.

## 1.22.0 — something new

**Before you update**

- Do this first.

Details of 1.22.0.


## 1.21.0 — valve topology

- **1.21.0** — first line.
  continued.

## 1.20.x — older

- **1.20.1** — a fix.
"""


def _current_version() -> str:
    namespace: dict = {}
    exec(VERSION_FILE.read_text(encoding="utf-8"), namespace)
    return namespace["__version__"]


def test_the_entry_runs_from_its_heading_to_the_next_one():
    entry = changelog_entry.find_entry(SAMPLE, "1.21.0")
    assert entry == "## 1.21.0 — valve topology\n\n- **1.21.0** — first line.\n  continued.\n"


def test_the_newest_entry_keeps_its_body_and_drops_trailing_blank_lines():
    entry = changelog_entry.find_entry(SAMPLE, "1.22.0")
    assert entry.startswith("## 1.22.0 — something new\n\n**Before you update**")
    assert entry.endswith("Details of 1.22.0.\n")


def test_a_version_that_is_a_prefix_of_another_is_not_matched():
    # "## 1.2" must not match "## 1.21.0"; nor must "## 1.21.0" match 1.21.0-beta's absence.
    assert changelog_entry.find_entry(SAMPLE, "1.2") is None
    assert changelog_entry.find_entry(SAMPLE, "1.20.1") is None, "a range heading is not an entry"


def test_a_pre_release_falls_back_to_its_stable_entry():
    assert changelog_entry.candidate_versions("1.21.0-beta") == ["1.21.0-beta", "1.21.0"]
    assert changelog_entry.candidate_versions("v1.21.0") == ["1.21.0"]
    entry = changelog_entry.find_entry(SAMPLE, "1.21.0-beta.2")
    assert entry.startswith("## 1.21.0 — valve topology")
    own = SAMPLE.replace("## 1.22.0 — something new", "## 1.21.0-beta — the beta")
    assert changelog_entry.find_entry(own, "1.21.0-beta").startswith("## 1.21.0-beta — the beta")


def test_the_script_prints_the_entry_and_fails_for_a_missing_one(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(SAMPLE, encoding="utf-8")
    found = subprocess.run(
        [sys.executable, str(SCRIPT), "1.21.0", "--changelog", str(changelog)],
        capture_output=True,
        text=True,
    )
    assert found.returncode == 0, found.stderr
    assert found.stdout == "## 1.21.0 — valve topology\n\n- **1.21.0** — first line.\n  continued.\n"

    missing = subprocess.run(
        [sys.executable, str(SCRIPT), "9.9.9", "--changelog", str(changelog)],
        capture_output=True,
        text=True,
    )
    assert missing.returncode == 1
    assert missing.stdout == ""
    assert "no entry for 9.9.9" in missing.stderr and "step 4b" in missing.stderr


def test_changelog_has_an_entry_for_the_version_in_version_py():
    """The gate: a release-bound PR adds its CHANGELOG entry with the bump
    (MAINTENANCE.md section 3a, step 4b), or the suite fails here."""
    version = _current_version()
    entry = changelog_entry.find_entry(CHANGELOG.read_text(encoding="utf-8"), version)
    assert entry is not None, (
        f"CHANGELOG.md has no '## {version}' entry for the version in Project/version.py; "
        "add the release notes there (MAINTENANCE.md section 3a, step 4b)"
    )
    assert len(entry.splitlines()) > 2, "an entry needs a body, not just a heading"
