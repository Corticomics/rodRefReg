"""Log Out is unavailable while a schedule runs.

Stop needs a logged-in user, and CLOSE ALL RELAYS no longer ends a
schedule. A logout mid-run used to grey out Stop and hide Settings,
leaving nothing in RRR that could stop the schedule. So from the Run click
to the end of the run or of Stop the Profile tab's Log Out button is greyed
out, and the logout handler refuses with a dialog that says what to do.
Once the run is over, also after a Stop that could not confirm the
hardware safe, logging out works as before.

Skips cleanly without PyQt5.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from utils.stop_sequence import StopResult  # noqa: E402

USER = {"username": "zes", "trainer_id": 1, "role": "normal"}
TIP = "A schedule is running: press Stop to end it, then log out"
REFUSAL = (
    "information",
    "Schedule running",
    "A schedule is running, so you cannot log out now. Stop needs a logged-in user: after "
    "a logout, nothing in RRR could stop the schedule.\n\nPress Stop to end the schedule, "
    "or wait until it has ended, then log out.",
)

# The QApplication this module uses, kept for the rest of the session. When a
# QApplication is destroyed, PyQt5 deletes every QObject without a parent.
_QAPP = []


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


@pytest.fixture(autouse=True)
def lock(qapp):
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield ol.get_operation_lock()
    ol._singleton = None


@pytest.fixture(autouse=True)
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


@pytest.fixture(autouse=True)
def no_worker(monkeypatch):
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: False)


@pytest.fixture
def slot_errors(monkeypatch):
    """Exceptions raised in a Qt slot. PyQt5 hands them to sys.excepthook,
    not to the code that emitted the signal, so a test sees them only here."""
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *exc: raised.append(exc[1]))
    return raised


def _profile(job):
    from ui.UserTab import UserTab  # noqa: PLC0415

    login = MagicMock()
    tab = UserTab(login, schedule_running=lambda: job["running"])
    tab.set_user(dict(USER))
    signals = []
    tab.logout_signal.connect(lambda: signals.append("logout"))
    return tab, login, signals


def test_log_out_is_greyed_out_from_run_to_the_end_of_the_run(lock):
    job = {"running": False}
    tab, _login, _signals = _profile(job)
    assert tab.logout_button.isEnabled() is True

    job["running"] = True
    assert lock.try_acquire("schedule")  # Run raises the flag, then takes the lock

    assert tab.logout_button.isEnabled() is False
    assert tab.logout_button.toolTip() == TIP

    job["running"] = False
    lock.release("schedule")  # every end clears the flag, then lets go

    assert tab.logout_button.isEnabled() is True
    assert tab.logout_button.toolTip() == ""


def test_a_logout_is_refused_while_a_schedule_runs(lock, dialogs):
    job = {"running": True}
    tab, login, signals = _profile(job)
    assert tab.logout_button.isEnabled() is False, "greyed out from the start of the session"

    tab.logout()

    assert dialogs == [REFUSAL]
    login.logout.assert_not_called()
    assert signals == []
    assert tab.current_user == USER, "still logged in"


def test_a_logout_works_once_the_run_has_ended(lock, dialogs):
    job = {"running": True}
    tab, login, signals = _profile(job)
    job["running"] = False

    tab.logout()

    assert dialogs == []
    login.logout.assert_called_once_with()
    assert signals == ["logout"]
    assert tab.current_user is None


def test_the_lock_changing_while_logged_out_touches_no_deleted_button(lock, slot_errors):
    """After a logout the profile's Log Out button is deleted; a later run
    (or priming session) must not reach it."""
    from PyQt5.QtCore import QCoreApplication, QEvent  # noqa: PLC0415

    job = {"running": False}
    tab, _login, _signals = _profile(job)
    tab.logout()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    assert lock.try_acquire("priming")
    lock.release("priming")

    assert slot_errors == [], "the refresh touched the deleted button"
    tab.set_user(dict(USER))  # logs in again: a new button, live
    assert tab.logout_button.isEnabled() is True


def test_without_a_job_flag_a_schedule_hold_counts_as_running(lock, dialogs):
    from ui.UserTab import UserTab  # noqa: PLC0415

    login = MagicMock()
    tab = UserTab(login)
    tab.set_user(dict(USER))
    assert lock.try_acquire("schedule")

    assert tab.logout_button.isEnabled() is False
    tab.logout()
    assert dialogs == [REFUSAL]
    login.logout.assert_not_called()


# --- the real main window ------------------------------------------------------------------


@pytest.fixture
def main_window(monkeypatch, system_controller, database_handler):
    """Builds the real main window with a real LoginSystem on the test
    database, an operator logged in through the Profile tab, and a stub for
    main.stop_program that returns the given StopResult. Each window is
    deleted at teardown, so none of its timers fires in a later test."""
    from models.login_system import LoginSystem  # noqa: PLC0415
    from PyQt5.QtCore import QCoreApplication, QEvent  # noqa: PLC0415
    from ui.gui import RodentRefreshmentGUI  # noqa: PLC0415

    monkeypatch.setattr(RodentRefreshmentGUI, "showMaximized", lambda self: None)
    windows = []

    def _build(stop_result):
        login = LoginSystem(database_handler)
        gui = RodentRefreshmentGUI(
            MagicMock(),  # main.run_program: not reached, the queued start is stubbed
            MagicMock(return_value=stop_result),  # main.stop_program
            MagicMock(),
            system_controller=system_controller,
            database_handler=database_handler,
            login_system=login,
            relay_handler=MagicMock(),
            notification_handler=MagicMock(),
        )
        windows.append(gui)
        assert login.create_user("zes", "pw") is True
        _log_in(gui)
        return gui, login

    yield _build
    for gui in windows:
        gui.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def _log_in(gui):
    gui.user_tab.username_input.setText("zes")
    gui.user_tab.password_input.setText("pw")
    gui.user_tab.handle_login()


def _press_run(section, monkeypatch):
    """The Run click up to "Starting...": the job flag and the lock. The
    deferred schedule checks it queues are stubbed (no schedule is loaded
    here) and run at once, so that nothing queued outlives the test."""
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    monkeypatch.setattr(section, "_prepare_and_execute_schedule", lambda _token=None: None)
    section.schedule_drop_area.current_schedule = SimpleNamespace(name="AM water")
    section.run_program()
    QApplication.processEvents()


def test_in_the_main_window_stop_stays_reachable_for_the_whole_run(
    lock, dialogs, slot_errors, monkeypatch, main_window
):
    """The real window: a logged-in operator presses Run. Until Stop, Log Out
    is greyed out and refused, so Stop stays enabled; a mode switch does not
    change that. After a clean Stop, Log Out works and greys Stop out."""
    gui, login = main_window(StopResult(True, True))
    section = gui.run_stop_section
    assert login.is_logged_in() and gui.user_tab.logout_button.isEnabled()
    assert lock.try_acquire("schedule")  # a stale hold, with no job in progress
    assert gui.user_tab.logout_button.isEnabled() is True, "Log Out follows the job flag"
    lock.release("schedule")

    _press_run(section, monkeypatch)

    assert section.stop_button.isEnabled() is True
    assert gui.user_tab.logout_button.isEnabled() is False
    assert gui.user_tab.logout_button.toolTip() == TIP
    gui.user_tab.logout()
    assert dialogs == [REFUSAL]
    assert login.is_logged_in() and section.stop_button.isEnabled() is True
    gui.settings_tab._toggle_mode()  # Super mode: the role changes, the login does not
    section.update_button_states()
    assert section.stop_button.isEnabled() is True

    section.stop_program()

    assert dialogs == [REFUSAL], "a clean Stop shows no dialog"
    assert section.job_in_progress is False and lock.is_busy() is False
    assert gui.user_tab.logout_button.isEnabled() is True
    assert gui.user_tab.logout_button.toolTip() == ""
    gui.user_tab.logout()
    assert login.is_logged_in() is False
    assert section.stop_button.isEnabled() is False
    assert gui.main_tab_widget.isTabVisible(gui.settings_tab_index) is False
    assert slot_errors == []


def test_logout_is_allowed_after_a_stop_that_latched_and_a_new_login_brings_close_all_back(
    lock, dialogs, slot_errors, monkeypatch, main_window, fake_relay_handler
):
    """A Stop that could not confirm every relay off ends the run and hands
    the schedule's hold to EMERGENCY. The run is over, so Log Out is live
    again and the logout goes through, which hides Settings. The latch
    outlives the session: logging in again brings back Settings and CLOSE
    ALL RELAYS, and a confirmed press clears it."""
    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    gui, login = main_window(StopResult(False, True))  # a relay HAT did not confirm OFF
    section = gui.run_stop_section
    close_all = gui.settings_tab.priming_widget.emergency_btn
    _press_run(section, monkeypatch)
    assert gui.user_tab.logout_button.isEnabled() is False
    assert close_all.isEnabled() is False

    section.stop_program()

    assert [shown[:2] for shown in dialogs] == [("critical", "Relays Not Confirmed Off")]
    assert section.job_in_progress is False and lock.held_by("emergency")
    assert gui.user_tab.logout_button.isEnabled() is True
    assert gui.user_tab.logout_button.toolTip() == ""

    gui.user_tab.logout()

    assert len(dialogs) == 1, "the logout is not refused"
    assert login.is_logged_in() is False
    assert gui.main_tab_widget.isTabVisible(gui.settings_tab_index) is False
    assert close_all.isEnabled() is False, "out of reach with Settings"
    assert lock.held_by("emergency"), "a logout does not clear the latch"

    _log_in(gui)

    assert login.is_logged_in() and gui.user_tab.logout_button.isEnabled() is True
    assert gui.main_tab_widget.isTabVisible(gui.settings_tab_index) is True
    assert close_all.isEnabled() is True and close_all.toolTip() == ""
    assert section.run_button.isEnabled() is False, "the latch still holds the hardware"

    gui.settings_tab.priming_widget._on_emergency_stop_clicked()  # the HAT answers now

    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")
    assert fake_relay_handler.trace == [(("all",), 0)]
    assert lock.is_busy() is False
    assert section.run_button.isEnabled() is True
    assert slot_errors == []


def test_a_help_search_for_logout_finds_why_log_out_is_greyed_out():
    """Operators type "logout" as one word; the Help search must still lead
    them to the Troubleshooting entry that says why Log Out is greyed out."""
    from utils.help_content_manager import HelpContentManager  # noqa: PLC0415

    found = [key for key, _snippet in HelpContentManager().search("logout")]

    assert "Troubleshooting" in found
