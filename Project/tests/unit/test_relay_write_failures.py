"""A relay write that did not happen is reported, never counted as water.

``RelayHandler`` used to swallow every failure and report success. That
covered a relay HAT that failed to initialise (every write skipped), a
relay on a HAT that was never found, and a vendor I²C error. On top of that,
the pulse loop ignored what the valve commands returned. A dead HAT therefore
recorded full deliveries while no water moved, calibrations counted pulses
that never fired, and the emergency stop always said "all relays closed".

These tests pin the new contract at each layer:

- ``RelayHandler`` returns False when a relay did not switch;
- a delivery stops at the first valve command that did not reach its relay,
  banking exactly the pulses whose valve opened;
- a calibration run stops, so no wrong mL/pulse is measured;
- an emergency stop that was not confirmed tells the operator to cut the power.
"""

from __future__ import annotations

import asyncio
import os
import re
import threading
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from drivers.solenoid_controller import IndependentSolenoidController, SolenoidController
from strategies.solenoid_flow_strategy import SolenoidFlowStrategy, ValveCommandError

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

Q = 0.034164  # mL per pulse
MASTER = 16
CAGE = 1
CAGE_MAP = {cage: cage for cage in range(1, 16)}


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PyQt5")
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


@pytest.fixture
def fresh_lock(qapp):
    # The panels subscribe to the OperationLock singleton: a fresh one per test.
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


# --- RelayHandler over fake HATs -----------------------------------------------------


class _FakeHat:
    """One SM16relind board: records writes, raises OSError while ``fail`` is set."""

    def __init__(self, stack):
        self.stack = stack
        self.fail = False
        self.fail_off = False
        self.writes = []

    def set(self, relay, state):
        if self.fail or (self.fail_off and not state):
            raise OSError(121, "Remote I/O error")
        self.writes.append((relay, state))

    def set_all(self, state):
        if self.fail:
            raise OSError(121, "Remote I/O error")
        self.writes.append(("all", state))


def _relay_handler(monkeypatch, num_hats, present=None, coordinated=False):
    """The real RelayHandler over fake boards; stacks outside ``present`` do not answer."""
    import gpio.gpio_handler as gh  # noqa: PLC0415

    hats = {}

    def board(stack):
        if present is not None and stack not in present:
            raise OSError(121, "Remote I/O error")
        hats[stack] = _FakeHat(stack)
        return hats[stack]

    monkeypatch.setattr(gh, "SM16relind", SimpleNamespace(SM16relind=board))
    monkeypatch.setattr(gh, "USING_CUSTOM_MODULE", False)
    handler = gh.RelayHandler([], num_hats)
    if not coordinated:
        handler._coordinator = None
    for hat in hats.values():
        hat.writes.clear()  # drop the set_all(0) of initialisation
    return handler, hats


def test_a_write_the_hat_took_is_reported(monkeypatch):
    handler, hats = _relay_handler(monkeypatch, 1)
    assert handler.set_relays([3], 1) is True
    assert handler.set_all_relays(0) is True
    assert hats[0].writes == [(3, 1), ("all", 0)]


def test_a_relay_on_a_hat_that_never_answered_is_not_reported_switched(monkeypatch):
    handler, hats = _relay_handler(monkeypatch, 2, present={0})
    assert handler.set_relays([17], 1) is False, "relay 17 is on the second HAT"
    assert handler.set_relays([3], 1) is True
    assert handler.set_relays([3, 17], 0) is False, "one of the two did not switch"
    assert hats[0].writes == [(3, 1), (3, 0)], "the relay that could switch still did"
    assert handler.set_all_relays(0) is False, "the second HAT's relays are unknown"
    assert hats[0].writes[-1] == ("all", 0)


def test_no_hat_at_all_fails_every_write(monkeypatch):
    """A missing vendor library or a HAT that is not seen at start-up."""
    handler, hats = _relay_handler(monkeypatch, 1, present=set())
    assert hats == {}
    assert handler.set_relays([1], 1) is False
    assert handler.set_all_relays(0) is False


def test_a_vendor_error_is_reported(monkeypatch):
    handler, hats = _relay_handler(monkeypatch, 1)
    hats[0].fail = True
    assert handler.set_relays([1], 1) is False
    assert handler.set_all_relays(0) is False


def test_an_id_below_one_is_refused_not_wrapped_onto_the_last_hat(monkeypatch):
    """divmod(0 - 1, 16) is (-1, 15): relay 16 of the LAST board, the master on one HAT."""
    handler, hats = _relay_handler(monkeypatch, 1)
    assert handler.set_relays([0], 1) is False
    assert hats[0].writes == []


def test_the_result_passes_through_the_i2c_coordinator(monkeypatch):
    handler, _hats = _relay_handler(monkeypatch, 2, present={0}, coordinated=True)
    assert handler._coordinator is not None
    assert handler.set_relays([1], 1) is True
    assert handler.set_relays([17], 1) is False
    assert handler.set_all_relays(0) is False


def test_a_pump_trigger_that_did_not_switch_is_not_reported(monkeypatch):
    from models.relay_unit import RelayUnit  # noqa: PLC0415

    handler, hats = _relay_handler(monkeypatch, 2, present={0})
    handler.relay_units = {
        1: RelayUnit(unit_id=1, relay_ids=(3,)),
        2: RelayUnit(unit_id=2, relay_ids=(17,)),
    }
    assert handler.trigger_relays([1], {"1": 2}, 0) == ["Relay Unit 1 triggered 2 times"]
    assert handler.trigger_relays([2], {"2": 2}, 0) == [], "relay 17 has no HAT"
    hats[0].fail_off = True  # switches on, then does not switch off
    assert handler.trigger_relays([1], {"1": 2}, 0) == [], "a relay possibly still ON"
    assert hats[0].writes[-1] == (3, 1), "stopped after the first trigger"
    hats[0].fail = True
    assert handler.trigger_relays([1], {"1": 2}, 0) == []


# --- the delivery strategy over the fake relay handler -------------------------------------


class _StubDB:
    def get_all_valve_calibrations(self):
        return {CAGE: self.get_valve_calibration(CAGE)}

    def get_valve_calibration(self, cage_id):
        return {
            'calibration_id': 1,
            'pulse_width_ms': 30,
            'volume_per_pulse_ml': Q,
            'inter_pulse_interval_ms': 1000,
        }


class _Spinning(BaseException):
    """Raised past a loop's own `except Exception` when it never waits."""


class _Clock:
    """The loop's clock in these tests. It moves only when the code sleeps,
    or when a test moves it (a relay write that fails slowly), so the time a
    valve stayed open is exact. A loop that reads it thousands of times
    without it moving never waits, and would spin forever here: it fails."""

    def __init__(self):
        self.now = 0.0
        self._seen = None
        self._still = 0

    def time(self):
        if self.now != self._seen:
            self._seen, self._still = self.now, 0
        else:
            self._still += 1
            if self._still > 10_000:
                raise _Spinning("a loop reads the clock without ever waiting")
        return self.now


def _strategy(valves, monkeypatch, pulse=True):
    strategy = SolenoidFlowStrategy(
        solenoid_controller=valves,
        flow_sensor=None,  # production runs calibration-only
        calibration_store=None,
        settings={
            'use_pulse_delivery': pulse,
            'pulse_width_ms': 30,
            'pulse_settling_ms': 100,
            'max_pulses_per_delivery': 100,
            'max_pulse_delivery_time_s': 120.0,
            'expected_flow_ml_min': 60.0,
        },
        database_handler=_StubDB(),
    )

    clock = _Clock()

    async def _sleep(seconds):
        clock.now += max(0.0, float(seconds))

    async def _no_rest(_interval_ms):
        return False

    monkeypatch.setattr(asyncio, 'sleep', _sleep)
    monkeypatch.setattr(asyncio, 'get_event_loop', lambda: clock)
    monkeypatch.setattr(strategy, '_rest_between_pulses', _no_rest)
    strategy.test_clock = clock
    return strategy


def _deliver(strategy, pulses):
    return asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=pulses * Q))


# The shared manifold's writes: prime (1, 2), hold (3), then per pulse n an
# open at 2n + 2 and a close at 2n + 3, then the final cage and master close.
def _steady(pulse_ml=Q, pulse_s=0.030):
    """The flow a late close is credited at: the pulse over its flowing time."""
    return pulse_ml / (pulse_s - SolenoidFlowStrategy.VALVE_DEAD_TIME_S)


def _open_write(n):
    return 2 * n + 2


def _close_write(n):
    return 2 * n + 3


def test_a_pulse_whose_valve_did_not_open_is_not_counted(fake_relay_handler, monkeypatch, capsys):
    fake_relay_handler.fail_on(nth=_open_write(3))
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert result.pulses == 2, "pulses 1 and 2 fired; pulse 3's valve never opened"
    assert result.delivered_ml == pytest.approx(2 * Q)
    assert fake_relay_handler.dropped == [((CAGE,), 1)]
    assert fake_relay_handler.trace[-2:] == [((CAGE,), 0), ((MASTER,), 0)], "closed at the end"
    assert fake_relay_handler.energized() == set()
    assert "[VALVE ERROR] cage 1" in capsys.readouterr().out


def test_a_pulse_whose_valve_did_not_close_is_banked_and_ends_the_delivery(
    fake_relay_handler, monkeypatch, capsys
):
    fake_relay_handler.fail_on(nth=_close_write(3))
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert result.pulses == 3, "pulse 3's valve opened: its water is in the cage"
    assert result.delivered_ml == pytest.approx(3 * Q)
    assert fake_relay_handler.dropped == [((CAGE,), 0)]
    assert fake_relay_handler.energized() == set(), "the second close attempt got through"
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out


