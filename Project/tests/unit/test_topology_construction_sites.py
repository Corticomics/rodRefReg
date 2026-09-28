"""The three places that build a valve controller all ask the topology (v1.20.0).

RelayWorker (schedules), PrimingControlWidget and the calibration wizard
each construct their own SolenoidController. From v1.20.0 all three go
through ``utils.topology.build_solenoid_controller`` so one device setting
decides, once, whether a master valve exists. The wizard's site is covered
in test_calibration_wizard_thread.py; this module covers the worker's
hardware initialisation (which had no test at all) and the priming widget.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from drivers.solenoid_controller import (  # noqa: E402
    IndependentSolenoidController,
    SolenoidController,
)

SHARED = {"num_hats": 1, "global_master_relay_id": 16, "valve_topology": "shared_manifold"}
INDEPENDENT = {"num_hats": 1, "global_master_relay_id": 16, "valve_topology": "independent"}


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


# --- RelayWorker._initialize_hardware ----------------------------------------


class _StubDB:
    def get_all_valve_calibrations(self):
        return {}

    def get_valve_calibration(self, cage_id):
        return None


def _worker(fake, settings, monkeypatch):
    """A RelayWorker with __init__ bypassed, ready for the deferred hardware init."""
    from drivers.uart_flow_sensor import TeensyUnavailableError  # noqa: PLC0415
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QObject  # noqa: PLC0415

    def _no_teensy(_settings):
        raise TeensyUnavailableError("no Teensy on this bench")

    monkeypatch.setattr("drivers.flow_sensor_factory.create_flow_sensor", _no_teensy)

    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker._deferred_solenoid_init = True
    worker._system_settings = dict(settings)
    worker.flow_sensor_optional = True
    worker.flow_sensor_available = False
    worker.relay_handler = fake
    worker.hardware_mode = 'solenoid'
    worker.pump_controller = None
    worker.volume_calculator = None
    worker.system_controller = SimpleNamespace(database_handler=_StubDB())
    worker.emitted = []
    worker.progress.connect(worker.emitted.append)
    return worker


def test_worker_builds_the_shared_controller_on_the_production_settings(
    fake_relay_handler, monkeypatch
):
    worker = _worker(fake_relay_handler, SHARED, monkeypatch)
    worker._initialize_hardware()

    valves = worker.strategy._valves
    assert type(valves) is SolenoidController
    assert valves.has_master is True
    assert valves._master == 16
    # No cage_relays stored: the fallback map is the 15 cages that skip the master.
    assert valves._cage_map == {cage: cage for cage in range(1, 16)}
    assert worker.strategy._has_master is True
    assert worker.flow_sensor_available is False  # calibration-only, as in production
    assert fake_relay_handler.trace == [], "initialisation drives no relay"


def test_worker_builds_the_independent_controller_from_the_setting(
    fake_relay_handler, monkeypatch
):
    worker = _worker(fake_relay_handler, INDEPENDENT, monkeypatch)
    worker._initialize_hardware()

    valves = worker.strategy._valves
    assert isinstance(valves, IndependentSolenoidController)
    assert worker.strategy._has_master is False
    valves.open_master()
    assert fake_relay_handler.trace == [], "the independent controller never drives relay 16"


def test_worker_honours_a_stored_cage_map(fake_relay_handler, monkeypatch):
    settings = dict(SHARED, cage_relays={"1": 3, "2": 7})
    worker = _worker(fake_relay_handler, settings, monkeypatch)
    worker._initialize_hardware()
    assert worker.strategy._valves._cage_map == {1: 3, 2: 7}


# --- PrimingControlWidget ------------------------------------------------------


@pytest.fixture
def priming_hardware(monkeypatch, fake_relay_handler):
    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    return fake_relay_handler


def test_priming_widget_builds_the_shared_controller(qapp, priming_hardware):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    widget = PrimingControlWidget(dict(SHARED), lambda *_: None)
    valves = widget._get_solenoid_controller()
    assert type(valves) is SolenoidController
    valves.open_master()
    assert priming_hardware.trace == [((16,), 1)]


def test_priming_widget_builds_the_independent_controller(qapp, priming_hardware):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    widget = PrimingControlWidget(dict(INDEPENDENT), lambda *_: None)
    valves = widget._get_solenoid_controller()
    assert isinstance(valves, IndependentSolenoidController)
    valves.open_master()
    valves.open_cage(3)
    assert priming_hardware.trace == [((3,), 1)], "master control is a no-op, cage still works"
