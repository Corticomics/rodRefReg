"""The installer's shell helpers and the diagnostic script, run under bash 4+.

Found on a real Raspberry Pi (lab validation, 2026-10-06):

- ``install.sh --dry-run`` stopped right after its banner: a warning given
  before any section aborted the installer under ``set -e``.
- The install's own I2C scan never ran for a normal user (``i2cdetect`` is in
  /usr/sbin), so a relay HAT jumpered to the wrong stack level went unnoticed.
  The scan now names the stack level RRR cannot use.
- ``diagnose.sh`` looked for the Python environment where it was before the
  blue-green layout, so its import checks reported it missing on every device.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
UI = REPO / "scripts" / "install" / "ui.sh"
LIB = REPO / "scripts" / "install" / "lib.sh"
DIAGNOSE = REPO / "scripts" / "runtime" / "diagnose.sh"

if not UI.exists():  # the release bundle ships scripts/, but check anyway
    pytest.skip("not running inside the repository", allow_module_level=True)


def _bash4():
    """A bash of version 4 or later, as the installer requires; macOS ships 3.2."""
    for candidate in (shutil.which("bash"), "/opt/homebrew/bin/bash", "/usr/local/bin/bash"):
        if not candidate or not Path(candidate).exists():
            continue
        probe = subprocess.run(
            [candidate, "-c", "echo ${BASH_VERSINFO[0]}"], capture_output=True, text=True
        )
        if probe.returncode == 0 and probe.stdout.strip().isdigit() and int(probe.stdout) >= 4:
            return candidate
    return None


BASH = _bash4()
pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash 4 or later, as the installer does")


def _run(script, env=None, cwd=REPO):
    return subprocess.run(
        [BASH, "-c", script], capture_output=True, text=True, cwd=cwd, env={**os.environ, **(env or {})}
    )


@pytest.fixture
def lib_env(tmp_path):
    """lib.sh also loads layout.sh, which looks the user up with getent;
    macOS has none, so give it one."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    getent = bin_dir / "getent"
    getent.write_text(f"#!/bin/sh\necho 'tester:x:1000:1000::{home}:/bin/bash'\n")
    getent.chmod(0o755)
    return {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "HOME": str(home)}


# --- a warning before any section ------------------------------------------------------------


def test_a_warning_before_any_section_does_not_abort_the_installer():
    done = _run(
        f'set -Eeuo pipefail; source "{UI}"; ui_warn "DRY-RUN mode"; echo survived; '
        'printf "warn=%s\\n" "${_UI_WARNS[@]}"'
    )
    assert done.returncode == 0, done.stderr
    assert "survived" in done.stdout
    assert "warn=DRY-RUN mode" in done.stdout, "recorded, with no section in front"


def test_a_warning_inside_a_section_is_still_tagged_with_it():
    done = _run(
        f'set -Eeuo pipefail; source "{UI}"; section "10-apt"; ui_warn "slow mirror"; '
        'printf "warn=%s\\n" "${_UI_WARNS[@]}"'
    )
    assert done.returncode == 0, done.stderr
    assert "warn=10-apt: slow mirror" in done.stdout


# --- the relay HAT's stack level from i2cdetect ------------------------------------------------

HEADER = "     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f"
EMPTY_ROW = " ".join(["--"] * 16)


def _grid(**rows):
    """i2cdetect -y 1 output with the given rows ("20" -> its 16 cells)."""
    lines = [HEADER, "00:                         -- -- -- -- -- -- -- -- "]
    for row in ("10", "20", "30", "40", "50", "60"):
        lines.append(f"{row}: {rows.get(row, EMPTY_ROW)}")
    lines.append("70: -- -- -- -- -- -- -- --                         ")
    return "\n".join(lines) + "\n"


def _row(**cells):
    """A row of 16 cells; keyword c3="23" puts "23" in column 3."""
    return " ".join(cells.get(f"c{i:x}", "--") for i in range(16))


@pytest.mark.parametrize(
    ("grid", "levels"),
    [
        # The lab rig on 2026-10-06: one HAT jumpered to stack level 4.
        (_grid(**{"20": _row(c3="23")}), ["4"]),
        (_grid(**{"20": _row(c7="27")}), ["0"]),
        (_grid(**{"20": _row(c6="26", c7="27")}), ["0", "1"]),
        (_grid(), []),
        # Other devices, and an address a kernel driver holds ("UU"), are not HATs.
        (_grid(**{"20": _row(c4="UU", c7="27"), "50": _row(c0="50"), "30": _row(c8="38")}), ["0"]),
    ],
)
def test_relay_hat_levels_reads_the_stack_level_from_i2cdetect(lib_env, grid, levels):
    done = subprocess.run(
        [BASH, "-c", f'set -Eeuo pipefail; source "{LIB}"; relay_hat_levels'],
        input=grid,
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, **lib_env},
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == levels


# --- diagnose.sh finds the Python environment ----------------------------------------------------


def _stub_python(path, version):
    path.parent.mkdir(parents=True)
    path.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "--version" ]; then echo "{version}"; else cat >/dev/null; echo "  ok   stub"; fi\n'
    )
    path.chmod(0o755)


def test_diagnose_uses_the_installed_venv(tmp_path):
    home = tmp_path / "home"
    _stub_python(home / "rrr" / "shared" / "venv" / "bin" / "python3", "Python 3.11.2 (installed)")
    done = subprocess.run(
        [BASH, str(DIAGNOSE)],
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home), "RRR_REPO": str(tmp_path / "no-clone")},
    )
    assert done.returncode == 0, done.stderr
    assert "Python 3.11.2 (installed)" in done.stdout
    assert "venv python missing" not in done.stdout


def test_diagnose_falls_back_to_a_developer_clone(tmp_path):
    clone = tmp_path / "clone"
    _stub_python(clone / ".venv" / "bin" / "python3", "Python 3.12.6 (clone)")
    done = subprocess.run(
        [BASH, str(DIAGNOSE)],
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(tmp_path / "empty-home"), "RRR_REPO": str(clone)},
    )
    assert done.returncode == 0, done.stderr
    assert "Python 3.12.6 (clone)" in done.stdout
