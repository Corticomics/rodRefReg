"""utils.updater.restart_app: restarting RRR without the systemd service.

A restart after a valve topology change keeps the version, so the new
instance meets this instance's single-instance lock (keyed by version, see
main.py) if it starts while this one still runs: it hands over and exits,
and once this one quits no RRR is left running. The relaunch therefore
waits for this process to exit before it runs the launcher.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from utils import updater


def _fake_launcher(tmp_path):
    """A stand-in for ~/.local/bin/rrr that records when it was started."""
    started = tmp_path / "started"
    shim = tmp_path / "rrr"
    shim.write_text(
        f'#!/bin/sh\n"{sys.executable}" -c "import sys, time; '
        f"open(sys.argv[1], 'w').write(repr(time.time()))\" \"{started}\"\n"
    )
    shim.chmod(0o755)
    return shim, started


def test_the_relaunch_waits_for_the_old_process_to_exit(tmp_path):
    shim, started = _fake_launcher(tmp_path)
    old = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1.0)"])
    exited = {}

    def reap():  # the old RRR's parent reaps it, so kill -0 then fails
        old.wait()
        exited["at"] = time.time()

    reaper = threading.Thread(target=reap)
    reaper.start()
    t0 = time.time()
    subprocess.run(["sh", "-c", updater._relaunch_command(old.pid, str(shim))], timeout=30, check=True)
    reaper.join()

    launched_at = float(started.read_text())
    assert launched_at >= exited["at"], "the launcher ran only after the old process had exited"
    assert launched_at - t0 < 10


def test_the_relaunch_gives_up_waiting_and_starts_anyway(tmp_path):
    shim, started = _fake_launcher(tmp_path)
    t0 = time.time()
    # This test process never exits during the run: the wait must end.
    subprocess.run(
        ["sh", "-c", updater._relaunch_command(os.getpid(), str(shim), poll_s=0.1, max_wait_s=0.5)],
        timeout=30,
        check=True,
    )
    assert started.exists()
    assert time.time() - t0 < 5


@pytest.fixture
def no_systemd_service(monkeypatch):
    def run(cmd, **_kw):
        assert cmd[:2] == ["systemctl", "--user"]
        return SimpleNamespace(returncode=3)  # inactive

    monkeypatch.setattr(updater.subprocess, "run", run)


def test_without_the_service_it_relaunches_through_the_launcher_after_this_process(
    monkeypatch, tmp_path, no_systemd_service
):
    pytest.importorskip("PyQt5")
    from PyQt5.QtCore import QTimer  # noqa: PLC0415

    shim = tmp_path / ".local" / "bin" / "rrr"
    shim.parent.mkdir(parents=True)
    shim.write_text("#!/bin/sh\n")
    monkeypatch.setattr(updater.os.path, "expanduser", lambda p: p.replace("~", str(tmp_path)))
    spawned, scheduled = [], []
    monkeypatch.setattr(updater.subprocess, "Popen", lambda args, **kw: spawned.append((args, kw)))
    monkeypatch.setattr(QTimer, "singleShot", staticmethod(lambda ms, fn: scheduled.append(ms)))

    restarted, message = updater.restart_app()

    assert restarted is True and "Relaunching" in message
    ((args, kw),) = spawned
    assert args[:2] == ["sh", "-c"]
    assert f"kill -0 {os.getpid()}" in args[2], "waits for this process"
    assert f'exec "{shim}"' in args[2]
    assert kw.get("start_new_session") is True, "outlives this process"
    assert scheduled == [300], "then this instance quits"


def test_without_the_launcher_it_does_not_quit(monkeypatch, tmp_path, no_systemd_service):
    monkeypatch.setattr(updater.os.path, "expanduser", lambda p: p.replace("~", str(tmp_path)))
    monkeypatch.setattr(updater.subprocess, "Popen", lambda *a, **k: pytest.fail("nothing to launch"))

    restarted, message = updater.restart_app()

    assert restarted is False and "~/.local/bin/rrr" in message
