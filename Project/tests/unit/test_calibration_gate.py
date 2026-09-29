"""A schedule does not start while a cage it waters has no calibration it can use.

Without one the delivery strategy guessed the volume per pulse (an empirical
~0.026 mL against the production valve's 0.034, so about 30 % too much
water). A calibration measured under the other valve topology is off by the
difference between the rigs. The Run path now refuses such a start, on the GUI
thread, before any worker exists, and resets the button and the operation
lock so the operator can calibrate straight away.
"""

from __future__ import annotations

import math
import os
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from utils.calibration_gate import (
    STALE,
    UNCALIBRATED,
    UNUSABLE,
    CageProblem,
    calibration_problems,
    format_problems,
    gate_applies,
    run_cage_ids,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SHARED = {"hardware_mode": "solenoid", "use_pulse_delivery": True, "pulse_width_ms": 20}
INDEPENDENT = dict(SHARED, valve_topology="independent")


def _row(cage, volume=0.034164, width=30, topology=None, interval=1000):
    return {
        'cage_id': cage,
        'relay_id': cage,
        'pulse_width_ms': width,
        'volume_per_pulse_ml': volume,
        'inter_pulse_interval_ms': interval,
        'topology': topology,
    }


# --- when the gate applies -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("settings", "applies"),
    [
        ({}, True),
        ({"hardware_mode": " Solenoid "}, True),
        ({"hardware_mode": None}, True),
        ({"hardware_mode": "pump"}, False),
        (dict(SHARED, use_pulse_delivery=False), False),
    ],
)
def test_the_gate_applies_to_solenoid_pulse_delivery_only(settings, applies):
    assert gate_applies(settings) is applies


def test_the_mode_is_read_as_the_worker_reads_it():
    pytest.importorskip("PyQt5")
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415

    for value in (None, "", "solenoid", " SOLENOID ", "pump", "Pump "):
        settings = {"hardware_mode": value}
        worker_says = RelayWorker._resolve_hardware_mode(settings) == 'solenoid'
        assert gate_applies(settings) is worker_says, value


# --- which cages a run waters ----------------------------------------------------------------


def test_a_staggered_run_waters_every_assigned_cage():
    assert run_cage_ids("Staggered", {"1": 3, "2": 5}, None) == {3, 5}


def test_an_instant_run_waters_only_the_cages_of_deliveries_still_ahead():
    future = [{'relay_unit_id': 2}, {'relay_unit_id': 4}]
    assert run_cage_ids("Instant", {"1": 9, "2": 2}, future) == {2, 4}


# --- the rule --------------------------------------------------------------------------------


def test_a_cage_without_a_row_is_uncalibrated():
    assert calibration_problems({3}, {}, SHARED) == [CageProblem(3, UNCALIBRATED)]


@pytest.mark.parametrize(
    "row",
    [
        _row(3, volume=0),
        _row(3, volume=-0.03),
        _row(3, volume=math.nan),
        _row(3, volume=None),
        _row(3, width=0),
        _row(3, width=None),
    ],
)
def test_a_row_without_a_usable_volume_or_width_is_unusable(row):
    assert calibration_problems({3}, {3: row}, SHARED) == [CageProblem(3, UNUSABLE)]


def test_a_calibration_from_the_other_topology_is_stale():
    rows = {3: _row(3, topology="independent")}
    assert calibration_problems({3}, rows, SHARED) == [CageProblem(3, STALE, "independent")]


def test_an_untagged_legacy_row_is_the_shared_manifold():
    rows = {3: _row(3, topology=None)}
    assert calibration_problems({3}, rows, SHARED) == []
    assert calibration_problems({3}, rows, INDEPENDENT) == [
        CageProblem(3, STALE, "shared_manifold (legacy)")
    ]


def test_what_does_not_disqualify_a_calibration():
    """The delivery replays the cage's own width and rest; a missing rest
    replays the legacy 100 ms; relay ids are not compared (cage 16 is relay
    17 on two HATs)."""
    rows = {
        3: _row(3, width=30),  # settings say 20 ms
        4: _row(4, interval=None),
        16: dict(_row(16), relay_id=17),
    }
    assert calibration_problems({3, 4, 16}, rows, dict(SHARED, num_hats=2)) == []


