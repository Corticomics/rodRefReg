"""The calibration table, Calibrate All and the CSV export follow the cage map.

They used to iterate a literal 1..15, so on a two-HAT device cages 16-31
were invisible and uncalibratable from the UI. Now they follow
utils.topology.cage_map_from(settings): 15 rows on one HAT (unchanged for
the production configuration), 31 on two, with relay numbers that skip the
master.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def dialogs(qapp, monkeypatch):
    """Every message box, recorded as (kind, title) instead of shown: offscreen,
    a modal box nobody closes would hang the run. Tests stub their own on top."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    shown = []

    def _box(kind, answer):
        return staticmethod(
            lambda *a, **k: shown.append((kind, a[1] if len(a) > 1 else None)) or answer
        )

    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, kind, _box(kind, QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "question", _box("question", QMessageBox.No))
    return shown


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


def _settings_tab(system_controller, database_handler, terminal=None):
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    return SettingsTab(
        system_controller,
        login_system=login,
        print_to_terminal=terminal or (lambda _msg: None),
        database_handler=database_handler,
    )


def test_one_hat_keeps_fifteen_rows(qapp, database_handler, system_controller):
    system_controller.settings['num_hats'] = 1
    tab = _settings_tab(system_controller, database_handler)
    assert tab.calibration_table.rowCount() == 15
    assert tab.calibration_table.item(14, 0).toolTip() == "Cage 15 - Relay 15"


def test_two_hats_show_every_cage_with_its_relay(qapp, database_handler, system_controller):
    system_controller.settings['num_hats'] = 2
    database_handler.save_valve_calibration(
        cage_id=16,
        relay_id=17,
        pulse_width_ms=30,
        volume_per_pulse_ml=0.033,
        stddev_ml=0.001,
        cv_pct=1.0,
        num_samples=250,
        inter_pulse_interval_ms=1000,
    )
    tab = _settings_tab(system_controller, database_handler)

    assert tab.calibration_table.rowCount() == 31
    assert tab.calibration_table.item(15, 0).toolTip() == "Cage 16 - Relay 17"
    assert tab.calibration_table.item(30, 0).toolTip() == "Cage 31 - Relay 32"
    assert tab.calibration_table.item(15, 1).text() == "[OK]", "cage 16's calibration is shown"
    assert tab.calibration_table.item(16, 1).text() == "Not Calibrated"


def test_export_lists_every_cage_in_the_map(
    qapp, database_handler, system_controller, tmp_path, monkeypatch
):
    from PyQt5.QtWidgets import QFileDialog, QMessageBox  # noqa: PLC0415

    system_controller.settings['num_hats'] = 2
    tab = _settings_tab(system_controller, database_handler)
    out = tmp_path / "report.csv"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), ""))
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    tab._export_calibration_report()

    lines = out.read_text().splitlines()
    assert lines[0].startswith("Cage,Status")
    assert len(lines) == 1 + 31
    assert lines[16].startswith("16,Not Calibrated")


def test_an_unreadable_stored_cage_map_does_not_take_the_tab_down(
    qapp, database_handler, system_controller, tmp_path, monkeypatch
):
    """
    SettingsTab is built unguarded inside the main window, so an exception
    here at boot means no window at all. A map that cannot be read (only
    reachable by hand-editing the database) falls back to the sequential
    layout for the hat count, in every view that reads the map.
    """
    from PyQt5.QtWidgets import QFileDialog, QMessageBox  # noqa: PLC0415

    system_controller.settings['num_hats'] = 1
    system_controller.settings['cage_relays'] = {"1": None, "2": 2}
    terminal = []
    tab = _settings_tab(system_controller, database_handler, terminal.append)

    assert tab.calibration_table.rowCount() == 15
    assert any("cage map is unreadable" in line for line in terminal)

    questions = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: questions.append(a) or QMessageBox.No),
    )
    tab._calibrate_all_uncalibrated()
    assert len(questions) == 1 and "Found 15 uncalibrated" in questions[0][2]

    out = tmp_path / "report.csv"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), ""))
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    tab._export_calibration_report()
    assert len(out.read_text().splitlines()) == 1 + 15


