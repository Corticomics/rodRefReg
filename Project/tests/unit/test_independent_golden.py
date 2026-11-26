"""The independent valve path, pinned relay by relay (the golden corpus).

One syringe and one valve per animal: no master valve, no manifold, nothing
to prime. 3.0.0 removes the shared manifold, so this is the path that stays.
These scenarios run the real code over the stateful fake relay handler of
conftest.py: the valve controller the device builds for the independent
topology (utils.topology.build_solenoid_controller), SolenoidFlowStrategy,
the calibration wizard's pulse worker, the Priming panel and RelayWorker.
The profile is the production one: 30 ms pulses, a 1000 ms rest, 32.936 uL
per pulse (the Parker 003-0257-900 with the upstream needle). Pulse mode
only.

Each scenario pins the exact sequence of relay writes (ids, state, order)
and, where the scenario has them, the waits, the DeliveryResult, the
operator's [VALVE ERROR], [VALVE CRITICAL] and [VALVE OK] lines, the
hardware lock and the dispensing_history row. Every expected value is a
literal, so a diff shows.

The rule from here on: a PR that changes a relay write on this path updates
this file on purpose and says why in its body. A PR that only deletes or
moves code (the continuous-mode removal, the master-valve removal) leaves it
as it is; when the master code goes, the one place that may change is the
builder in ``_valves`` (with its import).

  G1   a nine-pulse dose
  G2   a dose the pre-flight refuses: no relay moves
  G3   a Stop during the rest after pulse 4
  G4   the open of pulse 4 does not reach its relay
  G5   the close of pulse 2 is lost once, then closes on the retry
  G6   the cage's close never gets through
  G7   cage 1, then cage 2, from one strategy
  G8   a ten-pulse calibration run
  G9   priming: Open Selected, Close Selected, CLOSE ALL RELAYS
  G10  a staggered slot through RelayWorker, and its ledger row
  G11  an instant retry after a relay fault sends only the rest

Fault-injection indexes count every write attempt, the lost ones included
(FakeRelayHandler.fail_on): with no prime and no hold, pulse n opens at
write 2n - 1 and closes at write 2n.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from strategies.delivery_strategy import DeliveryResult
from strategies.solenoid_flow_strategy import SolenoidFlowStrategy
from utils.topology import build_solenoid_controller
from version import __version__

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

Q = 0.032936  # mL per pulse: the Parker 003-0257-900 at 30 ms, with the upstream needle
INDEPENDENT = {'valve_topology': 'independent', 'num_hats': 1, 'global_master_relay_id': 16}
CAGE_MAP = {cage: cage for cage in range(1, 16)}  # one HAT: cages 1-15 on relays 1-15
SETTINGS = {
    **INDEPENDENT,
    'use_pulse_delivery': True,
    'pulse_settling_ms': 100,
    'max_pulses_per_delivery': 100,
    'max_pulse_delivery_time_s': 120.0,
}

RELAY_FAULT = "Check the relay HAT; one that was not found at start-up needs RRR restarted."
STILL_OPEN = (
    "[VALVE CRITICAL] cage 1: the cage valve close did not reach its relay; the valve may "
    "still be OPEN. Check the rig; the Stop button switches every relay off and stops the "
    "schedule."
)


def _valves(fake):
    """The valve controller the device builds for the independent topology.

    The one place in this file (with its import) that may change when the
    master code goes."""
    return build_solenoid_controller(fake, INDEPENDENT, CAGE_MAP)


def _calibration(cage, calibration_id):
    """A cage's valve_calibration row as the database returns it."""
    return {
        'calibration_id': calibration_id,
        'cage_id': cage,
        'relay_id': cage,
        'pulse_width_ms': 30,
        'volume_per_pulse_ml': Q,
        'inter_pulse_interval_ms': 1000,
        'topology': 'independent',
    }


class _Calibrations:
    """The strategy's two calibration reads, over fixed rows."""

    def __init__(self, rows):
        self._rows = rows

    def get_all_valve_calibrations(self):
        return dict(self._rows)

    def get_valve_calibration(self, cage_id):
        return self._rows.get(cage_id)


class _Clock:
    """The event loop's clock: it moves only when the delivery waits."""

    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now


