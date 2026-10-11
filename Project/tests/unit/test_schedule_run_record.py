"""Each schedule run is recorded: what was scheduled, planned and delivered.

The worker opens the run's record at its first due delivery (not at Run: a
staggered run can wait days for its window, and a Stop before anything was due
must leave each animal's previous run on the Animals tab). main._record_run_end
closes it once, on the GUI thread, from worker.finished (a run that ended on its
own) or from stop_program (an operator Stop, with the stop sequence's result),
and writes one logs row per operator Stop. At start-up, a run a crash left
open is marked interrupted.

Planned is whole pulses at the cage's calibration, rounded as the planner rounds
(utils.dose_rounding), so a normal run delivers exactly its plan. Each animal's
complete_ml, fixed in the plan, is the credited volume at or above which it
counts as completed: for a staggered window the worker's own completion test,
for instant deliveries half a pulse under the plan or the worker's own
tolerance of the ask, whichever is lower. Never decided by delivered <
scheduled.
"""

from __future__ import annotations

import ast
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from utils.stop_sequence import StopResult

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from strategies.delivery_strategy import DeliveryResult  # noqa: E402

Q = 0.034164  # Parker valve without the needle, as calibrated on the Pi
PROJECT = Path(__file__).resolve().parents[2]


class _Cancel:
    def __init__(self):
        self.flag = False

    def is_set(self):
        return self.flag

    def set(self):
        self.flag = True


def _worker(monkeypatch, mode, q=Q, round_up=False, deliver=None):
    """A RelayWorker built as the delivery tests build it, plus the run-record
    attributes __init__ sets."""
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415

    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.delivered_volumes, worker.failed_deliveries, worker.issued_targets = {}, {}, {}
    worker.schedule_id, worker.schedule_name, worker.started_by = 12, 'AM water', 3
    worker.hardware_mode, worker.mode = 'solenoid', mode
    worker.database_handler = MagicMock()
    worker.database_handler.start_schedule_run.return_value = 41
    worker.settings = {
        'round_doses_up': round_up,
        'relay_unit_assignments': {'3': 1, '5': 2},
        'valve_topology': 'shared_manifold',
    }
    worker.delivery_instants = []
    worker._cancel_requested = _Cancel()
    worker.run_plan, worker.run_id, worker.stop_reason = {}, None, None
    worker._run_open_tried, worker.run_end_recorded = False, False
    worker.retries = []
    monkeypatch.setattr(
        type(worker), "schedule_retry", lambda self, data: self.retries.append(data), raising=False
    )
    # No Python slots: a slot proxy outlives a short-lived worker in the
    # suite's one process. Tests that need a signal use QSignalSpy.

    strategy = MagicMock()
    strategy.pulse_volume_for = lambda cage_id: q
    strategy._cal_snapshot = {}
    strategy._sensor = None

    async def _exact(relay_unit_id, target_volume_ml, triggers_hint=None):
        n = round(target_volume_ml / q)
        return DeliveryResult(success=True, delivered_ml=n * q, pulses=n)

    strategy.deliver = deliver or _exact
    worker.strategy = strategy
    return worker


def _delivery(animal_id, volume, cage=1):
    return {
        'animal_id': animal_id,
        'relay_unit_id': cage,
        'water_volume': volume,
        'instant_time': datetime(2026, 10, 9, 8, 0),
        'schedule_id': 12,
    }


def _retry(worker):
    """Run the retry schedule_retry queued, through execute_delivery, as its
    30 s timer would."""
    asyncio.run(worker.execute_delivery(worker.retries.pop(0)))


def _window(worker, animal_id, target, cage, slots=None):
    """run_staggered_cycle's chunking: min(target - delivered, per_cycle)."""
    cycles = max(target / 0.2, 2)
    per = min(target / cycles, 0.2)
    for _ in range(slots if slots is not None else int(cycles) + 1):
        delivered = worker.delivered_volumes.get(animal_id, 0.0)
        if not delivered < target:
            break
        worker._handle_delivery(_delivery(animal_id, min(target - delivered, per), cage))
        if worker.retries:
            _retry(worker)


def _instants(*rows):
    """(animal_id, cage, volume, hours from now) -> delivery_instants rows."""
    return [
        {
            'animal_id': animal_id,
            'relay_unit_id': cage,
            'water_volume': volume,
            'delivery_time': (datetime.now() + timedelta(hours=hours)).isoformat(),
        }
        for animal_id, cage, volume, hours in rows
    ]


# The QApplication this module uses, kept for the rest of the session. When a
# QApplication is destroyed, PyQt5 deletes every QObject without a parent,
# main.control_signals and any SystemController a later test holds included.
_QAPP = []


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


