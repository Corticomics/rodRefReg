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


def test_request_cancel_sets_token_and_reset_clears_it():
    strat, _ = _make_solenoid()
    assert strat._check_cancelled() is False
    strat.request_cancel()
    assert strat._check_cancelled() is True
    # v1.8.3: reset_cancel is the ONLY thing that clears the token, and
    # the worker calls it once per run — never per delivery chunk.
    strat.reset_cancel()
    assert strat._check_cancelled() is False


def test_deliver_does_not_clear_cancel(monkeypatch):
    """deliver() must NOT clear a cancel set mid-schedule (v1.8.2 bug).

    A cancel set between chunks must survive into the next deliver() so
    that chunk bails too. deliver() returns False immediately when the
    token is already set, without ever clearing it.
    """
    strat, _ = _make_solenoid(use_pulse=False)
    strat.request_cancel()

    routed = {"continuous": False}

    async def fake_continuous(cage_id, vol):
        routed["continuous"] = True
        return True

    monkeypatch.setattr(strat, "_deliver_continuous_mode", fake_continuous)
    result = asyncio.get_event_loop().run_until_complete(
        strat.deliver(relay_unit_id=1, target_volume_ml=0.5)
    )
    # Returned False without routing into the delivery, and token still set.
    assert result is False
    assert routed["continuous"] is False
    assert strat._check_cancelled() is True


def test_deliver_proceeds_after_reset(monkeypatch):
    """After reset_cancel, a fresh deliver() routes normally."""
    strat, _ = _make_solenoid(use_pulse=False)
    strat.request_cancel()
    strat.reset_cancel()  # worker does this once at schedule start

    routed = {"continuous": False}

    async def fake_continuous(cage_id, vol):
        routed["continuous"] = True
        return True

    monkeypatch.setattr(strat, "_deliver_continuous_mode", fake_continuous)
    result = asyncio.get_event_loop().run_until_complete(
        strat.deliver(relay_unit_id=1, target_volume_ml=0.5)
    )
    assert result is True
    assert routed["continuous"] is True


def test_cancelled_deliver_never_reports_success():
    """A cancelled delivery must return False, never True.

    Core safety invariant: once Stop is pressed the strategy must not
    report a completed delivery. With the token set, deliver() short-
    circuits to False before touching any valve.
    """
    strat, _ = _make_solenoid(use_pulse=False)
    strat.request_cancel()
    result = asyncio.get_event_loop().run_until_complete(
        strat.deliver(relay_unit_id=3, target_volume_ml=0.5)
    )
    assert result is False


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
