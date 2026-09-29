"""A calibration records the valve topology it was measured under (v1.21.0).

The manifold's head and the master valve (or their absence) shape the
volume per pulse, so a calibration measured on one topology is stale on the
other. valve_calibration and its history gain a nullable ``topology``
column; rows saved before it carry NULL, which reads as the shared manifold
because every device then ran one ("legacy").

A stale calibration is still used: refusing, or swapping in the default,
would change what an animal receives mid-schedule. It is flagged instead:
once per cage in the Terminal tab ([CAL TOPOLOGY]), once per run for the
cages the run waters, as 'Stale' in the Settings table and the CSV export,
and Calibrate All includes it.
"""

from __future__ import annotations

import asyncio
import csv
import os
import sqlite3
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from drivers.solenoid_controller import SolenoidController
from strategies.solenoid_flow_strategy import SolenoidFlowStrategy
from utils.topology import (
    INDEPENDENT,
    SHARED_MANIFOLD,
    calibration_is_legacy,
    calibration_is_stale,
    calibration_label,
    calibration_topology,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

Q = 0.032936

# The calibration tables as v1.16.0-v1.20.0 created them: interval, no topology.
OLD_CALIBRATION_DDL = """
    CREATE TABLE valve_calibration (
        calibration_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cage_id INTEGER NOT NULL UNIQUE, relay_id INTEGER NOT NULL,
        pulse_width_ms INTEGER NOT NULL, volume_per_pulse_ml REAL NOT NULL,
        stddev_ml REAL, coefficient_of_variation_pct REAL, num_samples INTEGER NOT NULL,
        calibration_date TEXT NOT NULL, calibrated_by INTEGER, notes TEXT,
        inter_pulse_interval_ms INTEGER
    );
    CREATE TABLE valve_calibration_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cage_id INTEGER NOT NULL, relay_id INTEGER NOT NULL,
        pulse_width_ms INTEGER NOT NULL, volume_per_pulse_ml REAL NOT NULL,
        stddev_ml REAL, coefficient_of_variation_pct REAL, num_samples INTEGER NOT NULL,
        calibration_date TEXT NOT NULL, calibrated_by INTEGER, notes TEXT,
        inter_pulse_interval_ms INTEGER
    );
"""


def _save(handler, cage_id=1, topology=None, volume=Q):
    kwargs = dict(
        cage_id=cage_id,
        relay_id=cage_id,
        pulse_width_ms=30,
        volume_per_pulse_ml=volume,
        stddev_ml=0.0003,
        cv_pct=1.0,
        num_samples=250,
        inter_pulse_interval_ms=1000,
    )
    if topology is not None:
        kwargs['topology'] = topology
    saved = handler.save_valve_calibration(**kwargs)
    assert saved is not None
    return saved


# --- schema and persistence ----------------------------------------------------


def test_old_calibration_tables_gain_the_column_in_place(tmp_path):
    db_path = tmp_path / "v1_20.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(OLD_CALIBRATION_DDL)
        conn.execute(
            "INSERT INTO valve_calibration (cage_id, relay_id, pulse_width_ms, "
            "volume_per_pulse_ml, num_samples, calibration_date, inter_pulse_interval_ms) "
            "VALUES (3, 3, 30, 0.032936, 250, '2026-09-15T10:00:00', 1000)"
        )

    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    handler = DatabaseHandler(db_path=str(db_path))
    for table in ('valve_calibration', 'valve_calibration_history'):
        with sqlite3.connect(db_path) as conn:
            columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        assert 'topology' in columns, table

    legacy = handler.get_valve_calibration(3)
    assert legacy['topology'] is None and legacy['inter_pulse_interval_ms'] == 1000
    assert calibration_label(legacy) == 'shared_manifold (legacy)'
    DatabaseHandler(db_path=str(db_path))  # re-running the migration is a no-op


@pytest.mark.parametrize("tag", [SHARED_MANIFOLD, INDEPENDENT, None])
def test_the_tag_round_trips_through_every_reader(database_handler, tag):
    calibration_id = _save(database_handler, cage_id=4, topology=tag)

    assert database_handler.get_valve_calibration(4)['topology'] == tag
    every = database_handler.get_all_valve_calibrations()[4]
    assert every['topology'] == tag
    # The id the ledger cites must not have moved when the column was added.
    assert every['calibration_id'] == calibration_id
    (history,) = database_handler.get_valve_calibration_history(4)
    assert history['topology'] == tag


# --- the rule ------------------------------------------------------------------


@pytest.mark.parametrize(
    "calibration,topology,legacy",
    [
        (None, SHARED_MANIFOLD, True),
        ({}, SHARED_MANIFOLD, True),
        ({'topology': None}, SHARED_MANIFOLD, True),
        ({'topology': 'shared_manifold'}, SHARED_MANIFOLD, False),
        ({'topology': ' Independent '}, INDEPENDENT, False),
        ({'topology': 'garbage'}, SHARED_MANIFOLD, True),
    ],
)
def test_what_a_stored_tag_means(calibration, topology, legacy):
    assert calibration_topology(calibration) == topology
    assert calibration_is_legacy(calibration) is legacy


@pytest.mark.parametrize(
    "device,tag,stale",
    [
        (SHARED_MANIFOLD, None, False),
        (SHARED_MANIFOLD, SHARED_MANIFOLD, False),
        (SHARED_MANIFOLD, INDEPENDENT, True),
        (INDEPENDENT, None, True),  # a legacy row was measured on the manifold
        (INDEPENDENT, SHARED_MANIFOLD, True),
        (INDEPENDENT, INDEPENDENT, False),
    ],
)
def test_when_a_calibration_is_stale(device, tag, stale):
    assert calibration_is_stale({'topology': tag}, {'valve_topology': device}) is stale


def test_no_calibration_is_uncalibrated_not_stale():
    assert calibration_is_stale(None, {'valve_topology': INDEPENDENT}) is False


# --- the delivery strategy -----------------------------------------------------


class _StubDB:
    def __init__(self, calibrations):
        self._calibrations = calibrations

    def get_all_valve_calibrations(self):
        return dict(self._calibrations)

    def get_valve_calibration(self, cage_id):
        return self._calibrations.get(cage_id)


def _cal(tag, volume=Q, calibration_id=42):
    return {
        'calibration_id': calibration_id,
        'pulse_width_ms': 30,
        'volume_per_pulse_ml': volume,
        'inter_pulse_interval_ms': 1000,
        'topology': tag,
    }


def _strategy(fake, db, device, monkeypatch=None):
    strategy = SolenoidFlowStrategy(
        solenoid_controller=SolenoidController(fake, 16, {1: 1, 2: 2}),
        flow_sensor=None,
        calibration_store=None,
        settings={
            'use_pulse_delivery': True,
            'pulse_width_ms': 30,
            'pulse_settling_ms': 100,
            'max_pulses_per_delivery': 100,
            'max_pulse_delivery_time_s': 120.0,
            'valve_topology': device,
        },
        database_handler=db,
    )
    if monkeypatch is not None:

        async def _no_sleep(_seconds):
            return None

        async def _no_rest(_interval_ms):
            return False

        monkeypatch.setattr(asyncio, 'sleep', _no_sleep)
        monkeypatch.setattr(strategy, '_rest_between_pulses', _no_rest)
    return strategy


@pytest.mark.parametrize(
    "device,tag,stale",
    [
        (SHARED_MANIFOLD, None, False),
        (SHARED_MANIFOLD, SHARED_MANIFOLD, False),
        (SHARED_MANIFOLD, INDEPENDENT, True),
        (INDEPENDENT, None, True),
        (INDEPENDENT, SHARED_MANIFOLD, True),
        (INDEPENDENT, INDEPENDENT, False),
    ],
)
def test_the_strategy_flags_a_stale_calibration_once(fake_relay_handler, capsys, device, tag, stale):
    strategy = _strategy(fake_relay_handler, _StubDB({1: _cal(tag)}), device)
    out = capsys.readouterr().out

    assert strategy._cal_snapshot[1][30]['topology'] == tag
    assert f"topology={calibration_label({'topology': tag})}" in out
    assert (1 in strategy.stale_calibrations()) is stale
    assert out.count("[CAL TOPOLOGY] cage=1") == (1 if stale else 0)
    if stale:
        assert f"this device runs {device}" in out and "recalibrate cage 1" in out
    assert fake_relay_handler.trace == [], "building a strategy drives nothing"


def test_a_stale_calibration_is_still_used(fake_relay_handler, monkeypatch, capsys):
    """Flag, never refuse or substitute: the animal gets what the calibration plans."""
    strategy = _strategy(fake_relay_handler, _StubDB({1: _cal(None, volume=0.034164)}),
                         INDEPENDENT, monkeypatch)
    capsys.readouterr()

    first = asyncio.run(strategy.deliver(relay_unit_id=1, target_volume_ml=3 * 0.034164))
    second = asyncio.run(strategy.deliver(relay_unit_id=1, target_volume_ml=3 * 0.034164))

    assert first.success and second.success
    assert first.pulses == second.pulses == 3
    assert first.volume_per_pulse_ml == pytest.approx(0.034164)
    assert capsys.readouterr().out.count("[CAL TOPOLOGY]") == 0, "reported at snapshot, not per chunk"


def test_the_read_through_path_flags_it_too(fake_relay_handler, capsys):
    strategy = _strategy(fake_relay_handler, _StubDB({2: _cal(SHARED_MANIFOLD)}), INDEPENDENT)
    strategy._cal_snapshot = {}  # as if the row was saved after the run started
    strategy._stale_calibrations = {}
    capsys.readouterr()

    asyncio.run(strategy._get_cage_calibration(2))
    assert strategy.stale_calibrations() == {2: SHARED_MANIFOLD}
    assert strategy._cal_snapshot[2][30]['topology'] == SHARED_MANIFOLD
    assert "[CAL TOPOLOGY] cage=2" in capsys.readouterr().out


def test_recalibrating_on_the_device_clears_it(database_handler, fake_relay_handler):
    _save(database_handler, cage_id=1, topology=SHARED_MANIFOLD)
    assert _strategy(fake_relay_handler, database_handler, INDEPENDENT).stale_calibrations() == {
        1: SHARED_MANIFOLD
    }
    _save(database_handler, cage_id=1, topology=INDEPENDENT)
    assert _strategy(fake_relay_handler, database_handler, INDEPENDENT).stale_calibrations() == {}


# --- the worker tells the operator, for the cages this run waters -----------------


@pytest.fixture
def qapp():
    pytest.importorskip("PyQt5")
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


def _worker(fake, db, device, monkeypatch, run_settings=None):
    from drivers.uart_flow_sensor import TeensyUnavailableError  # noqa: PLC0415
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QObject  # noqa: PLC0415

    def _no_teensy(_settings):
        raise TeensyUnavailableError("no Teensy on this bench")

    monkeypatch.setattr("drivers.flow_sensor_factory.create_flow_sensor", _no_teensy)
    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker._deferred_solenoid_init = True
    worker._system_settings = {'num_hats': 1, 'global_master_relay_id': 16, 'valve_topology': device}
    worker.settings = dict(run_settings or {})
    worker.flow_sensor_optional = True
    worker.flow_sensor_available = False
    worker.relay_handler = fake
    worker.hardware_mode = 'solenoid'
    worker.pump_controller = None
    worker.volume_calculator = None
    worker.system_controller = SimpleNamespace(database_handler=db)
    worker.emitted = []
    worker.progress.connect(worker.emitted.append)
    return worker


def _stale_lines(worker):
    return [line for line in worker.emitted if 'calibration measured on' in line]


def test_the_worker_names_each_stale_cage_the_run_waters(qapp, fake_relay_handler, monkeypatch):
    db = _StubDB({1: _cal(None), 2: _cal(INDEPENDENT, calibration_id=43)})
    worker = _worker(fake_relay_handler, db, INDEPENDENT, monkeypatch)
    worker._initialize_hardware()

    (line,) = _stale_lines(worker)
    assert "Cage 1: calibration measured on shared_manifold (legacy)" in line
    assert "runs independent" in line and "recalibrate cage 1" in line


def test_the_worker_stays_quiet_about_cages_the_run_does_not_water(
    qapp, fake_relay_handler, monkeypatch
):
    db = _StubDB({1: _cal(None)})
    instant = {'delivery_instants': [{'relay_unit_id': 2, 'animal_id': 7}]}
    worker = _worker(fake_relay_handler, db, INDEPENDENT, monkeypatch, run_settings=instant)
    worker._initialize_hardware()
    assert _stale_lines(worker) == []

    staggered = {'relay_unit_assignments': {'7': 1}}
    worker = _worker(fake_relay_handler, db, INDEPENDENT, monkeypatch, run_settings=staggered)
    worker._initialize_hardware()
    assert len(_stale_lines(worker)) == 1


def test_a_manifold_device_with_legacy_rows_says_nothing(qapp, fake_relay_handler, monkeypatch):
    worker = _worker(fake_relay_handler, _StubDB({1: _cal(None)}), SHARED_MANIFOLD, monkeypatch)
    worker._initialize_hardware()
    assert _stale_lines(worker) == []


# --- Settings -> Calibration ---------------------------------------------------------


@pytest.fixture
def settings_tab(qapp, database_handler, system_controller):
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None

    def _build(device):
        from ui.SettingsTab import SettingsTab  # noqa: PLC0415

        system_controller.settings['num_hats'] = 1
        system_controller.settings['valve_topology'] = device
        login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
        return SettingsTab(
            system_controller,
            login_system=login,
            print_to_terminal=lambda _msg: None,
            database_handler=database_handler,
        )

    yield _build
    ol._singleton = None


def test_the_table_marks_a_stale_row_and_its_button(settings_tab, database_handler):
    _save(database_handler, cage_id=1)  # legacy: measured on the manifold
    _save(database_handler, cage_id=2, topology=INDEPENDENT)
    tab = settings_tab(INDEPENDENT)
    table = tab.calibration_table

    stale = table.item(0, 1)
    assert stale.text() == "Stale"
    assert (stale.foreground().color().red(), stale.foreground().color().green()) == (200, 150)
    assert "shared_manifold (legacy)" in stale.toolTip() and "runs independent" in stale.toolTip()
    assert table.cellWidget(0, 5).property("variant") == "primary"

    assert table.item(1, 1).text() == "[OK]"
    assert table.item(1, 1).toolTip() == "Calibrated on independent"
    assert table.cellWidget(1, 5).property("variant") is None


def test_a_manifold_device_shows_legacy_rows_as_calibrated(settings_tab, database_handler):
    _save(database_handler, cage_id=1)
    tab = settings_tab(SHARED_MANIFOLD)
    assert tab.calibration_table.item(0, 1).text() == "[OK]"
    assert "legacy" in tab.calibration_table.item(0, 1).toolTip()


def test_the_export_carries_the_topology(settings_tab, database_handler, tmp_path, monkeypatch):
    from PyQt5.QtWidgets import QFileDialog, QMessageBox  # noqa: PLC0415

    _save(database_handler, cage_id=1)
    _save(database_handler, cage_id=2, topology=INDEPENDENT)
    tab = settings_tab(INDEPENDENT)
    out = tmp_path / "report.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), "")))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    tab._export_calibration_report()

    with open(out, newline='', encoding='utf-8') as handle:
        rows = list(csv.reader(handle))
    header, legacy, current, uncalibrated = rows[0], rows[1], rows[2], rows[3]
    assert header[-1] == "Topology" and all(len(r) == len(header) for r in rows)
    assert (legacy[1], legacy[-1]) == ("Stale", "shared_manifold (legacy)")
    assert (current[1], current[-1]) == ("Calibrated", "independent")
    assert uncalibrated[1] == "Not Calibrated"


def test_calibrate_all_includes_stale_cages(settings_tab, database_handler, monkeypatch):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    for cage in range(1, 16):
        _save(database_handler, cage_id=cage, topology=INDEPENDENT)
    _save(database_handler, cage_id=4)  # re-saved without a tag: legacy, stale here
    tab = settings_tab(INDEPENDENT)
    questions = []
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: questions.append(a) or QMessageBox.No)
    )
    tab._calibrate_all_uncalibrated()

    (question,) = questions
    assert "Found 0 uncalibrated valves" in question[2]
    assert "and 1 calibrated under the other valve topology (Stale):\n[4]" in question[2]