class _Golden:
    """The real strategy over the fake relay handler, with every wait recorded.

    asyncio.sleep is recorded instead of slept, and the rest between pulses
    as one figure, as test_topology_trace.py does; both move the clock, so a
    measured duration is exact. A Stop is the strategy's cooperative cancel
    (request_cancel), the call the Stop sequence makes into a delivery;
    ``on_rest`` presses it during a given rest (numbered from 1).
    """

    def __init__(self, fake, monkeypatch, cages=(1,)):
        self.clock = _Clock()
        self.sleeps = []
        self.rests = []
        self.on_rest = None
        rows = {cage: _calibration(cage, calibration_id=cage) for cage in cages}
        self.strategy = SolenoidFlowStrategy(
            solenoid_controller=_valves(fake),
            flow_sensor=None,  # production runs calibration-only
            calibration_store=None,
            settings=dict(SETTINGS),
            database_handler=_Calibrations(rows),
        )
        monkeypatch.setattr(asyncio, 'sleep', self._sleep)
        monkeypatch.setattr(asyncio, 'get_event_loop', lambda: self.clock)
        monkeypatch.setattr(self.strategy, '_rest_between_pulses', self._rest)

    async def _sleep(self, seconds):
        self.sleeps.append(round(float(seconds), 3))
        self.clock.now += float(seconds)

    async def _rest(self, interval_ms):
        self.rests.append(int(interval_ms))
        if self.on_rest is not None:
            self.on_rest(len(self.rests))
        self.clock.now += interval_ms / 1000.0
        return self.strategy._check_cancelled()

    def deliver(self, cage, volume_ml):
        return asyncio.run(self.strategy.deliver(relay_unit_id=cage, target_volume_ml=volume_ml))


def _operator_lines(out):
    """The lines the operator reads: [VALVE ERROR], [VALVE CRITICAL] and [VALVE OK]."""
    prefixes = ("[VALVE ERROR]", "[VALVE CRITICAL]", "[VALVE OK]")
    return [line for line in out.splitlines() if line.startswith(prefixes)]


def _lose_closes(fake, monkeypatch):
    """Every close of relay 1 is lost; its opens still get through."""
    real = fake.set_relays

    def lossy(relay_ids, state):
        if tuple(relay_ids) == (1,) and not state:
            fake.dropped.append(((1,), 0))
            return False
        return real(relay_ids, state)

    monkeypatch.setattr(fake, "set_relays", lossy)


# --- the delivery strategy ------------------------------------------------------------------


def test_g1_a_nine_pulse_dose_is_nine_cage_pulses_and_one_close(
    fake_relay_handler, monkeypatch, capsys
):
    """The copy of test_topology_trace.py's
    test_independent_trace_is_the_cage_pulses_and_nothing_else, with the
    whole result."""
    golden = _Golden(fake_relay_handler, monkeypatch)

    result = golden.deliver(1, 0.296424)

    assert fake_relay_handler.trace == [((1,), 1), ((1,), 0)] * 9 + [((1,), 0)]
    assert golden.sleeps == [0.03, 0.1] * 9  # each pulse: open 30 ms, settle 100 ms
    assert golden.rests == [1000] * 8  # between pulses, not after the last
    assert result == DeliveryResult(
        success=True,
        delivered_ml=pytest.approx(0.296424),
        duration_s=pytest.approx(9.17),
        pulses=9,
        volume_per_pulse_ml=0.032936,
        warning=None,
        calibration_id=1,
        pulse_width_ms=30,
        inter_pulse_interval_ms=1000,
    )
    assert fake_relay_handler.dropped == []
    assert fake_relay_handler.energized() == set()
    assert _operator_lines(capsys.readouterr().out) == []


def test_g2_a_dose_over_the_pulse_limit_is_refused_before_any_relay_moves(
    fake_relay_handler, monkeypatch, capsys
):
    """3.5 mL is 106.3 pulses; the estimate, 107, is over the limit of 100."""
    golden = _Golden(fake_relay_handler, monkeypatch)

    result = golden.deliver(1, 3.5)

    assert fake_relay_handler.trace == []
    assert (golden.sleeps, golden.rests) == ([], [])
    assert result == DeliveryResult(
        success=False,
        delivered_ml=0.0,
        duration_s=0.0,
        pulses=0,
        volume_per_pulse_ml=None,
        warning="delivery did not complete",
        calibration_id=1,
        pulse_width_ms=30,
        inter_pulse_interval_ms=1000,
    )
    assert _operator_lines(capsys.readouterr().out) == [
        "[VALVE ERROR] cage 1: the dose needs about 107 pulses, over the limit of 100 (dose "
        "too large, or the calibration is wrong); delivery stopped after 0 pulse(s), 0.000 mL"
    ]


