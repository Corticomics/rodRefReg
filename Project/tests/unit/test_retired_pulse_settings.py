"""No global Pulse Width, and pulse delivery always on (v2.1.0).

Settings > Delivery lost its Pulse Width spin box and its Enable Pulse Mode
checkbox. Each cage delivers at the profile it was calibrated at, and pulse
delivery is the only mode. These replace the tests of the old force-merge
(pulse_width_ms reset to 20 at every start). Pinned here, against the real
SystemController and database, and the real SettingsTab offscreen:

- a pulse_width_ms an older release saved (in the database, or in a legacy
  settings.json) is deleted when settings load, and no save writes one back;
  use_pulse_delivery is True after a load, a save and every start, in memory
  and in the database, whatever an older release saved;
- the Delivery tab shows neither control, says where each cage's profile is,
  and its auto-save writes neither key;
- a backup from an older release (pulse delivery off, a pulse width)
  restores the rest but turns neither back on: the next run's strategy is in
  pulse mode and Run's calibration check applies.
"""

from __future__ import annotations

import json
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


@pytest.fixture
def dialogs(monkeypatch):
    """Every message box, recorded as (kind, title, text) instead of shown."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    shown = []
    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(
            QMessageBox,
            kind,
            staticmethod(lambda *a, _kind=kind, **k: shown.append((_kind, a[1], a[2]))),
        )
    return shown


def _stored(database_handler):
    return database_handler.get_system_settings()


def _older_release_left(database_handler, pulse_width=50, pulse_mode=False):
    """The rows 2.0.0 or older wrote: a global pulse width and the mode flag."""
    database_handler.update_system_setting('pulse_width_ms', pulse_width, 'int')
    database_handler.update_system_setting('use_pulse_delivery', pulse_mode, 'bool')


# --- SystemController -----------------------------------------------------------------


def test_a_pulse_width_an_older_release_saved_is_deleted_at_load(database_handler, capsys):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    _older_release_left(database_handler)
    assert _stored(database_handler)['pulse_width_ms'] == 50
    assert _stored(database_handler)['use_pulse_delivery'] is False

    controller = SystemController(database_handler)

    assert 'pulse_width_ms' not in controller.settings
    assert 'pulse_width_ms' not in _stored(database_handler)
    # Before ensure_solenoid_defaults has run: the load alone forces it, in
    # memory and in the database (its force-merge compares with memory, so it
    # would leave a stored False behind; a revert would then load it).
    assert controller.settings['use_pulse_delivery'] is True
    assert _stored(database_handler)['use_pulse_delivery'] is True
    journal = capsys.readouterr().out
    assert "[SETTINGS] Removed the retired setting pulse_width_ms=50" in journal
    assert "[SETTINGS] Stored the fixed setting use_pulse_delivery=True (was False)" in journal

    SystemController(database_handler)  # the next start finds nothing to change
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_the_journal_says_when_the_database_refused_the_change(
    database_handler, monkeypatch, capsys
):
    """DatabaseHandler reports a database error by returning False. The
    journal must not say a change was stored when it was not; RRR still
    uses pulse delivery and no width, and the next start tries again."""
    from controllers.system_controller import SystemController  # noqa: PLC0415

    _older_release_left(database_handler)
    update, delete = database_handler.update_system_setting, database_handler.delete_system_setting
    monkeypatch.setattr(
        database_handler,
        "update_system_setting",
        lambda key, *a: False if key == 'use_pulse_delivery' else update(key, *a),
    )
    monkeypatch.setattr(
        database_handler,
        "delete_system_setting",
        lambda key: False if key == 'pulse_width_ms' else delete(key),
    )

    controller = SystemController(database_handler)

    journal = capsys.readouterr().out
    assert "Stored the fixed setting" not in journal
    assert "Removed the retired setting" not in journal
    assert (
        "[SETTINGS] Could not store the fixed setting use_pulse_delivery=True; the database "
        "still holds False, RRR uses True, and the next start tries again"
    ) in journal
    assert (
        "[SETTINGS] Could not remove the retired setting pulse_width_ms=50; it is ignored, "
        "and the next start tries again"
    ) in journal
    assert _stored(database_handler)['use_pulse_delivery'] is False, "as the journal says"
    assert controller.settings['use_pulse_delivery'] is True
    assert 'pulse_width_ms' not in controller.settings

    # The database works again at the next start. (Not monkeypatch.undo():
    # that would also unset the RRR_DATA the data-directory fixture set.)
    monkeypatch.setattr(database_handler, "update_system_setting", update)
    monkeypatch.setattr(database_handler, "delete_system_setting", delete)
    SystemController(database_handler)
    journal = capsys.readouterr().out
    assert "[SETTINGS] Removed the retired setting pulse_width_ms=50" in journal
    assert "[SETTINGS] Stored the fixed setting use_pulse_delivery=True (was False)" in journal
    assert _stored(database_handler)['use_pulse_delivery'] is True


def test_a_legacy_settings_json_cannot_bring_either_back(database_handler, write_legacy_settings):
    """A device still on a pre-v1.5.0 settings.json migrates it once, at its
    first start on this release: the width is not copied, and pulse delivery
    is on in memory and in the database."""
    from controllers.system_controller import SystemController  # noqa: PLC0415

    write_legacy_settings({"num_hats": 1, "pulse_width_ms": 50, "use_pulse_delivery": False})

    controller = SystemController(database_handler)

    assert controller.settings['num_hats'] == 1, "the migration ran"
    assert 'pulse_width_ms' not in controller.settings
    assert 'pulse_width_ms' not in _stored(database_handler)
    assert controller.settings['use_pulse_delivery'] is True
    assert _stored(database_handler)['use_pulse_delivery'] is True


def test_no_save_writes_a_pulse_width_or_turns_pulse_delivery_off(
    system_controller, database_handler
):
    system_controller.save_settings(
        {'pulse_width_ms': 40, 'use_pulse_delivery': False, 'num_hats': 1}
    )
    assert 'pulse_width_ms' not in _stored(database_handler)
    assert _stored(database_handler)['use_pulse_delivery'] is True
    assert 'pulse_width_ms' not in system_controller.settings
    assert system_controller.settings['use_pulse_delivery'] is True

    # The Settings tab saves the controller's own dict after writing to it.
    system_controller.settings.update(pulse_width_ms=45, use_pulse_delivery=False)
    system_controller.save_settings(system_controller.settings)
    assert 'pulse_width_ms' not in _stored(database_handler)
    assert _stored(database_handler)['use_pulse_delivery'] is True
    assert 'pulse_width_ms' not in system_controller.settings
    assert system_controller.settings['use_pulse_delivery'] is True


def test_every_start_forces_pulse_delivery_and_writes_no_pulse_width(database_handler):
    """main.setup() runs ensure_solenoid_defaults at every start. It used to
    force-merge pulse_width_ms = 20; it must still force pulse delivery on."""
    from controllers.system_controller import SystemController  # noqa: PLC0415

    _older_release_left(database_handler)
    controller = SystemController(database_handler)
    controller.ensure_solenoid_defaults()

    assert _stored(database_handler)['use_pulse_delivery'] is True
    assert 'pulse_width_ms' not in _stored(database_handler)
    assert 'pulse_width_ms' not in controller.settings
    assert 'pulse_width_ms' not in controller._get_persisted_keys()
    assert 'use_pulse_delivery' in controller._get_persisted_keys()


# --- Settings > Delivery ----------------------------------------------------------------


def _settings_tab(system_controller, database_handler):
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    return SettingsTab(
        system_controller,
        login_system=login,
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
    )


def test_the_delivery_tab_has_no_pulse_width_or_pulse_mode_control(
    qapp, system_controller, database_handler
):
    from PyQt5.QtCore import Qt  # noqa: PLC0415
    from PyQt5.QtWidgets import QCheckBox, QGroupBox, QLabel  # noqa: PLC0415

    tab = _settings_tab(system_controller, database_handler)
    page = tab.hardware_pump_settings

    assert not hasattr(tab, 'use_pulse_delivery') and not hasattr(tab, 'pulse_width_ms')
    checkboxes = [box.text() for box in page.findChildren(QCheckBox)]
    assert "Enable Pulse Mode" not in checkboxes
    assert "Round doses up to the next whole pulse" in checkboxes, "the rounding policy stays"
    labels = [label.text() for label in page.findChildren(QLabel)]
    assert not any(text.startswith("Pulse Width") for text in labels)

    group = tab.round_doses_up.parentWidget()
    assert isinstance(group, QGroupBox) and group.title() == "Pulse Delivery"
    rows = group.layout()
    [checkbox_row] = [
        rows.itemAt(i) for i in range(rows.count()) if rows.itemAt(i).widget() is tab.round_doses_up
    ]
    assert checkbox_row.alignment() == Qt.AlignLeft, "at its own width, as in the old form row"
    note = tab.pulse_profile_note
    assert note.parentWidget() is group and note.objectName() == "HelpText"
    assert note.text() == (
        "Deliveries to each cage use the pulse width and interval it was calibrated at: "
        "the Profile column in Settings\u00a0>\u00a0Calibration."
    )


def test_the_auto_save_writes_neither_key(qapp, system_controller, database_handler):
    tab = _settings_tab(system_controller, database_handler)
    system_controller.settings.update(pulse_width_ms=45, use_pulse_delivery=False)

    tab.round_doses_up.setChecked(True)  # stateChanged -> _auto_save_settings

    assert _stored(database_handler)['round_doses_up'] is True, "the save ran"
    assert 'pulse_width_ms' not in _stored(database_handler)
    assert _stored(database_handler)['use_pulse_delivery'] is True
    assert 'pulse_width_ms' not in system_controller.settings
    assert system_controller.settings['use_pulse_delivery'] is True


@pytest.mark.parametrize("widget_changes", [False, True], ids=["nothing-changes", "pump-volume"])
@pytest.mark.parametrize("pulse_mode", [False, True])
def test_a_backup_from_an_older_release_cannot_turn_pulse_delivery_off(
    qapp,
    system_controller,
    database_handler,
    dialogs,
    monkeypatch,
    tmp_path,
    pulse_mode,
    widget_changes,
):
    """restore_from_backup merges the backup into system_controller.settings,
    the dict the next Run copies. When the backup changes a value a widget
    shows (here the pump volume), the widget's auto-save runs save_settings,
    which also normalises that dict. A backup taken on the same device
    changes no widget and saves nothing, so there the restore's own drop is
    all that keeps the old keys out: both cases are run."""
    from PyQt5.QtWidgets import QFileDialog  # noqa: PLC0415
    from strategies.solenoid_flow_strategy import SolenoidFlowStrategy  # noqa: PLC0415
    from utils.calibration_gate import gate_applies  # noqa: PLC0415

    tab = _settings_tab(system_controller, database_handler)
    pump_volume = tab.pump_volume.value() + (10 if widget_changes else 0)
    backup = tmp_path / "rrr_backup.json"
    backup.write_text(
        json.dumps(
            {
                "pump_volume_ul": pump_volume,
                "calibration_factor": tab.calibration_factor.value(),
                "use_pulse_delivery": pulse_mode,
                "pulse_width_ms": 50,
            }
        )
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(backup), ""))
    )
    saves = []
    save_settings = system_controller.save_settings
    monkeypatch.setattr(
        system_controller,
        "save_settings",
        lambda settings_dict: saves.append(dict(settings_dict)) or save_settings(settings_dict),
    )

    tab.restore_from_backup()

    assert bool(saves) is widget_changes, "only a changed widget saves"
    settings = system_controller.settings
    assert settings['pump_volume_ul'] == pump_volume, "the rest of the backup applies"
    assert settings['use_pulse_delivery'] is True
    assert 'pulse_width_ms' not in settings
    assert 'pulse_width_ms' not in _stored(database_handler)
    # What the next Run gets: main.run_program copies these settings, and the
    # worker builds the strategy from them.
    strategy = SolenoidFlowStrategy(object(), None, None, dict(settings))
    assert strategy._use_pulse_mode is True
    assert gate_applies(settings) is True

    [(kind, title, text)] = dialogs
    assert (kind, title) == ("information", "Success")
    said = "The backup had pulse delivery turned off. That was not applied" in text
    assert said is (not pulse_mode), "said only when the backup had it off"
