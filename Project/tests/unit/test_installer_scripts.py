"""The installer's shell helpers and the diagnostic script, run under bash 4+.

Found on a real Raspberry Pi (lab validation, 2026-10-06):

- ``install.sh --dry-run`` stopped right after its banner: a warning given
  before any section aborted the installer under ``set -e``.
- The install's own I2C scan never ran for a normal user (``i2cdetect`` is in
  /usr/sbin), so a relay HAT jumpered to the wrong stack level went unnoticed.
  The scan now names the stack level RRR cannot use.
- ``diagnose.sh`` looked for the Python environment where it was before the
  blue-green layout, so its import checks reported it missing on every device.
- The dry run left an empty ``vendor/`` folder in the checkout.
- The installer's self-test, ``scripts/install/test_install.sh``, called every
  dry run unfinished: it looked for a message the installer stopped printing in
  May 2026. It also failed on any Pi where RRR was installed, because it
  required the paths a real install writes to be absent.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
UI = REPO / "scripts" / "install" / "ui.sh"
LIB = REPO / "scripts" / "install" / "lib.sh"
DIAGNOSE = REPO / "scripts" / "runtime" / "diagnose.sh"
HARDWARE = REPO / "scripts" / "install" / "40-hardware.sh"
SELFTEST = REPO / "scripts" / "install" / "test_install.sh"

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
pytestmark = pytest.mark.skipif(
    BASH is None, reason="needs bash 4 or later, as the installer does"
)


def _run(script, env=None, cwd=REPO):
    return subprocess.run(
        [BASH, "-c", script],
        capture_output=True,
        text=True,
        cwd=cwd,
        env={**os.environ, **(env or {})},
    )


@pytest.fixture
def lib_env(tmp_path):
    """lib.sh also loads layout.sh, which looks the user up with getent;
    macOS has none, so give it one. layout.sh also reads USER, which a login
    shell always sets and CI's Debian container does not."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    getent = bin_dir / "getent"
    getent.write_text(f"#!/bin/sh\necho 'tester:x:1000:1000::{home}:/bin/bash'\n")
    getent.chmod(0o755)
    return {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(home),
        "USER": "tester",
    }


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


# --- the install's final check: which stack level the HAT answers at -----------------------------


def _fake_i2cdetect(tmp_path, grid, exit_code=0):
    fake = tmp_path / "i2cdetect"
    fake.write_text(f"#!/bin/sh\ncat <<'GRID'\n{grid}GRID\nexit {exit_code}\n")
    fake.chmod(0o755)
    return fake


@pytest.mark.parametrize(
    ("grid", "exit_code", "expect"),
    [
        (_grid(**{"20": _row(c7="27")}), 0, "ok relay HAT at stack level 0 (0x27)"),
        (_grid(**{"20": _row(c3="23")}), 0, "warn relay HAT found at stack level(s) 4, not 0"),
        (
            _grid(**{"20": _row(c3="23", c6="26")}),
            0,
            "warn relay HAT found at stack level(s) 1, 4, not 0",
        ),
        (_grid(), 0, "warn no relay HAT answers on I2C bus 1"),
        # A scan that fails must not abort the install: it reports no HAT.
        (_grid(**{"20": _row(c7="27")}), 3, "warn no relay HAT answers on I2C bus 1"),
    ],
)
def test_the_final_check_reports_the_hat_level_and_never_aborts(
    lib_env, tmp_path, grid, exit_code, expect
):
    fake = _fake_i2cdetect(tmp_path, grid, exit_code)
    script = (
        f'set -Eeuo pipefail; source "{LIB}"; '
        'sudo() { "$@"; }; '  # the installer's sudo, without a password prompt
        'verify() { echo "ok $1"; }; warn() { echo "warn $*"; }; '
        f'report_relay_hat_level "{fake}"; echo "still running"'
    )
    done = _run(script, env=lib_env)
    assert done.returncode == 0, done.stderr
    assert expect in done.stdout, done.stdout
    assert "still running" in done.stdout


