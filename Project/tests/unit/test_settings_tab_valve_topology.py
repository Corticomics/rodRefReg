"""The valve topology control in Settings > Delivery (v1.21.0).

Headless (``QT_QPA_PLATFORM=offscreen``). The real ``SettingsTab`` runs
against the test ``SystemController`` and database. The radios show the
stored topology. A confirmed change is saved on its own, read back,
announced and marks other-topology calibrations Stale, and priming cannot
open a valve until RRR restarts. Every unsafe moment leaves the device on
its old topology:

- a hardware operation holding the lock;
- a delivery worker running, or the Run/Stop section mid-job;
- a schedule starting while the confirmation is open;
- nobody logged in;
- a database that does not keep the value.

A backup file cannot change the topology either.
"""

from __future__ import annotations

import io
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SHARED = "shared_manifold"
INDEPENDENT = "independent"
RESTART_TIP = "Restart RRR to prime with the new valve topology"


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    # SettingsTab and the priming panel subscribe to the OperationLock
    # singleton: a fresh one per test, as the other UI test modules do.
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


@pytest.fixture(autouse=True)
def _no_worker_running(monkeypatch):
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: False)


@pytest.fixture(autouse=True)
def journal(monkeypatch):
    """The process's own stdout, where the change is logged for the journal."""
    stream = io.StringIO()
    monkeypatch.setattr(sys, "__stdout__", stream)
    return stream


