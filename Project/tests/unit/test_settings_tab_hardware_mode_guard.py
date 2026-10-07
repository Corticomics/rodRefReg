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


def test_a_backup_file_cannot_switch_the_mode_behind_the_guard(
    qapp, system_controller, database_handler, warnings, monkeypatch, tmp_path
):
    """The review's case: Restore from Backup wrote hardware_mode straight
    into the settings the next run copies, with no guard and the combo still
    showing Solenoid."""
    import json  # noqa: PLC0415

    from PyQt5.QtWidgets import QFileDialog, QMessageBox  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    backup = tmp_path / "backup.json"
    # Widget values equal to the current ones: a changed widget would
    # auto-save the combo's mode back over the backup's and hide the bug.
    backup.write_text(
        json.dumps(
            {
                "pump_volume_ul": 50,
                "calibration_factor": 1.0,
                "min_trigger_interval_ms": 600,
                "hardware_mode": "pump",
            }
        )
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(backup), ""))
    )
    shown = []
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[2]))
    )
    tab = _tab(system_controller, database_handler)
    assert get_operation_lock().try_acquire("schedule")

    tab.restore_from_backup()

    assert system_controller.settings["min_trigger_interval_ms"] == 600, "the rest applies"
    _assert_still_solenoid(tab, system_controller, database_handler)
    assert "hardware mode (pump) was not applied" in shown[-1]


@pytest.mark.parametrize("backup_hats", [1, 2])
def test_a_backup_file_cannot_change_the_relay_layout(
    qapp, system_controller, database_handler, monkeypatch, tmp_path, backup_hats
):
    """The relay layout is the device's wiring. Restored from a file, a new
    HAT count would leave the relay handlers, and a priming session's
    valves, on the old one: it changes only through Change Relay Hats."""
    import json  # noqa: PLC0415

    from PyQt5.QtWidgets import QFileDialog, QMessageBox  # noqa: PLC0415

    system_controller.settings["num_hats"] = 2
    system_controller.settings["global_master_relay_id"] = 16
    system_controller.settings["cage_relays"] = {"1": 1}
    backup = tmp_path / "backup.json"
    backup.write_text(
        json.dumps(
            {
                "pump_volume_ul": 50,
                "calibration_factor": 1.0,
                "min_trigger_interval_ms": 700,
                "num_hats": backup_hats,
                "global_master_relay_id": 8,
                "relay_pairs": [[1, 2]],
                "cage_relays": {"1": 9},
            }
        )
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(backup), ""))
    )
    shown = []
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[2]))
    )
    tab = _tab(system_controller, database_handler)

    tab.restore_from_backup()

    settings = system_controller.settings
    assert settings["min_trigger_interval_ms"] == 700, "the rest applies"
    assert settings["num_hats"] == 2
    assert settings["global_master_relay_id"] == 16
    assert settings["cage_relays"] == {"1": 1}
    assert settings.get("relay_pairs") != [[1, 2]]
    said = "relay layout (1 relay HAT(s)) was not applied: this device keeps its 2"
    assert (said in shown[-1]) == (backup_hats == 1), "said only when the count differs"