def test_g3_a_stop_during_the_rest_after_pulse_4_ends_the_dose_with_one_close(
    fake_relay_handler, monkeypatch, capsys
):
    """The rest ends the loop; the finally closes the cage, and closes no master."""
    golden = _Golden(fake_relay_handler, monkeypatch)
    golden.on_rest = lambda n: n == 4 and golden.strategy.request_cancel()

    result = golden.deliver(1, 0.296424)

    assert fake_relay_handler.trace == [((1,), 1), ((1,), 0)] * 4 + [((1,), 0)]
    assert golden.sleeps == [0.03, 0.1] * 4
    assert golden.rests == [1000] * 4
    assert result == DeliveryResult(
        success=False,
        delivered_ml=pytest.approx(0.131744),
        duration_s=pytest.approx(4.52),
        pulses=4,
        volume_per_pulse_ml=0.032936,
        warning="delivery did not complete",
        calibration_id=1,
        pulse_width_ms=30,
        inter_pulse_interval_ms=1000,
    )
    assert fake_relay_handler.energized() == set()
    assert _operator_lines(capsys.readouterr().out) == [], "a Stop is not a failure"


def test_g4_an_open_that_does_not_reach_its_relay_ends_the_dose_after_three_pulses(
    fake_relay_handler, monkeypatch, capsys
):
    """Pulse 4 opens at write 7. Its valve never opened: no water is counted."""
    fake_relay_handler.fail_on(nth=7)
    golden = _Golden(fake_relay_handler, monkeypatch)

    result = golden.deliver(1, 0.296424)

    # Pulses 1-3, then pulse 4's safety close and the final close.
    assert fake_relay_handler.trace == [((1,), 1), ((1,), 0)] * 3 + [((1,), 0), ((1,), 0)]
    assert fake_relay_handler.dropped == [((1,), 1)]
    assert golden.sleeps == [0.03, 0.1] * 3
    assert golden.rests == [1000] * 3
    assert result == DeliveryResult(
        success=False,
        delivered_ml=pytest.approx(0.098808),
        duration_s=pytest.approx(3.39),
        pulses=3,
        volume_per_pulse_ml=0.032936,
        warning="delivery did not complete",
        calibration_id=1,
        pulse_width_ms=30,
        inter_pulse_interval_ms=1000,
    )
    assert fake_relay_handler.energized() == set()
    assert _operator_lines(capsys.readouterr().out) == [
        "[VALVE ERROR] Exception during pulse: open_cage(1) did not reach its relay",
        "[VALVE ERROR] cage 1: pulse failed: open_cage(1) did not reach its relay; delivery "
        f"stopped after 3 pulse(s), 0.099 mL. {RELAY_FAULT}",
    ]


def test_g5_a_close_lost_once_is_retried_at_once_and_its_pulse_is_banked(
    fake_relay_handler, monkeypatch, capsys
):
    """Pulse 2 closes at write 4. The first retry waits for nothing
    (CLOSE_RETRY_DELAYS_S starts at 0) and gets through, so the valve was
    open for one pulse: one calibrated pulse is banked, and the delivery
    ends, for the worker to retry the rest."""
    fake_relay_handler.fail_on(nth=4)
    golden = _Golden(fake_relay_handler, monkeypatch)

    result = golden.deliver(1, 0.296424)

    # Pulse 1, pulse 2's open, its close on the retry, then the final close.
    assert fake_relay_handler.trace == [
        ((1,), 1),
        ((1,), 0),
        ((1,), 1),
        ((1,), 0),
        ((1,), 0),
    ]
    assert fake_relay_handler.dropped == [((1,), 0)]
    assert golden.sleeps == [0.03, 0.1, 0.03], "no settle after the lost close, no retry wait"
    assert golden.rests == [1000]
    assert result == DeliveryResult(
        success=False,
        delivered_ml=pytest.approx(0.065872),
        duration_s=pytest.approx(1.16),
        pulses=2,
        volume_per_pulse_ml=0.032936,
        warning="delivery did not complete",
        calibration_id=1,
        pulse_width_ms=30,
        inter_pulse_interval_ms=1000,
    )
    assert fake_relay_handler.energized() == set()
    assert _operator_lines(capsys.readouterr().out) == [
        "[VALVE ERROR] cage 1: close_cage(1) did not reach its relay; closing again",
        "[VALVE ERROR] cage 1: close_cage(1) did not reach its relay; delivery stopped after "
        f"2 pulse(s), 0.066 mL. {RELAY_FAULT}",
    ]