@pytest.fixture
def main_module(monkeypatch):
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # main installs its own on import
    import main  # noqa: PLC0415

    db = MagicMock()
    db.finish_schedule_run.return_value = True  # this call closed the run
    animals_tab = SimpleNamespace(load_animals=MagicMock())
    monkeypatch.setattr(main, "database_handler", db, raising=False)
    monkeypatch.setattr(
        main,
        "login_system",
        SimpleNamespace(get_current_trainer=lambda: {'trainer_id': 3, 'username': 'alice'}),
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "gui",
        SimpleNamespace(projects_section=SimpleNamespace(animals_tab=animals_tab)),
        raising=False,
    )
    # A fresh one: main's module-level instance does not outlive another test
    # module's QApplication.
    monkeypatch.setattr(main, "control_signals", main.ControlSignals())
    monkeypatch.setattr(main, "_dbg", lambda _message: None)  # not the real debug log
    return main, db, animals_tab


def _finished(db):
    """finish_schedule_run's (run_id, end_reason, results), kwargs."""
    call = db.finish_schedule_run.call_args
    return call.args, call.kwargs


def _reloads(qapp, animals_tab):
    """How often the Animals tab reloaded, once the deferred calls have run."""
    qapp.processEvents()
    return animals_tab.load_animals.call_count


def _stop_with(monkeypatch, main, worker, sequence):
    """main.stop_program on ``worker``, with ``sequence`` as the stop sequence."""
    monkeypatch.setattr(main, "worker", worker)
    monkeypatch.setattr(main, "thread", None)
    monkeypatch.setattr(main, "relay_handler", None, raising=False)
    monkeypatch.setattr(main.stop_sequence, "execute_stop_sequence", sequence)
    return main.stop_program()


# --- the plan --------------------------------------------------------------------


@pytest.mark.parametrize("round_up,pulses_1ml,pulses_06", [(False, 29, 18), (True, 30, 18)])
def test_staggered_plan_is_the_window_target_in_whole_pulses(
    monkeypatch, round_up, pulses_1ml, pulses_06
):
    worker = _worker(monkeypatch, 'staggered', round_up=round_up)
    worker.animal_windows = {
        '3': {'target_volume': 1.0, 'relay_unit': 1},
        '5': {'target_volume': 0.6, 'relay_unit': 2},
    }
    plan = worker._build_run_plan()
    assert set(plan) == {3, 5}, "int animal ids"
    assert plan[3]['requested_ml'] == 1.0 and plan[3]['relay_unit_id'] == 1
    assert plan[3]['planned_ml'] == pytest.approx(pulses_1ml * Q)
    assert plan[5]['planned_ml'] == pytest.approx(pulses_06 * Q)
    assert plan[3]['q_ml'] == Q
    # complete as check_final_completion judges it: half a pulse, or at the dose
    tolerance = 1e-6 if round_up else Q / 2
    assert plan[3]['complete_ml'] == pytest.approx(1.0 - tolerance)


def test_staggered_plan_leaves_out_animals_without_a_target(monkeypatch):
    from PyQt5.QtCore import QTimer  # noqa: PLC0415

    worker = _worker(monkeypatch, 'staggered')
    worker.settings['desired_water_outputs'] = {'3': 0.5, '5': 0.0}
    worker.window_start = datetime.now() + timedelta(hours=1)
    worker.window_end = worker.window_start + timedelta(hours=1)
    worker.main_timer = QTimer(worker)
    worker.run_staggered_cycle()  # builds the windows, then waits for the window
    worker.main_timer.stop()
    assert set(worker._build_run_plan()) == {3}


@pytest.mark.parametrize(
    "round_up,pulses_5,pulses_6", [(False, 9 + 7 + 20, 23), (True, 9 + 8 + 21, 24)]
)
def test_instant_plan_counts_every_delivery_including_passed_ones(
    monkeypatch, round_up, pulses_5, pulses_6
):
    worker = _worker(monkeypatch, 'instant', round_up=round_up)
    worker.delivery_instants = _instants(
        (5, 2, 0.3, -1), (5, 2, 0.25, 1), (5, 2, 0.7, 3), (6, 1, 0.8, 2)
    )
    plan = worker._build_run_plan()
    assert plan[5]['requested_ml'] == pytest.approx(1.25), "the passed 0.3 mL is scheduled too"
    # Each delivery rounded on its own, as the planner does, and as the worker
    # credits them: 9 + 7 + 20 (9 + 8 + 21 under round-up), not the 37 pulses
    # of the 1.25 mL total.
    assert plan[5]['planned_ml'] == pytest.approx(pulses_5 * Q)
    assert plan[6]['planned_ml'] == pytest.approx(pulses_6 * Q)
    # half a pulse under the plan, or the worker's own tolerance of the ask,
    # whichever is lower: q/2 under nearest, 1e-6 under round-up
    tolerance = 1e-6 if round_up else Q / 2
    for animal_id in (5, 6):
        entry = plan[animal_id]
        assert entry['complete_ml'] == pytest.approx(
            min(entry['planned_ml'] - Q / 2, entry['requested_ml'] - tolerance)
        )