def test_an_id_that_is_not_a_number_fails_closed():
    assert calibration_problems({"x"}, {}, SHARED) == [CageProblem("x", UNCALIBRATED)]


def test_pump_mode_is_never_refused():
    assert calibration_problems({3}, {}, {"hardware_mode": "pump"}) == []


def test_problems_come_back_in_cage_order():
    problems = calibration_problems({12, 3, 7}, {}, SHARED)
    assert [p.cage_id for p in problems] == [3, 7, 12]


def test_the_dialog_names_every_cage_and_the_fix():
    problems = [
        CageProblem(3, UNCALIBRATED),
        CageProblem(7, UNCALIBRATED),
        CageProblem(12, STALE, "shared_manifold (legacy)"),
    ]
    text = format_problems(problems, INDEPENDENT)
    assert "3 cage(s)" in text
    assert "Not calibrated: cage 3, cage 7" in text
    assert "this device uses independent" in text
    assert "cage 12 (measured on shared_manifold (legacy))" in text
    assert "unusable" not in text, "empty groups are left out"
    assert "Settings > Calibration" in text


# --- reading the calibrations ------------------------------------------------------------------


def test_a_failed_read_can_be_told_from_nothing_calibrated(database_handler, monkeypatch):
    def broken():
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(database_handler, "connect", broken)
    assert database_handler.get_all_valve_calibrations() == {}, "callers keep the old default"
    with pytest.raises(sqlite3.Error):
        database_handler.get_all_valve_calibrations(raise_errors=True)


# --- the Run path ------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PyQt5")
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


@pytest.fixture
def run_path(qapp, database_handler, system_controller, monkeypatch):
    """The real RunStopSection, started as the Run button would start it."""
    import utils.operation_lock as ol  # noqa: PLC0415
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from ui.run_stop_section import RunStopSection  # noqa: PLC0415

    ol._singleton = None
    shown = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: shown.append((a[1], a[2])))
    )
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append(a[1:3])))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(
        database_handler, "get_schedule_staggered_windows", lambda _sid: [{"window": 1}]
    )
    started = []
    section = RunStopSection(
        lambda *args: started.append(args),
        MagicMock(),
        MagicMock(),
        system_controller=system_controller,
        database_handler=database_handler,
    )
    monkeypatch.setattr(section, "show_progress_tracker", lambda _schedule: None)

    def run(schedule):
        section.schedule_drop_area.current_schedule = schedule
        assert ol.get_operation_lock().try_acquire("schedule"), "as run_program does"
        section.job_in_progress = True
        section._prepare_and_execute_schedule()
        return section

    yield SimpleRun(run=run, started=started, shown=shown, lock=ol.get_operation_lock)
    ol._singleton = None


class SimpleRun:
    def __init__(self, run, started, shown, lock):
        self.run, self.started, self.shown, self.lock = run, started, shown, lock


def _staggered(cages):
    from models.Schedule import Schedule  # noqa: PLC0415

    now = datetime.now()
    schedule = Schedule(
        schedule_id=1,
        name="t",
        water_volume=0.6,
        start_time=(now + timedelta(hours=1)).isoformat(),
        end_time=(now + timedelta(hours=2)).isoformat(),
        created_by=1,
        is_super_user=False,
        delivery_mode="staggered",
    )
    schedule.animals = list(range(1, len(cages) + 1))
    schedule.relay_unit_assignments = {str(i): cage for i, cage in enumerate(cages, start=1)}
    schedule.desired_water_outputs = {str(i): 0.6 for i in schedule.animals}
    return schedule


def _calibrate(database_handler, cage, topology="shared_manifold"):
    assert database_handler.save_valve_calibration(
        cage_id=cage,
        relay_id=cage,
        pulse_width_ms=30,
        volume_per_pulse_ml=0.034164,
        stddev_ml=0.001,
        cv_pct=1.0,
        num_samples=250,
        inter_pulse_interval_ms=1000,
        topology=topology,
    )


def test_a_run_with_an_uncalibrated_cage_is_refused_and_reset(run_path, database_handler):
    _calibrate(database_handler, 3)
    section = run_path.run(_staggered([3, 7]))

    assert run_path.started == [], "no worker was started"
    ((title, text),) = run_path.shown
    assert title == "Valve calibration needed"
    assert "Not calibrated: cage 7" in text
    assert run_path.lock().is_busy() is False, "the lock is free for the calibration wizard"
    assert section.job_in_progress is False
    assert section.run_button.text() == "Run"