def test_g6_a_close_that_never_gets_through_raises_the_alarm(
    fake_relay_handler, monkeypatch, capsys
):
    """Pulse 1's close and its five retries (at once, at once, then after
    20, 50 and 100 ms) are lost, and so is the final close. The valve is
    still open; the pulse is banked with the 0.17 s it stayed open after
    its close was asked for, at the valve's steady flow."""
    _lose_closes(fake_relay_handler, monkeypatch)
    golden = _Golden(fake_relay_handler, monkeypatch)

    result = golden.deliver(1, 0.296424)

    assert fake_relay_handler.trace == [((1,), 1)]
    assert fake_relay_handler.dropped == [((1,), 0)] * 7
    assert golden.sleeps == [0.03, 0.02, 0.05, 0.1]
    assert golden.rests == []
    assert result == DeliveryResult(
        success=False,
        delivered_ml=pytest.approx(0.2995608),
        duration_s=pytest.approx(0.2),
        pulses=1,
        volume_per_pulse_ml=0.032936,
        warning="delivery did not complete",
        calibration_id=1,
        pulse_width_ms=30,
        inter_pulse_interval_ms=1000,
    )
    assert fake_relay_handler.energized() == {1}, "the fake shows what the alarm says"
    assert _operator_lines(capsys.readouterr().out) == [
        "[VALVE ERROR] cage 1: close_cage(1) did not reach its relay; closing again",
        STILL_OPEN,
        "[VALVE ERROR] cage 1: close_cage(1) did not reach its relay; delivery stopped after "
        f"1 pulse(s), 0.300 mL. {RELAY_FAULT}",
        STILL_OPEN,  # the final close is lost too
    ]


def test_g7_two_cages_from_one_strategy_never_cross_relays(
    fake_relay_handler, monkeypatch, capsys
):
    golden = _Golden(fake_relay_handler, monkeypatch, cages=(1, 2))

    first = golden.deliver(1, 0.098808)
    second = golden.deliver(2, 0.098808)

    assert fake_relay_handler.trace == (
        [((1,), 1), ((1,), 0)] * 3 + [((1,), 0)] + [((2,), 1), ((2,), 0)] * 3 + [((2,), 0)]
    )
    assert golden.sleeps == [0.03, 0.1] * 6
    assert golden.rests == [1000] * 4
    for result, calibration_id in ((first, 1), (second, 2)):
        assert result == DeliveryResult(
            success=True,
            delivered_ml=pytest.approx(0.098808),
            duration_s=pytest.approx(2.39),
            pulses=3,
            volume_per_pulse_ml=0.032936,
            warning=None,
            calibration_id=calibration_id,  # each cage cites its own row
            pulse_width_ms=30,
            inter_pulse_interval_ms=1000,
        )
    assert fake_relay_handler.energized() == set()
    assert _operator_lines(capsys.readouterr().out) == []


# --- the calibration wizard, Priming and the worker -----------------------------------------


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PyQt5")
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


@pytest.fixture
def fresh_lock(qapp):
    """The hardware lock is a singleton the panels subscribe to: a fresh one per test."""
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield ol.get_operation_lock()
    ol._singleton = None


@pytest.fixture
def hardware(monkeypatch, fake_relay_handler):
    """Every RelayHandler the code builds is the fake."""
    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    return fake_relay_handler


