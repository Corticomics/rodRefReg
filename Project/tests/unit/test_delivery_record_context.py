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
        )
    )
    row = _row(database_handler.db_path)
    assert row['topology'] == 'shared_manifold'
    assert row['calibration_id'] == 42
    assert (row['pulse_width_ms'], row['inter_pulse_interval_ms']) == (30, 1000)
    assert row['duration_s'] == pytest.approx(9.7)
    assert row['app_version'] == __version__


def test_log_delivery_without_context_still_works(database_handler):
    """Rows written by paths that know nothing about the context stay valid."""
    database_handler.log_delivery(_delivery())
    row = _row(database_handler.db_path)
    assert row['status'] == 'completed'
    assert all(row[column] is None for column in CONTEXT_COLUMNS)


# --- the strategy reports what it used --------------------------------------


def test_delivery_result_context_defaults_to_none():
    result = DeliveryResult(success=True)
    assert (result.calibration_id, result.pulse_width_ms, result.inter_pulse_interval_ms) == (
        None,
        None,
        None,
    )


class _StubDB:
    def __init__(self, calibrations):
        self._calibrations = calibrations

    def get_all_valve_calibrations(self):
        return dict(self._calibrations)

    def get_valve_calibration(self, cage_id):
        return self._calibrations.get(cage_id)


def _strategy(fake, calibrations, monkeypatch):
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
        database_handler=_StubDB(calibrations),
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
