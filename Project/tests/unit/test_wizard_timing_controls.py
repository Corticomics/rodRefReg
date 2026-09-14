"""Calibration wizard exposes and persists the pulse timing profile.

The wizard now configures both halves of the timing profile — pulse width
and the valve-closed inter-pulse interval — runs the pulse loop with them,
and stores the interval alongside the calibration so deliveries can replay
the same cadence. These tests pin the wiring end to end:

- the configured interval reaches the worker, and a cancel during a long
  rest returns promptly (the rest waits on the stop event, it does not
  sleep it out);
- the save call always carries the interval (the per-cage row is replaced,
  so omitting it would silently reset a stored profile to legacy timing);
- the run-time estimate tracks all three spin boxes;
- the duty-cycle advisory appears above the threshold and never blocks.

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

_SETTINGS = {"num_hats": 1, "global_master_relay_id": 16}


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    # Fresh OperationLock singleton per test (same pattern as the sibling
    # wizard tests — a stale QObject leaks across modules).
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
    def __init__(self, *_args, **_kwargs):
        self.calls = []

    def set_relays(self, relay_ids, state):
        self.calls.append((tuple(relay_ids), state, threading.get_ident()))
        return True


@pytest.fixture
def fake_relays(monkeypatch):
    created = []

    def _factory(*args, **kwargs):
        handler = _RecordingRelayHandler(*args, **kwargs)
        created.append(handler)
        return handler

    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", _factory)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    return created


def _make_wizard(db=None):
    from ui.CalibrationWizard import CalibrationWizard  # noqa: PLC0415

    controller = MagicMock()
    controller.settings = dict(_SETTINGS)
    return CalibrationWizard(
        cage_id=1,
        database_handler=db if db is not None else MagicMock(),
        system_controller=controller,
    )


def _drain_until(qapp, predicate, timeout_s=15.0):
    deadline = time.monotonic() + timeout_s
    while not predicate():
        if time.monotonic() > deadline:
            return False
        qapp.processEvents()
        time.sleep(0.005)
    return True


def test_configured_interval_reaches_worker_and_cancel_interrupts_rest(qapp, fake_relays):
    """A cancel during a 2 s rest must return at once, not wait it out."""
    wizard = _make_wizard()
    wizard.num_pulses = 50
    wizard.pulse_width_ms = 10
    wizard.inter_pulse_interval_ms = 2000

    progress_values = []
    wizard._execute_calibration()
    assert wizard._worker is not None
    assert wizard._worker._inter_pulse_interval_ms == 2000
    wizard._worker.progress.connect(progress_values.append)

    # First pulse completes, then the worker enters the 2 s rest.
    assert _drain_until(qapp, lambda: progress_values)

    started = time.monotonic()
    wizard._safe_cancel()  # bounded wait for the worker thread
    elapsed = time.monotonic() - started

    # Waiting on the stop event returns immediately; sleeping the rest out
    # would have taken the better part of two seconds.
    assert elapsed < 1.0, f"cancel waited {elapsed:.2f}s — rest was not interruptible"
    assert progress_values[-1] < 50

    handler = fake_relays[0]
    assert handler.calls[-1][1] == 0, "last relay write must be a close"
    wizard.close()


def test_save_always_persists_the_interval(qapp, fake_relays):
    """The per-cage row is replaced on save, so the interval must be written."""
    db = MagicMock()
    db.save_valve_calibration.return_value = 42

    wizard = _make_wizard(db=db)
    wizard.num_pulses = 100
    wizard.pulse_width_ms = 25
    wizard.inter_pulse_interval_ms = 750
    wizard.measured_volume_ml = 2.5
    wizard.calibration_result = {
        'volume_per_pulse_ml': 0.025,
        'stddev_ml': 0.001,
        'cv_pct': 4.0,
    }

    wizard._save_and_finish()

    kwargs = db.save_valve_calibration.call_args.kwargs
    assert kwargs['inter_pulse_interval_ms'] == 750
    assert kwargs['pulse_width_ms'] == 25
    # Provenance: the profile is also recorded in the notes.
    assert "750ms rest" in kwargs['notes']
    wizard.close()


def test_time_estimate_tracks_all_three_spin_boxes(qapp):
    wizard = _make_wizard()
    wizard._show_configuration()

    wizard.num_pulses_spin.setValue(100)
    wizard.pulse_width_spin.setValue(20)
    wizard.interval_spin.setValue(100)
    # 0.5 s settle + 100 x 120 ms = 12.5 s
    assert wizard.time_estimate.text() == "~12 seconds"

    # A longer rest must lengthen the estimate, not leave it stale.
    wizard.interval_spin.setValue(500)
    assert wizard.time_estimate.text() == "~52 seconds"

    # A wider pulse counts too (the old estimate ignored the width entirely).
    wizard.pulse_width_spin.setValue(120)
    assert wizard.time_estimate.text() == "~62 seconds"

    wizard.num_pulses_spin.setValue(500)
    assert wizard.time_estimate.text().endswith("minutes")
    wizard.close()


def test_duty_cycle_advisory_is_shown_above_threshold_only(qapp):
    wizard = _make_wizard()
    wizard._show_configuration()

    # isVisibleTo(): the dialog itself is never shown in an offscreen test,
    # so isVisible() would be False for every child regardless.
    # Default profile (20 ms / 500 ms = 3.8%) is comfortably quiet.
    wizard.pulse_width_spin.setValue(20)
    wizard.interval_spin.setValue(500)
    assert wizard.duty_warning.isVisibleTo(wizard) is False
    assert wizard.duty_warning.text() == ""

    # The long-standing 20 ms / 100 ms profile is 16.7% — advisory, never
    # blocking: the run stays available.
    wizard.interval_spin.setValue(100)
    assert wizard.duty_warning.isVisibleTo(wizard) is True
    assert "Duty cycle" in wizard.duty_warning.text()
    assert wizard.next_btn.isEnabled() is True
    wizard.close()
