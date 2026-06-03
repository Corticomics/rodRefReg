"""Instant deliveries route through the DeliveryStrategy, not the legacy path.

Before v1.14.0, ``run_instant_cycle`` fired ``trigger_relay`` →
``relay_handler.trigger_relays`` (legacy pump-trigger model), so on solenoid
hardware instant deliveries ignored pulse width / valve calibration / the flow
sensor and ran far slower than staggered. Now instant reuses ``_handle_delivery``
(the same path as staggered), which dispatches per ``hardware_mode``:
solenoid → ``strategy.deliver``, pump → ``trigger_relay``. ``_handle_delivery``
is also window-optional so the one-shot instant volume is used directly.

We exercise the real ``RelayWorker._handle_delivery`` by calling it with a
lightweight stand-in ``self`` (a SimpleNamespace) — no QObject construction, so
only a real ``QMutex`` is needed. Skips cleanly without PyQt5.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _restore_event_loop():
    """_handle_delivery's solenoid branch calls asyncio.set_event_loop(None)
    (correct in the worker thread). Running it on the test's MainThread leaves
    no current loop, which would break later tests that use
    asyncio.get_event_loop(). Restore one after each test."""
    import asyncio

    yield
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def _self(hardware_mode, *, animal_windows=None):
    from PyQt5.QtCore import QMutex  # noqa: PLC0415

    ns = SimpleNamespace(
        _cancel_requested=threading.Event(),
        schedule_id=42,
        delivered_volumes={},
        failed_deliveries={},
        mutex=QMutex(),
        hardware_mode=hardware_mode,
        strategy=MagicMock(deliver=AsyncMock(return_value=True)),
        trigger_relay=MagicMock(return_value=True),
        database_handler=MagicMock(),
        progress=MagicMock(),
        volume_updated=MagicMock(),
        schedule_retry=MagicMock(),
    )
    if animal_windows is not None:
        ns.animal_windows = animal_windows
    return ns


def _delivery(vol=0.5):
    return {
        "schedule_id": 42,
        "animal_id": 1,
        "relay_unit_id": 1,
        "water_volume": vol,
        "instant_time": datetime(2026, 6, 5, 9, 0, 0),
        "triggers": None,
    }


def test_instant_solenoid_routes_to_strategy():
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415

    me = _self("solenoid")  # no animal_windows -> instant (window-optional)
    assert RelayWorker._handle_delivery(me, _delivery(0.5)) is True

    me.strategy.deliver.assert_awaited_once()
    kwargs = me.strategy.deliver.await_args.kwargs
    assert kwargs["relay_unit_id"] == 1
    assert kwargs["target_volume_ml"] == 0.5
    me.trigger_relay.assert_not_called()


def test_instant_pump_uses_trigger_relay():
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415

    me = _self("pump")  # no animal_windows
    assert RelayWorker._handle_delivery(me, _delivery(0.5)) is True

    me.trigger_relay.assert_called_once_with(1, 0.5)
    me.strategy.deliver.assert_not_called()


def test_staggered_window_guard_still_holds():
    """Window-optional refactor must not weaken the staggered over-delivery guard."""
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415

    me = _self("solenoid", animal_windows={1: {"target_volume": 0.5}})
    me.delivered_volumes = {1: 0.5}  # already at target
    assert RelayWorker._handle_delivery(me, _delivery(0.5)) is True
    me.strategy.deliver.assert_not_called()  # guard short-circuits, no delivery
