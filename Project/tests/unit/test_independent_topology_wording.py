"""What the operator reads about relay 16 matches the device's valve topology.

On the independent topology (one syringe and one valve per animal) relay 16
stays reserved but has no master valve on it. The Cages tab, the schedule
wizard, the relay log line and the help still called it the master solenoid,
and the Cages tab drew it as the amber master terminal. The shared-manifold
wording stays as it was: the only change there is a missing "the" in two
wizard messages.
"""

from __future__ import annotations

import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from utils.topology import reserved_relay_reason

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SHARED = {"num_hats": 1, "global_master_relay_id": 16}
INDEPENDENT = dict(SHARED, valve_topology="independent")


def test_the_reserved_relay_reason_follows_the_topology():
    assert reserved_relay_reason(SHARED) == "reserved for the master solenoid"
    assert reserved_relay_reason(None) == "reserved for the master solenoid"
    assert reserved_relay_reason({"valve_topology": "bogus"}) == "reserved for the master solenoid"
    independent = reserved_relay_reason(INDEPENDENT)
    assert "reserved" in independent and "master solenoid" not in independent


# --- schedule wizard ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PyQt5")
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


def _config(animals, cage_ids):
    return {
        "schedule_type": "instant",
        "animals": animals,
        "parameters": {
            "name": "x",
            "animal_configs": {
                animal: {
                    "delivery_time": datetime(2026, 10, 1, 9, 0, 0),
                    "volume": 0.6,
                    "cage_id": cage,
                }
                for animal, cage in zip(animals, cage_ids)
            },
        },
    }


def _build(settings, animals, cage_ids):
    from ui.schedule_wizard import build_schedule_from_config  # noqa: PLC0415

    controller = SimpleNamespace(settings=settings)
    return build_schedule_from_config(
        _config(animals, cage_ids), trainer=None, system_controller=controller
    )


@pytest.mark.parametrize(
    ("settings", "expected", "absent"),
    [
        (INDEPENDENT, "reserved and unused on this device", "master solenoid"),
        (SHARED, "reserved for the master solenoid", None),
    ],
)
def test_too_many_animals_names_the_relay_for_the_device(qapp, settings, expected, absent):
    animals = list(range(1, 17))  # 16 animals, 15 cages on one HAT
    with pytest.raises(ValueError) as failure:
        _build(settings, animals, [None] * 16)
    assert expected in str(failure.value)
    if absent:
        assert absent not in str(failure.value)


def test_a_cage_on_the_reserved_relay_is_refused_in_the_device_s_words(qapp):
    settings = dict(INDEPENDENT, num_hats=2, cage_relays={"1": 1, "5": 16})
    with pytest.raises(ValueError, match="reserved and unused on this device") as failure:
        _build(settings, [1], [5])
    assert "master solenoid" not in str(failure.value)


def _step2(settings):
    from ui.schedule_wizard import Step2SelectAnimals  # noqa: PLC0415

    return Step2SelectAnimals(MagicMock(), system_controller=SimpleNamespace(settings=settings))


def test_the_selection_limit_banner_and_dialog_follow_the_topology(qapp, monkeypatch):
    from PyQt5.QtCore import Qt  # noqa: PLC0415
    from PyQt5.QtWidgets import QListWidgetItem, QMessageBox  # noqa: PLC0415

    shared = _step2(SHARED)
    assert "reserved for the master solenoid" in shared._limit_label.text()

    step = _step2(INDEPENDENT)
    assert "reserved and unused on this device" in step._limit_label.text()
    assert "master solenoid" not in step._limit_label.text()

    shown = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: shown.append(a[2]) or QMessageBox.Ok)
    )
    for animal in range(1, 17):
        item = QListWidgetItem(f"Animal {animal}")
        item.setData(Qt.UserRole, animal)
        step._animals_list.addItem(item)
    step._animals_list.selectAll()  # 16 > 15 cages
    assert shown, "the limit dialog was shown"
    assert "reserved and unused on this device" in shown[0]
    assert "master solenoid" not in shown[0]