def test_uncalibrated_cage_plans_at_the_fallback_quantum(monkeypatch):
    worker = _worker(monkeypatch, 'instant', q=0.026)  # pulse_volume_for's default
    worker.delivery_instants = _instants((5, 2, 0.3, 1))
    assert worker._build_run_plan()[5]['planned_ml'] == pytest.approx(12 * 0.026)


def test_a_strategy_without_pulses_plans_the_scheduled_amount(monkeypatch):
    worker = _worker(monkeypatch, 'instant')
    del worker.strategy.pulse_volume_for  # pump, or continuous mode
    worker.delivery_instants = _instants((5, 2, 0.25, 1))
    entry = worker._build_run_plan()[5]
    assert entry['planned_ml'] == entry['requested_ml'] == 0.25
    assert entry['q_ml'] is None
    assert entry['complete_ml'] == pytest.approx(0.24)


# --- opening the record ----------------------------------------------------------------


def test_the_run_opens_once_at_its_first_due_delivery(monkeypatch):
    worker = _worker(monkeypatch, 'instant')
    worker.delivery_instants = _instants((5, 2, 0.3, 1), (5, 2, 0.3, 2))
    db = worker.database_handler

    worker._handle_delivery(_delivery(5, 0.3, 2))
    worker._handle_delivery(_delivery(5, 0.3, 2))

    db.start_schedule_run.assert_called_once()
    kwargs = db.start_schedule_run.call_args.kwargs
    assert (kwargs['schedule_id'], kwargs['schedule_name']) == (12, 'AM water')
    assert (kwargs['delivery_mode'], kwargs['started_by']) == ('instant', 3)
    assert kwargs['animals'] == [
        {
            'animal_id': 5,
            'relay_unit_id': 2,
            'requested_ml': 0.6,
            'planned_ml': round(18 * Q, 6),
        }
    ]
    assert worker.run_id == 41 and set(worker.run_plan) == {5}


def test_a_delivery_after_stop_opens_no_run(monkeypatch):
    worker = _worker(monkeypatch, 'instant')
    worker.delivery_instants = _instants((5, 2, 0.3, 1))
    worker._cancel_requested.set()
    worker._handle_delivery(_delivery(5, 0.3, 2))
    worker.database_handler.start_schedule_run.assert_not_called()
    assert worker.run_id is None


@pytest.mark.parametrize(
    "refusal,said",
    [
        (RuntimeError("database is locked"), "database is locked"),
        (None, "the database did not accept it"),  # start_schedule_run's None
    ],
    ids=["raises", "refused"],
)
def test_a_run_that_cannot_be_recorded_still_delivers(monkeypatch, refusal, said):
    from PyQt5.QtTest import QSignalSpy  # noqa: PLC0415

    worker = _worker(monkeypatch, 'instant')
    worker.delivery_instants = _instants((5, 2, 0.3, 1))
    if refusal is None:
        worker.database_handler.start_schedule_run.return_value = None
    else:
        worker.database_handler.start_schedule_run.side_effect = refusal
    progress = QSignalSpy(worker.progress)

    worker._handle_delivery(_delivery(5, 0.3, 2))

    assert worker.delivered_volumes[5] == pytest.approx(9 * Q), "the delivery still ran"
    assert worker.run_id is None
    assert set(worker.run_plan) == {5}, "the plan is kept for the Stop's audit row"
    lines = [args[0] for args in progress if "Could not record this run" in args[0]]
    assert lines == [
        f"Could not record this run in the run history: {said}. Deliveries continue, "
        "and each one is still in the delivery log."
    ]


def test_a_new_worker_starts_with_no_run():
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415

    controller = SimpleNamespace(
        settings={'hardware_mode': 'solenoid'},
        settings_updated=SimpleNamespace(connect=lambda _s: None),
        database_handler=None,
    )
    settings = {'schedule_id': 12, 'window_start': 0, 'window_end': 1, 'mode': 'instant'}
    worker = RelayWorker(
        dict(settings, schedule_name='AM water', started_by=3), None, None, controller
    )
    assert (worker.schedule_name, worker.started_by) == ('AM water', 3)
    assert (worker.run_id, worker.run_plan, worker.stop_reason) == (None, {}, None)
    assert worker._run_open_tried is False and worker.run_end_recorded is False

    # The history needs a name (schedule_name is NOT NULL).
    unnamed = RelayWorker(settings, None, None, controller)
    assert (unnamed.schedule_name, unnamed.started_by) == ('Schedule 12', None)


# --- closing the record ---------------------------------------------------------------