def test_a_valve_that_never_closes_raises_the_alarm(fake_relay_handler, monkeypatch, capsys):
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    real = fake_relay_handler.set_relays

    def stuck(relay_ids, state):  # every close of the cage relay is lost
        if tuple(relay_ids) == (CAGE,) and not state:
            fake_relay_handler.dropped.append(((CAGE,), 0))
            return False
        return real(relay_ids, state)

    monkeypatch.setattr(fake_relay_handler, "set_relays", stuck)
    result = _deliver(strategy, 9)

    assert result.success is False
    assert result.pulses == 1
    out = capsys.readouterr().out
    assert "[VALVE CRITICAL] cage 1: the cage valve close did not reach its relay" in out
    # The button the alarm names also ends the run: the operator is told before pressing it.
    assert "CLOSE ALL RELAYS switches every relay off again and stops the schedule." in out
    assert fake_relay_handler.energized() == {CAGE}, "the fake shows what the alarm says"


def test_a_master_that_did_not_open_delivers_nothing(fake_relay_handler, monkeypatch):
    fake_relay_handler.fail_on(nth=1)  # the prime's master open
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert (result.pulses, result.delivered_ml) == (0, 0.0)
    assert all(CAGE not in ids for ids, _state in fake_relay_handler.trace), "no cage write"
    assert fake_relay_handler.energized() == set()


def test_the_independent_topology_stops_the_same_way(fake_relay_handler, monkeypatch):
    # No master: pulse n opens at write 2n - 1.
    fake_relay_handler.fail_on(nth=5)
    strategy = _strategy(IndependentSolenoidController(fake_relay_handler, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert result.pulses == 2
    assert all(MASTER not in ids for ids, _state in fake_relay_handler.trace)
    assert fake_relay_handler.energized() == set()


def test_continuous_mode_does_not_time_a_dose_through_a_valve_that_did_not_open(
    fake_relay_handler, monkeypatch
):
    fake_relay_handler.fail_on(relay=CAGE)
    strategy = _strategy(
        SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch, pulse=False
    )

    result = asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=0.6))

    assert result.success is False
    assert result.delivered_ml == 0.0
    assert fake_relay_handler.energized() == set(), "the master was closed again"


def test_continuous_mode_keeps_a_timed_dose_whose_close_needed_a_retry(
    fake_relay_handler, monkeypatch, capsys
):
    """The dose is in the cage; failing it would make the worker send it again."""
    fake_relay_handler.fail_on(nth=3)  # master open, cage open, cage CLOSE
    strategy = _strategy(
        SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch, pulse=False
    )

    result = asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=0.6))

    assert result.success is True
    assert fake_relay_handler.dropped == [((CAGE,), 0)]
    assert fake_relay_handler.energized() == set()
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out


def test_a_sensor_pulse_whose_valve_did_not_open_is_not_corrected_into_water(
    fake_relay_handler, monkeypatch
):
    """With too few flow samples the sensor path falls back to the calibrated
    volume: a valve that never opened must not reach that fallback."""
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    strategy._sensor = MagicMock()
    strategy._sensor.read_one.return_value = None
    strategy._sensor_available = True
    fake_relay_handler.fail_on(relay=CAGE)

    with pytest.raises(ValveCommandError) as failure:
        asyncio.run(strategy._execute_single_pulse(CAGE))
    assert failure.value.delivered_ml == 0.0


def test_the_valve_helper_turns_a_raising_command_into_a_valve_error(monkeypatch):
    strategy = _strategy(MagicMock(), monkeypatch)

    def unknown_cage(_cage_id):
        raise ValueError("Unknown cage_id 99")

    with pytest.raises(ValveCommandError, match="Unknown cage_id 99"):
        strategy._valve(unknown_cage, 99)
    assert strategy._closed(unknown_cage, 99) is False


# --- calibration --------------------------------------------------------------------------


@pytest.fixture
def calibration_worker(qapp, monkeypatch, fake_relay_handler):
    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())

    def run(num_pulses=3, settings=None):
        from ui.CalibrationWizard import _CalibrationPulseWorker  # noqa: PLC0415

        worker = _CalibrationPulseWorker(
            cage_id=CAGE,
            num_pulses=num_pulses,
            pulse_width_ms=1,
            system_settings=settings or {"num_hats": 1, "global_master_relay_id": MASTER},
            stop_event=threading.Event(),
            inter_pulse_interval_ms=0,
        )
        outcome, logs = [], []
        worker.finished.connect(lambda ok, error: outcome.append((ok, error)))
        worker.log.connect(logs.append)
        worker.run()
        return outcome[0], logs

    return run


def test_calibration_stops_at_a_pulse_whose_valve_did_not_open(
    calibration_worker, fake_relay_handler
):
    fake_relay_handler.fail_on(nth=4)  # master open, pulse 1 open + close, pulse 2 OPEN
    (ok, error), _logs = calibration_worker(num_pulses=3)
    assert ok is False
    assert "did not open at pulse 2 of 3" in error and "do not save" in error
    assert fake_relay_handler.energized() == set()


def test_calibration_stops_when_a_valve_did_not_close(calibration_worker, fake_relay_handler):
    fake_relay_handler.fail_on(nth=3)  # pulse 1's close
    (ok, error), _logs = calibration_worker(num_pulses=3)
    assert ok is False
    assert "did not close after pulse 1 of 3" in error and "may still be OPEN" in error
    assert fake_relay_handler.energized() == set(), "the fail-safe close got through"


def test_calibration_does_not_pulse_without_the_master(calibration_worker, fake_relay_handler):
    fake_relay_handler.fail_on(nth=1)
    (ok, error), _logs = calibration_worker(num_pulses=3)
    assert ok is False
    assert "master valve did not open" in error
    assert ((CAGE,), 1) not in fake_relay_handler.trace, "no cage valve opened"
    assert fake_relay_handler.energized() == set()


def test_a_clean_calibration_is_unchanged(calibration_worker, fake_relay_handler):
    (ok, error), _logs = calibration_worker(num_pulses=2)
    assert (ok, error) == (True, None)
    assert fake_relay_handler.trace == [
        ((MASTER,), 1),
        ((CAGE,), 1),
        ((CAGE,), 0),
        ((CAGE,), 1),
        ((CAGE,), 0),
        ((CAGE,), 0),
        ((MASTER,), 0),
    ]


# --- priming --------------------------------------------------------------------------------


@pytest.fixture
def priming(fresh_lock, monkeypatch, fake_relay_handler):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    shown = []
    for kind in ("warning", "critical", "information"):
        monkeypatch.setattr(
            QMessageBox,
            kind,
            staticmethod(
                lambda *a, _kind=kind, **k: shown.append((_kind, a[1])) or QMessageBox.Ok
            ),
        )
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    panel = PrimingControlWidget(
        {"num_hats": 1, "global_master_relay_id": MASTER}, lambda *_: None
    )
    return panel, shown


def test_an_unconfirmed_emergency_stop_says_to_cut_the_power(priming, fake_relay_handler):
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    panel, shown = priming
    panel._on_open_master_clicked()
    assert get_operation_lock().is_busy()
    fake_relay_handler.fail_all_off = True

    panel._on_emergency_stop_clicked()

    assert shown[-1] == ("critical", "Emergency Stop Failed")
    # A valve may still be open: the priming session keeps its hold on the
    # hardware, so no schedule can start onto that valve. (It used to be
    # force-released here; see test_emergency_stop.py.)
    assert get_operation_lock().held_by("priming")
    assert panel._model.is_master_open, "the panel still shows what may be open"


def test_a_confirmed_emergency_stop_is_unchanged(priming, fake_relay_handler):
    panel, shown = priming
    panel._on_emergency_stop_clicked()
    assert shown == [("information", "Emergency Stop")]


def test_close_master_closes_the_master_even_when_a_cage_did_not_close(
    priming, fake_relay_handler, monkeypatch
):
    """The master is upstream of the manifold: closing it is what cuts the
    supply to a cage valve left open. (This PR first kept the master open
    here; the review showed that leaves water flowing.)"""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    panel, _shown = priming
    texts = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: texts.append(a[2])))
    panel._on_open_master_clicked()
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(CAGE))
    panel._on_open_cage_clicked()
    fake_relay_handler.fail_on(relay=CAGE)

    panel._on_close_master_clicked()

    assert fake_relay_handler.energized() == {CAGE}, "the master closed; the cage did not"
    assert panel._model.is_master_open is False
    assert panel._model.is_cage_open(CAGE), "the panel still shows the cage open"
    assert "Cage valve(s) 1 did not confirm closed" in texts[-1]
    assert "The master was closed to cut their supply." in texts[-1]
    assert get_operation_lock().is_busy(), "the session goes on while a valve may be open"

    fake_relay_handler.fail_on()  # the fault clears; the operator closes the cage
    panel._on_close_cage_clicked()

    assert fake_relay_handler.energized() == set()
    assert get_operation_lock().is_busy() is False, "everything closed: the session ends"


def test_close_master_says_so_when_the_master_did_not_close_either(
    priming, fake_relay_handler, monkeypatch
):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    panel, _shown = priming
    texts = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: texts.append(a[2])))
    panel._on_open_master_clicked()
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(CAGE))
    panel._on_open_cage_clicked()
    real = fake_relay_handler.set_relays
    monkeypatch.setattr(
        fake_relay_handler, "set_relays", lambda ids, state: bool(state) and real(ids, state)
    )

    panel._on_close_master_clicked()

    assert "The master did not close either." in texts[-1]
    assert panel._model.is_master_open
    assert get_operation_lock().is_busy()


