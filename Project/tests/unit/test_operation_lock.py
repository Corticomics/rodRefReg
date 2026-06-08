"""Unit tests for the hardware OperationLock.

Exactly one of schedule/priming/calibration may hold the lock (shared master
valve + single flow sensor). These pin the acquire/refuse/re-entrant/release
semantics and the state_changed signal. A fresh OperationLock() is used per test
(not the singleton) for isolation.

Needs PyQt5 for the QObject signal; skips cleanly without it.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


def _lock():
    from utils.operation_lock import OperationLock  # noqa: PLC0415

    return OperationLock()


def test_acquire_then_conflict_is_refused(qapp):
    from utils.operation_lock import CALIBRATION, PRIMING, SCHEDULE  # noqa: PLC0415

    lock = _lock()
    assert lock.try_acquire(SCHEDULE) is True
    assert lock.is_busy() is True
    assert lock.held_by(SCHEDULE) is True
    # A different operation cannot acquire while SCHEDULE holds it.
    assert lock.try_acquire(PRIMING) is False
    assert lock.try_acquire(CALIBRATION) is False
    assert lock.active_operation() == SCHEDULE


def test_reentrant_same_operation(qapp):
    from utils.operation_lock import SCHEDULE  # noqa: PLC0415

    lock = _lock()
    assert lock.try_acquire(SCHEDULE) is True
    # Same op re-acquires freely (schedule fires many deliveries).
    assert lock.try_acquire(SCHEDULE) is True
    assert lock.active_operation() == SCHEDULE


def test_release_frees_for_next_operation(qapp):
    from utils.operation_lock import CALIBRATION, SCHEDULE  # noqa: PLC0415

    lock = _lock()
    lock.try_acquire(SCHEDULE)
    lock.release(SCHEDULE)
    assert lock.is_busy() is False
    assert lock.try_acquire(CALIBRATION) is True


def test_release_by_non_holder_is_noop(qapp):
    from utils.operation_lock import PRIMING, SCHEDULE  # noqa: PLC0415

    lock = _lock()
    lock.try_acquire(SCHEDULE)
    lock.release(PRIMING)  # not the holder
    assert lock.held_by(SCHEDULE) is True


def test_force_release_clears_any_holder(qapp):
    from utils.operation_lock import SCHEDULE  # noqa: PLC0415

    lock = _lock()
    lock.try_acquire(SCHEDULE)
    lock.force_release()
    assert lock.is_busy() is False


def test_state_changed_fires_on_transitions_only(qapp):
    from utils.operation_lock import SCHEDULE  # noqa: PLC0415

    lock = _lock()
    seen = []
    lock.state_changed.connect(lambda: seen.append(lock.active_operation()))

    lock.try_acquire(SCHEDULE)  # free -> held  (emit)
    lock.try_acquire(SCHEDULE)  # re-entrant    (no emit)
    lock.release(SCHEDULE)  # held -> free  (emit)
    lock.release(SCHEDULE)  # already free  (no emit)

    assert seen == [SCHEDULE, None]


def test_active_label_is_human_readable(qapp):
    from utils.operation_lock import PRIMING  # noqa: PLC0415

    lock = _lock()
    assert lock.active_label() == ""
    lock.try_acquire(PRIMING)
    assert "priming" in lock.active_label().lower()


def test_singleton_is_stable(qapp):
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    assert get_operation_lock() is get_operation_lock()