@pytest.fixture(autouse=True)
def dialogs(monkeypatch):
    """Record every message box instead of showing it (a modal box blocks a
    headless run). ``dialogs.answer`` is what the confirmation returns."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    record = SimpleNamespace(shown=[], answer=QMessageBox.No)

    def box(kind):
        def show(_parent, title, text, *_rest, **_kw):
            record.shown.append((kind, title, text))
            return record.answer if kind == "question" else QMessageBox.Ok

        return staticmethod(show)

    for kind in ("warning", "critical", "information", "question"):
        monkeypatch.setattr(QMessageBox, kind, box(kind))
    return record


def _titles(dialogs, kind):
    return [title for shown_kind, title, _text in dialogs.shown if shown_kind == kind]


def _settings_tab(
    system_controller, database_handler, *, logged_in=True, run_stop=None, terminal=None
):
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    login = SimpleNamespace(
        is_logged_in=lambda: logged_in,
        get_current_trainer=lambda: {"username": "alice", "role": "normal"} if logged_in else None,
    )
    return SettingsTab(
        system_controller,
        login_system=login,
        run_stop_section=run_stop,
        print_to_terminal=terminal if terminal is not None else (lambda _msg: None),
        database_handler=database_handler,
    )


def _stored(database_handler):
    from utils.topology import topology_from  # noqa: PLC0415

    return topology_from(database_handler.get_system_settings())


def _assert_unchanged(tab, system_controller, database_handler):
    assert system_controller.settings["valve_topology"] == SHARED
    assert _stored(database_handler) == SHARED
    assert tab.valve_topology_radios[SHARED].isChecked(), "the radios show the old topology"
    assert tab.priming_widget.master_open_btn.toolTip() != RESTART_TIP


# --- showing and changing the topology -------------------------------------------


def test_the_radios_show_the_stored_topology(qapp, database_handler, system_controller):
    tab = _settings_tab(system_controller, database_handler)
    assert tab.valve_topology_radios[SHARED].isChecked()
    assert not tab.valve_topology_radios[INDEPENDENT].isChecked()
    assert tab.valve_topology_radios[INDEPENDENT].isEnabled()

    system_controller.save_settings({"valve_topology": INDEPENDENT})
    tab = _settings_tab(system_controller, database_handler)
    assert tab.valve_topology_radios[INDEPENDENT].isChecked()


def test_a_confirmed_click_is_saved_read_back_and_announced(
    qapp, database_handler, system_controller, dialogs, journal
):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    terminal = []
    tab = _settings_tab(system_controller, database_handler, terminal=terminal.append)
    dialogs.answer = QMessageBox.Yes

    tab.valve_topology_radios[INDEPENDENT].click()  # the operator's click

    assert system_controller.settings["valve_topology"] == INDEPENDENT
    assert _stored(database_handler) == INDEPENDENT, "the next start loads it"
    assert tab.valve_topology_radios[INDEPENDENT].isChecked()
    assert _titles(dialogs, "question") == ["Change Valve Topology"]
    assert _titles(dialogs, "information") == ["Valve Topology Changed"]

    announced = [line for line in terminal if line.startswith("[TOPOLOGY]")]
    assert len(announced) == 1
    assert f"{SHARED} -> {INDEPENDENT} (by alice)" in announced[0]
    assert journal.getvalue() == announced[0] + "\n", "the journal gets the same line"


def test_a_declined_change_keeps_the_old_topology(
    qapp, database_handler, system_controller, dialogs
):
    tab = _settings_tab(system_controller, database_handler)

    tab.valve_topology_radios[INDEPENDENT].click()  # dialogs.answer is No

    _assert_unchanged(tab, system_controller, database_handler)
    assert _titles(dialogs, "question") == ["Change Valve Topology"]


def test_clicking_the_current_topology_does_nothing(
    qapp, database_handler, system_controller, dialogs
):
    tab = _settings_tab(system_controller, database_handler)
    tab.valve_topology_radios[SHARED].click()
    assert dialogs.shown == []
    _assert_unchanged(tab, system_controller, database_handler)


def test_the_confirmation_names_the_risk_of_each_direction(
    qapp, database_handler, system_controller, dialogs
):
    tab = _settings_tab(system_controller, database_handler)
    tab._on_valve_topology_chosen(INDEPENDENT)
    _kind, _title, text = dialogs.shown[-1]
    assert "NO WATER" in text and "relay 16" in text
    assert "Stale" in text and "reopened" in text
    assert "Run refuses a schedule that waters a Stale cage" in text, "since #170"

    system_controller.save_settings({"valve_topology": INDEPENDENT})
    tab = _settings_tab(system_controller, database_handler)
    tab._on_valve_topology_chosen(SHARED)
    _kind, _title, text = dialogs.shown[-1]
    assert "NO WATER" not in text
    assert "master valve feeds a shared manifold" in text and "relay 16" in text
    assert "Run refuses a schedule that waters a Stale cage" in text


def test_the_topology_note_says_run_refuses_a_stale_cage(qapp, database_handler, system_controller):
    from PyQt5.QtWidgets import QLabel  # noqa: PLC0415

    tab = _settings_tab(system_controller, database_handler)
    notes = [
        label.text()
        for label in tab.findChildren(QLabel)
        if label.text().startswith("Must match how this rig is plumbed")
    ]
    assert len(notes) == 1
    assert "a schedule watering a Stale cage will not start" in notes[0]
    assert "reopened" in notes[0]


def test_nobody_logged_in_cannot_change_it(qapp, database_handler, system_controller, dialogs):
    tab = _settings_tab(system_controller, database_handler, logged_in=False)
    tab.valve_topology_radios[INDEPENDENT].click()
    _assert_unchanged(tab, system_controller, database_handler)
    assert _titles(dialogs, "warning") == ["Access Denied"]
    assert _titles(dialogs, "question") == [], "refused before asking"


# --- refused while anything runs ----------------------------------------------------


@pytest.mark.parametrize("operation", ["schedule", "priming", "calibration"])
def test_refused_while_a_hardware_operation_holds_the_lock(
    qapp, database_handler, system_controller, dialogs, operation
):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    tab = _settings_tab(system_controller, database_handler)
    lock = get_operation_lock()
    assert lock.try_acquire(operation)

    radio = tab.valve_topology_radios[INDEPENDENT]
    assert not radio.isEnabled(), "greyed out while the lock is held"
    assert radio.toolTip() == f"Unavailable while {lock.active_label()} is in progress"

    dialogs.answer = QMessageBox.Yes
    assert tab._on_valve_topology_chosen(INDEPENDENT) is False
    _assert_unchanged(tab, system_controller, database_handler)
    assert _titles(dialogs, "warning") == ["Cannot Change Topology"]
    assert _titles(dialogs, "question") == [], "refused before asking"

    lock.release(operation)
    assert radio.isEnabled(), "live again once the operation lets go"


def test_refused_while_a_delivery_worker_runs(
    qapp, database_handler, system_controller, dialogs, monkeypatch
):
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)
    tab = _settings_tab(system_controller, database_handler)
    radio = tab.valve_topology_radios[INDEPENDENT]
    assert not radio.isEnabled()
    assert radio.toolTip() == "Unavailable while a schedule is running"

    assert tab._on_valve_topology_chosen(INDEPENDENT) is False
    _assert_unchanged(tab, system_controller, database_handler)
    assert _titles(dialogs, "question") == []


def test_refused_while_the_run_stop_section_has_a_job(
    qapp, database_handler, system_controller, dialogs
):
    run_stop = SimpleNamespace(job_in_progress=True)
    tab = _settings_tab(system_controller, database_handler, run_stop=run_stop)
    assert tab._on_valve_topology_chosen(INDEPENDENT) is False
    _assert_unchanged(tab, system_controller, database_handler)

    # No lock signal when the job ends: showing the Delivery sub-tab re-checks.
    run_stop.job_in_progress = False
    assert not tab.valve_topology_radios[INDEPENDENT].isEnabled()
    tab.tab_widget.setCurrentIndex(1)
    tab.tab_widget.setCurrentIndex(0)
    assert tab.valve_topology_radios[INDEPENDENT].isEnabled()


def test_a_schedule_started_during_the_confirmation_wins(
    qapp, database_handler, system_controller, dialogs, monkeypatch
):
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    tab = _settings_tab(system_controller, database_handler)

    def confirm_while_a_schedule_starts(_old, _new):
        # The confirmation is modal but the event loop runs under it.
        assert get_operation_lock().try_acquire("schedule")
        return True

    monkeypatch.setattr(tab, "_confirm_valve_topology", confirm_while_a_schedule_starts)
    assert tab._on_valve_topology_chosen(INDEPENDENT) is False
    _assert_unchanged(tab, system_controller, database_handler)
    assert _titles(dialogs, "warning") == ["Cannot Change Topology"]


# --- a database that does not keep the value ------------------------------------------


def test_a_value_the_database_does_not_keep_is_rolled_back(
    qapp, database_handler, system_controller, dialogs, monkeypatch
):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    system_controller.save_settings({"valve_topology": SHARED})  # the device's stored row
    terminal = []
    tab = _settings_tab(system_controller, database_handler, terminal=terminal.append)
    dialogs.answer = QMessageBox.Yes
    # A database that reads but does not write: update_system_setting swallows
    # the sqlite error and returns False, while save_settings still changes
    # the in-memory value.
    monkeypatch.setattr(database_handler, "update_system_setting", lambda *a, **k: False)

    assert tab._on_valve_topology_chosen(INDEPENDENT) is False

    _assert_unchanged(tab, system_controller, database_handler)
    assert tab.priming_widget.master_open_btn.isEnabled(), "priming is not locked"
    assert _titles(dialogs, "critical") == ["Topology Not Saved"]
    assert any(line.startswith("[TOPOLOGY] Valve topology NOT changed") for line in terminal)


def test_a_read_back_that_fails_undoes_the_write(
    qapp, database_handler, system_controller, dialogs, monkeypatch
):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    tab = _settings_tab(system_controller, database_handler)
    dialogs.answer = QMessageBox.Yes
    read = database_handler.get_system_settings
    # get_system_settings returns {} on a sqlite error: the write landed, the
    # read did not, so the app cannot know what the next start will load.
    monkeypatch.setattr(database_handler, "get_system_settings", lambda: {})

    assert tab._on_valve_topology_chosen(INDEPENDENT) is False

    assert read()["valve_topology"] == SHARED, "the next start agrees with the running app"
    assert system_controller.settings["valve_topology"] == SHARED
    assert tab.valve_topology_radios[SHARED].isChecked()
    assert _titles(dialogs, "critical") == ["Topology Not Confirmed"]


def test_an_unreadable_database_is_not_taken_for_the_default(
    qapp, database_handler, system_controller, dialogs, monkeypatch
):
    """The review's case: {} from an unreadable database normalised to
    shared_manifold, so a failed save to shared read back as done while the
    next start would load independent."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    system_controller.save_settings({"valve_topology": INDEPENDENT})
    terminal = []
    tab = _settings_tab(system_controller, database_handler, terminal=terminal.append)
    dialogs.answer = QMessageBox.Yes
    read = database_handler.get_system_settings
    monkeypatch.setattr(database_handler, "update_system_setting", lambda *a, **k: False)
    monkeypatch.setattr(database_handler, "get_system_settings", lambda: {})

    assert tab._on_valve_topology_chosen(SHARED) is False

    assert system_controller.settings["valve_topology"] == INDEPENDENT
    assert read()["valve_topology"] == INDEPENDENT
    assert tab.valve_topology_radios[INDEPENDENT].isChecked()
    assert _titles(dialogs, "critical") == ["Topology Not Confirmed"]
    assert _titles(dialogs, "information") == [], "never reported as changed"
    assert any(line.startswith("[TOPOLOGY] Valve topology NOT confirmed") for line in terminal)