# --- review follow-ups ----------------------------------------------------------------------


def test_a_missing_first_hat_does_not_shift_relays_onto_the_second(monkeypatch):
    """The review's case: stack 0 absent, stack 1 present. A compacted HAT list
    sent relay 3 to stack 1's relay 3 (physical relay 19, another animal's
    valve) and reported the write as made."""
    handler, hats = _relay_handler(monkeypatch, 2, present={1})
    assert handler.set_relays([3], 1) is False, "relay 3 is on the missing stack 0"
    assert hats[1].writes == [], "nothing reached the wrong board"
    assert handler.set_relays([19], 1) is True, "relay 19 is stack 1, relay 3"
    assert hats[1].writes == [(3, 1)]
    assert handler.set_all_relays(0) is False
    assert hats[1].writes[-1] == ("all", 0), "the present board is still switched off"


def test_a_pump_run_that_stops_part_way_credits_the_triggers_that_fired(monkeypatch):
    from models.relay_unit import RelayUnit  # noqa: PLC0415

    handler, hats = _relay_handler(monkeypatch, 1)
    handler.relay_units = {1: RelayUnit(unit_id=1, relay_ids=(3,))}
    real_set = hats[0].set
    calls = []

    def set_until_third_on(relay, state):
        calls.append(state)
        if calls.count(1) == 3 and state:
            raise OSError(121, "Remote I/O error")
        real_set(relay, state)

    hats[0].set = set_until_third_on
    assert handler.trigger_relays([1], {"1": 5}, 0) == []
    assert handler.last_trigger_counts == {1: 2}, "triggers 1 and 2 pumped"


def test_the_worker_credits_a_partial_pump_run(monkeypatch):
    """The review's case: a pump run that stopped part-way reported 0 mL, and
    the retry sent the whole dose on top of the triggers that had fired."""
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QMutex  # noqa: PLC0415

    handler = MagicMock()
    handler.trigger_relays.return_value = []
    handler.last_trigger_counts = {4: 3}
    worker = SimpleNamespace(
        mutex=QMutex(),
        _is_running=True,
        volume_calculator=SimpleNamespace(pump_volume_ul=50, calculate_triggers=lambda _v: 10),
        progress=SimpleNamespace(emit=lambda _m: None),
        relay_handler=handler,
        stagger_interval=0.5,
        notification_handler=None,
    )
    result = RelayWorker.trigger_relay(worker, 4, 0.5)
    assert result.success is False
    assert result.delivered_ml == pytest.approx(0.15), "3 triggers x 50 uL"
    assert result.pulses == 3


def _sensor_strategy(fake, monkeypatch):
    strategy = _strategy(SolenoidController(fake, MASTER, CAGE_MAP), monkeypatch)
    strategy._sensor = MagicMock()
    strategy._sensor.read_one.return_value = None
    strategy._sensor_available = True
    strategy._pulse_settling_ms = 0
    return strategy


def test_a_sensor_pulse_retries_a_lost_close_at_once_and_ends_the_delivery(
    fake_relay_handler, monkeypatch, capsys
):
    fake_relay_handler.fail_on(nth=2)  # write 1 opens the cage, write 2 is the close
    strategy = _sensor_strategy(fake_relay_handler, monkeypatch)
    seen = []  # the valve state at each flow reading
    strategy._sensor.read_one.side_effect = lambda: seen.append(fake_relay_handler.energized())
    with pytest.raises(ValveCommandError) as failure:
        asyncio.run(strategy._execute_single_pulse(CAGE))
    assert failure.value.delivered_ml > 0, "the pulse's water is banked"
    assert seen and seen[-1] == set(), "closed before the settling window, not after it"
    assert fake_relay_handler.trace == [((CAGE,), 1), ((CAGE,), 0)], "closed on the retry"
    assert fake_relay_handler.energized() == set()
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out


def test_a_sensor_pulse_that_never_closes_raises_the_alarm(
    fake_relay_handler, monkeypatch, capsys
):
    strategy = _sensor_strategy(fake_relay_handler, monkeypatch)
    real = fake_relay_handler.set_relays

    def stuck(relay_ids, state):
        if not state:
            fake_relay_handler.dropped.append((tuple(relay_ids), 0))
            return False
        return real(relay_ids, state)

    monkeypatch.setattr(fake_relay_handler, "set_relays", stuck)
    with pytest.raises(ValveCommandError):
        asyncio.run(strategy._execute_single_pulse(CAGE))
    assert "[VALVE CRITICAL] cage 1: the cage valve close" in capsys.readouterr().out


def test_continuous_mode_alarms_when_the_master_does_not_close_after_a_failed_open(
    fake_relay_handler, monkeypatch, capsys
):
    real = fake_relay_handler.set_relays

    def cage_dead_master_stuck(relay_ids, state):
        if tuple(relay_ids) == (CAGE,) or (tuple(relay_ids) == (MASTER,) and not state):
            fake_relay_handler.dropped.append((tuple(relay_ids), int(state)))
            return False
        return real(relay_ids, state)

    monkeypatch.setattr(fake_relay_handler, "set_relays", cage_dead_master_stuck)
    strategy = _strategy(
        SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch, pulse=False
    )
    result = asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=0.6))
    assert result.success is False
    assert "[VALVE CRITICAL] cage 1: the master valve close" in capsys.readouterr().out


def test_an_instant_retry_after_a_relay_fault_sends_only_the_rest(fake_relay_handler, monkeypatch):
    """End to end over the real strategy: 10 pulses asked, pulse 8's close
    lost (its valve opened, so it is banked), the retry fires the other 2.
    The instant retry planning comes from #165, which this PR is stacked on."""
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415

    fake_relay_handler.fail_on(nth=_close_write(8))
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.settings = {'valve_topology': 'shared_manifold', 'round_doses_up': False}
    worker.delivered_volumes, worker.failed_deliveries, worker.issued_targets = {}, {}, {}
    worker.schedule_id, worker.hardware_mode, worker.mode = 7, 'solenoid', 'instant'
    worker.database_handler = MagicMock()
    worker.progress.connect(lambda _m: None)
    worker.volume_updated.connect(lambda *_a: None)
    worker._cancel_requested = SimpleNamespace(is_set=lambda: False)
    worker.retries = []
    monkeypatch.setattr(
        RelayWorker, "schedule_retry", lambda self, data: self.retries.append(data), raising=False
    )
    worker.strategy = strategy
    data = {
        'animal_id': 1,
        'relay_unit_id': CAGE,
        'water_volume': 10 * Q,
        'instant_time': datetime(2026, 10, 1, 9, 0),
        'schedule_id': 7,
    }

    worker._handle_delivery(data)
    assert worker.retries == [data], "the relay fault ended the delivery"
    worker._handle_delivery(data)

    opens = [w for w in fake_relay_handler.trace if w == ((CAGE,), 1)]
    assert len(opens) == 10, "8 pulses, then the 2 still owed"
    rows = [c.args[0] for c in worker.database_handler.log_delivery.call_args_list]
    assert [r['status'] for r in rows] == ['partial', 'completed']
    assert sum(r['pulses_fired'] for r in rows) == 10
    assert fake_relay_handler.energized() == set()


def test_calibration_says_so_when_the_final_close_never_gets_through(
    calibration_worker, fake_relay_handler, monkeypatch, capsys
):
    """All pulses fired, then the end-of-run cage close is lost twice: the
    run must not report success with 'All valves closed'."""
    real = fake_relay_handler.set_relays
    writes = []

    def lose_the_final_closes(relay_ids, state):
        writes.append((tuple(relay_ids), state))
        # master open, 2 pulses (4 writes), then the final cage close and retry
        if len(writes) in (6, 8) and tuple(relay_ids) == (CAGE,):
            fake_relay_handler.dropped.append((tuple(relay_ids), int(state)))
            return False
        return real(relay_ids, state)

    monkeypatch.setattr(fake_relay_handler, "set_relays", lose_the_final_closes)
    (ok, error), logs = calibration_worker(num_pulses=2)
    assert ok is False
    assert "[VALVE CRITICAL] calibration of cage 1: the cage valve close" in error
    assert " All valves closed" not in logs
    assert "[VALVE CRITICAL]" in capsys.readouterr().out, "reaches System Messages"


