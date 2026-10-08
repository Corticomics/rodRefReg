"""A launch that hands over to a running RRR is not a failed start.

``scripts/runtime/launch.sh`` adds one to ``state/boot.json``'s
``fail_count`` for a launch, and only a clean start (the GUI's healthy mark,
about 8 s in) sets it back to 0. At 2 the launcher rolls the device back to
the previous release. A launch that finds this release already running hands
it ``b'raise'`` and exits without starting, so nothing cleared its count: two
clicks on the RRR icon while RRR ran made the next start roll back, and a
third click rolled back at once and started the previous release beside the
running one (its single-instance key differs).

launch.sh therefore does not count a launch when this release's
single-instance socket answers. Taking the count back in main() alone came
too late: main() looks only after main.py's imports, seconds on a Pi, so
quick launches stacked their counts. main() still takes back a count that
launch.sh did add (``RRR_LAUNCH_COUNTED=1``) when it hands over, which
happens when the running RRR was still starting as launch.sh looked.

Every test points ``RRR_HOME`` (and, for the launcher, ``HOME``) at a temp
directory, so a device's real ``~/rrr`` is never read or written, and the
launcher runs a release no real RRR runs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytest.importorskip("PyQt5.QtCore")  # utils.updater imports it

# Headless Qt: must be set before QApplication is constructed.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT = Path(__file__).resolve().parents[2]
LAUNCH_SH = PROJECT.parent / "scripts" / "runtime" / "launch.sh"


@pytest.fixture
def updater(monkeypatch, tmp_path):
    """utils.updater with its blue-green home in ``tmp_path``, run by a counted launch."""
    monkeypatch.setenv("RRR_HOME", str(tmp_path))
    monkeypatch.setenv("RRR_LAUNCH_COUNTED", "1")
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


def test_a_launch_the_launcher_did_not_count_takes_nothing_back(updater, monkeypatch, tmp_path):
    """The count left is a real failed start's (or another launch's): keep it."""
    monkeypatch.delenv("RRR_LAUNCH_COUNTED")
    version = updater.CURRENT_VERSION
    _write(_boot(tmp_path), {"release": version, "fail_count": 1})

    updater.undo_launch_count()

    assert json.loads(_boot(tmp_path).read_text()) == {"release": version, "fail_count": 1}


# ---- the real launch.sh -----------------------------------------------------


def _launcher_works_here():
    if not (LAUNCH_SH.exists() and shutil.which("bash")):
        return False
    probe = subprocess.run(["readlink", "-f", "/"], capture_output=True, text=True)
    return probe.returncode == 0


def _gnu_mv():
    probe = subprocess.run(["mv", "--version"], capture_output=True, text=True)
    return probe.returncode == 0 and "GNU" in probe.stdout


def _test_release():
    """A version no real RRR runs, so no running RRR answers its key."""
    return f"9.9.9-t{uuid.uuid4().hex[:8]}"


def _fake_rrr_home(tmp_path, version, app):
    """A blue-green ``~/rrr``: release ``version`` is current, 0.0.1 is previous.

    Both releases carry this checkout's launch.sh. ``app`` is the shell script
    that stands in for the venv's python3, so it runs where main.py would.
    Returns the home and the environment to launch with.
    """
    home = tmp_path / "rrr"
    for release in ("0.0.1", version):
        runtime = home / "releases" / release / "scripts" / "runtime"
        runtime.mkdir(parents=True)
        (home / "releases" / release / "Project").mkdir()
        shutil.copy(LAUNCH_SH, runtime / "launch.sh")
    (home / "current").symlink_to(home / "releases" / version)
    (home / "previous").symlink_to(home / "releases" / "0.0.1")
    venv_python = home / "shared" / "venv" / "bin" / "python3"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text(app)
    venv_python.chmod(0o755)
    # launch.sh reads boot.json and probes the socket with the python3 on PATH.
    tools = tmp_path / "bin"
    tools.mkdir()
    (tools / "python3").symlink_to(sys.executable)
    if not _gnu_mv():
        # A rollback runs GNU's `mv -T`. macOS's mv has no -T: rename the same way.
        (tools / "mv").write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "-T" ]; then\n'
            f'  exec "{sys.executable}" -c '
            '"import os, sys; os.replace(sys.argv[1], sys.argv[2])" "$2" "$3"\n'
            "fi\n"
            'exec /bin/mv "$@"\n'
        )
        (tools / "mv").chmod(0o755)
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "RRR_HOME": str(home),
        "PATH": f"{tools}{os.pathsep}{os.environ.get('PATH', '')}",
    }
    env.pop("RRR_LAUNCH_COUNTED", None)
    return home, env


def _launch(home, env):
    return subprocess.run(
        ["bash", str(home / "current" / "scripts" / "runtime" / "launch.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _boot_state(home):
    return json.loads((home / "state" / "boot.json").read_text())


def _current(home):
    return Path(os.path.realpath(home / "current")).name


# The app reports whether launch.sh told it that this launch was counted.
_REPORTS_THE_COUNT = 'echo "counted=${RRR_LAUNCH_COUNTED:-}"\n'


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


launcher = pytest.mark.skipif(
    not _launcher_works_here(), reason="needs bash, readlink -f and launch.sh"
)


@launcher
def test_a_launch_that_finds_this_release_running_is_not_counted(tmp_path, qapp):
    """launch.sh skips the sentinel when this release's key answers.

    main() reaches its own check only after its imports, seconds on a Pi, so
    taking the count back there came too late for launches that overlap: a
    third quick launch read 2 and rolled back beside the running RRR. Here
    the app takes nothing back, so only launch.sh can keep the count.

    The launch carries RRR_LAUNCH_COUNTED=1 the way a relaunch started by the
    running RRR does (it has its own launch's); the app must not see it.
    """
    from PyQt5.QtNetwork import QLocalServer  # noqa: PLC0415

    version = _test_release()
    home, env = _fake_rrr_home(tmp_path, version, "#!/bin/sh\n" + _REPORTS_THE_COUNT)
    _write(home / "state" / "boot.json", {"release": version, "fail_count": 0})
    env["RRR_LAUNCH_COUNTED"] = "1"
    running = QLocalServer()  # the running RRR, listening as main.py does
    key = f"rrr_single_instance_{version}"
    QLocalServer.removeServer(key)
    assert running.listen(key), running.errorString()
    try:
        for launch in range(1, 4):
            result = _launch(home, env)

            assert result.returncode == 0, f"launch {launch}: {result.stderr}"
            assert "rolling back" not in result.stderr, f"launch {launch} rolled back"
            assert _boot_state(home) == {"release": version, "fail_count": 0}, (
                f"launch {launch} counted although this release was running"
            )
            assert result.stdout == "counted=\n", (
                f"launch {launch} told the app it was counted: {result.stdout!r}"
            )
            assert _current(home) == version
    finally:
        running.close()


@launcher
def test_a_launch_counted_before_rrr_answered_is_taken_back_when_it_hands_over(tmp_path):
    """The running RRR was still starting when launch.sh looked, so it counted.

    The app then finds that RRR and hands over, as main() does, taking its
    count back. Three such launches never roll the release back.
    """
    version = _test_release()
    hand_over = tmp_path / "hand_over.py"
    hand_over.write_text(
        f"import sys\nsys.path.insert(0, {str(PROJECT)!r})\n"
        "from utils import updater\n"
        f"updater.CURRENT_VERSION = {version!r}  # the release this launch runs\n"
        "updater.undo_launch_count()\n"
    )
    home, env = _fake_rrr_home(
        tmp_path, version, f'#!/bin/sh\nexec "{sys.executable}" "{hand_over}"\n'
    )
    # RRR is running and healthy: it set the count back to 0 at its healthy mark.
    _write(home / "state" / "boot.json", {"release": version, "fail_count": 0})

    for launch in range(1, 4):
        result = _launch(home, env)

        assert result.returncode == 0, f"launch {launch}: {result.stderr}"
        assert "rolling back" not in result.stderr, f"launch {launch} rolled back"
        assert _boot_state(home) == {"release": version, "fail_count": 0}, (
            f"launch {launch} left a count towards the rollback"
        )
        assert _current(home) == version


@launcher
def test_a_release_that_fails_to_start_is_still_rolled_back(tmp_path):
    """Nothing answers the release's key: every launch counts, as before."""
    version = _test_release()
    home, env = _fake_rrr_home(tmp_path, version, "#!/bin/sh\n" + _REPORTS_THE_COUNT + "exit 1\n")
    _write(home / "state" / "boot.json", {"release": version, "fail_count": 0})

    for launch, count in ((1, 1), (2, 2)):
        result = _launch(home, env)

        assert result.stdout == "counted=1\n", f"launch {launch}: {result.stdout!r}"
        assert _boot_state(home) == {"release": version, "fail_count": count}
        assert _current(home) == version

    result = _launch(home, env)

    assert f"release {version} failed to start twice" in result.stderr, result.stderr
    assert _current(home) == "0.0.1"
    # The previous release's launch.sh then counted its own start.
    assert _boot_state(home) == {"release": "0.0.1", "fail_count": 1}
    assert result.stdout == "counted=1\n"