@pytest.mark.parametrize("round_up", [False, True])
def test_a_natural_end_records_every_animal_completed(monkeypatch, main_module, qapp, round_up):
    main, db, animals_tab = main_module
    worker = _worker(monkeypatch, 'staggered', round_up=round_up)
    worker.animal_windows = {
        '3': {'target_volume': 1.0, 'relay_unit': 1},
        '5': {'target_volume': 0.6, 'relay_unit': 2},
    }
    _window(worker, '3', 1.0, 1)
    _window(worker, '5', 0.6, 2)

    main._on_run_finished(worker)

    (run_id, reason, results), kwargs = _finished(db)
    assert (run_id, reason) == (41, 'completed')
    for animal_id in (3, 5):
        delivered, outcome = results[animal_id]
        assert outcome == 'completed'
        assert delivered == pytest.approx(worker.run_plan[animal_id]['planned_ml']), "1:1"
    assert kwargs == {'stopped_by': None, 'relays_confirmed_off': None, 'worker_exited': None}
    db.log_action.assert_not_called()
    animals_tab.load_animals.assert_not_called()  # deferred, out of the caller's way
    assert _reloads(qapp, animals_tab) == 1


@pytest.mark.parametrize("round_up,pulses", [(False, 23), (True, 24)])
def test_an_instant_run_that_ends_by_itself_is_completed_1_to_1(
    monkeypatch, main_module, round_up, pulses
):
    main, db, _tab = main_module
    worker = _worker(monkeypatch, 'instant', round_up=round_up)
    worker.delivery_instants = _instants((5, 2, 0.8, 1))
    worker._handle_delivery(_delivery(5, 0.8, 2))

    main._on_run_finished(worker)

    (_run_id, reason, results), _kwargs = _finished(db)
    assert worker.run_plan[5]['planned_ml'] == pytest.approx(pulses * Q)
    assert results == {5: (round(pulses * Q, 6), 'completed')}, "delivered = planned"
    assert reason == 'completed'


def test_an_operator_stop_is_recorded_once_with_one_audit_row(monkeypatch, main_module, qapp):
    main, db, animals_tab = main_module
    worker = _worker(monkeypatch, 'staggered')
    worker.animal_windows = {
        '3': {'target_volume': 0.4, 'relay_unit': 1},
        '5': {'target_volume': 1.0, 'relay_unit': 2},
    }
    _window(worker, '3', 0.4, 1)  # had its whole dose before Stop
    _window(worker, '5', 1.0, 2, slots=2)  # stopped after two chunks
    worker.stop_reason = 'operator'

    main._on_run_finished(worker)  # finished inside the stop sequence: deferred
    db.finish_schedule_run.assert_not_called()
    main._record_run_end(worker, StopResult(True, True))
    main._record_run_end(worker, StopResult(True, True))
    main._on_run_finished(worker)

    db.finish_schedule_run.assert_called_once()
    (_run_id, reason, results), kwargs = _finished(db)
    assert reason == 'stopped'
    assert results[3][1] == 'completed' and results[5][1] == 'stopped'
    assert kwargs == {'stopped_by': 3, 'relays_confirmed_off': True, 'worker_exited': True}
    db.log_action.assert_called_once_with(
        3,
        'schedule_stopped',
        "AM water (schedule 12, run 41) stopped by alice: animal 3 0.410 of 0.410 mL "
        "planned; animal 5 0.410 of 0.991 mL planned. Relays confirmed off: yes; "
        "worker exited: yes",
    )
    # The Stop reloads the Animals tab too, so a tab on screen shows the
    # stopped run at once: deferred, and once however often the close repeats.
    animals_tab.load_animals.assert_not_called()
    assert _reloads(qapp, animals_tab) == 1


def test_a_stop_before_the_first_delivery_writes_only_the_audit_row(
    monkeypatch, main_module, qapp
):
    main, db, animals_tab = main_module
    worker = _worker(monkeypatch, 'staggered')
    worker.stop_reason = 'operator'

    main._record_run_end(worker, StopResult(True, False))

    db.finish_schedule_run.assert_not_called()
    db.log_action.assert_called_once_with(
        3,
        'schedule_stopped',
        "AM water (schedule 12) stopped by alice: before its first delivery. Relays "
        "confirmed off: yes; worker exited: no",
    )
    assert _reloads(qapp, animals_tab) == 0, "no record, so the previous run stays on the tab"


@pytest.mark.parametrize("round_up", [False, True])
@pytest.mark.parametrize("mode", ["instant", "staggered"])
def test_one_pulse_short_of_the_plan_is_incomplete(monkeypatch, main_module, mode, round_up):
    main, db, _tab = main_module
    worker = _worker(monkeypatch, mode, round_up=round_up)
    if mode == 'instant':
        worker.delivery_instants = _instants((3, 1, 0.5, 1))
    else:
        worker.animal_windows = {'3': {'target_volume': 0.5, 'relay_unit': 1}}
    worker.run_plan, worker.run_id = worker._build_run_plan(), 41
    worker.delivered_volumes = {
        3 if mode == 'instant' else '3': worker.run_plan[3]['planned_ml'] - Q
    }

    main._on_run_finished(worker)

    (_run_id, reason, results), _kwargs = _finished(db)
    assert results[3][1] == 'incomplete' and reason == 'ended_short'


