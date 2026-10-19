"""The calibration wizard starts from the cage's last profile (v2.1.0).

The owner's decision (2026-10-19): the wizard starts from the cage's last
pulse width and interval; a cage never calibrated starts from the device's
most recent calibration, and a device with none from 30 ms / 1000 ms (the
production Parker 003-0257-900 valve's validated profile). The configuration
page says where its values came from, and Calibrate All Uncalibrated follows
the same rule for every cage it opens. Against the real database, offscreen;
the rule itself is test_pulse_profile.py's.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

Q = 0.034164


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
def _quiet(monkeypatch, tmp_path):
    """No real message boxes, and the wizard's debug log in a temp home."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    for name in ("warning", "critical", "information"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))


def _calibrate(db, cage, width, interval, date=None):
    assert db.save_valve_calibration(
        cage_id=cage,
        relay_id=cage,
        pulse_width_ms=width,
        volume_per_pulse_ml=Q,
        stddev_ml=0.0003,
        cv_pct=1.0,
        num_samples=250,
        inter_pulse_interval_ms=interval,
        topology='shared_manifold',
    )
    if date is not None:
        with db.connect() as conn:
            conn.execute(
                "UPDATE valve_calibration SET calibration_date = ? WHERE cage_id = ?",
                (date, cage),
            )
            conn.commit()


def _wizard(db, cage_id):
    from ui.CalibrationWizard import CalibrationWizard  # noqa: PLC0415

    controller = MagicMock()
    controller.settings = {"num_hats": 1, "global_master_relay_id": 16}
    return CalibrationWizard(cage_id=cage_id, database_handler=db, system_controller=controller)


def _configuration_page(wizard):
    """(pulse width, interval, what the page says) on the configuration step."""
    wizard.show_step(1)
    return (
        wizard.pulse_width_spin.value(),
        wizard.interval_spin.value(),
        wizard.profile_info.text(),
    )


def _two_calibrated_cages(db):
    _calibrate(db, 2, 30, 1000, date="2026-10-02T09:15:00")
    _calibrate(db, 3, 25, 800, date="2026-10-15T11:00:00")


def test_a_calibrated_cage_starts_from_its_own_profile(qapp, database_handler):
    _two_calibrated_cages(database_handler)
    wizard = _wizard(database_handler, 2)

    width, interval, says = _configuration_page(wizard)

    assert (width, interval) == (30, 1000), "its own, not cage 3's more recent one"
    assert says.startswith("Starting from this cage's last calibration: 30 ms / 1000 ms. ")
    assert says.endswith("Deliveries replay this cage's stored timing profile.")
    wizard.close()


def test_a_cage_never_calibrated_starts_from_the_device_s_most_recent(qapp, database_handler):
    _two_calibrated_cages(database_handler)
    wizard = _wizard(database_handler, 9)

    width, interval, says = _configuration_page(wizard)

    assert (width, interval) == (25, 800)
    assert says.startswith(
        "Starting from cage 3's calibration, the most recent on this device: 25 ms / 800 ms. "
    )
    wizard.close()


def test_a_device_with_no_calibration_starts_from_30_1000(qapp, database_handler):
    wizard = _wizard(database_handler, 1)

    width, interval, says = _configuration_page(wizard)

    assert (width, interval) == (30, 1000)
    assert says.startswith(
        "Starting from 30 ms / 1000 ms, the production valve's validated profile: no cage "
        "on this device has a calibration to start from. "
    )
    wizard.close()


def test_the_run_uses_the_starting_values_unless_the_operator_changes_them(
    qapp, database_handler
):
    _two_calibrated_cages(database_handler)
    wizard = _wizard(database_handler, 2)
    _configuration_page(wizard)

    wizard._show_execution()  # reads the spin boxes; the run itself starts later
    assert (wizard.pulse_width_ms, wizard.inter_pulse_interval_ms) == (30, 1000)
    wizard.close()

    changed = _wizard(database_handler, 2)
    _configuration_page(changed)
    changed.interval_spin.setValue(1500)
    changed._show_execution()
    assert (changed.pulse_width_ms, changed.inter_pulse_interval_ms) == (30, 1500)
    changed.close()


@pytest.mark.parametrize("calibrated_first", [False, True], ids=["new-device", "one-calibrated"])
def test_calibrate_all_opens_every_cage_by_the_same_rule(
    qapp, database_handler, system_controller, monkeypatch, calibrated_first
):
    """Each wizard of the batch starts from the device's most recent
    calibration at the time it opens, which includes the cages the batch has
    just calibrated. Each fake run here saves a different profile, so the
    next cage shows it is read afresh; the fourth wizard is cancelled, which
    ends the batch."""
    from PyQt5.QtCore import QTimer  # noqa: PLC0415
    from PyQt5.QtWidgets import QDialog, QMessageBox  # noqa: PLC0415
    from ui.CalibrationWizard import CalibrationWizard  # noqa: PLC0415
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    if calibrated_first:
        _calibrate(database_handler, 1, 30, 1000, date="2020-01-06T10:40:00")
    opened = []

    def _exec(wizard):
        profile = wizard.starting_profile
        opened.append((wizard.cage_id, wizard.pulse_width_ms, wizard.inter_pulse_interval_ms))
        if len(opened) == 4:
            return QDialog.Rejected
        _calibrate(
            database_handler,
            wizard.cage_id,
            profile.pulse_width_ms + 1,
            profile.interval_ms + 10,
        )
        return QDialog.Accepted

    monkeypatch.setattr(CalibrationWizard, "exec_", _exec)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(QTimer, "singleShot", staticmethod(lambda _ms, slot: slot()))
    system_controller.settings['num_hats'] = 1
    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    tab = SettingsTab(
        system_controller,
        login_system=login,
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
    )

    tab._calibrate_all_uncalibrated()

    if calibrated_first:
        assert opened == [(2, 30, 1000), (3, 31, 1010), (4, 32, 1020), (5, 33, 1030)]
    else:
        assert opened == [(1, 30, 1000), (2, 31, 1010), (3, 32, 1020), (4, 33, 1030)]
