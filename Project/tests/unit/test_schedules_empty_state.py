"""Regression test for the Schedules empty-state centering (QA item #6).

When there are no schedules the "No Schedules / Create Schedule" prompt used to
sit pinned to the bottom: the code hid the grid's inner widget but not the
surrounding scroll area, so the scroll kept its stretch and pushed the
no-stretch empty state down. The fix hides the scroll area itself and gives the
empty state the stretch so its AlignCenter layout centres it.

Skips when PyQt5 is unavailable; CI installs ``python3-pyqt5`` so it runs there.
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


def _make_hub(qapp):
    from PyQt5.QtCore import QObject, pyqtSignal  # noqa: PLC0415
    from ui.schedules_hub import SchedulesHub  # noqa: PLC0415

    class StubLoginSystem(QObject):
        login_status_changed = pyqtSignal()

        def get_current_trainer(self):
            return None

        def is_logged_in(self):
            return False

    database_handler = SimpleNamespace(
        get_all_schedules=lambda: [],
        get_schedules_by_trainer=lambda _tid: [],
    )
    return SchedulesHub(
        settings={},
        print_to_terminal=lambda *_: None,
        database_handler=database_handler,
        login_system=StubLoginSystem(),
    )


def test_empty_state_shown_and_scroll_hidden(qapp):
    """With no schedules the empty state shows and the scroll area is hidden."""
    hub = _make_hub(qapp)
    assert hub._scroll.isHidden()
    assert not hub._empty_state.isHidden()


def test_empty_state_has_stretch_for_vertical_centering(qapp):
    """The empty state carries layout stretch so it fills/centres, not bottom-pins."""
    hub = _make_hub(qapp)
    layout = hub.layout()
    idx = layout.indexOf(hub._empty_state)
    assert idx != -1
    assert layout.stretch(idx) == 1