def _one_pulse_short(monkeypatch, main, db, mode, dose, q, round_up):
    """The outcome of a run that credited one pulse less than its plan."""
    worker = _worker(monkeypatch, mode, q=q, round_up=round_up)
    if mode == 'instant':
        worker.delivery_instants = _instants((3, 1, dose, 1))
    else:
        worker.animal_windows = {'3': {'target_volume': dose, 'relay_unit': 1}}
    worker.run_plan, worker.run_id = worker._build_run_plan(), 41
    pulses = round(worker.run_plan[3]['planned_ml'] / q)
    worker.delivered_volumes = {3 if mode == 'instant' else '3': (pulses - 1) * q}

    main._on_run_finished(worker)

    (_run_id, reason, results), _kwargs = _finished(db)
    return pulses, results[3][1], reason


# 0.05 mL at 0.02 mL per pulse is an exact half-pulse tie (2.5 pulses): the
# plan rounds it up to 3, and 2 pulses are within half a pulse of the dose.
# 0.07 mL is a tie too (3.5 pulses), where 0.07 - 0.01 comes out a hair above
# 0.06 in floating point: the record's 1e-9 slack keeps 3 pulses within it.
# Below 0.02 mL per pulse the worker's 0.01 mL floor exceeds half a pulse:
# 0.31 mL at 0.015 plans 21 pulses, and 20 are within 0.01 mL of the dose.
_WITHIN_TOLERANCE = pytest.mark.parametrize(
    "dose,q,planned",
    [(0.05, 0.02, 3), (0.07, 0.02, 4), (0.31, 0.015, 21)],
    ids=["tie", "tie_in_floating_point", "small_q"],
)


@_WITHIN_TOLERANCE
@pytest.mark.parametrize("mode", ["instant", "staggered"])
def test_one_pulse_short_within_the_workers_own_tolerance_is_completed(
    monkeypatch, main_module, mode, dose, q, planned
):
    """Where RRR's own completion test counts one pulse short of the plan as
    done (nearest rounding), the record agrees: the cell is not red."""
    main, db, _tab = main_module
    assert _one_pulse_short(monkeypatch, main, db, mode, dose, q, round_up=False) == (
        planned,
        'completed',
        'completed',
    )


@_WITHIN_TOLERANCE
@pytest.mark.parametrize("mode", ["instant", "staggered"])
def test_round_up_counts_one_pulse_short_as_incomplete(
    monkeypatch, main_module, mode, dose, q, planned
):
    """Round-up promises the dose (its tolerance is 1e-6): the same credit is red."""
    main, db, _tab = main_module
    assert _one_pulse_short(monkeypatch, main, db, mode, dose, q, round_up=True) == (
        planned,
        'incomplete',
        'ended_short',
    )


def test_a_window_the_worker_completed_after_a_late_close_is_completed(monkeypatch, main_module):
    """A close that needed a retry is credited by open time (+0.3 pulse here),
    so the window closes off the pulse grid: 14.3 pulses for 0.5 mL, planned 15.
    The worker's completion pass calls that done (within half a pulse of the
    dose); the record must agree with the Terminal."""
    main, db, _tab = main_module
    calls = {'n': 0}

    async def _late_close_once(relay_unit_id, target_volume_ml, triggers_hint=None):
        calls['n'] += 1
        n = round(target_volume_ml / Q)
        if calls['n'] == 2:
            return DeliveryResult(success=False, delivered_ml=(n + 0.3) * Q, pulses=n)
        return DeliveryResult(success=True, delivered_ml=n * Q, pulses=n)

    worker = _worker(monkeypatch, 'staggered', deliver=_late_close_once)
    worker.animal_windows = {'3': {'target_volume': 0.5, 'relay_unit': 1}}
    _window(worker, '3', 0.5, 1)
    assert worker.delivered_volumes['3'] == pytest.approx(14.3 * Q)

    main._on_run_finished(worker)

    (_run_id, reason, results), _kwargs = _finished(db)
    assert results[3] == (pytest.approx(14.3 * Q), 'completed') and reason == 'completed'