def test_close_master_is_not_refused_by_a_missing_second_hat(
    fresh_lock, monkeypatch, fake_relay_handler
):
    """The review's case: close_all_cages wrote every cage relay, including a
    missing second HAT's, and refused although the one open cage had closed."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    for kind in ("warning", "critical", "information"):
        monkeypatch.setattr(QMessageBox, kind, staticmethod(lambda *a, **k: QMessageBox.Ok))
    panel = PrimingControlWidget(
        {"num_hats": 2, "global_master_relay_id": MASTER}, lambda *_: None
    )
    panel._on_open_master_clicked()
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(CAGE))
    panel._on_open_cage_clicked()
    fake_relay_handler.fail_on(relay=17)  # cage 16 on the missing second HAT

    panel._on_close_master_clicked()

    assert panel._model.is_master_open is False
    assert get_operation_lock().is_busy() is False
    assert fake_relay_handler.energized() == set()


# --- review round 2 -------------------------------------------------------------------------


def _fail_on_writes(hat, ordinals):
    """Make the given ON writes to ``hat`` (1-based, counted over every ON
    attempt) raise, as an I2C error burst does."""
    real_set, attempts = hat.set, []

    def flaky(relay, state):
        if state:
            attempts.append(relay)
            if len(attempts) in ordinals:
                raise OSError(121, "Remote I/O error")
        real_set(relay, state)

    hat.set = flaky


def _pump_worker(monkeypatch, *, calibration_factor=1.0, window_target=None):
    """A RelayWorker in pump mode over the real RelayHandler, PumpController
    and PumpStrategy, with one relay unit (4) on a fake HAT."""
    from controllers.pump_controller import PumpController  # noqa: PLC0415
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from models.relay_unit import RelayUnit  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415
    from strategies.pump_strategy import PumpStrategy  # noqa: PLC0415
    from utils.volume_calculator import VolumeCalculator  # noqa: PLC0415

    handler, hats = _relay_handler(monkeypatch, 1)
    handler.relay_units = {4: RelayUnit(unit_id=4, relay_ids=(3,))}
    monkeypatch.setattr("gpio.gpio_handler.time.sleep", lambda _s: None)
    settings = {"pump_volume_ul": 50, "calibration_factor": calibration_factor, "min_triggers": 1}
    calculator = VolumeCalculator(
        SimpleNamespace(
            settings=settings, settings_updated=SimpleNamespace(connect=lambda _s: None)
        )
    )
    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.settings = {"valve_topology": "shared_manifold"}
    worker.delivered_volumes, worker.failed_deliveries, worker.issued_targets = {}, {}, {}
    worker.schedule_id, worker.hardware_mode = 7, "pump"
    worker.mode = "staggered" if window_target else "instant"
    worker._is_running, worker.stagger_interval, worker.notification_handler = True, 0, None
    worker.database_handler = MagicMock()
    worker.relay_handler, worker.volume_calculator = handler, calculator
    worker.strategy = PumpStrategy(PumpController(handler, MagicMock()), calculator)
    worker._cancel_requested = SimpleNamespace(is_set=lambda: False)
    if window_target:
        worker.animal_windows = {1: {"target_volume": window_target, "relay_unit": 4}}
    worker.progress.connect(lambda _m: None)
    worker.volume_updated.connect(lambda *_a: None)
    worker.retries = []
    monkeypatch.setattr(
        RelayWorker, "schedule_retry", lambda self, data: self.retries.append(data), raising=False
    )
    return worker, hats[0]


def _pump_delivery(volume, **extra):
    return {
        "animal_id": 1,
        "relay_unit_id": 4,
        "water_volume": volume,
        "instant_time": datetime(2026, 10, 1, 9, 0),
        "schedule_id": 7,
        **extra,
    }


def _triggers_fired(hat):
    return sum(1 for _relay, state in hat.writes if state == 1)


def _ledger(worker):
    rows = [c.args[0] for c in worker.database_handler.log_delivery.call_args_list]
    return [(r["status"], round(r["volume_actual_ml"], 6), r["pulses_fired"]) for r in rows]


def test_a_staggered_pump_retry_fires_only_the_rest(monkeypatch):
    """The review's case: the delivery carries the trigger count planned for
    the whole dose; the retry fired all 10 again on top of the 3 that had
    run (13 triggers, 0.65 mL against 0.5)."""
    worker, hat = _pump_worker(monkeypatch, window_target=0.5)
    _fail_on_writes(hat, {4})
    data = _pump_delivery(0.5, triggers=10)

    worker._handle_delivery(data)
    assert worker.retries == [data]
    assert asyncio.run(worker.execute_delivery(data)) is True

    assert _triggers_fired(hat) == 10
    assert worker.delivered_volumes[1] == pytest.approx(0.5)
    assert _ledger(worker) == [("partial", 0.15, 3), ("completed", 0.35, 7)]


def test_a_pump_retry_that_stops_part_way_is_credited_too(monkeypatch):
    """The review's case: the retry runs through PumpStrategy, which reported
    0 mL and the commanded trigger count when a relay stopped it."""
    worker, hat = _pump_worker(monkeypatch)
    _fail_on_writes(hat, {4, 9})  # attempt 1 stops after 3, attempt 2 after 4 more
    data = _pump_delivery(0.5)

    worker._handle_delivery(data)
    assert asyncio.run(worker.execute_delivery(data)) is False
    assert asyncio.run(worker.execute_delivery(data)) is True

    assert _triggers_fired(hat) == 10
    assert worker.delivered_volumes[1] == pytest.approx(0.5)
    assert _ledger(worker) == [("partial", 0.15, 3), ("partial", 0.2, 4), ("completed", 0.15, 3)]


def test_partial_pump_credit_honours_the_calibration_factor(monkeypatch):
    """At factor 0.5 a trigger stands for 100 uL: 1.0 mL is 10 triggers. The
    partial credit used 50 uL, so the retry over-dosed (13 triggers)."""
    worker, hat = _pump_worker(monkeypatch, calibration_factor=0.5)
    _fail_on_writes(hat, {6})
    data = _pump_delivery(1.0)

    worker._handle_delivery(data)
    assert worker.delivered_volumes[1] == pytest.approx(0.5), "5 of 10 triggers"
    assert asyncio.run(worker.execute_delivery(data)) is True

    assert _triggers_fired(hat) == 10
    assert worker.delivered_volumes[1] == pytest.approx(1.0)


def test_a_failed_dispense_is_not_credited_with_an_earlier_run_s_triggers(monkeypatch):
    """The controller's count is per call: a dispense that never reached the
    relays must not read the last run's triggers as its own."""
    from controllers.pump_controller import PumpController  # noqa: PLC0415

    handler, _hats = _relay_handler(monkeypatch, 1)
    from models.relay_unit import RelayUnit  # noqa: PLC0415

    handler.relay_units = {4: RelayUnit(unit_id=4, relay_ids=(3,))}
    monkeypatch.setattr("gpio.gpio_handler.time.sleep", lambda _s: None)
    pump = PumpController(handler, MagicMock())
    assert asyncio.run(pump.dispense_water(4, 0.25, 5)) is True
    assert pump.triggers_fired() == 5
    assert asyncio.run(pump.dispense_water(99, 0.25, 5)) is False, "no such unit"
    assert pump.triggers_fired() == 0


def test_a_pump_relay_that_does_not_switch_off_is_retried_then_alarmed(monkeypatch, capsys):
    from models.relay_unit import RelayUnit  # noqa: PLC0415

    handler, hats = _relay_handler(monkeypatch, 1)
    handler.relay_units = {1: RelayUnit(unit_id=1, relay_ids=(3,))}
    real_set, offs = hats[0].set, []

    def lose_first_off(relay, state):
        if not state:
            offs.append(relay)
            if len(offs) == 1:
                raise OSError(121, "Remote I/O error")
        real_set(relay, state)

    hats[0].set = lose_first_off
    assert handler.trigger_relays([1], {"1": 2}, 0) == ["Relay Unit 1 triggered 2 times"]
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out, "the second attempt got through"

    hats[0].set = real_set
    hats[0].fail_off = True
    assert handler.trigger_relays([1], {"1": 2}, 0) == []
    assert handler.last_trigger_counts == {1: 1}
    out = capsys.readouterr().out
    assert "[VALVE CRITICAL] relay unit 1: relay(s) 3 did not switch off" in out
    assert "CLOSE ALL RELAYS switches every relay off again and stops the schedule." in out


def test_a_pump_relay_that_does_not_answer_cannot_be_confirmed_off(monkeypatch, capsys):
    """Its on and off writes both fail from the start: it may have been left
    on before, so the alarm is raised, worded for what is known."""
    from models.relay_unit import RelayUnit  # noqa: PLC0415

    handler, hats = _relay_handler(monkeypatch, 1)
    handler.relay_units = {1: RelayUnit(unit_id=1, relay_ids=(3,))}
    hats[0].fail = True
    assert handler.trigger_relays([1], {"1": 2}, 0) == []
    out = capsys.readouterr().out
    assert "relay(s) 3 are not answering, so they cannot be confirmed off" in out
    assert "did not switch off" not in out


def test_a_pump_relay_whose_switch_on_reported_failure_may_be_on(monkeypatch, capsys):
    """The review's case: trigger 1 switches on and off cleanly; trigger 2's
    switch-on reaches the relay but reports an I2C error; every later write
    fails. The relay is on, so its failed switch-off must alarm (an earlier
    version of this PR spared it as 'seen off')."""
    from models.relay_unit import RelayUnit  # noqa: PLC0415

    handler, hats = _relay_handler(monkeypatch, 1)
    handler.relay_units = {1: RelayUnit(unit_id=1, relay_ids=(3,))}
    real_set = hats[0].set

    def latches_then_fails(relay, state):
        if len(hats[0].writes) == 2:  # trigger 2's switch-on: applied, then an error
            real_set(relay, state)
            raise OSError(121, "Remote I/O error")
        if len(hats[0].writes) > 2:
            raise OSError(121, "Remote I/O error")
        real_set(relay, state)

    hats[0].set = latches_then_fails
    assert handler.trigger_relays([1], {"1": 3}, 0) == []
    assert hats[0].writes[-1] == (3, 1), "the relay is on"
    assert handler.last_trigger_counts == {1: 1}, "only trigger 1 is credited"
    out = capsys.readouterr().out
    assert "[VALVE CRITICAL] relay unit 1: relay(s) 3 are not answering" in out


