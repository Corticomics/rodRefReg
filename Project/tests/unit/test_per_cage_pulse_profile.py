"""Each cage delivers at the pulse profile it was calibrated at (v2.1.0).

v2.1.0 removed the global Pulse Width from Settings > Delivery. A delivery to
a cage pulses at the width and rest stored with that cage's calibration
(valve_calibration holds one profile per cage), and no setting changes that:
a pulse_width_ms an older release left in the settings is ignored. Pinned
here, over the real database handler and valve controller and a fake relay
HAT:

- a cage calibrated at 30 ms / 1000 ms holds its valve open 30 ms per pulse
  and rests 1000 ms between pulses whatever a stale pulse_width_ms says, and
  the delivery log records 30 / 1000 and the calibration row;
- two cages at different profiles each get their own in the same run;
- a cage with no calibration (Run refuses one) falls back to the named
  empirical width, not to a setting;
- the snapshot's choice of a cage's profile is deterministic.
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from drivers.solenoid_controller import SolenoidController
from strategies import solenoid_flow_strategy
from strategies.solenoid_flow_strategy import (
    FALLBACK_PULSE_WIDTH_MS,
    LEGACY_INTER_PULSE_INTERVAL_MS,
    SolenoidFlowStrategy,
)

Q = 0.034164  # Parker 003-0257-900 at 30 ms / 1000 ms, as calibrated on the Pi
MASTER = 16

# What an older release can have left in the settings: nothing, the 20 ms
# every start forced, or a width an operator set in the session.
STALE = [
    pytest.param({}, id="no-pulse-width"),
    pytest.param({'pulse_width_ms': 20}, id="stale-20-ms"),
    pytest.param({'pulse_width_ms': 50}, id="stale-50-ms"),
]


class _Clock:
    """Stands in for the strategy module's asyncio: a sleep returns at once and
    is recorded with the relays that were on, so a pulse's open time is the
    sleep taken while its cage relay is on."""

    def __init__(self, relays):
        self._relays = relays
        self.sleeps = []  # (seconds, relays on)

    def __getattr__(self, name):
        return getattr(asyncio, name)

    async def sleep(self, seconds, *_args, **_kwargs):
        self.sleeps.append((seconds, frozenset(self._relays.energized())))

    def open_times(self, relay):
        return [seconds for seconds, on in self.sleeps if relay in on]


def _calibrate(db, cage, width, interval, q):
    """The cage's calibration as the wizard saves it."""
    calibration_id = db.save_valve_calibration(
        cage_id=cage,
        relay_id=cage,
        pulse_width_ms=width,
        volume_per_pulse_ml=q,
        stddev_ml=0.0003,
        cv_pct=1.0,
        num_samples=250,
        inter_pulse_interval_ms=interval,
        topology='shared_manifold',
    )
    assert calibration_id
    return calibration_id


def _strategy(relays, stale, db):
    return SolenoidFlowStrategy(
        solenoid_controller=SolenoidController(relays, MASTER, {1: 1, 2: 2, 3: 3}),
        flow_sensor=None,  # calibration-only, as the production rig runs
        calibration_store=None,
        settings={
            'use_pulse_delivery': True,
            'pulse_settling_ms': 100,
            'max_pulses_per_delivery': 100,
            'max_pulse_delivery_time_s': 120.0,
            'valve_topology': 'shared_manifold',
            **stale,
        },
        database_handler=db,
    )


def _record_rests(strategy, monkeypatch):
    """The rest asked for after each pulse, in ms."""
    rests = []
    rest = strategy._rest_between_pulses

    async def _recorded(interval_ms):
        rests.append(interval_ms)
        return await rest(interval_ms)

    monkeypatch.setattr(strategy, '_rest_between_pulses', _recorded)
    return rests


@pytest.mark.parametrize("stale", STALE)
def test_a_cage_calibrated_at_30_1000_pulses_at_30_1000_whatever_a_setting_says(
    database_handler, fake_relay_handler, monkeypatch, stale
):
    calibration_id = _calibrate(database_handler, 1, 30, 1000, Q)
    strategy = _strategy(fake_relay_handler, stale, database_handler)
    clock = _Clock(fake_relay_handler)
    monkeypatch.setattr(solenoid_flow_strategy, 'asyncio', clock)
    rests = _record_rests(strategy, monkeypatch)

    result = asyncio.run(strategy.deliver(relay_unit_id=1, target_volume_ml=3 * Q))

    assert result.success is True and result.pulses == 3
    assert clock.open_times(relay=1) == [0.03, 0.03, 0.03], "30 ms open per pulse"
    assert rests == [1000, 1000], "1000 ms closed between pulses"
    assert (result.pulse_width_ms, result.inter_pulse_interval_ms) == (30, 1000)
    assert result.calibration_id == calibration_id
    assert result.volume_per_pulse_ml == pytest.approx(Q)
    assert result.delivered_ml == pytest.approx(3 * Q)
    assert fake_relay_handler.energized() == set()


def _worker(monkeypatch, strategy, db, settings):
    """A RelayWorker built as the delivery tests build it, with this test's
    strategy, writing its delivery log to the real database."""
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415

    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.delivered_volumes, worker.failed_deliveries, worker.issued_targets = {}, {}, {}
    worker.schedule_id, worker.schedule_name, worker.started_by = 12, 'AM water', 3
    worker.hardware_mode, worker.mode = 'solenoid', 'instant'
    worker.database_handler = MagicMock()
    worker.database_handler.start_schedule_run.return_value = 41
    worker.database_handler.log_delivery.side_effect = db.log_delivery
    worker.settings = settings
    worker.delivery_instants = []
    worker._cancel_requested = MagicMock(is_set=lambda: False)
    worker.run_plan, worker.run_id, worker.stop_reason = {}, None, None
    worker._run_open_tried, worker.run_end_recorded = False, False
    worker.retries = []
    monkeypatch.setattr(
        type(worker), "schedule_retry", lambda self, data: self.retries.append(data), raising=False
    )
    worker.strategy = strategy
    return worker


