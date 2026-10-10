"""Each schedule run is recorded: what was scheduled, planned and delivered.

The worker opens the run's record at its first due delivery (not at Run: a
staggered run can wait days for its window, and a Stop before anything was due
must leave each animal's previous run on the Animals tab).

Planned is whole pulses at the cage's calibration, rounded as the planner rounds
(utils.dose_rounding), so a normal run delivers exactly its plan. Each animal's
complete_ml, fixed in the plan, is the credited volume at or above which it
counts as completed: for a staggered window the worker's own completion test,
for instant deliveries half a pulse under the plan or the worker's own
tolerance of the ask, whichever is lower. Never decided by delivered <
scheduled.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from strategies.delivery_strategy import DeliveryResult  # noqa: E402

Q = 0.034164  # Parker valve without the needle, as calibrated on the Pi


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