# --- relay log line ------------------------------------------------------------------------


def test_the_relay_log_line_names_the_relay_for_the_device(capsys):
    from models.relay_unit_manager import RelayUnitManager  # noqa: PLC0415

    RelayUnitManager(dict(SHARED, hardware_mode="solenoid"))
    assert "(master on relay 16)" in capsys.readouterr().out
    RelayUnitManager(dict(INDEPENDENT, hardware_mode="solenoid"))
    out = capsys.readouterr().out
    assert "(relay 16 reserved; no master valve)" in out
    assert "master on relay" not in out


# --- Cages tab -----------------------------------------------------------------------------


def _cages_tab(settings, database_handler):
    from ui.cages_visualization_tab import CagesVisualizationTab  # noqa: PLC0415

    controller = SimpleNamespace(settings=settings)
    return CagesVisualizationTab(database_handler, system_controller=controller)


def _texts(widget):
    from PyQt5.QtWidgets import QLabel  # noqa: PLC0415

    return [label.text() for label in widget.findChildren(QLabel)]


def test_the_cages_tab_shows_relay_16_as_reserved_on_an_independent_rig(qapp, database_handler):
    tab = _cages_tab(dict(INDEPENDENT), database_handler)
    terminal = tab._relay_widgets[16]
    assert "RESERVED (unused)" in _texts(terminal)
    assert "MASTER SOLENOID" not in _texts(terminal)
    assert terminal.objectName() == "RelayTerminal", "not the amber master terminal"
    assert "leave it unwired" in terminal.toolTip()
    terminal._start_editing()
    assert terminal._editing is False, "the reserved terminal is not renameable"
    assert tab._master_legend_label.text() == "Reserved relay (unused)"
    assert "independent (no master valve)" in tab._status_label.text()


def test_the_cages_tab_is_unchanged_on_a_shared_rig(qapp, database_handler):
    tab = _cages_tab(dict(SHARED), database_handler)
    terminal = tab._relay_widgets[16]
    assert "MASTER SOLENOID" in _texts(terminal)
    assert terminal.objectName() == "MasterTerminal"
    assert tab._master_legend_label.text() == "Master solenoid"
    assert "independent" not in tab._status_label.text()


def test_the_cages_tab_follows_a_topology_change_when_shown(qapp, database_handler):
    from PyQt5.QtGui import QShowEvent  # noqa: PLC0415

    settings = dict(SHARED)
    tab = _cages_tab(settings, database_handler)
    settings["valve_topology"] = "independent"  # changed in Settings while RRR runs
    tab.showEvent(QShowEvent())
    assert "RESERVED (unused)" in _texts(tab._relay_widgets[16])
    assert tab._master_legend_label.text() == "Reserved relay (unused)"


def test_the_cages_info_dialog_follows_the_topology(qapp, database_handler, monkeypatch):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    shown = []
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[2]))
    )
    _cages_tab(dict(INDEPENDENT), database_handler)._show_relay_info()
    _cages_tab(dict(SHARED), database_handler)._show_relay_info()
    independent, shared = shown
    assert "never driven" in independent and "master solenoid is global" not in independent
    assert "The master solenoid is global (default: relay 16 on HAT 0)." in shared


# --- help ----------------------------------------------------------------------------------


def test_the_help_describes_relay_16_and_priming_for_both_rigs():
    from utils.help_content_manager import HelpContentManager  # noqa: PLC0415

    help_ = HelpContentManager()
    cages = help_.get_content("Cages")
    assert "Relay 16 (Reserved)" in cages and "RESERVED (unused)" in cages
    priming = help_.get_content("Priming")
    assert "Shared-manifold rig:" in priming and "Independent rig" in priming
    assert "about three days" in priming