def test_a_run_whose_cages_are_all_calibrated_starts(run_path, database_handler):
    for cage in (3, 7):
        _calibrate(database_handler, cage)
    run_path.run(_staggered([3, 7]))
    assert len(run_path.started) == 1
    assert run_path.shown == []


def test_a_stale_calibration_refuses_the_run(run_path, database_handler, system_controller):
    system_controller.settings["valve_topology"] = "independent"
    _calibrate(database_handler, 3, topology=None)  # legacy: measured on the manifold
    run_path.run(_staggered([3]))
    assert run_path.started == []
    ((title, text),) = run_path.shown
    assert "cage 3 (measured on shared_manifold (legacy))" in text


def test_pump_mode_runs_without_valve_calibrations(run_path, system_controller):
    system_controller.settings["hardware_mode"] = "pump"
    run_path.run(_staggered([3]))
    assert len(run_path.started) == 1


def test_an_instant_run_is_judged_on_the_deliveries_still_ahead(
    run_path, database_handler, monkeypatch
):
    from models.Schedule import Schedule  # noqa: PLC0415

    _calibrate(database_handler, 2)  # cage 9 is not calibrated
    now = datetime.now()
    rows = [
        (1, None, None, (now - timedelta(hours=1)).isoformat(), 0.6, None, 9),
        (2, None, None, (now + timedelta(hours=1)).isoformat(), 0.6, None, 2),
    ]
    monkeypatch.setattr(database_handler, "get_schedule_instant_deliveries", lambda _sid: rows)
    schedule = Schedule(1, "t", 0.6, None, None, 1, False, delivery_mode="instant")
    schedule.animals = [1, 2]
    schedule.relay_unit_assignments = {"1": 9, "2": 2}
    schedule.desired_water_outputs = {"1": 0.6, "2": 0.6}

    run_path.run(schedule)

    assert run_path.shown == []
    assert len(run_path.started) == 1, "cage 9's delivery is in the past"


def test_a_calibration_table_that_cannot_be_read_refuses_the_run(run_path, database_handler, monkeypatch):
    def broken(**_kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(database_handler, "get_all_valve_calibrations", broken)
    section = run_path.run(_staggered([3]))
    assert run_path.started == []
    ((title, _text),) = run_path.shown
    assert title == "Can't check valve calibrations"
    assert run_path.lock().is_busy() is False
    assert section.run_button.text() == "Run"


def test_an_instant_delivery_still_ahead_to_an_uncalibrated_cage_refuses_the_run(
    run_path, database_handler, monkeypatch
):
    from models.Schedule import Schedule  # noqa: PLC0415

    _calibrate(database_handler, 2)
    later = (datetime.now() + timedelta(hours=1)).isoformat()
    rows = [(1, None, None, later, 0.6, None, 9), (2, None, None, later, 0.6, None, 2)]
    monkeypatch.setattr(database_handler, "get_schedule_instant_deliveries", lambda _sid: rows)
    schedule = Schedule(1, "t", 0.6, None, None, 1, False, delivery_mode="instant")
    schedule.animals = [1, 2]
    schedule.relay_unit_assignments = {"1": 9, "2": 2}
    schedule.desired_water_outputs = {"1": 0.6, "2": 0.6}

    run_path.run(schedule)

    assert run_path.started == []
    ((title, text),) = run_path.shown
    assert title == "Valve calibration needed" and "Not calibrated: cage 9" in text


def test_a_refused_start_takes_down_the_loading_monitor(run_path, database_handler, monkeypatch):
    """run_program opens the Execution Monitor in its loading state before
    the checks run; every refusal must take it down again, as reset_ui does."""
    from ui.run_stop_section import RunStopSection  # noqa: PLC0415

    hidden = []
    gui = type("RodentRefreshmentGUI", (), {"hide_execution_monitor": lambda self: hidden.append(1)})
    monkeypatch.setattr(RunStopSection, "_get_parent_gui", lambda self: gui())

    run_path.run(_staggered([3]))  # cage 3 is not calibrated

    assert run_path.started == []
    assert hidden == [1]