class _Rests(threading.Event):
    """The wizard's stop event, never set: each rest it waits is recorded, not waited."""

    def __init__(self):
        super().__init__()
        self.waits = []

    def wait(self, timeout=None):
        self.waits.append(timeout)
        return self.is_set()


def test_g8_a_ten_pulse_calibration_pulses_the_cage_valve_and_nothing_else(
    qapp, hardware, monkeypatch
):
    from ui.CalibrationWizard import _CalibrationPulseWorker  # noqa: PLC0415

    slept = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(round(seconds, 3)))
    rests = _Rests()
    worker = _CalibrationPulseWorker(
        cage_id=1,
        num_pulses=10,
        pulse_width_ms=30,
        system_settings=dict(INDEPENDENT),
        stop_event=rests,
        inter_pulse_interval_ms=1000,
    )
    outcome, progress, logs = [], [], []
    worker.finished.connect(lambda ok, error: outcome.append((ok, error)))
    worker.progress.connect(progress.append)
    worker.log.connect(logs.append)

    worker.run()

    assert hardware.trace == [((1,), 1), ((1,), 0)] * 10 + [((1,), 0)]
    assert slept == [0.03] * 10, "the pulse widths; no master settle"
    assert rests.waits == [1.0] * 10, "a rest after every pulse, the last one included"
    assert outcome == [(True, None)]
    assert progress == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert logs[-2:] == [" Completed 10 pulses", " All valves closed"]
    assert hardware.energized() == set()


def test_g9_priming_opens_and_closes_one_cage_valve_and_frees_the_hardware(
    fresh_lock, hardware, monkeypatch
):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: False)  # no delivery worker alive
    shown = []
    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(
            QMessageBox,
            kind,
            staticmethod(lambda *a, _kind=kind, **k: shown.append((_kind, a[1], a[2]))),
        )
    lock = fresh_lock
    panel = PrimingControlWidget(
        dict(INDEPENDENT), lambda *_: None, schedule_running=lambda: False
    )

    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(3))
    panel._on_open_cage_clicked()  # Open Selected

    assert hardware.trace == [((3,), 1)]
    assert lock.held_by("priming"), "the first cage valve opened starts the session"

    panel._on_close_cage_clicked()  # Close Selected

    assert hardware.trace == [((3,), 1), ((3,), 0)]
    assert lock.is_busy() is False, "the last cage valve closed ends it"

    panel._on_emergency_stop_clicked()  # CLOSE ALL RELAYS

    assert hardware.trace == [((3,), 1), ((3,), 0), (("all",), 0)]
    assert lock.is_busy() is False
    assert shown == [("information", "Emergency Stop", "All relays have been closed.")]
    assert hardware.energized() == set()


def _worker(strategy, monkeypatch, mode):
    """A RelayWorker stand-in (the harness of test_delivery_record_context.py)
    driving the real strategy, with an independent device's settings."""
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415

    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.settings = {'valve_topology': 'independent', 'round_doses_up': False}
    worker.delivered_volumes, worker.failed_deliveries, worker.issued_targets = {}, {}, {}
    worker.schedule_id, worker.hardware_mode, worker.mode = 7, 'solenoid', mode
    worker.database_handler = MagicMock()
    worker.progress.connect(lambda _m: None)
    worker.volume_updated.connect(lambda *_a: None)
    worker._cancel_requested = threading.Event()
    worker.retries = []
    monkeypatch.setattr(
        RelayWorker, "schedule_retry", lambda self, data: self.retries.append(data), raising=False
    )
    worker.strategy = strategy
    return worker


def _slot(volume_ml):
    """One delivery as the worker's timer hands it over: schedule 7, animal 1, cage 1."""
    return {
        'schedule_id': 7,
        'animal_id': 1,
        'relay_unit_id': 1,
        'water_volume': volume_ml,
        'instant_time': datetime(2026, 11, 3, 9, 0),
    }


def _ledger(worker):
    """The dispensing_history rows the worker wrote, in order."""
    return [call.args[0] for call in worker.database_handler.log_delivery.call_args_list]


