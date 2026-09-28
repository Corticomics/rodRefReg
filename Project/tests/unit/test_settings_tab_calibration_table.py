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

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


def _settings_tab(system_controller, database_handler):
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    return SettingsTab(
        system_controller,
        login_system=login,
        print_to_terminal=lambda _msg: None,
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
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), "")))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    tab._export_calibration_report()

    lines = out.read_text().splitlines()
    assert lines[0].startswith("Cage,Status")
    assert len(lines) == 1 + 31
    assert lines[16].startswith("16,Not Calibrated")
