"""dispensing_history records the context a delivery ran under (v1.21.0).

Two devices now run two valve topologies with per-cage calibrations that
change over time. To compare their ledgers - or one device's rows before
and after a recalibration - each row carries: the topology, the
valve_calibration row in force, the pulse width and inter-pulse interval
the pulses were fired at, the wall-clock duration, and the app version.
All nullable; older rows read NULL ("not recorded").

Pinned here: the in-place migration, the writer, the strategy reporting
the calibration row and profile it used (and nothing when it fell back to
the default), and the worker passing all of it to the ledger.
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from drivers.solenoid_controller import SolenoidController
from strategies.delivery_strategy import DeliveryResult
from strategies.solenoid_flow_strategy import (
    LEGACY_INTER_PULSE_INTERVAL_MS,
    SolenoidFlowStrategy,
)
from version import __version__

CONTEXT_COLUMNS = (
    'topology',
    'calibration_id',
    'pulse_width_ms',
    'inter_pulse_interval_ms',
    'duration_s',
    'app_version',
    'volume_requested_ml',
    'dose_rounding',
)

# The table as v1.17.0 created it, before the context columns existed.
OLD_DISPENSING_HISTORY_DDL = """
    CREATE TABLE dispensing_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id INTEGER NOT NULL,
        animal_id INTEGER NOT NULL,
        relay_unit_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        volume_dispensed REAL NOT NULL,
        status TEXT NOT NULL,
        cycle_index INTEGER DEFAULT NULL,
        volume_actual_ml REAL DEFAULT NULL,
        pulses_fired INTEGER DEFAULT NULL,
        volume_per_pulse_ml REAL DEFAULT NULL
    )