def _ledger(db):
    with sqlite3.connect(db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM dispensing_history")]


@pytest.mark.parametrize("stale", STALE)
def test_the_delivery_log_records_the_cage_s_profile_not_a_setting(
    database_handler, fake_relay_handler, monkeypatch, stale
):
    pytest.importorskip("PyQt5")
    calibration_id = _calibrate(database_handler, 1, 30, 1000, Q)
    # The strategy reads the device's settings, the worker its copy of them:
    # both carry the stale key.
    strategy = _strategy(fake_relay_handler, stale, database_handler)
    monkeypatch.setattr(solenoid_flow_strategy, 'asyncio', _Clock(fake_relay_handler))
    worker = _worker(
        monkeypatch, strategy, database_handler, {'valve_topology': 'shared_manifold', **stale}
    )

    worker._handle_delivery(
        {
            'animal_id': 3,
            'relay_unit_id': 1,
            'water_volume': 2 * Q,
            'instant_time': datetime(2026, 10, 19, 8, 0),
            'schedule_id': 12,
        }
    )

    [row] = _ledger(database_handler)
    assert row['status'] == 'completed'
    assert (row['pulse_width_ms'], row['inter_pulse_interval_ms']) == (30, 1000)
    assert row['calibration_id'] == calibration_id
    assert row['pulses_fired'] == 2
    assert row['volume_per_pulse_ml'] == pytest.approx(Q)
    assert worker.retries == []


def test_two_cages_each_pulse_at_their_own_profile_in_one_run(
    database_handler, fake_relay_handler, monkeypatch
):
    _calibrate(database_handler, 1, 30, 1000, Q)
    _calibrate(database_handler, 2, 20, 500, 0.026)
    # A stale width that matches one of them must not pull the other to it.
    strategy = _strategy(fake_relay_handler, {'pulse_width_ms': 30}, database_handler)
    clock = _Clock(fake_relay_handler)
    monkeypatch.setattr(solenoid_flow_strategy, 'asyncio', clock)
    rests = _record_rests(strategy, monkeypatch)

    first = asyncio.run(strategy.deliver(relay_unit_id=1, target_volume_ml=2 * Q))
    second = asyncio.run(strategy.deliver(relay_unit_id=2, target_volume_ml=2 * 0.026))

    assert (first.pulse_width_ms, first.inter_pulse_interval_ms) == (30, 1000)
    assert (second.pulse_width_ms, second.inter_pulse_interval_ms) == (20, 500)
    assert clock.open_times(relay=1) == [0.03, 0.03]
    assert clock.open_times(relay=2) == [0.02, 0.02]
    assert rests == [1000, 500]


class _NoCalibrations:
    def get_all_valve_calibrations(self):
        return {}

    def get_valve_calibration(self, _cage_id):
        return None


@pytest.mark.parametrize("stale", STALE)
def test_a_cage_with_no_calibration_falls_back_to_the_named_width_not_a_setting(
    fake_relay_handler, stale
):
    """Run refuses such a cage (utils.calibration_gate); this is the strategy's
    defence in depth, and no setting chooses its width any more."""
    strategy = _strategy(fake_relay_handler, stale, _NoCalibrations())

    width, interval, volume = asyncio.run(strategy._get_cage_calibration(3))

    assert (width, interval) == (FALLBACK_PULSE_WIDTH_MS, LEGACY_INTER_PULSE_INTERVAL_MS)
    assert (width, interval) == (20, 100)
    assert volume == pytest.approx(0.026), "the bench-measured volume at 20 ms"
    assert strategy.pulse_volume_for(3) == pytest.approx(0.026)


def test_the_snapshot_holds_one_profile_per_cage(database_handler, fake_relay_handler):
    """valve_calibration keeps one row per cage: a recalibration replaces it."""
    _calibrate(database_handler, 1, 20, 500, 0.026)
    latest = _calibrate(database_handler, 1, 30, 1000, Q)

    strategy = _strategy(fake_relay_handler, {}, database_handler)

    assert list(strategy._cal_snapshot[1]) == [30]
    assert strategy._cal_snapshot[1][30]['id'] == latest
    assert strategy._get_snapshot_entry(1) == (30, 1000, pytest.approx(Q))


@pytest.mark.parametrize("newest_first", [False, True], ids=["older-first", "newer-first"])
@pytest.mark.parametrize("stale", STALE)
def test_the_snapshot_choice_of_a_cage_s_profile_is_deterministic(
    fake_relay_handler, stale, newest_first
):
    """Only a hand-built snapshot can hold two profiles for a cage. The most
    recently saved one (the higher calibration id) wins, whatever order they
    were added in and whatever width a setting names. Before v2.1.0 the
    Settings pulse width won."""
    strategy = _strategy(fake_relay_handler, stale, None)
    older = (20, {'id': 7, 'volume_per_pulse_ml': 0.026, 'inter_pulse_interval_ms': 500})
    newer = (30, {'id': 9, 'volume_per_pulse_ml': Q, 'inter_pulse_interval_ms': 1000})
    strategy._cal_snapshot = {1: dict([newer, older] if newest_first else [older, newer])}

    assert strategy._get_snapshot_entry(1) == (30, 1000, pytest.approx(Q))
    assert strategy.pulse_volume_for(1) == pytest.approx(Q)
