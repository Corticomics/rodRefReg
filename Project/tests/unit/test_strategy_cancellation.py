"""Cooperative-cancellation tests for the delivery strategies.

Part of the v1.8.2 safety follow-up. v1.8.1 made Stop *safe* (hardware
dropped first, bounded waits). This locks the behavior that makes Stop
*clean*: a delivery in flight, when cancelled, exits fast and closes the
master valve via its finally block — so the worker thread returns from
run_until_complete and the GUI's bounded wait succeeds without ever
needing terminate().

Qt-free and hardware-free: the strategies take injected mock collaborators.
"""

from __future__ import annotations

import asyncio

from unittest.mock import MagicMock

from strategies.solenoid_flow_strategy import SolenoidFlowStrategy
from strategies.pump_strategy import PumpStrategy


# ---------------------------------------------------------------------------
# SolenoidFlowStrategy
# ---------------------------------------------------------------------------

def _make_solenoid(use_pulse=False):
    valves = MagicMock()
    sensor = MagicMock()
    cal = MagicMock()
    settings = {'use_pulse_delivery': use_pulse}
    strat = SolenoidFlowStrategy(valves, sensor, cal, settings)
    return strat, valves


def test_request_cancel_sets_token():
    strat, _ = _make_solenoid()
    assert strat._check_cancelled() is False
    strat.request_cancel()
    assert strat._check_cancelled() is True


def test_deliver_clears_stale_cancel_then_routes(monkeypatch):
    """A fresh deliver() clears a stale cancel from a prior run."""
    strat, _ = _make_solenoid(use_pulse=False)
    strat.request_cancel()  # stale flag from a previous run

    captured = {}

    async def fake_continuous(cage_id, vol):
        # By the time the mode method runs, the stale flag must be cleared.
        captured['cancelled_at_entry'] = strat._check_cancelled()
        return True

    monkeypatch.setattr(strat, "_deliver_continuous_mode", fake_continuous)
    result = asyncio.get_event_loop().run_until_complete(
        strat.deliver(relay_unit_id=1, target_volume_ml=0.5)
    )
    assert result is True
    assert captured['cancelled_at_entry'] is False


def test_cancelled_continuous_delivery_never_reports_success():
    """A cancelled continuous delivery must return False, never True.

    Core safety invariant: once the operator presses Stop, the strategy
    must not report a delivery as completed. The valve-closing itself is
    the pre-existing finally block (hardware-verified in v1.8.1); this
    test locks the new behavior — the cancel token short-circuits the
    delivery loop to a False result. We keep the token set through the
    run (deliver() would otherwise clear it at entry) to simulate a
    cancel that lands the instant delivery begins.
    """
    strat, valves = _make_solenoid(use_pulse=False)
    strat._cancel_event.set()
    orig_clear = strat._cancel_event.clear
    strat._cancel_event.clear = lambda: None  # keep cancelled through deliver()
    try:
        result = asyncio.get_event_loop().run_until_complete(
            strat.deliver(relay_unit_id=3, target_volume_ml=0.5)
        )
    finally:
        strat._cancel_event.clear = orig_clear

    assert result is False
    # The master valve must be closed on the way out (finally block).
    valves.close_master.assert_called()


# ---------------------------------------------------------------------------
# PumpStrategy (atomic — cancel can only prevent a not-yet-dispatched run)
# ---------------------------------------------------------------------------

def test_pump_request_cancel_prevents_dispatch():
    pump = MagicMock()
    volcalc = MagicMock()
    volcalc.calculate_triggers.return_value = 3
    volcalc.pump_volume_ul = 100
    strat = PumpStrategy(pump, volcalc)

    strat.request_cancel()
    result = asyncio.get_event_loop().run_until_complete(
        strat.deliver(relay_unit_id=1, target_volume_ml=0.3)
    )
    assert result is False
    pump.dispense_water.assert_not_called()


def test_pump_normal_dispatch_after_no_cancel():
    pump = MagicMock()

    async def _dispense(*_a):
        return True

    pump.dispense_water.side_effect = _dispense
    volcalc = MagicMock()
    volcalc.calculate_triggers.return_value = 3
    volcalc.pump_volume_ul = 100
    strat = PumpStrategy(pump, volcalc)

    result = asyncio.get_event_loop().run_until_complete(
        strat.deliver(relay_unit_id=1, target_volume_ml=0.3)
    )
    assert result is True
    pump.dispense_water.assert_called_once()
