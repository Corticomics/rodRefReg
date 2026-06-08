"""Process-wide hardware operation lock.

Exactly one hardware operation may be active at a time: running a **schedule**,
**priming**, or **calibration**. All three open the *single shared master
solenoid*, and schedule + calibration both consume the *single flow sensor*, so
they cannot physically overlap. This is operation-level mutual exclusion,
sitting ABOVE the per-transaction :class:`drivers.i2c_coordinator.I2CCoordinator`
(which only serialises ~50 ms I²C writes and force-releases — not enough to keep
two long operations apart).

It is exposed as a ``QObject`` process-wide singleton via
:func:`get_operation_lock` (mirroring ``get_i2c_coordinator``) so every UI entry
point can use it without dependency-injection plumbing — notably
``PrimingControlWidget``, which has no ``system_controller``. ``state_changed``
lets widgets enable/disable their controls.

Two enforcement layers use this:
- **Guard (authoritative):** each path calls :meth:`try_acquire` at start
  (refusing on conflict) and releases on every exit path.
- **UI (usability):** widgets subscribe to :attr:`state_changed` and disable the
  controls belonging to the other operations.

The lock is *advisory*: it gates the three known user entry points, not the I²C
bus itself. Those three are the only initiators of hardware operations.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

# Operation identifiers.
SCHEDULE = "schedule"
PRIMING = "priming"
CALIBRATION = "calibration"

_LABELS = {
    SCHEDULE: "a schedule run",
    PRIMING: "a priming session",
    CALIBRATION: "a calibration",
}


class OperationLock(QObject):
    """Single-holder, re-entrant-per-owner hardware operation lock."""

    # Emitted whenever the busy/idle state changes (free→held or held→free).
    state_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._mutex = threading.RLock()
        self._active: Optional[str] = None
        self._log = logging.getLogger(self.__class__.__name__)

    def try_acquire(self, operation: str, label: str = "") -> bool:
        """Acquire for ``operation``. Non-blocking.

        Returns True if the lock was free (now held by ``operation``) or is
        already held by the *same* ``operation`` (re-entrant — a schedule fires
        many deliveries, priming opens several valves). Returns False, without
        side effects, if a *different* operation holds it.
        """
        became_busy = False
        with self._mutex:
            if self._active is not None and self._active != operation:
                self._log.info(
                    "Operation '%s' refused: '%s' already active", operation, self._active
                )
                return False
            became_busy = self._active is None
            self._active = operation
        if became_busy:
            self.state_changed.emit()
        return True

    def release(self, operation: str) -> None:
        """Release iff ``operation`` currently holds the lock (idempotent)."""
        changed = False
        with self._mutex:
            if self._active == operation:
                self._active = None
                changed = True
        if changed:
            self.state_changed.emit()

    def force_release(self) -> None:
        """Unconditionally clear the lock — the stop/emergency failsafe path."""
        changed = False
        with self._mutex:
            if self._active is not None:
                self._log.warning("Force-releasing operation lock held by '%s'", self._active)
                self._active = None
                changed = True
        if changed:
            self.state_changed.emit()

    def active_operation(self) -> Optional[str]:
        with self._mutex:
            return self._active

    def active_label(self) -> str:
        """Human-readable description of the active operation (for messages)."""
        with self._mutex:
            if self._active is None:
                return ""
            return _LABELS.get(self._active, self._active)

    def is_busy(self) -> bool:
        with self._mutex:
            return self._active is not None

    def held_by(self, operation: str) -> bool:
        with self._mutex:
            return self._active == operation

    def reset(self) -> None:
        """Test seam: clear state silently (use in test setup/teardown)."""
        with self._mutex:
            self._active = None


_singleton: Optional[OperationLock] = None


def get_operation_lock() -> OperationLock:
    """Return the process-wide :class:`OperationLock` (lazily created)."""
    global _singleton
    if _singleton is None:
        _singleton = OperationLock()
    return _singleton
