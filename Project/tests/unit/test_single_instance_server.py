"""A running RRR keeps answering its single-instance key for the whole run.

main() probes ``rrr_single_instance_<version>`` before it starts anything:
when a running RRR answers, the new copy sends ``b'raise'`` and exits instead
of starting a second RRR on the same relays. The no-splash start-up (the one
RRR uses) kept its QLocalServer in a local variable referenced only by its own
slot. That reference cycle is collectable: the first garbage collection after
start-up deleted the server and its socket, and a later launch then ran
beside the first.

The server also stops listening when RRR quits, so a launch during a slow
shutdown starts a new RRR instead of handing over to one that is exiting, and
it replaces a socket file left behind by an RRR that was killed.

Each test listens on a key of its own and removes it afterwards, so a running
RRR on the same machine is never touched.
"""

from __future__ import annotations

import ast
import gc
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

# Headless Qt: must be set before QApplication is constructed.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QDir  # noqa: E402
from PyQt5.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

MAIN_PY = Path(__file__).resolve().parents[2] / "main.py"


class _Window:
    """Stands in for the main window: records what the server asks of it."""

    def __init__(self):
        self.calls = []

    def show(self):
        self.calls.append("show")

    def raise_(self):
        self.calls.append("raise_")

    def activateWindow(self):
        self.calls.append("activateWindow")

    def system_message_signal(self, text):
        pass


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dbg_lines():
    """What main writes to its debug log during the test."""
    return []


@pytest.fixture
def main(monkeypatch, dbg_lines):
    """The main module, logging to ``dbg_lines``, with no server kept yet."""
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # main installs its own on import
    import main as module  # noqa: PLC0415

    monkeypatch.setattr(module, "_dbg", dbg_lines.append)
    monkeypatch.setattr(module, "_single_instance_server", None)
    yield module
    if module._single_instance_server is not None:
        module._single_instance_server.close()


@pytest.fixture
def key(main):
    """A key no running RRR uses; its socket is removed after the test."""
    name = f"rrr_t_si_{uuid.uuid4().hex[:12]}"
    yield name
    QLocalServer.removeServer(name)


@pytest.fixture
def quits(main, monkeypatch):
    """Records SafeQApplication.instance().quit() instead of quitting."""
    calls = []
    app = SimpleNamespace(quit=lambda: calls.append("quit"))
    monkeypatch.setattr(main.SafeQApplication, "instance", staticmethod(lambda: app))
    return calls


def _connect(key, message=None):
    """Connect to ``key`` as a second launch does; None when nothing answers."""
    sock = QLocalSocket()
    sock.connectToServer(key)
    if not sock.waitForConnected(1000):
        return None
    if message:
        sock.write(message)
        sock.flush()
        sock.waitForBytesWritten(1000)
    return sock


def _process_events_until(qapp, done, timeout=3.0):
    deadline = time.monotonic() + timeout
    while not done() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)


def test_the_server_still_answers_after_a_garbage_collection(main, key, qapp):
    main._start_single_instance_server(key, _Window())  # the test keeps no reference
    gc.collect()
    qapp.processEvents()

    client = _connect(key)
    assert client is not None, "the single-instance server was garbage-collected"
    client.abort()


def test_quit_makes_rrr_exit(main, key, qapp, quits, dbg_lines):
    window = _Window()
    main._start_single_instance_server(key, window)

    client = _connect(key, b"quit")
    assert client is not None
    _process_events_until(qapp, lambda: quits)

    assert quits == ["quit"]
    assert window.calls == []
    assert "received 'quit' from peer; exiting" in dbg_lines


@pytest.mark.parametrize("message", [b"raise", b"hello", None], ids=["raise", "other", "nothing"])
def test_any_other_message_brings_the_window_forward(main, key, qapp, quits, message):
    window = _Window()
    main._start_single_instance_server(key, window)

    client = _connect(key, message)
    assert client is not None
    _process_events_until(qapp, lambda: window.calls)

    assert window.calls == ["show", "raise_", "activateWindow"]
    assert quits == []


def test_a_key_it_cannot_listen_on_is_logged_and_start_up_carries_on(
    main, qapp, dbg_lines, tmp_path
):
    unusable = str(tmp_path / "no-such-folder" / "rrr")
    server = main._start_single_instance_server(unusable, _Window())

    assert not server.isListening()
    assert main._single_instance_server is server
    assert any(line.startswith("single-instance server could not listen") for line in dbg_lines)


_LISTEN_THEN_WAIT = """\
import sys, time
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtNetwork import QLocalServer
app = QCoreApplication([])
server = QLocalServer()
assert server.listen(sys.argv[1]), server.errorString()
print("listening", flush=True)
time.sleep(60)
"""