def test_changing_the_hat_count_refreshes_the_calibration_table(monkeypatch):
    """main.change_relay_hats used to refresh only the Cages tab, leaving a
    calibration table sized for the old hat count until a manual Refresh."""
    import sys  # noqa: PLC0415

    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # main installs its own on import
    import main  # noqa: PLC0415

    settings = {'num_hats': 1, 'cage_relays': {"1": 1}}
    gui = SimpleNamespace(
        projects_section=SimpleNamespace(cages_tab=SimpleNamespace(refresh=MagicMock())),
        settings_tab=SimpleNamespace(
            refresh_calibration_table=MagicMock(),
            priming_widget=SimpleNamespace(refresh_hardware=MagicMock()),
        ),
        print_to_terminal=MagicMock(),
    )
    monkeypatch.setattr(main.QInputDialog, "getInt", staticmethod(lambda *a, **k: (2, True)))
    monkeypatch.setattr(main, "RelayUnitManager", MagicMock())
    monkeypatch.setattr(main, "cleanup", lambda: None)
    # Run-time globals that setup() normally binds.
    monkeypatch.setattr(main, "app_settings", settings, raising=False)
    monkeypatch.setattr(main, "relay_handler", MagicMock(), raising=False)
    monkeypatch.setattr(main, "system_controller", MagicMock(), raising=False)
    monkeypatch.setattr(main, "gui", gui, raising=False)

    main.change_relay_hats()

    assert settings['num_hats'] == 2 and settings['cage_relays'] == {}
    gui.projects_section.cages_tab.refresh.assert_called_once()
    gui.settings_tab.refresh_calibration_table.assert_called_once()
    # Priming keeps its own relay handler; it must follow the new count.
    gui.settings_tab.priming_widget.refresh_hardware.assert_called_once()


# --- rows the Run gate would refuse (#170) ------------------------------------------------


def _save(database_handler, cage, volume=0.034164, cv=1.0, topology="shared_manifold"):
    assert database_handler.save_valve_calibration(
        cage_id=cage,
        relay_id=cage,
        pulse_width_ms=30,
        volume_per_pulse_ml=volume,
        stddev_ml=0.001,
        cv_pct=1.0 if cv is None else cv,
        num_samples=250,
        inter_pulse_interval_ms=1000,
        topology=topology,
    )
    if cv is None:
        # The app's own save always writes a CV; older rows or a hand edit
        # may not have one.
        with database_handler.connect() as conn:
            conn.execute(
                "UPDATE valve_calibration SET coefficient_of_variation_pct = NULL "
                "WHERE cage_id = ?",
                (cage,),
            )
            conn.commit()


def _statuses(tab):
    """{cage: status text} for every row of the calibration table."""
    return {
        int(tab.calibration_table.item(row, 0).toolTip().split()[1]): tab.calibration_table.item(
            row, 1
        ).text()
        for row in range(tab.calibration_table.rowCount())
    }


def test_a_calibration_run_would_refuse_is_shown_as_invalid(
    qapp, database_handler, system_controller
):
    """A zero or negative volume per pulse used to show as [OK] while Run
    refused the cage as unusable."""
    system_controller.settings['num_hats'] = 1
    _save(database_handler, 3, volume=0.0)
    tab = _settings_tab(system_controller, database_handler)

    status = tab.calibration_table.item(2, 1)
    assert status.text() == "Invalid"
    assert "will not start until it is recalibrated" in status.toolTip()
    assert tab.calibration_table.cellWidget(2, tab.CAL_COL_ACTION).property("variant") == "primary"


def test_a_missing_cv_does_not_take_the_table_down(qapp, database_handler, system_controller):
    """The CV column may be NULL; formatting it used to raise, which left the
    calibration table half built."""
    system_controller.settings['num_hats'] = 1
    _save(database_handler, 4, cv=None)
    tab = _settings_tab(system_controller, database_handler)

    assert tab.calibration_table.rowCount() == 15
    assert tab.calibration_table.item(3, 1).text() == "[OK]"
    assert tab.calibration_table.item(3, tab.CAL_COL_CV).text() == "—"
    assert tab.calibration_table.item(14, 1).text() == "Not Calibrated", "the rows after it too"


def test_settings_and_run_agree_on_which_cages_need_calibrating(
    qapp, database_handler, system_controller
):
    """Every row that is not [OK] is a cage Run refuses, and the other way round."""
    from utils.calibration_gate import calibration_problems  # noqa: PLC0415

    settings = system_controller.settings
    settings.update(
        num_hats=1,
        hardware_mode="solenoid",
        use_pulse_delivery=True,
        valve_topology="shared_manifold",
    )
    _save(database_handler, 1)
    _save(database_handler, 2, volume=0.0)
    _save(database_handler, 3, volume=-0.01)
    _save(database_handler, 4, topology="independent")
    tab = _settings_tab(system_controller, database_handler)

    shown = _statuses(tab)
    refused = {
        p.cage_id
        for p in calibration_problems(
            range(1, 16), database_handler.get_all_valve_calibrations(), settings
        )
    }
    assert {cage for cage, status in shown.items() if status != "[OK]"} == refused
    assert (shown[1], shown[2], shown[3], shown[4], shown[5]) == (
        "[OK]",
        "Invalid",
        "Invalid",
        "Stale",
        "Not Calibrated",
    )


