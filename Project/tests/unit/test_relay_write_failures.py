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
import threading
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

    async def _no_sleep(_seconds):
        return None

    async def _no_rest(_interval_ms):
        return False

    monkeypatch.setattr(asyncio, 'sleep', _no_sleep)
    monkeypatch.setattr(strategy, '_rest_between_pulses', _no_rest)
    return strategy


def _deliver(strategy, pulses):
    return asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=pulses * Q))


# The shared manifold's writes: prime (1, 2), hold (3), then per pulse n an
# open at 2n + 2 and a close at 2n + 3, then the final cage and master close.
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
    assert get_operation_lock().is_busy() is False, "the failsafe still frees the lock"


def test_a_confirmed_emergency_stop_is_unchanged(priming, fake_relay_handler):
    panel, shown = priming
    panel._on_emergency_stop_clicked()
    assert shown == [("information", "Emergency Stop")]


def test_close_master_keeps_it_open_when_the_cages_did_not_close(priming, fake_relay_handler):
    panel, shown = priming
    panel._on_open_master_clicked()
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(CAGE))
    panel._on_open_cage_clicked()
    fake_relay_handler.fail_on(relay=CAGE)

    panel._on_close_master_clicked()

    assert shown[-1] == ("warning", "Hardware Error")
    assert panel._model.is_master_open, "the master stays open with a cage unconfirmed"
    assert fake_relay_handler.energized() == {MASTER, CAGE}
