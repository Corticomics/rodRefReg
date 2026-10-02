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


def _make_wizard(num_pulses, pulse_width_ms=10, settings=None, cage_id=1):
    from ui.CalibrationWizard import CalibrationWizard  # noqa: PLC0415

    controller = MagicMock()
    controller.settings = dict(_SETTINGS if settings is None else settings)
    wizard = CalibrationWizard(
        cage_id=cage_id, database_handler=MagicMock(), system_controller=controller
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


def test_independent_topology_pulses_the_cage_and_never_the_master(qapp, fake_relays):
    """On the independent topology (v1.20.0) the wizard drives only the cage valve."""
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    wizard = _make_wizard(num_pulses=5, settings=dict(_SETTINGS, valve_topology="independent"))
    results = []
    log_lines = []

    wizard._execute_calibration()
    assert wizard._worker is not None
    wizard._worker.finished.connect(lambda ok, err: results.append((ok, err)))
    wizard._worker.log.connect(log_lines.append)

    assert _drain_until(qapp, lambda: results and wizard._worker is None)
    assert results[0] == (True, None)

    # The wizard's own branch: it said so, and never claimed to open a master.
    assert any("No master valve on this topology" in line for line in log_lines), log_lines
    assert not any("Master valve opened" in line for line in log_lines), log_lines

    writes = [(ids, state) for ids, state, _ in fake_relays[0].calls]
    assert writes, "no relay writes recorded"
    assert all(ids != (_MASTER_RELAY,) for ids, _ in writes), writes
    assert writes[0] == ((_CAGE_RELAY,), 1)
    assert writes[-1] == ((_CAGE_RELAY,), 0)
    assert sum(1 for ids, state in writes if ids == (_CAGE_RELAY,) and state == 1) == 5

    assert get_operation_lock().is_busy() is False
    wizard.close()


def test_second_hat_cage_pulses_the_relay_it_is_wired_to(qapp, fake_relays):
    """Cage 16 exists only with two HATs and drives relay 17, not relay 16."""
    wizard = _make_wizard(num_pulses=3, settings=dict(_SETTINGS, num_hats=2), cage_id=16)
    results = []

    wizard._execute_calibration()
    assert wizard._worker is not None
    wizard._worker.finished.connect(lambda ok, err: results.append((ok, err)))
    assert _drain_until(qapp, lambda: results and wizard._worker is None)
    assert results[0] == (True, None)

    writes = [(ids, state) for ids, state, _ in fake_relays[0].calls]
    assert writes[0] == ((_MASTER_RELAY,), 1)
    assert [w for w in writes if w == ((17,), 1)] == [((17,), 1)] * 3
    assert not any(ids == (16,) and state == 1 for ids, state in writes[1:]), (
        "relay 16 is the master, opened once before the pulses and never as a cage"
    )
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


# --- Esc ends a run as the X button does ------------------------------------------------------
#
# QDialog sends Esc to reject(), which hides the dialog without a closeEvent.
# The Cancel button is disabled during a run, so Esc was the natural way out,
# and it left the pulse worker running with no window and the lock held.


def _press_escape(wizard):
    from PyQt5.QtCore import Qt  # noqa: PLC0415
    from PyQt5.QtTest import QTest  # noqa: PLC0415

    QTest.keyClick(wizard, Qt.Key_Escape)


_WAYS_OUT = {
    "escape": _press_escape,
    "reject": lambda wizard: wizard.reject(),
    "x button": lambda wizard: wizard.close(),
    "cancel": lambda wizard: wizard._safe_cancel(),
}


@pytest.mark.parametrize("way_out", ["escape", "reject", "x button"])
def test_closing_the_wizard_mid_run_stops_the_pulses(qapp, fake_relays, way_out):
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    # 200 pulses would take ~22 s: the close must cut that short.
    wizard = _make_wizard(num_pulses=200)
    wizard.show()
    progress_values = []

    wizard._execute_calibration()
    assert wizard._worker is not None
    thread = wizard._worker_thread
    wizard._worker.progress.connect(progress_values.append)
    assert _drain_until(qapp, lambda: progress_values)

    _WAYS_OUT[way_out](wizard)

    try:
        assert wizard.isVisible() is False
        assert thread.isRunning() is False, "the pulse worker outlived its wizard"
        assert get_operation_lock().is_busy() is False

        handler = fake_relays[0]
        assert 0 < progress_values[-1] < 200
        assert any(ids == (_MASTER_RELAY,) and state == 0 for ids, state, _ in handler.calls)
        assert handler.calls[-1][1] == 0, "last relay write must be a close"

        # Nothing pulses afterwards.
        writes = len(handler.calls)
        deadline = time.monotonic() + 0.3
        while time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert len(handler.calls) == writes
        assert _drain_until(qapp, lambda: wizard._worker is None)
    finally:
        wizard._shutdown_worker()
        wizard._finalize_run()


@pytest.mark.parametrize("way_out", ["escape", "reject", "x button", "cancel"])
def test_a_wizard_closed_before_its_run_starts_never_starts_it(qapp, fake_relays, way_out):
    """The run starts half a second after its step is shown. A wizard closed
    in that time used to start the whole run with no window on screen."""
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    wizard = _make_wizard(num_pulses=200)
    wizard.show()
    wizard.show_step(1)  # the configuration step builds the spin boxes
    wizard.show_step(2)  # arms the delayed start

    _WAYS_OUT[way_out](wizard)

    try:
        deadline = time.monotonic() + 0.9
        while time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert wizard._worker_thread is None, "a run started after the wizard was closed"
        assert fake_relays == [], "no relay handler was even built"
        assert get_operation_lock().is_busy() is False
    finally:
        wizard._shutdown_worker()
        wizard._finalize_run()


def test_escape_in_the_modal_wizard_returns_with_nothing_running(qapp, fake_relays):
    """The real launch path: exec_() blocks in the modal loop, the run starts
    from the execution step's timer, and Esc is pressed while it pulses."""
    from PyQt5.QtCore import QTimer  # noqa: PLC0415
    from PyQt5.QtWidgets import QDialog  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    wizard = _make_wizard(num_pulses=200)
    seen = {}

    def _start():
        wizard.show_step(1)
        wizard.num_pulses_spin.setValue(200)
        wizard.pulse_width_spin.setValue(10)
        wizard.show_step(2)

    def _escape_once_pulsing():
        if wizard._worker_thread is not None and wizard.progress_bar.value() > 0:
            seen["thread"] = wizard._worker_thread
            seen["lock"] = get_operation_lock().held_by("calibration")
            poll.stop()
            _press_escape(wizard)

    poll = QTimer()
    poll.setInterval(20)
    poll.timeout.connect(_escape_once_pulsing)
    QTimer.singleShot(0, _start)
    poll.start()
    # A backstop so a broken run cannot hang the suite in the modal loop.
    QTimer.singleShot(12_000, wizard.close)

    try:
        result = wizard.exec_()

        assert seen.get("lock") is True, "the run held the lock while it pulsed"
        assert result == QDialog.Rejected
        assert seen["thread"].isRunning() is False
        assert get_operation_lock().is_busy() is False
        assert fake_relays[0].calls[-1][1] == 0, "last relay write must be a close"
    finally:
        poll.stop()
        wizard._shutdown_worker()
        wizard._finalize_run()


# --- a worker that does not stop keeps the lock ------------------------------------------------
#
# Only a relay command that does not return (a hung I2C bus) outlasts the
# wait. The wizard used to release the lock anyway and say so only in its own
# log, which the close was about to hide: a schedule could then start beside
# a run that still had a valve open.


@pytest.mark.parametrize("way_out", ["escape", "x button", "cancel"])
def test_a_run_that_does_not_stop_keeps_the_lock_and_says_so(qapp, monkeypatch, way_out):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from ui.CalibrationWizard import CalibrationWizard  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    hung, unblock = threading.Event(), threading.Event()

    class _HangingRelayHandler(_RecordingRelayHandler):
        def set_relays(self, relay_ids, state):
            if tuple(relay_ids) == (_CAGE_RELAY,) and state and not unblock.is_set():
                super().set_relays(relay_ids, state)  # the valve did open
                hung.set()
                unblock.wait(20)  # ...and the command never returns
                return True
            return super().set_relays(relay_ids, state)

    created = []

    def _factory(*args, **kwargs):
        created.append(_HangingRelayHandler(*args, **kwargs))
        return created[-1]

    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", _factory)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    monkeypatch.setattr(CalibrationWizard, "STOP_WAIT_MS", 200)
    shown = []
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append((a[1], a[2])))
    )

    wizard = _make_wizard(num_pulses=5)
    wizard.show()
    wizard._execute_calibration()
    thread = wizard._worker_thread
    try:
        assert hung.wait(10), "the worker reached the relay command that hangs"

        _WAYS_OUT[way_out](wizard)

        # The wizard is gone, the worker is not: the run still owns the hardware.
        assert wizard.isVisible() is False
        assert thread.isRunning() is True
        assert get_operation_lock().held_by("calibration"), "nothing else may start"
        assert get_operation_lock().try_acquire("schedule") is False
        ((title, text),) = shown
        assert title == "Calibration Did Not Stop"
        assert "a valve may be OPEN" in text
        assert "Disconnect the valve power supply now" in text

        # The command returns at last: the worker closes its valves and ends,
        # and only then is the lock released.
        unblock.set()
        assert _drain_until(qapp, lambda: wizard._worker is None)
        assert thread.isRunning() is False
        assert get_operation_lock().is_busy() is False
        assert created[0].calls[-1][1] == 0, "last relay write is a close"
        assert len(shown) == 1
    finally:
        unblock.set()
        wizard._shutdown_worker(wait_ms=5000)
        wizard._finalize_run()
