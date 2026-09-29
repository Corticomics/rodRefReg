"""StrategyFactory refuses a hardware mode it does not know (v1.21.0).

It used to fall back to the pump strategy for any unrecognised value, and
the worker defaulted a missing mode to 'pump'. On a valve rig either path
would pulse the relays with pump trigger timing instead of refusing.
Devices always boot in 'solenoid' (SystemController forces it), so these
pin the configuration-error paths, not a production one.
"""

from __future__ import annotations

import pytest

from drivers.solenoid_controller import SolenoidController
from strategies.factory import VALID_HARDWARE_MODES, StrategyFactory
from strategies.pump_strategy import PumpStrategy
from strategies.solenoid_flow_strategy import SolenoidFlowStrategy

PULSE_SETTINGS = {
    'use_pulse_delivery': True,
    'pulse_width_ms': 30,
    'pulse_settling_ms': 100,
    'max_pulses_per_delivery': 100,
    'max_pulse_delivery_time_s': 120.0,
}


@pytest.mark.parametrize("mode", ["solenoid", " Solenoid ", "SOLENOID"])
def test_solenoid_modes_build_the_solenoid_strategy(fake_relay_handler, mode):
    strategy = StrategyFactory.create(
        mode,
        solenoid_controller=SolenoidController(fake_relay_handler, 16, {1: 1}),
        settings=dict(PULSE_SETTINGS),
    )
    assert isinstance(strategy, SolenoidFlowStrategy)
    assert fake_relay_handler.trace == [], "building a strategy drives nothing"


@pytest.mark.parametrize("mode", ["pump", " Pump "])
def test_pump_mode_builds_the_pump_strategy(mode):
    strategy = StrategyFactory.create(mode, pump_controller=object(), volume_calculator=object())
    assert isinstance(strategy, PumpStrategy)


@pytest.mark.parametrize("mode", ["valve", "solenoidd", "", "   ", None, 1])
def test_unknown_modes_are_refused_not_pumped(mode):
    with pytest.raises(ValueError) as excinfo:
        StrategyFactory.create(mode, pump_controller=object(), volume_calculator=object())
    message = str(excinfo.value)
    assert "hardware_mode" in message and repr(mode) in message
    assert all(valid in message for valid in VALID_HARDWARE_MODES)


def test_solenoid_mode_still_requires_its_controller():
    with pytest.raises(ValueError, match="solenoid_controller"):
        StrategyFactory.create("solenoid", settings=dict(PULSE_SETTINGS))


# --- the worker's side ------------------------------------------------------


@pytest.fixture
def resolve():
    pytest.importorskip("PyQt5")
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415

    return RelayWorker._resolve_hardware_mode


@pytest.mark.parametrize(
    "settings,expected",
    [
        ({}, "solenoid"),
        ({"hardware_mode": None}, "solenoid"),
        ({"hardware_mode": ""}, "solenoid"),
        ({"hardware_mode": "solenoid"}, "solenoid"),
        ({"hardware_mode": " Pump "}, "pump"),
        ({"hardware_mode": "valve"}, "valve"),  # passed through; the factory refuses it
    ],
)
def test_worker_resolves_a_missing_mode_to_solenoid(resolve, settings, expected):
    assert resolve(settings) == expected


def test_worker_rejects_settings_that_are_not_a_dict(resolve):
    with pytest.raises(TypeError, match="dict"):
        resolve(None)