def _lose_closes(fake, monkeypatch, count, clock=None, slow_s=0.0, relay=CAGE):
    """Lose the first ``count`` close writes to ``relay``; each lost one takes
    ``slow_s`` on the loop's clock, as an I2C timeout does. Returns the loop
    clock at every close of that relay."""
    real, closes = fake.set_relays, []

    def flaky(relay_ids, state):
        if not state and tuple(relay_ids) == (relay,):
            closes.append(clock.now if clock else None)
            if len(closes) <= count:
                if clock:
                    clock.now += slow_s
                return False
        return real(relay_ids, state)

    monkeypatch.setattr(fake, "set_relays", flaky)
    return closes


def test_a_sensor_pulse_left_open_for_the_window_banks_the_time_the_valve_was_open(
    fake_relay_handler, monkeypatch, capsys
):
    """The first close and every immediate retry are lost, and the late close
    after the measurement window gets through: the valve was open for about
    sixteen pulse widths. The sensor saturates far below a pulse's flow, so
    its reading (and the adaptive correction, which falls back to one
    calibrated pulse) cannot show that water: the pulse is scaled by the time
    its valve was open."""
    strategy = _sensor_strategy(fake_relay_handler, monkeypatch)
    retries = len(strategy.CLOSE_RETRY_DELAYS_S)
    closes = _lose_closes(fake_relay_handler, monkeypatch, 1 + retries, strategy.test_clock)
    strategy._sensor.read_one.side_effect = lambda: (3000.0, 25.0)  # uL/min, saturated

    with pytest.raises(ValveCommandError) as failure:
        asyncio.run(strategy._execute_single_pulse(CAGE))

    assert len(closes) == 2 + retries, "the first close, every retry, then the late one"
    assert fake_relay_handler.energized() == set()
    extra_s = closes[-1] - closes[0]  # from the close asked for to the one that got through
    assert failure.value.delivered_ml == pytest.approx(Q + extra_s * _steady())
    assert failure.value.delivered_ml > 3 * Q, "the open time, not one pulse, is banked"
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out


def test_a_sensor_pulse_closed_on_an_immediate_retry_banks_the_corrected_pulse(
    fake_relay_handler, monkeypatch
):
    fake_relay_handler.fail_on(nth=2)
    strategy = _sensor_strategy(fake_relay_handler, monkeypatch)
    with pytest.raises(ValveCommandError) as failure:
        asyncio.run(strategy._execute_single_pulse(CAGE))
    assert failure.value.delivered_ml == pytest.approx(Q), "one calibrated pulse, as before"


def test_continuous_mode_says_a_cage_that_never_answered_cannot_be_confirmed_closed(
    fake_relay_handler, monkeypatch, capsys
):
    """A cage whose relay never answers: its open and its close both fail.
    It may have been left open before the run, so the alarm is raised, and
    worded for what is known: not that its close failed after an open."""
    fake_relay_handler.fail_on(relay=CAGE)
    strategy = _strategy(
        SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch, pulse=False
    )
    result = asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=0.6))
    assert result.success is False
    out = capsys.readouterr().out
    assert "[VALVE CRITICAL] cage 1: the cage valve's relay is not answering" in out
    assert "cannot be confirmed closed" in out
    assert "the cage valve close did not reach its relay" not in out
    assert "the master valve" not in out, "the master opened and closed"
    assert fake_relay_handler.energized() == set()


def _continuous_sensor_strategy(fake, monkeypatch):
    strategy = _strategy(SolenoidController(fake, MASTER, CAGE_MAP), monkeypatch, pulse=False)
    strategy._sensor = MagicMock()
    strategy._sensor.clear_queue.return_value = 0
    strategy._sensor.ensure_streaming.return_value = True
    strategy._sensor_available = True
    return strategy


def test_the_sensor_continuous_path_closes_the_master_when_the_cage_does_not_open(
    fake_relay_handler, monkeypatch, capsys
):
    fake_relay_handler.fail_on(relay=CAGE)
    strategy = _continuous_sensor_strategy(fake_relay_handler, monkeypatch)
    result = asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=0.6))
    assert result.success is False
    assert fake_relay_handler.trace[-2:] == [((MASTER,), 1), ((MASTER,), 0)], "opened, then closed"
    assert fake_relay_handler.energized() == set()
    out = capsys.readouterr().out
    assert "cage 1: the cage valve's relay is not answering" in out, "its state is unknown"
    assert "the master valve" not in out


def test_the_sensor_continuous_path_alarms_when_the_opened_master_does_not_close(
    fake_relay_handler, monkeypatch, capsys
):
    real = fake_relay_handler.set_relays

    def cage_dead_master_stuck(relay_ids, state):
        if tuple(relay_ids) == (CAGE,) or (tuple(relay_ids) == (MASTER,) and not state):
            return False
        return real(relay_ids, state)

    monkeypatch.setattr(fake_relay_handler, "set_relays", cage_dead_master_stuck)
    strategy = _continuous_sensor_strategy(fake_relay_handler, monkeypatch)
    result = asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=0.6))
    assert result.success is False
    out = capsys.readouterr().out
    assert "[VALVE CRITICAL] cage 1: the master valve close" in out
    assert "the cage valve close" not in out


# --- review round 3 -------------------------------------------------------------------------


