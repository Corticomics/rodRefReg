"""A launch that hands over to a running RRR is not a failed start.

``scripts/runtime/launch.sh`` adds one to ``state/boot.json``'s
``fail_count`` on every launch, and only a clean start (the GUI's healthy
mark, about 8 s in) sets it back to 0. At 2 the launcher rolls the device
back to the previous release. A launch that finds this release already
running hands it ``b'raise'`` and exits without starting, so nothing cleared
its count: two clicks on the RRR icon while RRR ran made the next start roll
back, and a third click rolled back at once and started the previous release
beside the running one (its single-instance key differs). main() now takes
the count back with ``updater.undo_launch_count()`` when it hands over.

Every test points ``RRR_HOME`` (and, for the launcher, ``HOME``) at a temp
directory, so a device's real ``~/rrr`` is never read or written.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PyQt5.QtCore")  # utils.updater imports it

PROJECT = Path(__file__).resolve().parents[2]
LAUNCH_SH = PROJECT.parent / "scripts" / "runtime" / "launch.sh"


@pytest.fixture
def updater(monkeypatch, tmp_path):
    """utils.updater with its blue-green home in ``tmp_path``."""
    monkeypatch.setenv("RRR_HOME", str(tmp_path))
    from utils import updater as module  # noqa: PLC0415

    return module


def _boot(tmp_path):
    return tmp_path / "state" / "boot.json"


def _write(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state) if isinstance(state, dict) else state)


@pytest.mark.parametrize("before, after", [(1, 0), (2, 1), (0, 0)])
def test_a_hand_over_takes_back_one_launch_and_never_goes_below_zero(
    updater, tmp_path, before, after
):
    version = updater.CURRENT_VERSION
    _write(_boot(tmp_path), {"release": version, "fail_count": before})

    updater.undo_launch_count()

    assert json.loads(_boot(tmp_path).read_text()) == {"release": version, "fail_count": after}


@pytest.mark.parametrize(
    "content",
    [
        '{"release": "0.0.1", "fail_count": 2}',  # another release's count
        "not json",
        '["release", 2]',
        '{"release": "VERSION", "fail_count": "many"}',
    ],
    ids=["other-release", "not-json", "not-an-object", "bad-count"],
)
def test_a_count_it_cannot_read_as_this_release_s_is_left_alone(updater, tmp_path, content):
    content = content.replace("VERSION", updater.CURRENT_VERSION)
    _write(_boot(tmp_path), content)

    updater.undo_launch_count()

    assert _boot(tmp_path).read_text() == content


def test_off_device_there_is_no_count_to_take_back(updater, monkeypatch, tmp_path):
    monkeypatch.delenv("RRR_HOME")

    updater.undo_launch_count()

    assert not (tmp_path / "state").exists()


def _launcher_works_here():
    if not (LAUNCH_SH.exists() and shutil.which("bash")):
        return False
    probe = subprocess.run(["readlink", "-f", "/"], capture_output=True, text=True)
    return probe.returncode == 0


@pytest.mark.skipif(not _launcher_works_here(), reason="needs bash, readlink -f and launch.sh")
def test_launches_that_hand_over_never_roll_the_release_back(tmp_path):
    """The real launch.sh, three times, each launch handing over as main() does."""
    from version import __version__ as version  # noqa: PLC0415

    home = tmp_path / "rrr"
    for release in ("0.0.1", version):  # the previous release, then the current one
        runtime = home / "releases" / release / "scripts" / "runtime"
        runtime.mkdir(parents=True)
        (home / "releases" / release / "Project").mkdir()
        shutil.copy(LAUNCH_SH, runtime / "launch.sh")
    (home / "current").symlink_to(home / "releases" / version)
    (home / "previous").symlink_to(home / "releases" / "0.0.1")
    boot = home / "state" / "boot.json"
    # RRR is running and healthy: it set the count back to 0 at its healthy mark.
    _write(boot, {"release": version, "fail_count": 0})

    # The release's interpreter: each launch finds RRR running and hands over.
    hand_over = tmp_path / "hand_over.py"
    hand_over.write_text(
        f"import sys\nsys.path.insert(0, {str(PROJECT)!r})\n"
        "from utils import updater\nupdater.undo_launch_count()\n"
    )
    venv_bin = home / "shared" / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python3").write_text(f'#!/bin/sh\nexec "{sys.executable}" "{hand_over}"\n')
    (venv_bin / "python3").chmod(0o755)
    # launch.sh reads boot.json with the python3 on PATH; make sure there is one.
    tools = tmp_path / "bin"
    tools.mkdir()
    (tools / "python3").symlink_to(sys.executable)
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "RRR_HOME": str(home),
        "PATH": f"{tools}{os.pathsep}{os.environ.get('PATH', '')}",
    }

    for launch in range(1, 4):
        result = subprocess.run(
            ["bash", str(home / "current" / "scripts" / "runtime" / "launch.sh")],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"launch {launch}: {result.stderr}"
        assert "rolling back" not in result.stderr, f"launch {launch} rolled back"
        assert json.loads(boot.read_text()) == {"release": version, "fail_count": 0}, (
            f"launch {launch} left a count towards the rollback"
        )
        assert Path(os.path.realpath(home / "current")) == (home / "releases" / version).resolve()