def test_a_socket_left_by_a_killed_rrr_does_not_stop_the_next_one(main, key, qapp):
    """A crash or kill -9 leaves the socket file behind; the next RRR replaces it.

    Without that, listen() fails with 'Address in use' and the next RRR runs
    with no single-instance guard at all.
    """
    with subprocess.Popen(
        [sys.executable, "-c", _LISTEN_THEN_WAIT, key], stdout=subprocess.PIPE, text=True
    ) as killed:
        try:
            assert killed.stdout.readline().strip() == "listening"
        finally:
            killed.kill()  # SIGKILL: no clean-up runs, so the socket file stays
            killed.wait(10)
    assert os.path.exists(os.path.join(QDir.tempPath(), key)), "no stale socket to replace"

    server = main._start_single_instance_server(key, _Window())

    assert server.isListening(), server.errorString()
    client = _connect(key)
    assert client is not None, "a second launch would not find this RRR"
    client.abort()


_QUIT_THEN_LAUNCH = """\
import sys
project, key = sys.argv[1], sys.argv[2]
sys.path.insert(0, project)
from PyQt5.QtCore import QTimer
from PyQt5.QtNetwork import QLocalSocket
from PyQt5.QtWidgets import QApplication
import main
main._dbg = lambda message: None
app = QApplication([])
class Window:
    def show(self): pass
    def raise_(self): pass
    def activateWindow(self): pass
server = main._start_single_instance_server(key, Window())
QTimer.singleShot(0, app.quit)
app.exec_()
# RRR has quit, but its process is still shutting down. A launch now:
launch = QLocalSocket()
launch.connectToServer(key)
print("answered" if launch.waitForConnected(1000) else "not answered", flush=True)
"""


def test_rrr_stops_answering_once_it_quits(key, tmp_path):
    """A launch during a slow shutdown must not hand over to an RRR that is exiting.

    It would exit too, and no RRR would come back. This runs in a process of
    its own, whose QApplication really quits, as RRR's does.
    """
    env = {**os.environ, "HOME": str(tmp_path), "QT_QPA_PLATFORM": "offscreen"}
    env.pop("RRR_HOME", None)  # no ~/rrr, no debug log outside tmp_path
    env.pop("RRR_DATA", None)
    result = subprocess.run(
        [sys.executable, "-c", _QUIT_THEN_LAUNCH, str(MAIN_PY.parent), key],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    # Importing main may print hardware warnings first; the probe's answer is last.
    assert result.stdout.splitlines()[-1:] == ["not answered"], "RRR still answered after it quit"


def test_the_no_splash_start_up_still_answers_after_a_garbage_collection(
    main, key, qapp, monkeypatch
):
    """The start-up RRR runs (USE_SPLASH_SCREEN is False), end to end."""
    monkeypatch.setattr(main, "setup", lambda: None)
    monkeypatch.setattr(main, "gui", _Window(), raising=False)
    # No settings: the theme step is skipped, so the shared QApplication keeps its style.
    monkeypatch.setattr(main, "system_controller", None, raising=False)
    monkeypatch.setitem(
        sys.modules,
        "ui.update_notifier",
        SimpleNamespace(UpdateNotifier=SimpleNamespace(check_for_updates=lambda gui: None)),
    )
    # The start-up redirects stdout and stderr to the System Messages panel.
    monkeypatch.setattr(sys, "stdout", sys.stdout)
    monkeypatch.setattr(sys, "stderr", sys.stderr)

    main._main_without_splash(qapp, key)
    gc.collect()
    qapp.processEvents()

    client = _connect(key)
    assert client is not None, "the no-splash start-up lost its single-instance server"
    client.abort()


def test_a_second_launch_brings_rrr_forward_and_takes_back_its_launch_count(
    main, qapp, monkeypatch, dbg_lines, capsys
):
    """main() itself, as a second launch, while the 'running RRR' listens."""
    version = f"t{uuid.uuid4().hex[:12]}"  # a key of this test's own
    monkeypatch.setattr(main, "__version__", version)
    key = f"rrr_single_instance_{version}"
    window = _Window()
    main._start_single_instance_server(key, window)
    taken_back = []
    monkeypatch.setattr(main.updater, "undo_launch_count", lambda: taken_back.append(True))

    class _SecondRRR:
        def __init__(self, *args):
            raise AssertionError("main() started a second RRR instead of handing over")

    monkeypatch.setattr(main, "SafeQApplication", _SecondRRR)

    try:
        assert main.main() is None
        _process_events_until(qapp, lambda: window.calls)
    finally:
        QLocalServer.removeServer(key)

    assert window.calls == ["show", "raise_", "activateWindow"]
    assert taken_back == [True]
    said = f"RRR v{version} is already running; asked it to show its window"
    assert said in dbg_lines
    assert said in capsys.readouterr().err, "a launch from a terminal would show nothing"


def _top_level_functions():
    tree = ast.parse(MAIN_PY.read_text())
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def _calls(node, name):
    return [
        call
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == name
    ]


def test_both_start_up_paths_start_the_server_through_the_helper():
    """The splash start-up cannot run headless, so this pins both paths statically."""
    functions = _top_level_functions()

    for path in ("_main_with_splash", "_main_without_splash"):
        assert _calls(functions[path], "_start_single_instance_server"), (
            f"{path} does not start the single-instance server through the helper"
        )
    builders = sorted(name for name, node in functions.items() if _calls(node, "QLocalServer"))
    assert builders == ["_start_single_instance_server"], (
        f"QLocalServer is built outside the helper, in {builders}"
    )