def test_a_failed_open_master_keeps_the_session_while_a_cage_may_be_open(
    priming, fake_relay_handler, monkeypatch
):
    """The review's case: after Close Master left a cage valve unconfirmed,
    Open Master is live again, and when that open failed the panel released
    the hardware lock. A schedule could then open the master onto the cage."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    panel, _shown = priming
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    panel._on_open_master_clicked()
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(CAGE))
    panel._on_open_cage_clicked()
    fake_relay_handler.fail_on(relay=CAGE)
    panel._on_close_master_clicked()  # the master closes, the cage does not
    assert panel.master_open_btn.isEnabled()

    fake_relay_handler.fail_on(relay=MASTER)
    panel._on_open_master_clicked()  # and this open fails

    assert get_operation_lock().is_busy(), "a valve may be open: the session goes on"
    assert get_operation_lock().try_acquire("schedule") is False


def test_a_failed_open_master_with_nothing_open_frees_the_lock(
    priming, fake_relay_handler, monkeypatch
):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    panel, _shown = priming
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    fake_relay_handler.fail_on(relay=MASTER)
    panel._on_open_master_clicked()
    assert get_operation_lock().is_busy() is False


def test_a_late_close_is_priced_at_the_valve_s_steady_flow():
    """The review's case: the extra open time was priced at the pulse's
    average flow, which includes the valve's opening dead time, so a late
    close was under-counted by 25-53 % and the rest of the dose, sent
    afterwards, over-dosed. The bench (Parker 003-0257-900: 62.2 uL at 50 ms,
    141.5 uL at 100 ms, fit slope 1.544 uL/ms) puts the steady flow near
    1.54-1.59 mL/s."""
    by_time = SolenoidFlowStrategy._pulse_by_open_time
    assert by_time(Q, 0.040, 1.040, 0.030) == pytest.approx(Q + 1.0 * _steady())
    assert by_time(Q, 0.040, 0.040, 0.030) == pytest.approx(Q), "closed on time"
    assert by_time(Q, 0.040, 0.030, 0.030) == pytest.approx(Q), "never below one pulse"
    one_second_ml = by_time(0.034164, 0.0, 1.0, 0.030) - 0.034164
    assert 1.544 <= one_second_ml <= 1.544 * 1.1, "at, not under, the bench's steady flow"


@pytest.mark.parametrize("controller", ["shared", "independent"])
def test_a_close_that_fails_slowly_is_credited_with_the_time_the_valve_stayed_open(
    fake_relay_handler, monkeypatch, capsys, controller
):
    """The production path (calibration-only). An I2C timeout takes about a
    second to fail, and the valve is open all that time. The pulse used to be
    credited as one calibrated pulse, so the retry sent the rest of the dose
    on top of water nobody counted."""
    valves = (
        SolenoidController(fake_relay_handler, MASTER, CAGE_MAP)
        if controller == "shared"
        else IndependentSolenoidController(fake_relay_handler, CAGE_MAP)
    )
    strategy = _strategy(valves, monkeypatch)
    closes = _lose_closes(fake_relay_handler, monkeypatch, 1, strategy.test_clock, slow_s=1.0)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert result.pulses == 1, "the delivery ends at the pulse whose close failed"
    assert closes[1] - closes[0] == pytest.approx(1.0), "retried as soon as it failed"
    assert result.delivered_ml == pytest.approx(Q + 1.0 * _steady())
    assert fake_relay_handler.energized() == set()
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out


def test_a_close_lost_several_times_is_retried_with_short_waits(
    fake_relay_handler, monkeypatch, capsys
):
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    closes = _lose_closes(fake_relay_handler, monkeypatch, 4, strategy.test_clock)

    result = _deliver(strategy, 9)

    # The first close, two immediate retries, one after 20 ms, then 50 ms.
    assert closes[4] - closes[0] == pytest.approx(0.02 + 0.05)
    assert result.pulses == 1
    assert result.delivered_ml == pytest.approx(Q + 0.07 * _steady())
    assert fake_relay_handler.energized() == set()
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out


def test_a_sensor_pulse_whose_close_fails_slowly_is_credited_with_the_open_time(
    fake_relay_handler, monkeypatch
):
    strategy = _sensor_strategy(fake_relay_handler, monkeypatch)
    closes = _lose_closes(fake_relay_handler, monkeypatch, 1, strategy.test_clock, slow_s=1.0)

    with pytest.raises(ValveCommandError) as failure:
        asyncio.run(strategy._execute_single_pulse(CAGE))

    assert len(closes) == 2, "the immediate retry got through"
    asked, closed_at = closes
    assert failure.value.delivered_ml == pytest.approx(Q + (closed_at - asked) * _steady())
    assert failure.value.delivered_ml > 10 * Q


def test_a_sensor_pulse_closed_on_the_second_retry_raises_no_alarm(
    fake_relay_handler, monkeypatch, capsys
):
    strategy = _sensor_strategy(fake_relay_handler, monkeypatch)
    closes = _lose_closes(fake_relay_handler, monkeypatch, 2, strategy.test_clock)

    with pytest.raises(ValveCommandError) as failure:
        asyncio.run(strategy._execute_single_pulse(CAGE))

    assert len(closes) == 3
    assert failure.value.delivered_ml == pytest.approx(Q), "both retries were immediate"
    assert fake_relay_handler.energized() == set()
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out


@pytest.mark.parametrize("controller", ["shared", "independent"])
def test_a_dead_hat_alarms_that_its_valves_cannot_be_confirmed_closed(
    fake_relay_handler, monkeypatch, capsys, controller
):
    """With every write lost, no valve can be confirmed closed: one may have
    been left open before the run. The alarm says so, and does not claim a
    valve opened (an earlier version of this PR kept it silent, which also
    silenced a valve left open by a failed Stop or a crash)."""
    monkeypatch.setattr(fake_relay_handler, "set_relays", lambda _ids, _state: False)
    valves = (
        SolenoidController(fake_relay_handler, MASTER, CAGE_MAP)
        if controller == "shared"
        else IndependentSolenoidController(fake_relay_handler, CAGE_MAP)
    )
    strategy = _strategy(valves, monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert result.delivered_ml == 0.0
    out = capsys.readouterr().out
    assert "is not answering, so the valve cannot be confirmed closed" in out
    assert "close did not reach its relay; the valve may still be OPEN" not in out


def test_a_redundant_close_that_fails_after_a_confirmed_close_raises_no_alarm(
    fake_relay_handler, monkeypatch, capsys
):
    """The final safety close of the cage repeats pulse 9's confirmed close;
    losing it does not make the valve open."""
    fake_relay_handler.fail_on(nth=_close_write(9) + 1)
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is True and result.pulses == 9
    assert fake_relay_handler.dropped == [((CAGE,), 0)]
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out


def test_a_valve_open_when_its_close_is_lost_still_raises_the_alarm(
    fake_relay_handler, monkeypatch, capsys
):
    """The alarm stays for a valve that did open: every cage close lost."""
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    _lose_closes(fake_relay_handler, monkeypatch, 1_000, strategy.test_clock)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert "[VALVE CRITICAL] cage 1: the cage valve close" in capsys.readouterr().out
    assert fake_relay_handler.energized() == {CAGE}


def test_a_pump_retry_after_a_dry_first_attempt_plans_from_its_capped_volume(monkeypatch):
    """The review's case: chunk A (0.2 mL, 4 triggers planned) fails at its
    first trigger; chunk B then delivers 0.2 of the window's 0.3 mL; A's
    retry, capped to the 0.1 mL still owed, fired the 4 planned triggers."""
    worker, hat = _pump_worker(monkeypatch, window_target=0.3)
    _fail_on_writes(hat, {1})
    a = _pump_delivery(0.2, triggers=4)

    worker._handle_delivery(a)
    assert worker.delivered_volumes.get(1, 0) == 0
    worker._handle_delivery(_pump_delivery(0.2, triggers=4))
    assert worker.delivered_volumes[1] == pytest.approx(0.2)
    assert asyncio.run(worker.execute_delivery(a)) is True

    assert worker.delivered_volumes[1] == pytest.approx(0.3)
    assert _triggers_fired(hat) == 6


def test_a_pump_delivery_records_the_triggers_it_fired(monkeypatch):
    """First attempts went through trigger_relay, whose ledger rows said 0."""
    worker, _hat = _pump_worker(monkeypatch)
    worker._handle_delivery(_pump_delivery(0.25))
    assert _ledger(worker) == [("completed", 0.25, 5)]


def test_the_settling_window_waits_between_sensor_reads(fake_relay_handler, monkeypatch):
    """The settling loop's sleep sat after the loop, so it read the sensor as
    fast as it could for the whole window instead of once per sample period."""
    strategy = _sensor_strategy(fake_relay_handler, monkeypatch)
    reads = []

    def read_one():
        reads.append(strategy.test_clock.now)
        if len(reads) > 1_000:
            raise _Spinning("the settling loop never waits")

    strategy._sensor.read_one.side_effect = read_one
    asyncio.run(strategy._execute_single_pulse(CAGE))
    assert 1 < len(reads) < 100, "about one read per sample period over 0.33 s"



# --- review round 4 (PR #171) -------------------------------------------------------------------


def test_a_valve_left_open_before_the_run_still_raises_the_alarm(
    fake_relay_handler, monkeypatch, capsys
):
    """The review's case: a valve left open by a failed Stop or a crash, on a
    board that still does not answer. Its open fails, so this run never saw
    it switch; it must still alarm (it did on main). Independent topology:
    no master valve to cut the supply."""
    fake_relay_handler.states[CAGE] = 1  # open before the run
    fake_relay_handler.fail_on(relay=CAGE)
    strategy = _strategy(IndependentSolenoidController(fake_relay_handler, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert fake_relay_handler.energized() == {CAGE}
    out = capsys.readouterr().out
    assert "[VALVE CRITICAL] cage 1: the cage valve's relay is not answering" in out


def test_a_print_that_fails_cannot_leave_a_valve_open(fake_relay_handler, monkeypatch):
    """The review's case: a print between the open and the close raised (the
    journal pipe broken), the valve stayed open, and the pulse loop pulsed on
    for up to two minutes with it open. Prints now cannot raise."""
    import strategies.solenoid_flow_strategy as module  # noqa: PLC0415

    def broken_pipe(*args, **_kwargs):
        if args and str(args[0]).startswith("[VALVE]"):
            raise BrokenPipeError(32, "Broken pipe")

    monkeypatch.setattr(module, "print", broken_pipe, raising=False)
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is True and result.pulses == 9
    assert result.delivered_ml == pytest.approx(9 * Q)
    assert fake_relay_handler.energized() == set()


def test_an_unexpected_failure_in_a_pulse_ends_the_delivery(
    fake_relay_handler, monkeypatch, capsys
):
    """Anything but a relay fault used to be logged and skipped, the loop
    pulsing on. It now ends the delivery, and the valves are closed."""
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    real, calls = strategy._get_cage_calibration, []

    async def fails_on_pulse_3(cage_id):
        calls.append(cage_id)
        if len(calls) == 4:  # the plan's lookup, then pulses 1, 2 and 3
            raise RuntimeError("calibration store unavailable")
        return await real(cage_id)

    monkeypatch.setattr(strategy, "_get_cage_calibration", fails_on_pulse_3)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert result.pulses == 2
    assert result.delivered_ml == pytest.approx(2 * Q)
    assert [w for w in fake_relay_handler.trace if w == ((CAGE,), 1)] == [((CAGE,), 1)] * 2
    assert fake_relay_handler.energized() == set()
    assert "[VALVE ERROR] cage 1: pulse 3 failed: calibration store unavailable" in (
        capsys.readouterr().out
    )


def test_an_alarmed_valve_that_closes_after_all_says_so(fake_relay_handler, monkeypatch, capsys):
    """The first close and every retry are lost (alarm); the delivery's final
    safety close gets through. The operator is told, instead of being left
    with an alarm about a valve that is closed."""
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    retries = len(strategy.CLOSE_RETRY_DELAYS_S)
    _lose_closes(fake_relay_handler, monkeypatch, 1 + retries, strategy.test_clock)

    result = _deliver(strategy, 9)

    assert result.success is False
    assert fake_relay_handler.energized() == set()
    out = capsys.readouterr().out
    alarm = out.index("[VALVE CRITICAL] cage 1: the cage valve close did not reach its relay")
    assert out.index("[VALVE OK] The cage 1 valve closed after all") > alarm


def test_a_valve_command_it_cannot_identify_counts_as_possibly_open(monkeypatch, capsys):
    """Tracking reads the controller method's name; a wrapped or mocked one
    has none. It must fail safe (alarm), not silence the alarm."""
    strategy = _strategy(MagicMock(), monkeypatch)
    assert strategy._closed(MagicMock(return_value=True), CAGE) is True
    strategy._alarm_unclosed(CAGE, "cage")
    assert "cannot be confirmed closed" in capsys.readouterr().out



# --- review round 5 (PR #171) -------------------------------------------------------------------


def test_an_open_that_latched_but_reported_failure_still_alarms(
    fake_relay_handler, monkeypatch, capsys
):
    """The review's case (critical): pulses 1 and 2 are clean, so the cage was
    seen closed. Pulse 3's open reaches the relay but reports an error, and
    every later write is lost. The valve is open; with no master (independent)
    nothing cuts its supply. It was logged as 'seen to close and has not
    opened since' with no alarm: an attempted open now makes it unknown."""
    real, opens = fake_relay_handler.set_relays, []

    def third_open_latches(relay_ids, state):
        if tuple(relay_ids) == (CAGE,) and state:
            opens.append(1)
            if len(opens) == 3:
                real(relay_ids, state)  # the relay switched on...
                return False  # ...and the write reported a failure
        if len(opens) >= 3:
            return False  # the bus stays wedged
        return real(relay_ids, state)

    monkeypatch.setattr(fake_relay_handler, "set_relays", third_open_latches)
    strategy = _strategy(IndependentSolenoidController(fake_relay_handler, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 9)

    assert result.pulses == 2
    assert fake_relay_handler.energized() == {CAGE}, "the valve is open"
    out = capsys.readouterr().out
    assert "[VALVE CRITICAL] cage 1: the cage valve's relay is not answering" in out


@pytest.mark.parametrize("width_ms", [10, 12, 15, 20, 30, 50, 100, 200, 500])
def test_a_late_close_is_priced_at_no_less_than_the_bench_flow_at_every_width(width_ms):
    """The review's case: a proportional floor on the flowing time priced the
    late close of a pulse under 18 ms far below the valve's steady flow (0.26x
    at 10 ms), so the rest of the dose, sent afterwards, over-dosed. The bench
    fit: volume = 1.544 uL/ms x width - 13.4 uL."""
    pulse_ml = (1.544 * width_ms - 13.4) / 1000
    by_time = SolenoidFlowStrategy._pulse_by_open_time
    rate_ul_per_ms = (by_time(pulse_ml, 0.0, 1.0, width_ms / 1000) - pulse_ml) / 1.0  # mL/s == uL/ms
    assert 1.544 <= rate_ul_per_ms <= 1.544 * 1.35


class _BrokenStdout:
    """sys.stdout after the journal pipe has gone."""

    def write(self, _text):
        raise BrokenPipeError(32, "Broken pipe")

    def flush(self):
        raise BrokenPipeError(32, "Broken pipe")


@pytest.mark.parametrize("controller", ["shared", "independent"])
def test_a_broken_stdout_cannot_stop_a_close(fake_relay_handler, monkeypatch, controller):
    """The review's case: the valve controller printed before each close write,
    so a broken stdout stopped every close before it was written, and the
    valve stayed open. Every print on the path now cannot raise."""
    import sys  # noqa: PLC0415

    valves = (
        SolenoidController(fake_relay_handler, MASTER, CAGE_MAP)
        if controller == "shared"
        else IndependentSolenoidController(fake_relay_handler, CAGE_MAP)
    )
    strategy = _strategy(valves, monkeypatch)
    monkeypatch.setattr(sys, "stdout", _BrokenStdout())

    result = _deliver(strategy, 9)

    assert result.success is True and result.pulses == 9
    assert fake_relay_handler.energized() == set()



# --- review round 6 (PR #171) -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("width_ms", "pulse_ul"),
    [(10, 23.4), (10, 5.0), (12, 24.0), (17, 40.0)],
)
def test_a_late_close_is_never_priced_above_what_a_valve_can_pass(width_ms, pulse_ul):
    """The review's case: with a width near the dead time the model divides by
    about a millisecond. The retired valve's 10 ms / 23.4 uL pulse, closed
    20 ms late (about 54 uL of water), was credited 491 uL, and the retry then
    withheld the dose. The rate is capped at what a fully open valve passes."""
    pulse_ml = pulse_ul / 1000
    by_time = SolenoidFlowStrategy._pulse_by_open_time
    cap = SolenoidFlowStrategy.MAX_STEADY_FLOW_ML_S
    credited = by_time(pulse_ml, 0.0, 0.020, width_ms / 1000)
    assert credited <= pulse_ml + 0.020 * cap + 1e-12
    assert credited >= pulse_ml