# --- what a change does to calibrations and priming ------------------------------------


def test_a_change_marks_calibrations_stale_and_locks_priming_until_restart(
    qapp, database_handler, system_controller, dialogs
):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    database_handler.save_valve_calibration(
        cage_id=1,
        relay_id=1,
        pulse_width_ms=30,
        volume_per_pulse_ml=0.034,
        stddev_ml=0.001,
        cv_pct=1.0,
        num_samples=250,
        inter_pulse_interval_ms=1000,
        topology=SHARED,
    )
    tab = _settings_tab(system_controller, database_handler)
    priming = tab.priming_widget
    assert tab.calibration_table.item(0, 1).text() == "[OK]"
    assert priming.master_open_btn.isEnabled()

    dialogs.answer = QMessageBox.Yes
    assert tab._on_valve_topology_chosen(INDEPENDENT) is True

    assert tab.calibration_table.item(0, 1).text() == "Stale"
    for button in (priming.master_open_btn, priming.cage_open_btn):
        assert not button.isEnabled()
        assert button.toolTip() == RESTART_TIP
    assert priming.emergency_btn.isEnabled(), "closing everything still works"
    priming._on_open_master_clicked()
    assert priming._solenoid_controller is None, "refused before any hardware is set up"
    assert get_operation_lock().is_busy() is False

    # Switched back before any restart: the panel matches the device again.
    assert tab._on_valve_topology_chosen(SHARED) is True
    assert tab.calibration_table.item(0, 1).text() == "[OK]"
    assert priming.master_open_btn.isEnabled()
    assert priming.master_open_btn.toolTip() == ""