def test_calibrate_all_includes_an_invalid_calibration(
    qapp, database_handler, system_controller, monkeypatch, dialogs
):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    system_controller.settings['num_hats'] = 1
    for cage in range(1, 16):
        _save(database_handler, cage, volume=0.0 if cage == 7 else 0.034164)
    tab = _settings_tab(system_controller, database_handler)
    questions = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: questions.append(a) or QMessageBox.No),
    )

    tab._calibrate_all_uncalibrated()

    assert ("information", "All Calibrated") not in dialogs
    assert len(questions) == 1
    assert "1 with an unusable calibration (Invalid):\n[7]" in questions[0][2]


def test_the_report_marks_an_invalid_calibration_and_a_missing_cv(
    qapp, database_handler, system_controller, tmp_path, monkeypatch, dialogs
):
    from PyQt5.QtWidgets import QFileDialog, QMessageBox  # noqa: PLC0415

    system_controller.settings['num_hats'] = 1
    _save(database_handler, 2, volume=0.0)
    _save(database_handler, 4, cv=None)
    tab = _settings_tab(system_controller, database_handler)
    out = tmp_path / "report.csv"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), ""))
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    tab._export_calibration_report()

    assert [kind for kind, _title in dialogs if kind == "critical"] == [], "the export failed"
    lines = out.read_text().splitlines()
    assert lines[2].startswith("2,Invalid,0.000000,")
    assert lines[4].startswith("4,Calibrated,0.034164,—,")


@pytest.mark.parametrize(
    ("mode", "says"),
    [
        ({"hardware_mode": "solenoid", "use_pulse_delivery": True}, "will not start"),
        ({"hardware_mode": "pump"}, "The current delivery mode does not use it"),
        ({"hardware_mode": "solenoid", "use_pulse_delivery": False}, "does not use it"),
    ],
)
def test_the_invalid_and_stale_tooltips_say_what_run_will_do(
    qapp, database_handler, system_controller, mode, says
):
    """Run refuses such a cage only in solenoid pulse delivery; in pump or
    continuous mode the calibration is not used, and the tooltip said a
    schedule would not start when it would."""
    system_controller.settings.update(num_hats=1, valve_topology="shared_manifold", **mode)
    _save(database_handler, 2, volume=0.0)
    _save(database_handler, 4, topology="independent")
    tab = _settings_tab(system_controller, database_handler)

    for row in (1, 3):  # cage 2 Invalid, cage 4 Stale
        assert says in tab.calibration_table.item(row, 1).toolTip()


def test_the_report_quotes_notes_and_leaves_missing_ones_empty(
    qapp, database_handler, system_controller, tmp_path, monkeypatch
):
    """Notes were written between bare quotes: a quote or comma in them
    shifted the columns, and a missing note was written as "None"."""
    import csv  # noqa: PLC0415

    from PyQt5.QtWidgets import QFileDialog  # noqa: PLC0415

    system_controller.settings['num_hats'] = 1
    _save(database_handler, 3)
    _save(database_handler, 5)
    with database_handler.connect() as conn:
        conn.execute(
            "UPDATE valve_calibration SET notes = ? WHERE cage_id = 3", ('a "quoted", note',)
        )
        conn.execute("UPDATE valve_calibration SET notes = NULL WHERE cage_id = 5")
        conn.commit()
    tab = _settings_tab(system_controller, database_handler)
    out = tmp_path / "report.csv"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), ""))
    )

    tab._export_calibration_report()

    rows = list(csv.reader(out.read_text(encoding="utf-8").splitlines()))
    assert {len(row) for row in rows} == {10}, "every row has the header's ten columns"
    assert rows[3][8] == 'a "quoted", note' and rows[3][9] == "shared_manifold"
    assert rows[5][8] == "", "a missing note is empty, not 'None'"


# --- each cage's profile (v2.1.0) ------------------------------------------------------


def _calibrate_profile(database_handler, cage, width, interval, **extra):
    row = {"volume": 0.034164, "topology": "shared_manifold", **extra}
    assert database_handler.save_valve_calibration(
        cage_id=cage,
        relay_id=cage,
        pulse_width_ms=width,
        volume_per_pulse_ml=row["volume"],
        stddev_ml=0.001,
        cv_pct=1.0,
        num_samples=250,
        inter_pulse_interval_ms=interval,
        topology=row["topology"],
    )