def test_g10_a_staggered_slot_fires_whole_pulses_and_records_them(
    qapp, fake_relay_handler, monkeypatch
):
    """A 0.2 mL slot of a 0.6 mL window: 6.07 pulses, so 6 at the nearest."""
    golden = _Golden(fake_relay_handler, monkeypatch)
    worker = _worker(golden.strategy, monkeypatch, mode='staggered')
    worker.animal_windows = {1: {'relay_unit': 1, 'target_volume': 0.6}}

    assert worker._handle_delivery(_slot(0.2)) is True

    assert fake_relay_handler.trace == [((1,), 1), ((1,), 0)] * 6 + [((1,), 0)]
    assert golden.sleeps == [0.03, 0.1] * 6
    assert golden.rests == [1000] * 5
    assert _ledger(worker) == [
        {
            'schedule_id': 7,
            'animal_id': 1,
            'relay_unit_id': 1,
            'volume_delivered': pytest.approx(0.197616),
            'volume_actual_ml': pytest.approx(0.197616),
            'pulses_fired': 6,
            'volume_per_pulse_ml': 0.032936,
            'timestamp': '2026-11-03T09:00:00',
            'status': 'completed',
            'topology': 'independent',
            'app_version': __version__,
            'delivery_mode': 'staggered',
            'calibration_id': 1,
            'pulse_width_ms': 30,
            'inter_pulse_interval_ms': 1000,
            'duration_s': pytest.approx(5.78),
            'volume_requested_ml': 0.2,
            'dose_rounding': 'nearest',
        }
    ]
    assert worker.delivered_volumes == {1: pytest.approx(0.197616)}
    assert worker.retries == []
    assert fake_relay_handler.energized() == set()


def test_g11_an_instant_retry_after_a_relay_fault_sends_only_the_rest(
    qapp, fake_relay_handler, monkeypatch, capsys
):
    """The independent twin of test_relay_write_failures.py's
    test_an_instant_retry_after_a_relay_fault_sends_only_the_rest. 10 pulses
    are asked for; pulse 8's close (write 16) is lost once and gets through
    on the retry, so pulse 8 is banked and the delivery ends; the worker's
    retry plans the 2 pulses still owed."""
    fake_relay_handler.fail_on(nth=16)
    golden = _Golden(fake_relay_handler, monkeypatch)
    worker = _worker(golden.strategy, monkeypatch, mode='instant')
    data = _slot(0.32936)

    assert worker._handle_delivery(data) is False
    assert worker.retries == [data], "the relay fault ended the delivery"
    assert worker._handle_delivery(data) is True  # the retry, as schedule_retry runs it

    first = [((1,), 1), ((1,), 0)] * 7 + [((1,), 1), ((1,), 0), ((1,), 0)]
    retry = [((1,), 1), ((1,), 0)] * 2 + [((1,), 0)]
    assert fake_relay_handler.trace == first + retry
    assert fake_relay_handler.dropped == [((1,), 0)]
    context = {
        'schedule_id': 7,
        'animal_id': 1,
        'relay_unit_id': 1,
        'volume_per_pulse_ml': 0.032936,
        'timestamp': '2026-11-03T09:00:00',
        'topology': 'independent',
        'app_version': __version__,
        'delivery_mode': 'instant',
        'calibration_id': 1,
        'pulse_width_ms': 30,
        'inter_pulse_interval_ms': 1000,
        'volume_requested_ml': 0.32936,  # the retry keeps the first ask
        'dose_rounding': 'nearest',
    }
    assert _ledger(worker) == [
        {
            **context,
            'volume_delivered': 0,
            'volume_actual_ml': pytest.approx(0.263488),
            'pulses_fired': 8,
            'status': 'partial',
            'duration_s': pytest.approx(7.94),
        },
        {
            **context,
            'volume_delivered': pytest.approx(0.065872),
            'volume_actual_ml': pytest.approx(0.065872),
            'pulses_fired': 2,
            'status': 'completed',
            'duration_s': pytest.approx(1.26),
        },
    ]
    assert worker.delivered_volumes == {1: pytest.approx(0.32936)}
    assert fake_relay_handler.energized() == set()
    assert _operator_lines(capsys.readouterr().out) == [
        "[VALVE ERROR] cage 1: close_cage(1) did not reach its relay; closing again",
        "[VALVE ERROR] cage 1: close_cage(1) did not reach its relay; delivery stopped after "
        f"8 pulse(s), 0.263 mL. {RELAY_FAULT}",
    ]
