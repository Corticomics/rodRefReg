"""The Schedules Hub "Edit Schedule" button in multi-select mode.

It appears next to "Delete Selected" while selecting, stays disabled unless
exactly one schedule is selected (editing is single-schedule), and hides again
when select mode is cancelled. Skips cleanly without PyQt5.
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


def _make_hub(database_handler):
    from PyQt5.QtCore import QObject, pyqtSignal  # noqa: PLC0415
    from ui.schedules_hub import SchedulesHub  # noqa: PLC0415

    class StubLogin(QObject):
        login_status_changed = pyqtSignal()

        def get_current_trainer(self):
            return None

        def is_logged_in(self):
            return True

    return SchedulesHub(
        settings={},
        print_to_terminal=lambda *_: None,
        database_handler=database_handler,
        login_system=StubLogin(),
        system_controller=None,
    )


def _seed(database_handler, name):
    from models.Schedule import Schedule  # noqa: PLC0415

    start = datetime.now() + timedelta(days=1)
    end = start + timedelta(hours=1)
    sched = Schedule(None, name, 1.0, start.isoformat(), end.isoformat(), 1, 0, "staggered")
    sched.add_animal(animal_id=1, relay_unit_id=1, desired_volume=1.0)
    database_handler.add_staggered_schedule(sched)


def test_edit_button_enabled_only_for_single_selection(qapp, database_handler):
    _seed(database_handler, "A")
    _seed(database_handler, "B")
    hub = _make_hub(database_handler)
    hub.load_schedules()
    assert len(hub._all_schedules) == 2

    # Hidden until select mode is entered.
    assert hub._edit_selected_btn.isHidden()

    hub._toggle_select_mode()
    assert not hub._edit_selected_btn.isHidden()
    assert not hub._edit_selected_btn.isEnabled()  # nothing selected yet

    first, second = hub._all_schedules[0], hub._all_schedules[1]

    hub._on_selection_toggled(first, True)
    assert hub._edit_selected_btn.isEnabled()  # exactly one

    hub._on_selection_toggled(second, True)
    assert not hub._edit_selected_btn.isEnabled()  # two selected -> disabled

    hub._on_selection_toggled(second, False)
    assert hub._edit_selected_btn.isEnabled()  # back to one

    hub._toggle_select_mode()  # cancel
    assert hub._edit_selected_btn.isHidden()


def test_edit_selected_is_noop_without_single_selection(qapp, database_handler):
    _seed(database_handler, "A")
    hub = _make_hub(database_handler)
    hub.load_schedules()
    hub._toggle_select_mode()
    # No selection: must not raise or open anything.
    hub._edit_selected()
    assert hub._select_mode is True
