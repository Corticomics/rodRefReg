"""Guard-layer integration: priming refuses/holds the OperationLock correctly.

Proves the guard pattern end to end on the priming path (constructible with just
a settings dict). The schedule and calibration paths use the identical
acquire/release pattern against the same lock (unit-tested in
test_operation_lock.py) and are validated on the Pi.

Skips cleanly without PyQt5.
"""

from __future__ import annotations

import os
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
    # Force a fresh singleton bound to the live QApplication for each test
    # (a stale QObject leaked across test modules otherwise).
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


@pytest.fixture(autouse=True)
def _silence_msgbox(monkeypatch):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    for name in ("warning", "critical", "information"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))


def test_priming_refused_while_schedule_active(qapp):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import SCHEDULE, get_operation_lock  # noqa: PLC0415

    lock = get_operation_lock()
    assert lock.try_acquire(SCHEDULE) is True  # a schedule is running

    w = PrimingControlWidget(_SETTINGS, lambda *_: None)
    w._on_open_master_clicked()

    # Refused before touching hardware; the schedule still owns the lock.
    assert w._solenoid_controller is None
    assert lock.held_by(SCHEDULE) is True


def test_priming_acquires_on_open_and_releases_on_close(qapp, monkeypatch):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import PRIMING, get_operation_lock  # noqa: PLC0415

    w = PrimingControlWidget(_SETTINGS, lambda *_: None)
    ctrl = MagicMock()
    ctrl.open_master.return_value = True
    ctrl.close_master.return_value = True
    ctrl.get_open_cages = MagicMock(return_value=set())
    monkeypatch.setattr(w, "_get_solenoid_controller", lambda: ctrl)

    w._on_open_master_clicked()
    assert get_operation_lock().held_by(PRIMING) is True
    ctrl.open_master.assert_called_once()

    w._on_close_master_clicked()
    assert get_operation_lock().is_busy() is False


def test_priming_releases_when_hardware_unavailable(qapp, monkeypatch):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    w = PrimingControlWidget(_SETTINGS, lambda *_: None)
    monkeypatch.setattr(w, "_get_solenoid_controller", lambda: None)  # init failed
    w._on_open_master_clicked()
    # Acquired then released on the graceful abort — no stale lock.
    assert get_operation_lock().is_busy() is False