def test_a_backup_file_cannot_change_the_topology(
    qapp, database_handler, system_controller, dialogs, monkeypatch, tmp_path
):
    from PyQt5.QtWidgets import QFileDialog  # noqa: PLC0415

    backup = tmp_path / "backup.json"
    backup.write_text(
        json.dumps({"pump_volume_ul": 60, "calibration_factor": 1.0, "valve_topology": INDEPENDENT})
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(backup), ""))
    )
    tab = _settings_tab(system_controller, database_handler)

    tab.restore_from_backup()

    assert system_controller.settings["pump_volume_ul"] == 60, "the rest of the backup applies"
    _assert_unchanged(tab, system_controller, database_handler)
    assert _titles(dialogs, "information") == ["Success"]
    _kind, _title, text = dialogs.shown[-1]
    assert f"valve topology ({INDEPENDENT}) was not applied" in text


# --- the priming panel on its own ---------------------------------------------------------

_SETTINGS = {"num_hats": 1, "global_master_relay_id": 16}


@pytest.fixture
def fake_relays(monkeypatch, fake_relay_handler):
    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    return fake_relay_handler


def _select(panel, cage_id):
    index = panel.cage_selector.findData(cage_id)
    assert index >= 0
    panel.cage_selector.setCurrentIndex(index)


