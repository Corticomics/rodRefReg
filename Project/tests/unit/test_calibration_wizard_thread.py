"""CalibrationWizard pulse loop runs on a worker thread (offscreen Qt).

The wizard used to run the whole pulse loop inline on the GUI thread
(time.sleep per pulse), freezing the dialog for the entire run. These tests
prove the refactored behavior with a fake relay handler and a tiny run:

- the run completes and the worker's finished signal reports success;
- progress is emitted at least once per pulse and reaches the wizard's
  progress bar (live UI updates — the point of the refactor);
- no relay open/close call executes on the GUI thread;
- a cancel requested mid-run stops the loop early, still closes the master
  valve, and releases the operation lock.

Skips cleanly without PyQt5 (CI installs python3-pyqt5 so it runs there).
"""

from __future__ import annotations

import os
import threading
import time
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Matches the wizard's hard-coded cage map: cage 1 -> relay 1, master -> 16.
_SETTINGS = {"num_hats": 1, "global_master_relay_id": 16}
_MASTER_RELAY = 16
_CAGE_RELAY = 1


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    # Force a fresh OperationLock singleton per test (same pattern as
    # test_operation_gating.py — a stale QObject leaks across modules).
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


@pytest.fixture(autouse=True)
def _silence_msgbox(monkeypatch):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    for name in ("warning", "critical", "information"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))


class _RecordingRelayHandler:
    """Fake RelayHandler recording every relay write and its thread ident."""

    def __init__(self, *_args, **_kwargs):
        self.calls = []  # (relay_ids tuple, state, thread ident)

    def set_relays(self, relay_ids, state):
        self.calls.append((tuple(relay_ids), state, threading.get_ident()))
        return True


@pytest.fixture
def fake_relays(monkeypatch):
    """Patch the hardware seam the worker imports lazily inside run()."""
    created = []

    def _factory(*args, **kwargs):
        handler = _RecordingRelayHandler(*args, **kwargs)
        created.append(handler)
        return handler

    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", _factory)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    return created


def _make_wizard(num_pulses, pulse_width_ms=10):
    from ui.CalibrationWizard import CalibrationWizard  # noqa: PLC0415

    controller = MagicMock()
    controller.settings = dict(_SETTINGS)
    wizard = CalibrationWizard(
        cage_id=1, database_handler=MagicMock(), system_controller=controller
    )
    # Bypass the config step's spin boxes; drive the run parameters directly.
    wizard.num_pulses = num_pulses
    wizard.pulse_width_ms = pulse_width_ms
    return wizard


def _drain_until(qapp, predicate, timeout_s=15.0):
    """Pump the event loop until predicate() is true (bounded)."""
    deadline = time.monotonic() + timeout_s
    while not predicate():
        if time.monotonic() > deadline:
            return False
        qapp.processEvents()
        time.sleep(0.005)
    return True


def test_run_completes_off_gui_thread(qapp, fake_relays):
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    wizard = _make_wizard(num_pulses=3)
    results = []
    progress_values = []

    wizard._execute_calibration()
    # Safe to attach spies here: the worker settles for 0.5 s after opening
    # the master valve before its first pulse, so nothing has been emitted
    # yet. These lambdas run directly on the worker thread (list.append is
    # thread-safe); assertions all happen on the GUI thread after the drain.
    assert wizard._worker is not None
    wizard._worker.finished.connect(lambda ok, err: results.append((ok, err)))
    wizard._worker.progress.connect(progress_values.append)

    # The operation lock is held for exactly the duration of the run.
    assert _drain_until(qapp, lambda: progress_values)
    assert get_operation_lock().held_by("calibration") is True

    # Wait for the run to finish AND for the wizard's queued finished slot
    # (which tears down the thread and releases the lock) to run.
    assert _drain_until(qapp, lambda: results and wizard._worker is None)

    # (a) completed successfully
    success, error = results[0]
    assert success is True
    assert error is None

    # (b) progress emitted at least once per pulse, and reached the UI
    assert len(progress_values) >= 3
    assert progress_values[-1] == 3
    assert wizard.progress_bar.value() == 3

    # (c) no relay call ran on the GUI thread; one worker thread did them all
    handler = fake_relays[0]
    gui_ident = threading.get_ident()
    assert handler.calls, "no relay calls recorded"
    assert all(ident != gui_ident for _, _, ident in handler.calls)
    assert len({ident for _, _, ident in handler.calls}) == 1

    # Full hardware sequence: master open, 3 open/close pulses, all closed
    opens = [c for c in handler.calls if c[0] == (_CAGE_RELAY,) and c[1] == 1]
    assert len(opens) == 3
    assert handler.calls[0] == ((_MASTER_RELAY,), 1, handler.calls[0][2])
    assert handler.calls[-1][:2] == ((_MASTER_RELAY,), 0)

    # Lock released once the run is over
    assert get_operation_lock().is_busy() is False
    wizard.close()


def test_cancel_mid_run_stops_early_and_closes_master(qapp, fake_relays):
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    # 200 pulses would take ~22 s — the cancel must cut that short.
    wizard = _make_wizard(num_pulses=200)
    progress_values = []

    wizard._execute_calibration()
    assert wizard._worker is not None
    wizard._worker.progress.connect(progress_values.append)

    # Let at least one pulse complete, then cancel mid-run.
    assert _drain_until(qapp, lambda: progress_values)
    wizard._safe_cancel()  # blocks (bounded) until the worker thread stops

    # (d) the loop stopped early...
    handler = fake_relays[0]
    assert 0 < progress_values[-1] < 200

    # ...and the master valve was still closed; no valve left open.
    assert any(ids == (_MASTER_RELAY,) and state == 0 for ids, state, _ in handler.calls)
    assert handler.calls[-1][1] == 0, "last relay write must be a close"

    # Lock released on the cancel path; worker thread torn down after the
    # queued finished signal drains.
    assert get_operation_lock().is_busy() is False
    assert _drain_until(qapp, lambda: wizard._worker is None)
    assert wizard._worker_thread is None
