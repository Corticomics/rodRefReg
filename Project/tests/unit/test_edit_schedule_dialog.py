"""Smoke + behaviour tests for the rebuilt ScheduleEditDialog.

The dialog reuses the wizard's ``Step3ConfigureParameters`` and saves through
``update_staggered_schedule``. These tests assert it (a) pre-fills the saved
name/volume/cage from the schedule, and (b) actually persists an edit end to
end. Skips cleanly when PyQt5 is unavailable; CI installs ``python3-pyqt5``.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


def _seed_staggered(database_handler):
    """Create a 2-animal staggered schedule and return its Schedule object."""
    from models.Schedule import Schedule  # noqa: PLC0415

    start = datetime.now() + timedelta(days=1)
    end = start + timedelta(hours=1)
    sched = Schedule(
        schedule_id=None,
        name="Morning ration",
        water_volume=3.0,
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        created_by=1,
        is_super_user=0,
        delivery_mode="staggered",
    )
    sched.add_animal(animal_id=1, relay_unit_id=1, desired_volume=1.0)
    sched.add_animal(animal_id=2, relay_unit_id=2, desired_volume=2.0)
    sid = database_handler.add_staggered_schedule(sched)
    assert sid is not None

    # Re-read so we hand the dialog the same shape the hub does.
    return next(s for s in database_handler.get_all_schedules() if s.schedule_id == sid)


def test_dialog_prefills_from_schedule(qapp, database_handler):
    from ui.schedules_hub import ScheduleEditDialog  # noqa: PLC0415

    schedule = _seed_staggered(database_handler)
    dlg = ScheduleEditDialog(schedule, database_handler, system_controller=None)

    assert dlg._step3 is not None
    configs = dlg._step3.get_animal_configs()
    assert configs[1]["volume"] == 1.0
    assert configs[2]["volume"] == 2.0
    assert configs[1]["cage_id"] == 1
    assert configs[2]["cage_id"] == 2
    assert dlg._step3._name_input.text() == "Morning ration"


def test_dialog_save_persists_edit(qapp, database_handler):
    from PyQt5.QtWidgets import QDialog  # noqa: PLC0415
    from ui.schedules_hub import ScheduleEditDialog  # noqa: PLC0415

    schedule = _seed_staggered(database_handler)
    dlg = ScheduleEditDialog(schedule, database_handler, system_controller=None)

    # Operator bumps animal 1's volume and renames the schedule.
    dlg._step3._animal_widgets[1]["volume"].setValue(4.0)
    dlg._step3._name_input.setText("Edited ration")

    dlg._save_changes()
    assert dlg.result() == QDialog.Accepted

    details = database_handler.get_schedule_details(schedule.schedule_id)[0]
    assert details["desired_water_outputs"]["1"] == 4.0
    assert details["desired_water_outputs"]["2"] == 2.0


def test_instant_schedule_shows_notice_not_form(qapp, database_handler):
    from models.Schedule import Schedule  # noqa: PLC0415
    from ui.schedules_hub import ScheduleEditDialog  # noqa: PLC0415

    instant = Schedule(
        schedule_id=999,
        name="Instant one",
        water_volume=1.0,
        start_time=datetime.now().isoformat(),
        end_time=datetime.now().isoformat(),
        created_by=1,
        is_super_user=0,
        delivery_mode="instant",
    )
    dlg = ScheduleEditDialog(instant, database_handler, system_controller=None)
    # Instant mode renders the notice path, not the Step-3 form.
    assert dlg._step3 is None