"""


def _columns(db_path, table):
    with sqlite3.connect(db_path) as conn:
        return {col[1] for col in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _row(db_path, history_id=None):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM dispensing_history"
        if history_id is not None:
            query += f" WHERE history_id = {int(history_id)}"
        return dict(conn.execute(query + " ORDER BY history_id DESC").fetchone())


def _delivery(**extra):
    data = {
        'schedule_id': 7,
        'animal_id': 1,
        'relay_unit_id': 3,
        'timestamp': '2026-09-28T10:00:00',
        'volume_delivered': 0.3,
        'status': 'completed',
    }
    data.update(extra)
    return data


# --- schema -----------------------------------------------------------------


def test_old_database_gains_the_context_columns(tmp_path: Path):
    db_path = tmp_path / "pre_context.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(OLD_DISPENSING_HISTORY_DDL)
        conn.execute(
            "INSERT INTO dispensing_history (schedule_id, animal_id, relay_unit_id, timestamp, "
            "volume_dispensed, status, volume_actual_ml, pulses_fired, volume_per_pulse_ml) "
            "VALUES (1, 1, 1, '2026-09-01T00:00:00', 0.3, 'completed', 0.296, 9, 0.032936)"
        )
        conn.commit()
    assert not set(CONTEXT_COLUMNS) & _columns(db_path, 'dispensing_history')

    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    handler = DatabaseHandler(db_path=str(db_path))
    assert set(CONTEXT_COLUMNS) <= _columns(db_path, 'dispensing_history')

    old = _row(db_path)
    assert old['pulses_fired'] == 9, "the legacy row survives"
    assert all(old[column] is None for column in CONTEXT_COLUMNS), "legacy rows read NULL"

    DatabaseHandler(db_path=str(db_path))  # re-running the migration is a no-op
    handler.log_delivery(_delivery(topology='independent', app_version='9.9.9'))
    assert _row(db_path)['topology'] == 'independent'


def test_log_delivery_stores_the_context(database_handler):
    database_handler.log_delivery(
        _delivery(
            volume_actual_ml=0.296,
            pulses_fired=9,
            volume_per_pulse_ml=0.032936,
            topology='shared_manifold',
            calibration_id=42,
            pulse_width_ms=30,
            inter_pulse_interval_ms=1000,
            duration_s=9.7,
            app_version=__version__,
            volume_requested_ml=0.3,
            dose_rounding='nearest',
        )
    )
    row = _row(database_handler.db_path)
    assert row['topology'] == 'shared_manifold'
    assert row['calibration_id'] == 42
    assert (row['pulse_width_ms'], row['inter_pulse_interval_ms']) == (30, 1000)
    assert row['duration_s'] == pytest.approx(9.7)
    assert row['app_version'] == __version__
    assert row['volume_requested_ml'] == pytest.approx(0.3)
    assert row['dose_rounding'] == 'nearest'


def test_log_delivery_without_context_still_works(database_handler):
    """Rows written by paths that know nothing about the context stay valid."""
    database_handler.log_delivery(_delivery())
    row = _row(database_handler.db_path)
    assert row['status'] == 'completed'
    assert all(row[column] is None for column in CONTEXT_COLUMNS)


# --- the strategy reports what it used --------------------------------------


def test_delivery_result_context_defaults_to_none():
    """Nothing recorded reaches the ledger as NULL, never as a measured zero."""
    result = DeliveryResult(success=True)
    assert (result.calibration_id, result.pulse_width_ms, result.inter_pulse_interval_ms) == (
        None,
        None,
        None,
    )
    assert result.duration_s is None


def test_outcomes_nobody_timed_carry_no_duration():
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415

    assert RelayWorker._as_delivery_result(True, 0.3).duration_s is None
    assert RelayWorker._as_delivery_result(False, 0.3).duration_s is None


def test_pump_strategy_times_its_dispense():
    from strategies.pump_strategy import PumpStrategy  # noqa: PLC0415

    class _Pump:
        async def dispense_water(self, relay_unit_id, volume_ml, triggers):
            await asyncio.sleep(0.02)
            return True

    class _Calculator:
        pump_volume_ul = 50.0

        def calculate_triggers(self, volume_ml):
            return 6

    result = asyncio.run(PumpStrategy(_Pump(), _Calculator()).deliver(1, 0.3))
    assert result.success is True and result.pulses == 6
    assert result.duration_s is not None and result.duration_s >= 0.02
    assert result.calibration_id is None, "the pump has no calibration row to cite"


class _StubDB:
    def __init__(self, calibrations):
        self._calibrations = calibrations

    def get_all_valve_calibrations(self):
        return dict(self._calibrations)

    def get_valve_calibration(self, cage_id):
        return self._calibrations.get(cage_id)


def _strategy(fake, calibrations, monkeypatch, db=None):
    strategy = SolenoidFlowStrategy(
        solenoid_controller=SolenoidController(fake, 16, {1: 1}),
        flow_sensor=None,
        calibration_store=None,
        settings={
            'use_pulse_delivery': True,
            'pulse_width_ms': 30,
            'pulse_settling_ms': 100,
            'max_pulses_per_delivery': 100,
            'max_pulse_delivery_time_s': 120.0,
        },
        database_handler=db if db is not None else _StubDB(calibrations),
    )

    async def _no_sleep(_seconds):
        return None

    async def _no_rest(_interval_ms):
        return False

    monkeypatch.setattr(asyncio, 'sleep', _no_sleep)
    monkeypatch.setattr(strategy, '_rest_between_pulses', _no_rest)
    return strategy


def test_strategy_reports_the_calibration_row_and_profile_it_fired_at(
    fake_relay_handler, monkeypatch
):
    calibration = {
        1: {
            'calibration_id': 42,
            'pulse_width_ms': 30,
            'volume_per_pulse_ml': 0.032936,
            'inter_pulse_interval_ms': 1000,
        }
    }
    strategy = _strategy(fake_relay_handler, calibration, monkeypatch)

    result = asyncio.run(strategy.deliver(relay_unit_id=1, target_volume_ml=3 * 0.032936))

    assert result.success is True and result.pulses == 3
    assert result.calibration_id == 42
    assert (result.pulse_width_ms, result.inter_pulse_interval_ms) == (30, 1000)
    assert result.duration_s >= 0.0


def test_strategy_cites_the_row_the_real_handler_saved(
    database_handler, fake_relay_handler, monkeypatch
):
    """
    The per-run snapshot is built from get_all_valve_calibrations, which
    did not return the row id: every calibrated cage banked id 0 and the
    ledger read NULL on the production path while the stub-backed test
    stayed green. Pinned against the real handler, including the id
    changing when a cage is recalibrated (INSERT OR REPLACE makes a new row).
    """

    def _save(volume):
        saved = database_handler.save_valve_calibration(
            cage_id=1,
            relay_id=1,
            pulse_width_ms=30,
            volume_per_pulse_ml=volume,
            stddev_ml=0.0003,
            cv_pct=1.0,
            num_samples=250,
            inter_pulse_interval_ms=1000,
        )
        assert saved is not None
        return saved

    first = _save(0.032936)
    strategy = _strategy(fake_relay_handler, None, monkeypatch, db=database_handler)
    result = asyncio.run(strategy.deliver(relay_unit_id=1, target_volume_ml=3 * 0.032936))
    assert result.success is True and result.calibration_id == first
    assert (result.pulse_width_ms, result.inter_pulse_interval_ms) == (30, 1000)

    second = _save(0.034164)
    assert second != first
    rerun = _strategy(fake_relay_handler, None, monkeypatch, db=database_handler)
    result = asyncio.run(rerun.deliver(relay_unit_id=1, target_volume_ml=3 * 0.034164))
    assert result.calibration_id == second
    assert result.volume_per_pulse_ml == pytest.approx(0.034164)


def test_strategy_reports_no_calibration_row_when_it_fell_back(fake_relay_handler, monkeypatch):
    """An uncalibrated cage runs on the empirical default: no row to cite."""
    strategy = _strategy(fake_relay_handler, {}, monkeypatch)

    result = asyncio.run(strategy.deliver(relay_unit_id=1, target_volume_ml=0.05))

    assert result.calibration_id is None
    assert result.pulse_width_ms == strategy._pulse_width_ms
    assert result.inter_pulse_interval_ms == LEGACY_INTER_PULSE_INTERVAL_MS


# --- the worker passes it to the ledger ----------------------------------------


def _worker(monkeypatch, settings):
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415

    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.settings = settings
    worker.delivered_volumes = {}
    worker.failed_deliveries = {}
    worker.issued_targets = {}
    worker.schedule_id = 7
    worker.hardware_mode = 'solenoid'
    worker.database_handler = MagicMock()
    worker.strategy = MagicMock()
    worker.progress.connect(lambda _m: None)
    worker.volume_updated.connect(lambda *_a: None)

    class _Event:
        def is_set(self):
            return False

    worker._cancel_requested = _Event()
    monkeypatch.setattr(type(worker), "schedule_retry", lambda self, data: None, raising=False)
    return worker


@pytest.mark.parametrize("topology", ["shared_manifold", "independent"])
def test_worker_logs_the_context_it_ran_under(monkeypatch, topology):
    pytest.importorskip("PyQt5")
    worker = _worker(monkeypatch, {'valve_topology': topology})

    async def _deliver(relay_unit_id, target_volume_ml, triggers_hint=None):
        return DeliveryResult(
            success=True,
            delivered_ml=3 * 0.032936,
            duration_s=3.4,
            pulses=3,
            volume_per_pulse_ml=0.032936,
            calibration_id=42,
            pulse_width_ms=30,
            inter_pulse_interval_ms=1000,
        )

    worker.strategy.deliver = _deliver
    worker._handle_delivery(
        {
            'animal_id': 1,
            'relay_unit_id': 3,
            'water_volume': 0.1,
            'instant_time': datetime(2026, 9, 28, 8, 0, 0),
            'schedule_id': 7,
        }
    )

    logged = worker.database_handler.log_delivery.call_args.args[0]
    assert logged['status'] == 'completed'
    assert logged['topology'] == topology
    assert logged['calibration_id'] == 42
    assert (logged['pulse_width_ms'], logged['inter_pulse_interval_ms']) == (30, 1000)
    assert logged['duration_s'] == pytest.approx(3.4)
    assert logged['app_version'] == __version__


# --- the dose asked for, before whole-pulse rounding ---------------------------
#
# The whole-pulse planner rewrites water_volume to pulses x q before the
# delivery is logged, so volume_dispensed carries the plan, not the ask.
# Without the ask, a planner or rounding regression cannot be seen from the
# ledger, and two rigs with different q put the same nominal dose in
# different cells.

NEEDLE_Q = 0.032936  # mL per pulse, Parker valve with the upstream needle


def _pulse_worker(monkeypatch, q=NEEDLE_Q, round_up=False):
    pytest.importorskip("PyQt5")
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415

    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.settings = {'valve_topology': 'shared_manifold', 'round_doses_up': round_up}
    worker.delivered_volumes = {}
    worker.failed_deliveries = {}
    worker.issued_targets = {}
    worker.schedule_id = 7
    worker.hardware_mode = 'solenoid'
    worker.database_handler = MagicMock()
    worker.progress.connect(lambda _m: None)
    worker.volume_updated.connect(lambda *_a: None)

    class _Event:
        def is_set(self):
            return False

    worker._cancel_requested = _Event()
    worker.retries = []
    monkeypatch.setattr(
        type(worker), "schedule_retry", lambda self, data: self.retries.append(data), raising=False
    )

    strategy = MagicMock()
    strategy.pulse_volume_for = lambda cage_id: q
    worker.outcomes = []  # scripted results, consumed in order; then success

    async def _deliver(relay_unit_id, target_volume_ml, triggers_hint=None):
        n = round(target_volume_ml / q)
        if worker.outcomes:
            return worker.outcomes.pop(0)(n)
        return DeliveryResult(success=True, delivered_ml=n * q, pulses=n, volume_per_pulse_ml=q)

    strategy.deliver = _deliver
    worker.strategy = strategy
    return worker


def _instant(volume):
    return {
        'animal_id': 1,
        'relay_unit_id': 3,
        'water_volume': volume,
        'instant_time': datetime(2026, 9, 29, 8, 0, 0),
        'schedule_id': 7,
    }


def _logged(worker):
    return [call.args[0] for call in worker.database_handler.log_delivery.call_args_list]


@pytest.mark.parametrize("round_up,pulses,policy", [(False, 18, 'nearest'), (True, 19, 'up')])
def test_worker_logs_the_dose_asked_for_before_rounding(monkeypatch, round_up, pulses, policy):
    """0.6 mL at q = 32.936 uL is 18.2 pulses: 18 at nearest, 19 rounded up."""
    worker = _pulse_worker(monkeypatch, round_up=round_up)
    worker._handle_delivery(_instant(0.6))

    (row,) = _logged(worker)
    assert row['volume_requested_ml'] == pytest.approx(0.6)
    assert row['dose_rounding'] == policy
    assert row['pulses_fired'] == pulses
    # volume_dispensed keeps its meaning: the plan, whole pulses x q.
    assert row['volume_delivered'] == pytest.approx(pulses * NEEDLE_Q)


def test_a_retry_keeps_the_first_ask(monkeypatch):
    worker = _pulse_worker(monkeypatch)
    worker.outcomes = [
        lambda n: DeliveryResult(
            success=False, delivered_ml=0.0, pulses=0, volume_per_pulse_ml=NEEDLE_Q
        )
    ]
    data = _instant(0.6)
    worker._handle_delivery(data)
    assert worker.retries == [data]
    worker._handle_delivery(data)  # schedule_retry re-enters with the same dict

    first, second = _logged(worker)
    assert (first['status'], second['status']) == ('failed', 'completed')
    assert first['volume_requested_ml'] == pytest.approx(0.6)
    assert second['volume_requested_ml'] == pytest.approx(0.6)


def test_a_staggered_chunk_logs_its_own_ask(monkeypatch):
    worker = _pulse_worker(monkeypatch)
    worker.animal_windows = {1: {'target_volume': 0.6}}
    worker._handle_delivery(_instant(0.2))

    (row,) = _logged(worker)
    assert row['volume_requested_ml'] == pytest.approx(0.2)
    assert row['dose_rounding'] == 'nearest'


def test_a_delivery_not_rounded_to_pulses_records_no_policy(monkeypatch):
    worker = _pulse_worker(monkeypatch)
    del worker.strategy.pulse_volume_for  # pump / continuous: no pulse quantum
    worker._handle_delivery(_instant(0.25))

    (row,) = _logged(worker)
    assert row['volume_requested_ml'] == pytest.approx(0.25)
    assert row['dose_rounding'] is None