@pytest.mark.parametrize("round_up,dose", [(False, 0.3), (True, 0.28)], ids=["nearest", "up"])
def test_a_late_close_retry_on_an_instant_delivery_is_completed(
    monkeypatch, main_module, round_up, dose
):
    """The first attempt banks 3 pulses and one late close priced at 1.3 pulses,
    then fails; the retry plans the ask minus that (5 pulses). 8.3 pulses land
    within the worker's tolerance of the ask, but short of the 9 planned by
    more than half a pulse: half a pulse under the plan alone would call it
    red."""
    main, db, _tab = main_module
    calls = {'n': 0}

    async def _late_close_first(relay_unit_id, target_volume_ml, triggers_hint=None):
        calls['n'] += 1
        if calls['n'] == 1:
            return DeliveryResult(success=False, delivered_ml=3.3 * Q, pulses=3)
        n = round(target_volume_ml / Q)
        return DeliveryResult(success=True, delivered_ml=n * Q, pulses=n)

    worker = _worker(monkeypatch, 'instant', round_up=round_up, deliver=_late_close_first)
    worker.delivery_instants = _instants((5, 2, dose, 1))
    worker._handle_delivery(_delivery(5, dose, 2))
    _retry(worker)
    assert worker.delivered_volumes[5] == pytest.approx(8.3 * Q)
    assert worker.run_plan[5]['planned_ml'] - Q / 2 > 8.3 * Q

    main._on_run_finished(worker)

    (_run_id, reason, results), _kwargs = _finished(db)
    assert results[5] == (pytest.approx(8.3 * Q), 'completed') and reason == 'completed'


def test_an_instant_run_with_a_passed_delivery_ends_incomplete(monkeypatch, main_module):
    """Two animals with one delivery each, as RRR creates them; Run pressed
    after animal 5's time. The run covers the whole schedule: animal 5 is in
    it with nothing delivered."""
    main, db, _tab = main_module
    worker = _worker(monkeypatch, 'instant')
    worker.delivery_instants = _instants((5, 2, 0.3, -1), (6, 1, 0.25, 1))
    worker._handle_delivery(_delivery(6, 0.25, 1))  # the worker skips the passed one

    main._on_run_finished(worker)

    (_run_id, reason, results), _kwargs = _finished(db)
    assert results == {5: (0.0, 'incomplete'), 6: (round(7 * Q, 6), 'completed')}
    assert reason == 'ended_short'
    animals = db.finish_schedule_run.call_args.args[2]
    assert set(animals) == {5, 6}


def test_the_circuit_breaker_ends_the_run_incomplete(monkeypatch, main_module):
    from PyQt5.QtCore import QTimer  # noqa: PLC0415
    from PyQt5.QtTest import QSignalSpy  # noqa: PLC0415

    main, db, _tab = main_module

    async def _fails(relay_unit_id, target_volume_ml, triggers_hint=None):
        return DeliveryResult(success=False, delivered_ml=0.0, pulses=0)

    worker = _worker(monkeypatch, 'staggered', deliver=_fails)
    worker.animal_windows = {'3': {'target_volume': 0.6, 'relay_unit': 1, 'last_delivery': None}}
    worker.settings['desired_water_outputs'] = {'3': 0.6}
    worker.monitor_timer, worker.main_timer = QTimer(), QTimer()
    worker.timers, worker.retry_timers, worker._is_running = [], {}, True
    worker._completion_retry_counts = {'3': 10}  # the breaker's last pass
    finished = QSignalSpy(worker.finished)
    _window(worker, '3', 0.6, 1, slots=1)
    worker.retries.clear()

    worker.check_final_completion()  # -> _log_undelivered, stop(), finished
    assert len(finished) == 1
    main._on_run_finished(worker)  # what the queued finished connection runs

    (_run_id, reason, results), _kwargs = _finished(db)
    assert results[3] == (0.0, 'incomplete') and reason == 'ended_short'


def test_the_record_is_written_after_the_worker_is_deleted(monkeypatch, main_module):
    from PyQt5 import sip  # noqa: PLC0415

    main, db, _tab = main_module
    worker = _worker(monkeypatch, 'instant')
    worker.delivery_instants = _instants((5, 2, 0.3, 1))
    worker._handle_delivery(_delivery(5, 0.3, 2))
    sip.delete(worker)  # deleteLater can run before the queued slot does

    main._on_run_finished(worker)

    db.finish_schedule_run.assert_called_once()


def test_a_failure_to_record_never_raises(monkeypatch, main_module, capsys):
    main, db, _tab = main_module
    worker = _worker(monkeypatch, 'instant')
    worker.delivery_instants = _instants((5, 2, 0.3, 1))
    worker._handle_delivery(_delivery(5, 0.3, 2))
    db.finish_schedule_run.side_effect = RuntimeError("database is locked")

    main._record_run_end(worker, StopResult(True, True))

    assert (
        "[RUN] Could not record how this run ended: database is locked. Each delivery is "
        "in the delivery log." in capsys.readouterr().out
    )


