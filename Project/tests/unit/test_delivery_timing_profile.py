"""Deliveries replay each cage's calibrated pulse timing profile.

A calibration measures volume per pulse at a particular cadence (pulse
width + valve-closed rest). Delivering at a different cadence reproduces a
different duty cycle — and therefore a different volume per pulse — so the
strategy now resolves and replays the stored interval alongside the width.

Pinned here:
- the stored interval reaches the delivery path; a calibration saved before
  the profile existed (NULL) keeps the legacy 100 ms cadence exactly;
- the per-run snapshot carries the interval;
- the rest is cancellable in slices, so Stop is honoured promptly even at a
  long interval;
- a timing profile too slow for the time limit is refused before any water
  moves, and legacy defaults are never refused.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

from strategies.solenoid_flow_strategy import (
    LEGACY_INTER_PULSE_INTERVAL_MS,
    SolenoidFlowStrategy,
)


class _StubDB:
    """Minimal DatabaseHandler stand-in for calibration reads."""

    def __init__(self, calibrations=None):
        self._calibrations = calibrations or {}

    def get_all_valve_calibrations(self):
        return dict(self._calibrations)

    def get_valve_calibration(self, cage_id):
        return self._calibrations.get(cage_id)


def _cal(volume=0.025, width=20, interval=500, cal_id=1):
    row = {
        'calibration_id': cal_id,
        'pulse_width_ms': width,
        'volume_per_pulse_ml': volume,
        'inter_pulse_interval_ms': interval,
    }
    return row


def _make(settings=None, db=None, valves=None):
    return SolenoidFlowStrategy(
        solenoid_controller=valves if valves is not None else object(),
        flow_sensor=None,
        calibration_store=None,
        settings=settings or {},
        database_handler=db,
    )


def test_snapshot_carries_interval():
    db = _StubDB({1: _cal(interval=750)})
    strategy = _make(db=db)
    assert strategy._cal_snapshot[1][20]['inter_pulse_interval_ms'] == 750

    pw, interval, vol = strategy._get_snapshot_entry(1)
    assert (pw, interval) == (20, 750)
    assert vol == 0.025


def test_legacy_null_interval_keeps_old_cadence():
    """Calibrations saved before the profile existed must not change cadence."""
    db = _StubDB({1: _cal(interval=None)})
    strategy = _make(db=db)

    _pw, interval, _vol = asyncio.run(strategy._get_cage_calibration(1))
    assert interval == LEGACY_INTER_PULSE_INTERVAL_MS == 100


def test_uncalibrated_cage_falls_back_to_legacy_cadence():
    strategy = _make(db=_StubDB({}))
    pw, interval, vol = asyncio.run(strategy._get_cage_calibration(99))
    assert interval == LEGACY_INTER_PULSE_INTERVAL_MS
    assert pw == strategy._pulse_width_ms
    assert vol > 0


def test_db_read_through_resolves_and_caches_interval():
    """A cage missing from the snapshot still picks up its stored profile."""
    db = _StubDB({1: _cal(interval=800)})
    strategy = _make(db=db)
    strategy._cal_snapshot = {}  # force the read-through branch

    pw, interval, _vol = asyncio.run(strategy._get_cage_calibration(1))
    assert (pw, interval) == (20, 800)
    # ...and caches it for the rest of the run.
    assert strategy._cal_snapshot[1][20]['inter_pulse_interval_ms'] == 800


def test_rest_is_cancellable_within_one_slice():
    """A 2 s rest must abort promptly, not hold Stop past its budget."""
    strategy = _make()

    async def _run():
        strategy.request_cancel()
        started = time.monotonic()
        cancelled = await strategy._rest_between_pulses(2000)
        return cancelled, time.monotonic() - started

    cancelled, elapsed = asyncio.run(_run())
    assert cancelled is True
    assert elapsed < 0.3, f"rest held for {elapsed:.2f}s after cancel"


def test_rest_waits_the_full_interval_when_not_cancelled():
    strategy = _make()

    async def _run():
        started = time.monotonic()
        cancelled = await strategy._rest_between_pulses(300)
        return cancelled, time.monotonic() - started

    cancelled, elapsed = asyncio.run(_run())
    assert cancelled is False
    assert elapsed >= 0.29


def test_legacy_profile_is_never_refused_upfront():
    """The new duration guard must not reject anything the old code allowed."""
    strategy = _make()
    # Worst case the old limits permitted: 100 pulses at legacy cadence.
    period_s = strategy._estimate_pulse_period_s(20, LEGACY_INTER_PULSE_INTERVAL_MS)
    assert 100 * period_s < 120.0

    # And with a sensor in the loop (measurement window + restart amortisation).
    strategy._sensor_available = True
    sensor_period_s = strategy._estimate_pulse_period_s(20, LEGACY_INTER_PULSE_INTERVAL_MS)
    assert 100 * sensor_period_s < 120.0


def test_slow_profile_is_refused_before_any_water_moves():
    """
    A profile too slow for the time limit must fail dry.

    Tripping the mid-flight limit instead reports zero delivered after the
    animal has had part of the dose, and the retry then sends the full
    volume again.
    """
    valves = MagicMock()
    db = _StubDB({1: _cal(volume=0.025, interval=2000)})
    strategy = _make(
        settings={'max_pulse_delivery_time_s': 60.0, 'max_pulses_per_delivery': 100},
        db=db,
        valves=valves,
    )

    # 1 mL at 0.025 mL/pulse = 41 pulses; at a 2 s rest that is well over 60 s.
    ok = asyncio.run(strategy._deliver_pulse_mode(cage_id=1, target_volume_ml=1.0))

    assert ok is False
    assert valves.open_cage.call_count == 0, "refusal must happen before any pulse"
    # The master is left closed, not held open by the abandoned delivery.
    assert valves.close_master.called


def test_workable_profile_is_not_refused():
    """The same dose at the default interval stays within budget."""
    valves = MagicMock()
    db = _StubDB({1: _cal(volume=0.025, interval=500)})
    strategy = _make(
        settings={'max_pulse_delivery_time_s': 120.0, 'max_pulses_per_delivery': 100},
        db=db,
        valves=valves,
    )
    _pw, interval, vol = asyncio.run(strategy._get_cage_calibration(1))
    estimated_pulses = int(1.0 / vol) + 1
    assert estimated_pulses * strategy._estimate_pulse_period_s(20, interval) < 120.0