def test_a_shared_priming_panel_will_not_open_after_a_switch(qapp, fake_relays, dialogs):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    settings = dict(_SETTINGS)
    panel = PrimingControlWidget(settings, lambda *_: None)
    assert panel.master_open_btn.isEnabled()

    settings["valve_topology"] = INDEPENDENT  # Settings changes the shared dict
    panel.refresh_topology_state()
    assert not panel.master_open_btn.isEnabled()
    assert panel.master_open_btn.toolTip() == RESTART_TIP

    panel._on_open_master_clicked()
    assert fake_relays.trace == [], "refused before touching hardware"
    assert get_operation_lock().is_busy() is False
    assert _titles(dialogs, "information") == ["Restart required"]

    # A lock cycle elsewhere, or an emergency stop, must not bring Open back.
    lock = get_operation_lock()
    lock.try_acquire("schedule")
    lock.release("schedule")
    assert not panel.master_open_btn.isEnabled()
    assert panel.master_open_btn.toolTip() == RESTART_TIP
    panel._on_emergency_stop_clicked()
    assert fake_relays.trace == [(("all",), 0)]
    assert not panel.master_open_btn.isEnabled()
    assert panel.cage_close_btn.isEnabled(), "closing a valve still works"
    # Nor may the valve state: a master reported closed keeps Open shut, in
    # whichever order a caller updates the model and the lock.
    panel._on_master_state_changed(False)
    assert not panel.master_open_btn.isEnabled()


def test_a_close_after_a_switch_keeps_the_panel_on_its_own_topology(qapp, fake_relays):
    """The review's case: a Close after a switch built (and kept) a controller
    for the new topology; switching back then re-enabled Open Master on a
    controller that never drives the master valve."""
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    settings = dict(_SETTINGS)
    panel = PrimingControlWidget(settings, lambda *_: None)
    settings["valve_topology"] = INDEPENDENT
    panel.refresh_topology_state()
    _select(panel, 1)
    panel._on_close_cage_clicked()
    assert panel._solenoid_controller.has_master is True, "built for the panel's topology"

    settings["valve_topology"] = SHARED  # switched back before any restart
    panel.refresh_topology_state()
    panel._on_open_master_clicked()
    assert fake_relays.trace[-1] == ((16,), 1), "Open Master drives the master relay"
    panel._on_close_master_clicked()
    assert fake_relays.energized() == set()

    reverse = dict(_SETTINGS, valve_topology=INDEPENDENT)
    panel = PrimingControlWidget(reverse, lambda *_: None)
    reverse["valve_topology"] = SHARED
    _select(panel, 1)
    panel._on_close_cage_clicked()
    assert panel._solenoid_controller.has_master is False


def test_an_independent_priming_panel_will_not_open_after_a_switch(qapp, fake_relays):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415
    from utils.operation_lock import get_operation_lock  # noqa: PLC0415

    settings = dict(_SETTINGS, valve_topology=INDEPENDENT)
    panel = PrimingControlWidget(settings, lambda *_: None)
    _select(panel, 3)
    assert panel.cage_open_btn.isEnabled()

    settings["valve_topology"] = SHARED
    panel.refresh_topology_state()
    assert not panel.cage_open_btn.isEnabled()
    assert panel.cage_open_btn.toolTip() == RESTART_TIP

    _select(panel, 5)
    assert not panel.cage_open_btn.isEnabled(), "a selector change must not re-enable Open"
    panel._on_open_cage_clicked()
    assert fake_relays.trace == [], "refused before touching hardware"
    assert get_operation_lock().is_busy() is False

    settings["valve_topology"] = INDEPENDENT  # switched back before any restart
    panel.refresh_topology_state()
    assert panel.cage_open_btn.isEnabled()
