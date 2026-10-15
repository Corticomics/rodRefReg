"""main lets go of a run's QThread only once the thread has finished.

When a run ends, its QThread finishes in QThreadPrivate::finish: it emits
finished and deletes what was deleteLater'd on it, the worker and PyQt's slot
proxies, which needs the GIL. Qt 5 already reports isRunning() False there.
main.cleanup, on the GUI thread, used to drop main.thread as soon as
isRunning() was False. Dropping the last Python reference runs ~QThread, which
waits for that finish while the GUI thread holds the GIL: a deadlock. RRR froze
at the end of a run (the valves were already closed) and had to be killed.
run_program dropped a previous thread on the same check.

Each test runs the scenario in a process of its own, so a deadlock fails the
test within a timeout instead of hanging the suite.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PyQt5")

PROJECT = Path(__file__).resolve().parents[2]

# How long the call may take before the child dumps its stacks and exits 1.
# The call itself takes about half a second (the slowed finish below).
DEADLINE_S = 20
# The backstop: Python, the import of main and the deadline, on a slow runner.
CHILD_TIMEOUT_S = 120

_DROP_A_FINISHING_THREAD = """\
import faulthandler, sys, threading, time, weakref
from types import SimpleNamespace
project, call, deadline_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
sys.path.insert(0, project)
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtWidgets import QApplication
import main

app = QApplication([])
main.relay_handler = None
main.gui = None
main.worker = None
finishing = threading.Event()

def finish_slowly():
    # On the run's thread, inside QThreadPrivate::finish, where isRunning() is
    # already False. Like deleting the worker there, it needs the GIL: it
    # sleeps without it, then takes it back.
    finishing.set()
    time.sleep(0.5)

thread = QThread()
thread.finished.connect(finish_slowly, Qt.DirectConnection)
thread.start()
thread.quit()
if not finishing.wait(deadline_s):
    sys.exit("the thread did not start to finish")
print(f"finishing; isRunning() is {thread.isRunning()}", flush=True)
let_go = weakref.ref(thread)
main.thread = thread
del thread  # main.thread holds the only reference, as at the end of a run

faulthandler.dump_traceback_later(deadline_s, exit=True)  # a deadlock: its stacks, exit 1
if call == "cleanup":
    main.cleanup()
else:
    # Run pressed while the previous run's thread is finishing. The start
    # then fails (system_controller is not a QObject); the previous thread
    # is dropped before that.
    main.system_controller = SimpleNamespace(settings={})
    main.controller = SimpleNamespace(pump_controller=None)
    main.database_handler = None
    main.notification_handler = None
    schedule = SimpleNamespace(
        name="t", schedule_id=1, water_volume=0.6,
        relay_unit_assignments={}, desired_water_outputs={},
    )
    main.run_program(schedule, "Staggered", 0.0, 1.0)
faulthandler.cancel_dump_traceback_later()
print(f"{call} returned; the thread was let go: {let_go() is None}", flush=True)
"""


@pytest.mark.parametrize("call", ["cleanup", "run_program"])
def test_a_thread_that_is_still_finishing_is_waited_for_then_let_go(call, tmp_path):
    env = {**os.environ, "HOME": str(tmp_path), "QT_QPA_PLATFORM": "offscreen"}
    env.pop("RRR_HOME", None)  # no ~/rrr, no debug log outside tmp_path
    env.pop("RRR_DATA", None)
    # CI's Ubuntu job installs the requirements into the user site under the real
    # HOME; with HOME moved, the child must still import what this process imports.
    env["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)
    killed = None
    try:
        result = subprocess.run(
            [sys.executable, "-c", _DROP_A_FINISHING_THREAD, str(PROJECT), call, str(DEADLINE_S)],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=CHILD_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        killed = exc
    if killed is not None:
        # Bytes (or None) even with text=True: the child was killed mid-output.
        output = "".join(
            part.decode(errors="replace") if isinstance(part, bytes) else part
            for part in (killed.stdout or b"", killed.stderr or b"")
        )
        pytest.fail(f"the child did not exit within {CHILD_TIMEOUT_S} s (killed):\n{output}")

    lines = result.stdout.splitlines()
    assert "finishing; isRunning() is False" in lines, result.stdout + result.stderr
    assert f"{call} returned; the thread was let go: True" in lines, (
        f"main.{call}() did not return, or kept the thread, while it finished "
        f"(exit {result.returncode}); the child's stacks:\n{result.stderr}"
    )
