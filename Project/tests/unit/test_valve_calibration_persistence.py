"""Persistence tests for the valve-calibration pulse timing profile.

Pins the ``inter_pulse_interval_ms`` column added to ``valve_calibration``
and ``valve_calibration_history``: the round-trip through
``save_valve_calibration`` / ``get_valve_calibration``, the one-row-per-cage
(current + history) semantics, and the idempotent additive migration that
upgrades a pre-feature database in place. ``NULL`` means "legacy timing" —
a calibration saved before the column existed (or without the kwarg).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Pre-feature DDL, copied verbatim from create_tables() as it shipped before
# the inter_pulse_interval_ms column existed. Used to simulate an old device
# database that must be auto-migrated on DatabaseHandler construction.
OLD_VALVE_CALIBRATION_DDL = """
    CREATE TABLE IF NOT EXISTS valve_calibration (
        calibration_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cage_id INTEGER NOT NULL UNIQUE,
        relay_id INTEGER NOT NULL,
        pulse_width_ms INTEGER NOT NULL,
        volume_per_pulse_ml REAL NOT NULL,
        stddev_ml REAL,
        coefficient_of_variation_pct REAL,
        num_samples INTEGER NOT NULL,
        calibration_date TEXT NOT NULL,
        calibrated_by INTEGER,
        notes TEXT,
        FOREIGN KEY(calibrated_by) REFERENCES trainers(trainer_id)
    )
"""

OLD_VALVE_CALIBRATION_HISTORY_DDL = """
    CREATE TABLE IF NOT EXISTS valve_calibration_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cage_id INTEGER NOT NULL,
        relay_id INTEGER NOT NULL,
        pulse_width_ms INTEGER NOT NULL,
        volume_per_pulse_ml REAL NOT NULL,
        stddev_ml REAL,
        coefficient_of_variation_pct REAL,
        num_samples INTEGER NOT NULL,
        calibration_date TEXT NOT NULL,
        calibrated_by INTEGER,
        notes TEXT,
        FOREIGN KEY(calibrated_by) REFERENCES trainers(trainer_id)
    )
"""


def _save(handler, cage_id, **overrides):
    """Save a calibration with sane defaults; kwargs mirror production callers."""
    params = {
        "cage_id": cage_id,
        "relay_id": cage_id,
        "pulse_width_ms": 100,
        "volume_per_pulse_ml": 0.025,
        "stddev_ml": 0.001,
        "cv_pct": 4.0,
        "num_samples": 20,
        "calibrated_by": None,
        "notes": None,
    }
    params.update(overrides)
    return handler.save_valve_calibration(**params)


def _table_columns(db_path, table):
    with sqlite3.connect(db_path) as conn:
        return {col[1] for col in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_interval_round_trip(database_handler):
    """Saved interval must read back; omitting the kwarg must read back None."""
    assert _save(database_handler, 1, inter_pulse_interval_ms=500) is not None
    cal = database_handler.get_valve_calibration(1)
    assert cal is not None
    assert cal["inter_pulse_interval_ms"] == 500

    # Legacy-style save (kwarg omitted) -> NULL -> None ("legacy timing").
    assert _save(database_handler, 2) is not None
    cal = database_handler.get_valve_calibration(2)
    assert cal is not None
    assert cal["inter_pulse_interval_ms"] is None


def test_one_row_per_cage_with_full_history(database_handler):
    """Re-calibrating a cage replaces the current row but appends to history."""
    _save(database_handler, 3, pulse_width_ms=100, inter_pulse_interval_ms=250)
    _save(database_handler, 3, pulse_width_ms=150, inter_pulse_interval_ms=750)

    # Current calibration holds only the second profile.
    cal = database_handler.get_valve_calibration(3)
    assert cal["pulse_width_ms"] == 150
    assert cal["inter_pulse_interval_ms"] == 750

    # History keeps both profiles.
    history = database_handler.get_valve_calibration_history(3)
    assert len(history) == 2
    profiles = {(h["pulse_width_ms"], h["inter_pulse_interval_ms"]) for h in history}
    assert profiles == {(100, 250), (150, 750)}


def test_old_database_is_auto_migrated(tmp_path: Path):
    """A pre-feature DB gains the column on construction; legacy rows read None."""
    db_path = tmp_path / "old_rrr_database.db"

    # Build the old-schema database with raw sqlite3 and one legacy row.
    with sqlite3.connect(db_path) as conn:
        conn.execute(OLD_VALVE_CALIBRATION_DDL)
        conn.execute(OLD_VALVE_CALIBRATION_HISTORY_DDL)
        conn.execute(
            """
            INSERT INTO valve_calibration
            (cage_id, relay_id, pulse_width_ms, volume_per_pulse_ml,
             stddev_ml, coefficient_of_variation_pct, num_samples,
             calibration_date, calibrated_by, notes)
            VALUES (7, 7, 100, 0.025, 0.001, 4.0, 20, '2026-01-01T00:00:00', NULL, NULL)
            """
        )
        conn.commit()

    assert "inter_pulse_interval_ms" not in _table_columns(db_path, "valve_calibration")

    # Constructing the handler must migrate both tables without raising.
    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    handler = DatabaseHandler(db_path=str(db_path))

    assert "inter_pulse_interval_ms" in _table_columns(db_path, "valve_calibration")
    assert "inter_pulse_interval_ms" in _table_columns(db_path, "valve_calibration_history")

    # The legacy row survives and reads back as legacy timing (None).
    cal = handler.get_valve_calibration(7)
    assert cal is not None
    assert cal["pulse_width_ms"] == 100
    assert cal["inter_pulse_interval_ms"] is None

    # A fresh save with an interval works on the migrated tables.
    assert _save(handler, 7, pulse_width_ms=120, inter_pulse_interval_ms=400) is not None
    cal = handler.get_valve_calibration(7)
    assert cal["inter_pulse_interval_ms"] == 400

    # Re-running the migration (a second handler) must be a no-op, not an error.
    DatabaseHandler(db_path=str(db_path))
    assert handler.get_valve_calibration(7)["inter_pulse_interval_ms"] == 400


def test_get_all_valve_calibrations_includes_interval(database_handler):
    """The bulk getter must expose the new key for every cage."""
    _save(database_handler, 1, inter_pulse_interval_ms=300)
    _save(database_handler, 2)  # legacy-style, no interval

    calibrations = database_handler.get_all_valve_calibrations()
    assert set(calibrations.keys()) == {1, 2}
    assert calibrations[1]["inter_pulse_interval_ms"] == 300
    assert calibrations[2]["inter_pulse_interval_ms"] is None
