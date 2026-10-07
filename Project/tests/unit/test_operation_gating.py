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


def test_priming_open_buttons_grey_out_when_locked_elsewhere(qapp):
    """Phase 2 UI gating: when a schedule (or calibration) holds the lock, the
    priming Open buttons are visibly disabled via the state_changed signal;
    releasing re-enables them per valve state."""
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import SCHEDULE, get_operation_lock  # noqa: PLC0415

    w = PrimingControlWidget(_SETTINGS, lambda *_: None)
    # Idle: master closed -> Open Master enabled.
    assert w.master_open_btn.isEnabled() is True

    # Another operation acquires -> state_changed fires -> Open buttons disabled.
    get_operation_lock().try_acquire(SCHEDULE)
    assert w.master_open_btn.isEnabled() is False
    assert w.cage_open_btn.isEnabled() is False

    # Release -> Open Master re-enabled (master still closed).
    get_operation_lock().force_release()
    assert w.master_open_btn.isEnabled() is True


# --- independent topology (v1.21.0): no master valve, the lock follows the cages --


_INDEPENDENT = dict(_SETTINGS, valve_topology="independent")


@pytest.fixture
def fake_relays(monkeypatch, fake_relay_handler):
    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    return fake_relay_handler


def _select(w, cage_id):
    index = w.cage_selector.findData(cage_id)
    assert index >= 0
    w.cage_selector.setCurrentIndex(index)


def test_independent_hides_the_master_and_lets_a_cage_open_directly(qapp, fake_relays):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    w = PrimingControlWidget(_INDEPENDENT, lambda *_: None)
    assert w.master_group.isHidden() is True
    assert "no master valve" in w.cage_info_label.text()
    assert "daily" in w.daily_check_label.text()
    # No "open master first" step: the cage Open button is live on selection.
    assert w.cage_open_btn.isEnabled() is True

    shared = PrimingControlWidget(_SETTINGS, lambda *_: None)
    assert shared.master_group.isHidden() is False
    assert shared.cage_open_btn.isEnabled() is False, "shared path unchanged: master first"


def test_independent_lock_follows_the_cage_valves(qapp, fake_relays):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import PRIMING, get_operation_lock  # noqa: PLC0415

    w = PrimingControlWidget(_INDEPENDENT, lambda *_: None)
    lock = get_operation_lock()

    _select(w, 3)
    w._on_open_cage_clicked()
    assert lock.held_by(PRIMING) is True
    assert fake_relays.trace == [((3,), 1)]

    _select(w, 5)
    w._on_open_cage_clicked()
    assert fake_relays.trace == [((3,), 1), ((5,), 1)]

    w._on_close_cage_clicked()  # cage 5; cage 3 still open -> session continues
    assert lock.held_by(PRIMING) is True

    _select(w, 3)
    w._on_close_cage_clicked()  # last open valve -> session over
    assert lock.is_busy() is False
    assert fake_relays.energized() == set()
    assert all(16 not in ids for ids, _state in fake_relays.trace)


def test_independent_cage_open_is_refused_while_a_schedule_runs(qapp, fake_relays):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import SCHEDULE, get_operation_lock  # noqa: PLC0415

    get_operation_lock().try_acquire(SCHEDULE)
    w = PrimingControlWidget(_INDEPENDENT, lambda *_: None)
    assert w.cage_open_btn.isEnabled() is False, "greyed out while the schedule holds the lock"

    _select(w, 3)
    assert w.cage_open_btn.isEnabled() is False, "a selector change must not re-enable Open"
    w._on_open_cage_clicked()
    assert fake_relays.trace == [], "refused before touching hardware"
    assert get_operation_lock().held_by(SCHEDULE) is True

    get_operation_lock().release(SCHEDULE)
    assert w.cage_open_btn.isEnabled() is True, "live again once the schedule lets go"


def test_independent_emergency_stop_closes_everything_and_frees_the_lock(qapp, fake_relays):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    w = PrimingControlWidget(_INDEPENDENT, lambda *_: None)
    _select(w, 3)
    w._on_open_cage_clicked()

    w._on_emergency_stop_clicked()
    assert fake_relays.trace[-1] == (("all",), 0)
    assert fake_relays.energized() == set()
    assert get_operation_lock().is_busy() is False
    # The virtual master stays "open": priming can start again straight away.
    assert w.cage_open_btn.isEnabled() is True