def test_each_calibrated_row_shows_the_profile_its_deliveries_use(
    qapp, database_handler, system_controller
):
    """No global pulse width any more: the table shows the width and interval
    each cage was calibrated at, which its deliveries replay. The tooltip says
    what the calibration was, then what applies to the row: deliveries use it
    (and wait the settling time after each pulse, which the calibration run
    does not), or, on a Stale row, what Run does about it."""
    system_controller.settings.update(num_hats=1, valve_topology="shared_manifold")
    _calibrate_profile(database_handler, 1, 30, 1000)
    _calibrate_profile(database_handler, 2, 20, None)  # saved before v1.16.0 stored one
    _calibrate_profile(database_handler, 3, 25, 800, topology="independent")  # Stale
    _calibrate_profile(database_handler, 4, 30, 1000, volume=0.0)  # Invalid
    tab = _settings_tab(system_controller, database_handler)
    table = tab.calibration_table

    assert table.horizontalHeaderItem(tab.CAL_COL_PROFILE).text() == "Profile"
    assert table.horizontalHeaderItem(tab.CAL_COL_PROFILE).toolTip() == (
        "The pulse width / interval each cage was calibrated at: how long the valve opens "
        "for each pulse, and the valve-closed rest between pulses. Deliveries to the cage "
        "use them."
    )
    profile = [table.item(row, tab.CAL_COL_PROFILE) for row in range(5)]
    assert [item.text() for item in profile] == [
        "30 / 1000 ms",
        "20 / 100 ms",
        "25 / 800 ms",
        "—",
        "—",
    ]
    assert profile[0].toolTip() == (
        "Calibrated at 30 ms open, then 1000 ms closed before the next pulse. Deliveries "
        "to cage 1 use this pulse width and interval; after each pulse they also wait "
        "100 ms for the valve to settle."
    )
    assert profile[1].toolTip() == (
        "Calibrated at 20 ms open, before RRR recorded the interval (v1.16.0): the 100 ms "
        "shown is the interval RRR used then. Deliveries to cage 2 use this pulse width "
        "and interval; after each pulse they also wait 100 ms for the valve to settle."
    )
    stale = table.item(2, tab.CAL_COL_STATUS)
    assert stale.text() == "Stale"
    assert profile[2].toolTip() == (
        "Calibrated at 25 ms open, then 800 ms closed before the next pulse. A schedule "
        "watering this cage will not start until it is recalibrated."
    )
    assert stale.toolTip().endswith(
        "A schedule watering this cage will not start until it is recalibrated."
    ), "the same consequence as its Status cell"
    assert profile[3].toolTip() == "No usable calibration: recalibrate this cage."
    assert profile[4].toolTip() == "Not calibrated"
    # An uncalibrated row's dash is the same grey as the row's other dashes.
    volume = table.item(4, tab.CAL_COL_VOLUME)
    assert profile[4].foreground().color() == volume.foreground().color()
    # The other columns kept their content.
    assert table.item(0, tab.CAL_COL_VOLUME).text() == "0.034164"
    assert table.item(0, tab.CAL_COL_CV).text() == "1.00%"
    assert table.item(0, tab.CAL_COL_STATUS).text() == "[OK]"


def test_the_profile_tooltip_follows_the_delivery_mode_and_the_settling_time(
    qapp, database_handler, system_controller
):
    """In pump mode no delivery uses a valve calibration, so the tooltip does
    not say one does; a Stale row says what its Status cell says. The
    settling wait is read from the settings the next run copies. A stored
    interval that cannot be used (only a hand edit stores one) is named as
    such."""
    system_controller.settings.update(
        num_hats=1, valve_topology="shared_manifold", hardware_mode="pump"
    )
    _calibrate_profile(database_handler, 1, 30, 1000)
    _calibrate_profile(database_handler, 3, 25, 800, topology="independent")  # Stale
    _calibrate_profile(database_handler, 5, 30, -5)  # a hand edit
    tab = _settings_tab(system_controller, database_handler)
    table = tab.calibration_table

    assert table.item(0, tab.CAL_COL_PROFILE).toolTip() == (
        "Calibrated at 30 ms open, then 1000 ms closed before the next pulse. The current "
        "delivery mode does not use it."
    )
    assert table.item(2, tab.CAL_COL_PROFILE).toolTip() == (
        "Calibrated at 25 ms open, then 800 ms closed before the next pulse. The current "
        "delivery mode does not use it, but pulse delivery would refuse it until it is "
        "recalibrated."
    )

    system_controller.settings.update(hardware_mode="solenoid", pulse_settling_ms=150)
    tab.refresh_calibration_table()
    assert table.item(0, tab.CAL_COL_PROFILE).toolTip().endswith(
        "after each pulse they also wait 150 ms for the valve to settle."
    )
    assert table.item(4, tab.CAL_COL_PROFILE).text() == "30 / 100 ms"
    assert table.item(4, tab.CAL_COL_PROFILE).toolTip().startswith(
        "Calibrated at 30 ms open. Its stored interval cannot be used, so the 100 ms shown "
        "is the interval RRR used before v1.16.0. Deliveries to cage 5 use"
    )