def test_the_retired_valve_s_short_pulse_is_credited_sensibly():
    by_time = SolenoidFlowStrategy._pulse_by_open_time
    assert by_time(0.0234, 0.0, 0.020, 0.010) == pytest.approx(0.0234 + 0.020 * 2.1)  # 65.4 uL
    assert by_time(0.034164, 0.0, 1.0, 0.030) == pytest.approx(0.034164 + 0.034164 / 0.021), (
        "production is under the ceiling and unchanged"
    )


def test_an_open_that_took_long_to_fail_is_reported(fake_relay_handler, monkeypatch, capsys):
    """The review's case: an open that hangs for about a second (an I2C
    timeout) and then reports failure may have switched the relay first. No
    water is credited for a failed open, so the operator is told."""
    strategy = _strategy(IndependentSolenoidController(fake_relay_handler, CAGE_MAP), monkeypatch)
    real, opens = fake_relay_handler.set_relays, []

    def third_open_hangs(relay_ids, state):
        if tuple(relay_ids) == (CAGE,) and state:
            opens.append(1)
            if len(opens) == 3:
                strategy.test_clock.now += 1.0
                return False
        return real(relay_ids, state)

    monkeypatch.setattr(fake_relay_handler, "set_relays", third_open_hangs)

    result = _deliver(strategy, 9)

    assert result.pulses == 2 and result.delivered_ml == pytest.approx(2 * Q)
    out = capsys.readouterr().out
    assert "the command took 1.0 s to fail" in out
    assert "its water is not counted" in out


def test_an_open_that_fails_at_once_gets_no_such_note(fake_relay_handler, monkeypatch, capsys):
    fake_relay_handler.fail_on(nth=_open_write(3))
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    _deliver(strategy, 9)
    assert "to fail" not in capsys.readouterr().out


@pytest.mark.parametrize("fault", ["hat missing", "first hat errors"])
def test_a_broken_stdout_cannot_stop_the_all_off(monkeypatch, fault):
    """The review's case: set_all_relays printed its "HAT missing" line before
    writing to the HATs that are there, and its error line between HATs. With
    a broken stdout the emergency all-off raised before reaching a present
    HAT, and that is the action every alarm tells the operator to use."""
    import sys  # noqa: PLC0415

    present = {0} if fault == "hat missing" else {0, 1}
    handler, hats = _relay_handler(monkeypatch, 2, present=present)
    assert handler.set_relays([3], 1) is True
    if fault == "first hat errors":
        hats[0].fail = True
    monkeypatch.setattr(sys, "stdout", _BrokenStdout())

    assert handler.set_all_relays(0) is False, "one HAT did not take it"

    reached = hats[0] if fault == "hat missing" else hats[1]
    assert reached.writes[-1] == ("all", 0), "the HAT that answers was still switched off"


def test_a_broken_stdout_cannot_stop_a_pump_relay_s_switch_off(monkeypatch, caplog):
    """A failed write's own print raised out of the switch-off, so the retry
    and the alarm never ran."""
    import sys  # noqa: PLC0415

    from models.relay_unit import RelayUnit  # noqa: PLC0415

    handler, hats = _relay_handler(monkeypatch, 1)
    handler.relay_units = {1: RelayUnit(unit_id=1, relay_ids=(3,))}
    real_set, offs = hats[0].set, []

    def lose_first_off(relay, state):
        if not state:
            offs.append(relay)
            if len(offs) == 1:
                raise OSError(121, "Remote I/O error")
        real_set(relay, state)

    hats[0].set = lose_first_off
    monkeypatch.setattr(sys, "stdout", _BrokenStdout())

    assert handler.trigger_relays([1], {"1": 2}, 0) == ["Relay Unit 1 triggered 2 times"]
    assert len(offs) == 3, "the lost switch-off was tried again, then trigger 2's"
    assert hats[0].writes[-1] == (3, 0)

    hats[0].fail_off = True
    with caplog.at_level("ERROR"):
        assert handler.trigger_relays([1], {"1": 1}, 0) == []
    assert any("[VALVE CRITICAL] relay unit 1" in r.getMessage() for r in caplog.records)


def test_the_sensor_loop_s_own_close_counts_as_seen(fake_relay_handler, monkeypatch, capsys):
    """Legacy continuous mode with a sensor: the loop closed the valves outside
    the state tracking, so when its close got through and the finally's repeat
    of it was lost, the alarm said the valve may still be OPEN."""
    strategy = _continuous_sensor_strategy(fake_relay_handler, monkeypatch)

    async def no_reading(_cage_id, _max_errors):
        return None  # every read fails: the loop gives up and closes

    monkeypatch.setattr(strategy, "_read_sensor_robust", no_reading)
    real, cage_closes = fake_relay_handler.set_relays, []

    def lose_the_repeat(relay_ids, state):
        if tuple(relay_ids) == (CAGE,) and not state:
            cage_closes.append(1)
            if len(cage_closes) == 2:
                return False  # the finally's redundant close
        return real(relay_ids, state)

    monkeypatch.setattr(fake_relay_handler, "set_relays", lose_the_repeat)

    result = asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=0.6))

    assert result.success is False
    assert len(cage_closes) == 2
    assert fake_relay_handler.energized() == set()
    assert "[VALVE CRITICAL]" not in capsys.readouterr().out


def test_a_strategy_can_be_built_and_deliver_with_stdout_already_broken(
    fake_relay_handler, monkeypatch
):
    """Its two start-up debug prints used to raise before any delivery."""
    import sys  # noqa: PLC0415

    monkeypatch.setattr(sys, "stdout", _BrokenStdout())
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 3)

    assert result.success is True and result.pulses == 3
    assert fake_relay_handler.energized() == set()


# --- the stop line exists on every path (docs review) -----------------------------------------