def test_a_refused_finish_prints_the_line(monkeypatch, main_module, capsys):
    """finish_schedule_run returns False, without raising, when the database
    refused the write (a lock held over about 5 s): the run stays 'running'
    until the next start marks it interrupted, and the Terminal says so."""
    main, db, _tab = main_module
    db.finish_schedule_run.return_value = False
    worker = _worker(monkeypatch, 'instant')
    worker.delivery_instants = _instants((5, 2, 0.3, 1))
    worker._handle_delivery(_delivery(5, 0.3, 2))

    main._on_run_finished(worker)

    db.finish_schedule_run.assert_called_once()
    assert (
        "[RUN] Could not record how this run ended: the database did not accept it. The "
        "Animals tab shows it as running until RRR restarts; each delivery is in the "
        "delivery log." in capsys.readouterr().out
    )


def test_a_run_the_database_refused_still_records_the_stop_figures(monkeypatch, main_module, qapp):
    """start_schedule_run returned None: there is no run to close, but water
    went out, so the Stop's audit row gives the figures, not "before its first
    delivery"."""
    from PyQt5.QtTest import QSignalSpy  # noqa: PLC0415

    main, db, animals_tab = main_module
    worker = _worker(monkeypatch, 'instant')
    worker.database_handler.start_schedule_run.return_value = None
    worker.delivery_instants = _instants((5, 2, 0.3, 1))
    progress = QSignalSpy(worker.progress)
    worker._handle_delivery(_delivery(5, 0.3, 2))
    assert any("Could not record this run in the run history" in args[0] for args in progress)

    _stop_with(monkeypatch, main, worker, lambda *_args, **_kwargs: StopResult(True, True))

    db.finish_schedule_run.assert_not_called()
    db.log_action.assert_called_once_with(
        3,
        'schedule_stopped',
        "AM water (schedule 12) stopped by alice: animal 5 0.307 of 0.307 mL planned. "
        "Relays confirmed off: yes; worker exited: yes",
    )
    assert _reloads(qapp, animals_tab) == 0


def test_a_finished_signal_during_the_stop_sequence_leaves_the_record_to_stop(
    monkeypatch, main_module, qapp
):
    """The worker's queued finished can run inside the Stopping dialog's event
    pump, before the stop sequence has its result. It must leave the record
    to stop_program, which writes it with that result: here the relays were
    not confirmed off."""
    main, db, animals_tab = main_module
    worker = _worker(monkeypatch, 'instant')
    worker.delivery_instants = _instants((5, 2, 0.3, 1), (6, 1, 0.5, 2))
    worker._handle_delivery(_delivery(5, 0.3, 2))  # animal 6's time has not come
    during = []

    def _sequence(handler, worker_obj, thread_obj, signals, dialog_factory=None):
        main._on_run_finished(worker_obj)  # the queued finished, run by the dialog's pump
        during.append(db.finish_schedule_run.call_count)
        return StopResult(relays_confirmed_off=False, worker_exited=True)

    result = _stop_with(monkeypatch, main, worker, _sequence)

    assert during == [0], "nothing is recorded before the sequence has its result"
    assert result == StopResult(False, True)
    db.finish_schedule_run.assert_called_once()
    (run_id, reason, results), kwargs = _finished(db)
    assert (run_id, reason) == (41, 'stopped')
    assert results == {5: (round(9 * Q, 6), 'completed'), 6: (0.0, 'stopped')}
    assert kwargs == {'stopped_by': 3, 'relays_confirmed_off': False, 'worker_exited': True}
    assert db.log_action.call_args.args[2].endswith("Relays confirmed off: no; worker exited: yes")
    assert _reloads(qapp, animals_tab) == 1, "one reload, from the Stop's record"


# --- the hooks in main.py -----------------------------------------------------------


def test_run_program_binds_the_run_end_hook_to_its_worker(monkeypatch, main_module, qapp):
    from PyQt5.QtCore import QEvent, QObject, pyqtSignal, pyqtSlot  # noqa: PLC0415

    main, _db, _tab = main_module
    made, order = [], []

    class _Worker(QObject):
        finished = pyqtSignal()
        progress = pyqtSignal(str)
        volume_updated = pyqtSignal(str, float)

        def __init__(self, settings, *_args):
            super().__init__()
            self.settings = settings
            self.stop_reason = None  # as RelayWorker.__init__ sets it
            made.append(self)

        @pyqtSlot()
        def run_cycle(self):
            self.finished.emit()

        @pyqtSlot()
        def stop(self):
            pass

    class _Controller(QObject):
        settings = {}

    monkeypatch.setattr(main, "RelayWorker", _Worker)
    monkeypatch.setattr(main, "system_controller", _Controller(), raising=False)
    monkeypatch.setattr(main, "controller", SimpleNamespace(pump_controller=None), raising=False)
    monkeypatch.setattr(main, "relay_handler", None, raising=False)
    monkeypatch.setattr(main, "notification_handler", None, raising=False)
    monkeypatch.setattr(main, "thread", None)
    monkeypatch.setattr(main, "worker", None)
    monkeypatch.setattr(main, "_record_run_end", lambda w, r=None: order.append(('record', w)))
    monkeypatch.setattr(main, "cleanup", lambda: order.append(('cleanup', main.worker)))
    schedule = SimpleNamespace(name='AM water', schedule_id=12, instant_deliveries=[])

    assert main.run_program(schedule, 'instant', 0, 1) is True
    assert main.thread.wait(5000)
    for _ in range(5):
        qapp.processEvents()
    # Let deleteLater (worker, thread, slot proxies) finish before the next test.
    qapp.sendPostedEvents(None, QEvent.DeferredDelete)

    assert made[0].settings['schedule_name'] == 'AM water'
    assert made[0].settings['started_by'] == 3
    assert order[0] == ('record', made[0]), "the record first, bound to this worker"
    assert [kind for kind, _ in order] == ['record', 'cleanup']