def test_the_final_check_uses_i2cdetect_from_usr_sbin_when_not_on_path():
    """i2c-tools installs to /usr/sbin, which is not on a normal user's PATH."""
    text = (REPO / "scripts" / "install" / "60-verify.sh").read_text()
    assert "I2CDETECT=/usr/sbin/i2cdetect" in text
    assert 'report_relay_hat_level "$I2CDETECT"' in text


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


# --- the dry run changes nothing ------------------------------------------------------------------


def test_the_hardware_modules_dry_run_leaves_no_vendor_folder(lib_env, tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    script = (
        f'set -Eeuo pipefail; export DRY_RUN=1 REPO_ROOT="{checkout}"; source "{LIB}"; '
        f'boot_firmware_dir() {{ echo "{tmp_path}/boot"; }}; '  # a dev machine may have no /boot
        f'source "{HARDWARE}"; echo "module finished"'
    )
    done = _run(script, env={**lib_env, "RRR_PLAIN": "1"})
    assert done.returncode == 0, done.stderr
    assert "module finished" in done.stdout
    assert not (checkout / "vendor").exists()


# --- the self-test's end marker -------------------------------------------------------------------


def _self_test_end_marker():
    """The text test_install.sh takes as proof that the dry run reached its end."""
    line = next(ln for ln in SELFTEST.read_text().splitlines() if '"dry-run reached end"' in ln)
    return re.search(r"-e '([^']+)'", line).group(1)


@pytest.mark.parametrize(
    ("module", "finishes"),
    [("info 'module ran'\n", True), ("false\n", False)],
    ids=["finishes", "aborts"],
)
def test_the_end_marker_is_printed_only_when_the_installer_finishes(
    lib_env, tmp_path, module, finishes
):
    """The real install.sh and helpers, with one stand-in module."""
    copy = tmp_path / "repo"
    shutil.copytree(REPO / "scripts" / "install", copy / "scripts" / "install")
    for real_module in (copy / "scripts" / "install").glob("[0-9][0-9]-*.sh"):
        real_module.unlink()
    (copy / "scripts" / "install" / "10-only.sh").write_text(module)
    shutil.copy(REPO / "install.sh", copy)
    done = subprocess.run(
        [BASH, str(copy / "install.sh"), "--dry-run", "-y"],
        capture_output=True,
        text=True,
        env={**os.environ, **lib_env, "RRR_PLAIN": "1"},
    )
    output = done.stdout + done.stderr
    assert (done.returncode == 0) is finishes, output
    assert (_self_test_end_marker() in output) is finishes, output


# --- the self-test's no-change checks -------------------------------------------------------------


@pytest.fixture
def selftest(lib_env, tmp_path):
    """Runs the real test_install.sh in a repository whose install.sh is a stub
    with the given body. The release tree and venv it watches are under the
    stub user's home (layout.sh)."""
    repo = tmp_path / "repo"
    (repo / "scripts" / "install").mkdir(parents=True)
    (repo / "scripts" / "runtime").mkdir()
    for name in ("test_install.sh", "layout.sh"):
        shutil.copy(REPO / "scripts" / "install" / name, repo / "scripts" / "install")
    (repo / "scripts" / "runtime" / "launch.sh").write_text("#!/usr/bin/env bash\n")
    bin_dir = Path(lib_env["PATH"].split(os.pathsep)[0])
    (bin_dir / "bash").symlink_to(BASH)  # the self-test's bash -n and the stub's shebang
    shellcheck = bin_dir / "shellcheck"  # installed on some machines only: keep it out
    shellcheck.write_text("#!/bin/sh\nexit 0\n")
    shellcheck.chmod(0o755)
    home = Path(lib_env["HOME"])

    def run(install_body):
        stub = repo / "install.sh"
        stub.write_text('#!/usr/bin/env bash\n[[ "${1:-}" == --help ]] && exit 0\n' + install_body)
        stub.chmod(0o755)
        done = subprocess.run(
            [BASH, str(repo / "scripts" / "install" / "test_install.sh")],
            capture_output=True,
            text=True,
            env={**os.environ, **lib_env},
        )
        return done.returncode, re.sub(r"\x1b\[[0-9;]*m", "", done.stdout + done.stderr)

    run.repo, run.home = repo, home
    return run


def _finish():
    return f"echo '{_self_test_end_marker()}'\n"


def _install(run):
    """What a real install leaves: two releases, current, a venv, the vendor clone, a bundle."""
    rrr = run.home / "rrr"
    (rrr / "releases" / "0.9").mkdir(parents=True)
    (rrr / "releases" / "1.0" / "Project").mkdir(parents=True)
    (rrr / "releases" / "1.0" / "Project" / "main.py").write_text("print()\n")
    (rrr / "current").symlink_to(rrr / "releases" / "1.0")
    (rrr / "shared" / "venv" / "bin").mkdir(parents=True)
    (rrr / "shared" / "venv" / "bin" / "python3").write_text("#!/bin/sh\n")
    (rrr / "shared" / "venv" / "lib" / "pkg").mkdir(parents=True)
    (run.repo / "vendor" / "16relind-rpi").mkdir(parents=True)
    (run.repo / "vendor" / "16relind-rpi" / "Makefile").write_text("all:\n")
    (run.repo / "dist").mkdir()
    (run.repo / "dist" / "rrr-1.0.rrrupdate").write_text("bundle\n")
    return [
        rrr / "releases",
        rrr / "current",
        rrr / "shared" / "venv",
        run.repo / "vendor",
        run.repo / "dist",
    ]


def test_the_self_test_passes_a_clean_dry_run_on_a_fresh_pi(selftest):
    code, out = selftest(_finish())
    assert code == 0, out
    assert "PASS  dry-run reached end" in out
    assert f"PASS  {selftest.home}/rrr/shared/venv NOT created" in out
    assert f"PASS  {selftest.repo}/vendor NOT created" in out


def test_the_self_test_fails_a_dry_run_that_stopped_early(selftest):
    # The exit trap prints the summary on an abort too, so it proves nothing.
    code, out = selftest("echo '  install complete with warnings'\n")
    assert code == 1, out
    assert "FAIL  dry-run did not finish" in out


def test_the_self_test_fails_a_dry_run_that_creates_the_vendor_folder(selftest):
    code, out = selftest("mkdir vendor\n" + _finish())
    assert code == 1, out
    assert f"FAIL  {selftest.repo}/vendor was created during dry-run" in out


def test_the_self_test_passes_an_installed_pi_the_dry_run_left_alone(selftest):
    watched = _install(selftest)
    code, out = selftest(_finish())
    assert code == 0, out
    for path in watched:
        assert f"PASS  {path} unchanged (it was there before)" in out


# Each change a real install makes on an installed Pi, which a dry run must not.
# The pause keeps a rewrite off the clock tick of the self-test's mark; on a Pi
# the installer's first write comes seconds after it.
CHANGES = {
    "stages a release": ('mkdir "$HOME/rrr/releases/2.0"', "rrr/releases"),
    "repoints current": ('ln -sfn "$HOME/rrr/releases/0.9" "$HOME/rrr/current"', "rrr/current"),
    "rewrites the venv": (
        'sleep 0.1; echo x >"$HOME/rrr/shared/venv/bin/python3"',
        "rrr/shared/venv",
    ),
    "pulls the vendor clone": ("touch vendor/16relind-rpi/NEW", "vendor"),
    "rebuilds the bundle": ("sleep 0.1; echo x >dist/rrr-1.0.rrrupdate", "dist"),
}


@pytest.mark.parametrize(("change", "path"), CHANGES.values(), ids=CHANGES.keys())
def test_the_self_test_fails_a_dry_run_that_changes_an_installed_pi(selftest, change, path):
    _install(selftest)
    code, out = selftest(change + "\n" + _finish())
    assert code == 1, out
    base = selftest.home if path.startswith("rrr/") else selftest.repo
    assert f"FAIL  {base / path} was changed during dry-run" in out


def test_the_self_test_ignores_python_caches_in_the_venv(selftest):
    """The final check imports modules from the venv, which may write caches."""
    _install(selftest)
    cache = '"$HOME/rrr/shared/venv/lib/pkg/__pycache__"'
    code, out = selftest(f"sleep 0.1; mkdir -p {cache}; touch {cache}/x.pyc\n" + _finish())
    assert code == 0, out
    assert f"PASS  {selftest.home}/rrr/shared/venv unchanged (it was there before)" in out
