"""A running RRR keeps answering its single-instance key for the whole run.

main() probes ``rrr_single_instance_<version>`` before it starts anything:
when a running RRR answers, the new copy sends ``b'raise'`` and exits instead
of starting a second RRR on the same relays. The no-splash start-up (the one
RRR uses) kept its QLocalServer in a local variable referenced only by its own
slot. That reference cycle is collectable: the first garbage collection after
start-up deleted the server and its socket, and a later launch then ran
beside the first.

Each test listens on a key of its own and removes it afterwards, so a running
RRR on the same machine is never touched.
"""

from __future__ import annotations

import ast
import gc
import os
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

# Headless Qt: must be set before QApplication is constructed.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