def test_stop_program_records_with_the_worker_it_captured(monkeypatch, main_module):
    main, _db, _tab = main_module
    worker = SimpleNamespace(stop_reason=None)
    seen, recorded = {}, []
    result = StopResult(True, True)

    def _sequence(handler, worker_obj, thread_obj, signals, dialog_factory=None):
        seen['worker'], seen['stop_reason'] = worker_obj, worker_obj.stop_reason
        main.worker = None  # what a queued cleanup() does inside the sequence's dialog
        return result

    monkeypatch.setattr(main, "_record_run_end", lambda w, r=None: recorded.append((w, r)))

    assert _stop_with(monkeypatch, main, worker, _sequence) is result
    assert seen == {'worker': worker, 'stop_reason': 'operator'}
    assert recorded == [(worker, result)]


def test_stop_program_records_even_when_the_sequence_fails(monkeypatch, main_module):
    main, _db, _tab = main_module
    worker = SimpleNamespace(stop_reason=None)
    recorded = []

    def _broken(*_args, **_kwargs):
        raise RuntimeError("teardown failed")

    monkeypatch.setattr(main, "_record_run_end", lambda w, r=None: recorded.append((w, r)))

    result = _stop_with(monkeypatch, main, worker, _broken)

    assert result == StopResult(relays_confirmed_off=False, worker_exited=True)
    assert recorded == [(worker, result)]


@pytest.mark.parametrize("start_up", ["setup", "_create_gui_from_components"])
def test_start_up_marks_interrupted_runs_before_the_window_is_built(start_up):
    """Neither start-up path can run headless (see test_settings_tab_built_once),
    so the order is pinned statically: the database first, then the
    reconciliation, then the GUI, whose Animals tab reads each animal's last
    run. Not in DatabaseHandler.create_tables, which --selftest and
    tools/set_valve_topology.py run while RRR may be running."""
    tree = ast.parse((PROJECT / "main.py").read_text())
    body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == start_up)
    source = [ast.unparse(statement) for statement in body.body]
    db = next(i for i, s in enumerate(source) if s.startswith("database_handler = "))
    mark = source.index("_mark_interrupted_runs(database_handler)")
    gui = next(i for i, s in enumerate(source) if s.startswith("gui = RodentRefreshmentGUI("))
    assert db < mark < gui


def test_marking_interrupted_runs_never_raises(main_module, capsys):
    main, _db, _tab = main_module
    db = MagicMock()
    db.mark_interrupted_schedule_runs.return_value = 2
    main._mark_interrupted_runs(db)
    assert "2 schedule run(s) were still running when RRR last closed" in capsys.readouterr().out

    db.mark_interrupted_schedule_runs.side_effect = RuntimeError("no such table")
    main._mark_interrupted_runs(db)
    assert "Could not check for runs cut off" in capsys.readouterr().out


def test_the_start_up_lines_also_go_to_the_debug_log(monkeypatch, main_module, capsys):
    """They are printed before stdout goes to the Terminal tab, so outside
    rrr.service's journal only the debug log keeps them."""
    main, _db, _tab = main_module
    logged = []
    monkeypatch.setattr(main, "_dbg", logged.append)
    db = MagicMock()

    db.mark_interrupted_schedule_runs.return_value = 0
    main._mark_interrupted_runs(db)
    assert (capsys.readouterr().out, logged) == ("", []), "nothing was cut off"

    db.mark_interrupted_schedule_runs.return_value = 1
    main._mark_interrupted_runs(db)
    line = (
        "[RUN] 1 schedule run(s) were still running when RRR last closed; they are now "
        "recorded as interrupted. What they delivered is in the delivery log "
        "(tools/gravimetric_check.py daily)."
    )
    assert (capsys.readouterr().out, logged) == (line + "\n", [line])

    logged.clear()
    db.mark_interrupted_schedule_runs.side_effect = RuntimeError("no such table")
    main._mark_interrupted_runs(db)
    line = "[RUN] Could not check for runs cut off when RRR last closed: no such table"
    assert (capsys.readouterr().out, logged) == (line + "\n", [line])
