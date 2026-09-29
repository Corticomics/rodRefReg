"""The Hardware Mode switch is refused while anything drives the hardware.

It used to check ``run_stop_section.worker``, an attribute RunStopSection
never had, so a switch between solenoid and pump went through (and was
auto-saved) in the middle of a schedule, a priming session or a
calibration. It now uses the same check as the valve topology control.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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


@pytest.fixture(autouse=True)
def _no_worker_running(monkeypatch):
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: False)


@pytest.fixture(autouse=True)
def warnings(monkeypatch):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    shown = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: shown.append(a[1]) or QMessageBox.Ok)
    )
    return shown


def _tab(system_controller, database_handler, run_stop=None):
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    return SettingsTab(
        system_controller,
        login_system=login,
        run_stop_section=run_stop,
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
    )


def _switch_to_pump(tab):
    tab.hardware_mode_combo.setCurrentIndex(tab.hardware_mode_combo.findData("pump"))


def _assert_still_solenoid(tab, system_controller, database_handler):
    assert tab.hardware_mode_combo.currentData() == "solenoid", "the combo is put back"
    assert system_controller.settings["hardware_mode"] == "solenoid"
    assert database_handler.get_system_settings().get("hardware_mode", "solenoid") == "solenoid"


def test_an_idle_device_switches_and_saves(qapp, system_controller, database_handler, warnings):
    tab = _tab(system_controller, database_handler)
    assert tab.hardware_mode_combo.isEnabled()
    _switch_to_pump(tab)
    assert system_controller.settings["hardware_mode"] == "pump"
    assert database_handler.get_system_settings()["hardware_mode"] == "pump"
    assert warnings == []


@pytest.mark.parametrize("operation", ["schedule", "priming", "calibration"])
def test_refused_while_a_hardware_operation_holds_the_lock(
    qapp, system_controller, database_handler, warnings, operation
):
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    tab = _tab(system_controller, database_handler)
    lock = get_operation_lock()
    assert lock.try_acquire(operation)
    assert not tab.hardware_mode_combo.isEnabled()
    assert tab.hardware_mode_combo.toolTip() == (
        f"Unavailable while {lock.active_label()} is in progress"
    )

    _switch_to_pump(tab)  # what a click would do, had the combo been live

    assert warnings == ["Cannot Change Mode"]
    _assert_still_solenoid(tab, system_controller, database_handler)
    lock.release(operation)
    assert tab.hardware_mode_combo.isEnabled()


def test_refused_while_a_delivery_worker_runs(
    qapp, system_controller, database_handler, warnings, monkeypatch
):
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)
    tab = _tab(system_controller, database_handler)
    _switch_to_pump(tab)
    assert warnings == ["Cannot Change Mode"]
    _assert_still_solenoid(tab, system_controller, database_handler)


def test_refused_while_the_run_stop_section_has_a_job(
    qapp, system_controller, database_handler, warnings
):
    tab = _tab(system_controller, database_handler, run_stop=SimpleNamespace(job_in_progress=True))
    _switch_to_pump(tab)
    assert warnings == ["Cannot Change Mode"]
    _assert_still_solenoid(tab, system_controller, database_handler)