@pytest.mark.parametrize(
    ("controller", "reason"),
    [
        ("shared", "manifold prime failed: open_master() did not reach its relay"),
        ("independent", "pulse failed: open_cage(1) did not reach its relay"),
    ],
)
def test_a_dead_hat_prints_the_stop_line_on_both_topologies(
    fake_relay_handler, monkeypatch, capsys, controller, reason
):
    """The docs review's case: on the shared manifold a dead HAT fails every
    delivery at the manifold prime, and that failure reached only the logger.
    The docs, the Help tab and the circuit breaker all send the operator to a
    [VALVE ERROR] line that the production rig never printed."""
    monkeypatch.setattr(fake_relay_handler, "set_relays", lambda _ids, _state: False)
    valves = (
        SolenoidController(fake_relay_handler, MASTER, CAGE_MAP)
        if controller == "shared"
        else IndependentSolenoidController(fake_relay_handler, CAGE_MAP)
    )
    strategy = _strategy(valves, monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is False
    out = capsys.readouterr().out
    assert f"[VALVE ERROR] cage 1: {reason}; delivery stopped after 0 pulse(s), 0.000 mL" in out
    assert "Check the relay HAT; one that was not found at start-up needs RRR restarted." in out


def test_a_master_hold_that_does_not_open_prints_the_stop_line(
    fake_relay_handler, monkeypatch, capsys
):
    """The prime's open and close get through; the hold's open is lost."""
    fake_relay_handler.fail_on(nth=3)
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)

    result = _deliver(strategy, 9)

    assert result.success is False and result.pulses == 0
    assert all(CAGE not in ids or not state for ids, state in fake_relay_handler.trace)
    out = capsys.readouterr().out
    assert (
        "[VALVE ERROR] cage 1: open_master() did not reach its relay; delivery stopped after "
        "0 pulse(s), 0.000 mL. Check the relay HAT"
    ) in out


# --- a Stop around the manifold prime (v2.0.0) -----------------------------------------------
#
# The stop sequence switches every relay off first, then cancels. The prime
# had no cancel check, so a Stop during it, or just before it, reopened the
# master for the 0.3 s hold (and, before the prime, for the prime itself)
# after the all-off.


def _stop_at(fake, strategy, monkeypatch, when):
    """Run the stop sequence's first two steps (all relays off, then the
    cancel) at the first sleep where ``when(trace)`` holds."""
    fake_sleep = asyncio.sleep  # the fake clock's

    async def _sleep(seconds):
        if when(fake.trace) and not strategy._check_cancelled():
            fake.set_all_relays(0)
            strategy.request_cancel()
        await fake_sleep(seconds)

    monkeypatch.setattr(asyncio, 'sleep', _sleep)


def test_a_stop_during_the_prime_does_not_open_the_master_again(fake_relay_handler, monkeypatch):
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    _stop_at(fake_relay_handler, strategy, monkeypatch, lambda t: t == [((MASTER,), 1)])

    result = _deliver(strategy, 9)

    assert result.success is False and result.pulses == 0
    after_stop = fake_relay_handler.trace[fake_relay_handler.trace.index((("all",), 0)) :]
    assert all(state == 0 for _ids, state in after_stop), after_stop
    assert fake_relay_handler.energized() == set()


def test_a_stop_before_the_prime_opens_no_valve(fake_relay_handler, monkeypatch):
    """The cancel landed after deliver() checked, e.g. during a sensor restart."""
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    pulse_mode = strategy._deliver_pulse_mode

    async def _stopped_first(cage_id, volume_ml):
        fake_relay_handler.set_all_relays(0)
        strategy.request_cancel()
        return await pulse_mode(cage_id, volume_ml)

    monkeypatch.setattr(strategy, '_deliver_pulse_mode', _stopped_first)

    result = _deliver(strategy, 9)

    assert result.success is False and result.pulses == 0
    assert fake_relay_handler.trace == [(("all",), 0)], "no valve opened after the all-off"


def test_a_stop_during_the_hold_closes_the_master_without_a_pulse(fake_relay_handler, monkeypatch):
    """Unchanged: the loop's first check ends a delivery stopped during the hold."""
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    hold = [((MASTER,), 1), ((MASTER,), 0), ((MASTER,), 1)]
    _stop_at(fake_relay_handler, strategy, monkeypatch, lambda t: t == hold)

    result = _deliver(strategy, 9)

    assert result.success is False and result.pulses == 0
    assert ((CAGE,), 1) not in fake_relay_handler.trace, "no pulse fired"
    assert fake_relay_handler.energized() == set()


# --- the pulse and time limits print the stop line too (last review) ---------------------------
#
# Four ways a pulse delivery fails without any relay fault: two refusals
# before water moves and two limits inside the loop. Each reached only the
# logger, so the circuit breaker's "a [VALVE ERROR] line above names the
# cage" pointed at nothing.

STOP_LINE = r"\[VALVE ERROR\] cage 1: {reason}; delivery stopped after {pulses} pulse\(s\), {ml} mL"


def _stop_lines(out):
    return [line for line in out.splitlines() if "delivery stopped after" in line]


def test_a_dose_over_the_pulse_limit_is_refused_with_the_stop_line(
    fake_relay_handler, monkeypatch, capsys
):
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    strategy._settings['max_pulses_per_delivery'] = 5

    result = _deliver(strategy, 9)

    assert result.success is False and result.pulses == 0
    assert all(CAGE not in ids for ids, _state in fake_relay_handler.trace), "no pulse fired"
    lines = _stop_lines(capsys.readouterr().out)
    assert len(lines) == 1
    assert re.fullmatch(
        STOP_LINE.format(
            reason=r"the dose needs about \d+ pulses, over the limit of 5 "
            r"\(dose too large, or the calibration is wrong\)",
            pulses=0,
            ml=r"0\.000",
        ),
        lines[0],
    ), lines[0]
    assert "Check the relay HAT" not in lines[0], "not a relay fault"


def test_a_delivery_too_slow_for_the_time_limit_is_refused_with_the_stop_line(
    fake_relay_handler, monkeypatch, capsys
):
    strategy = _strategy(IndependentSolenoidController(fake_relay_handler, CAGE_MAP), monkeypatch)
    strategy._settings['max_pulse_delivery_time_s'] = 5.0

    result = _deliver(strategy, 9)

    assert result.success is False and result.pulses == 0
    assert fake_relay_handler.trace == [], "refused before any relay moved"
    lines = _stop_lines(capsys.readouterr().out)
    assert len(lines) == 1
    assert re.fullmatch(
        STOP_LINE.format(
            reason=r"the delivery would take about \d+\.\d s, over the limit of 5 s "
            r"\(\d+ pulses at 30 ms \+ 1000 ms rest\): shorten the rest between pulses or "
            r"split the dose",
            pulses=0,
            ml=r"0\.000",
        ),
        lines[0],
    ), lines[0]
    assert "Check the relay HAT" not in lines[0]


def test_the_pulse_limit_inside_the_loop_prints_the_stop_line(
    fake_relay_handler, monkeypatch, capsys
):
    """Pulses that give less than planned (a sensor-corrected pulse) run the
    loop into its pulse limit with water already in the cage."""
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    strategy._settings['max_pulses_per_delivery'] = 10

    async def _weak_pulse(_cage_id):
        return Q / 10

    monkeypatch.setattr(strategy, '_execute_single_pulse', _weak_pulse)

    result = _deliver(strategy, 9)

    assert result.success is False and result.pulses == 10
    assert abs(result.delivered_ml - Q) < 1e-9
    lines = _stop_lines(capsys.readouterr().out)
    assert lines == [
        "[VALVE ERROR] cage 1: the limit of 10 pulses was reached; delivery stopped after "
        "10 pulse(s), 0.034 mL"
    ]


def test_the_time_limit_inside_the_loop_prints_the_stop_line(
    fake_relay_handler, monkeypatch, capsys
):
    """The estimate fits the limit, but each pulse then takes far longer
    (relay writes that succeed slowly)."""
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    strategy._settings['max_pulse_delivery_time_s'] = 20.0

    async def _slow_pulse(_cage_id):
        strategy.test_clock.now += 8.0
        return Q

    monkeypatch.setattr(strategy, '_execute_single_pulse', _slow_pulse)

    result = _deliver(strategy, 9)

    assert result.success is False and result.pulses == 3
    assert abs(result.delivered_ml - 3 * Q) < 1e-9
    lines = _stop_lines(capsys.readouterr().out)
    assert lines == [
        "[VALVE ERROR] cage 1: the time limit of 20 s was passed; delivery stopped after "
        "3 pulse(s), 0.102 mL"
    ]


def test_an_operator_stop_prints_no_stop_line(fake_relay_handler, monkeypatch, capsys):
    """Stop is not a failure: the delivery ends, the valves close, no [VALVE ERROR]."""
    strategy = _strategy(SolenoidController(fake_relay_handler, MASTER, CAGE_MAP), monkeypatch)
    fired = []

    async def _pulse_then_stop(_cage_id):
        fired.append(1)
        if len(fired) == 2:
            strategy.request_cancel()
        return Q

    monkeypatch.setattr(strategy, '_execute_single_pulse', _pulse_then_stop)

    result = _deliver(strategy, 9)

    assert result.success is False and result.pulses == 2
    out = capsys.readouterr().out
    assert "VALVE ERROR" not in out and "delivery stopped after" not in out
    assert fake_relay_handler.energized() == set()


def test_the_time_refusal_never_prints_two_equal_figures(fake_relay_handler, monkeypatch, capsys):
    """Rounded to whole seconds, an estimate just over a limit that is not a
    whole number read "about 11 s, over the limit of 11 s"."""
    strategy = _strategy(IndependentSolenoidController(fake_relay_handler, CAGE_MAP), monkeypatch)
    strategy._settings['max_pulse_delivery_time_s'] = 11.2

    result = _deliver(strategy, 9)

    assert result.success is False and fake_relay_handler.trace == []
    (line,) = _stop_lines(capsys.readouterr().out)
    said = re.search(r"would take about ([\d.]+) s, over the limit of ([\d.]+) s", line)
    assert said, line
    assert said.group(2) == "11.2", "the limit as configured"
    assert float(said.group(1)) > float(said.group(2)), line
