"""Priming's CLOSE ALL RELAYS is unavailable while a schedule runs, and frees
the hardware lock only when it is safe to.

The button used to switch every relay off and force-clear the operation lock,
whatever held it. Later it also stopped a running schedule. Now it is a
priming and recovery control: Stop is the one way to end a schedule, so
from the Run click to the end of the run or of Stop, CLOSE ALL RELAYS and
Close Selected are greyed out, and a click that still arrives is refused
before it touches the relays.

At every other time it works as before. The lock is cleared only when every
relay is confirmed off and nothing that can open a valve is still running.
Otherwise its holder keeps it, and when nobody holds it the emergency stop
takes it itself (EMERGENCY). A confirmed press also clears the EMERGENCY hold
a Stop takes when it cannot confirm every relay off or its worker did not
exit.
"""

from __future__ import annotations

import os
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from utils.stop_sequence import StopResult  # noqa: E402

MASTER = 16
CAGE = 1
SETTINGS = {"num_hats": 1, "global_master_relay_id": MASTER}

RUNNING_TIP = "A schedule is running: press Stop to end it"


def _refusal(control):
    return (
        "information",
        "Schedule running",
        f"A schedule is running, so {control} is not available.\n\n"
        "To end the schedule, press the Stop button: Stop switches every relay off "
        "and stops the schedule.",
    )


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


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
def relays(monkeypatch, fake_relay_handler):
    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    return fake_relay_handler


def _panel(schedule_running=None):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    return PrimingControlWidget(dict(SETTINGS), lambda *_: None, schedule_running=schedule_running)


def _idle():
    """The Run/Stop section's job flag with no schedule job in progress."""
    return False


def _latched_by_stop(lock):
    """The state a Stop leaves when it cannot confirm every relay off or its
    worker did not exit: the job is over, and the schedule's hold has passed
    to EMERGENCY in one step, as Stop hands it over."""
    lock.hold_until_safe("schedule")
    assert lock.held_by("emergency")


# --- refused while a schedule runs ----------------------------------------------------------


def test_close_all_relays_is_refused_while_a_schedule_runs(relays, lock, dialogs):
    """Replaces "CLOSE ALL RELAYS stops a running schedule": Stop ends a
    schedule now, so the button does nothing at all mid-run."""
    panel = _panel(lambda: True)
    assert lock.try_acquire("schedule")

    panel._on_emergency_stop_clicked()

    assert relays.trace == [], "refused before anything touched the relays"
    assert panel._relay_handler is None, "no handler built: building one switches every relay off"
    assert lock.held_by("schedule"), "the run keeps its hold"
    assert dialogs == [_refusal("CLOSE ALL RELAYS")]


def test_close_selected_is_refused_while_a_schedule_runs(relays, lock, dialogs):
    panel = _panel(lambda: True)
    assert lock.try_acquire("schedule")
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(CAGE))

    panel._on_close_cage_clicked()

    assert relays.trace == []
    assert panel._solenoid_controller is None and panel._relay_handler is None
    assert lock.held_by("schedule")
    assert dialogs == [_refusal("Close Selected")]


def test_a_panel_without_the_run_stop_section_treats_a_schedule_hold_as_running(
    relays, lock, dialogs
):
    """Replaces "a schedule it cannot stop keeps its hold": a panel built
    without the job flag must not free a schedule's lock, and now does not
    touch the relays either."""
    panel = _panel()
    assert lock.try_acquire("schedule")
    assert panel.emergency_btn.isEnabled() is False

    panel._on_emergency_stop_clicked()

    assert relays.trace == []
    assert lock.held_by("schedule"), "priming and calibration stay locked out"
    assert dialogs == [_refusal("CLOSE ALL RELAYS")]

    lock.release("schedule")
    assert panel.emergency_btn.isEnabled() is True


def test_a_cage_selector_change_mid_run_keeps_close_selected_greyed(relays, lock):
    running = {"job": False}
    panel = _panel(lambda: running["job"])
    assert panel.cage_close_btn.isEnabled() is True

    running["job"] = True
    assert lock.try_acquire("schedule")  # its state_changed greys the Close controls

    for button in (panel.emergency_btn, panel.cage_close_btn):
        assert button.isEnabled() is False
        assert button.toolTip() == RUNNING_TIP
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(5))
    assert panel.cage_close_btn.isEnabled() is False, "a selector change must not re-enable it"

    running["job"] = False
    lock.release("schedule")
    for button in (panel.emergency_btn, panel.cage_close_btn):
        assert button.isEnabled() is True
        assert button.toolTip() == ""


# --- no schedule running: unchanged ---------------------------------------------------------


def test_with_nothing_running_it_is_unchanged(relays, lock, dialogs):
    panel = _panel(_idle)
    panel._on_open_master_clicked()
    assert lock.held_by("priming")

    panel._on_emergency_stop_clicked()

    assert relays.trace[-1] == (("all",), 0) and relays.trace.count((("all",), 0)) == 1
    assert relays.energized() == set()
    assert lock.is_busy() is False
    assert dialogs == [("information", "Emergency Stop", "All relays have been closed.")]


def test_a_worker_still_running_keeps_the_hold(relays, lock, dialogs, monkeypatch):
    """No job is in progress, yet a delivery worker is alive. The Stop button
    is greyed out in that state, so the dialog must not send the operator to
    it."""
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)
    panel = _panel(_idle)
    assert lock.try_acquire("schedule")

    panel._on_emergency_stop_clicked()

    assert lock.held_by("schedule")
    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop")
    assert "delivery worker has not stopped" in text and "restart the Raspberry Pi" in text
    assert "Press Stop" not in text


def test_a_stale_hold_is_still_cleared(relays, lock, dialogs):
    """The failsafe it always was: a hold with nothing behind it (no job, no
    worker) must not lock the operator out of the app."""
    panel = _panel(_idle)
    assert lock.try_acquire("schedule")
    assert panel.emergency_btn.isEnabled() is True, "no job: the button is live"

    panel._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert dialogs == [("information", "Emergency Stop", "All relays have been closed.")]


def test_relays_not_confirmed_off_keep_the_priming_session(relays, lock, dialogs):
    panel = _panel()
    panel._on_open_master_clicked()
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(CAGE))
    panel._on_open_cage_clicked()
    relays.fail_all_off = True

    panel._on_emergency_stop_clicked()

    assert dialogs[-1][:2] == ("critical", "Emergency Stop Failed")
    assert dialogs[-1][2].endswith(
        "The priming session stays open. Run and calibration stay unavailable until every "
        "relay is confirmed off. Once the relay HAT answers, press CLOSE ALL RELAYS again; "
        "or close and reopen RRR."
    )
    assert lock.held_by("priming"), "no schedule can start onto a valve that may be open"
    assert lock.try_acquire("schedule") is False
    assert panel._model.is_master_open and panel._model.is_cage_open(CAGE)

    relays.fail_all_off = False  # the fault clears; the operator presses it again
    panel._on_emergency_stop_clicked()

    assert relays.energized() == set()
    assert lock.is_busy() is False
    assert not panel._model.is_master_open and not panel._model.is_cage_open(CAGE)


def test_an_unconfirmed_stop_latch_is_cleared_by_a_confirmed_close_all(relays, lock, dialogs):
    """Replaces "relays not confirmed off still stop the schedule": Stop now
    takes the EMERGENCY hold itself. CLOSE ALL RELAYS is live once the job is
    over, keeps the hold while the relays are unconfirmed, and frees it once
    they are."""
    panel = _panel(_idle)
    assert lock.try_acquire("schedule")
    _latched_by_stop(lock)
    assert panel.emergency_btn.isEnabled() is True
    relays.fail_all_off = True

    panel._on_emergency_stop_clicked()

    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop Failed")
    assert "Disconnect the valve power supply now" in text
    assert "schedule" not in text
    assert text.endswith(
        "Run, priming and calibration stay unavailable until every relay is confirmed off. "
        "Once the relay HAT answers, press CLOSE ALL RELAYS again; or close and reopen RRR."
    )
    assert lock.held_by("emergency")
    assert lock.active_label() == "an unconfirmed emergency stop"
    assert lock.try_acquire("schedule") is False, "Run cannot start onto a valve that may be open"

    relays.fail_all_off = False  # the HAT answers again; the operator presses it again
    panel._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")


def test_relays_not_confirmed_off_with_nothing_running_lock_the_hardware(relays, lock, dialogs):
    panel = _panel(_idle)
    relays.fail_all_off = True

    panel._on_emergency_stop_clicked()

    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop Failed")
    assert "schedule" not in text, "none was running"
    assert lock.held_by("emergency")

    # Priming cannot open a valve either, and says why.
    panel._on_open_master_clicked()
    assert dialogs[-1][0] == "warning"
    assert "an unconfirmed emergency stop" in dialogs[-1][2]
    assert relays.energized() == set()
    assert lock.held_by("emergency")

    relays.fail_all_off = False
    panel._on_emergency_stop_clicked()
    assert lock.is_busy() is False


def test_close_all_after_a_stop_that_left_a_live_worker_holds_until_it_exits(
    relays, lock, dialogs, monkeypatch
):
    """Replaces "a worker that outlives the stop is not reported stopped":
    Stop abandoned a worker thread that will not exit and took the EMERGENCY
    hold. The button must not free it beside a worker that can pulse again,
    nor send the operator to the greyed-out Stop button."""
    from utils import updater  # noqa: PLC0415

    alive = {"worker": True}
    monkeypatch.setattr(updater, "_busy_check", lambda: alive["worker"])
    panel = _panel(_idle)
    assert lock.try_acquire("schedule")
    _latched_by_stop(lock)

    panel._on_emergency_stop_clicked()

    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop")
    assert "delivery worker has not stopped" in text
    assert "disconnect the valve power supply and restart the Raspberry Pi" in text
    assert "was stopped" not in text and "Press Stop" not in text
    assert lock.held_by("emergency")
    assert lock.try_acquire("priming") is False

    panel._on_emergency_stop_clicked()  # pressed again, as the dialog says; still alive

    assert dialogs[-1] == dialogs[0], "the same message comes back"
    assert lock.held_by("emergency")

    alive["worker"] = False  # it exits; the operator presses the button again
    panel._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")


def test_a_calibration_hold_is_not_freed(relays, lock, dialogs):
    """Its wizard is modal, so the button should be out of reach while a
    calibration pulses. A hold seen here is not known to be stale: Esc once
    closed the wizard and left its worker pulsing."""
    panel = _panel(_idle)
    assert lock.try_acquire("calibration")

    panel._on_emergency_stop_clicked()

    assert relays.trace == [(("all",), 0)]
    assert lock.held_by("calibration"), "a schedule cannot start beside a calibration"
    ((kind, title, text),) = dialogs
    assert (kind, title) == ("warning", "Emergency Stop")
    assert "a calibration holds the hardware" in text
    assert "close and reopen RRR" in text


@pytest.mark.parametrize("fault", ["handler cannot be built", "all-off raises"])
def test_a_panel_that_cannot_switch_the_relays_says_so_once_and_locks_the_hardware(
    monkeypatch, fake_relay_handler, lock, dialogs, fault
):
    """Replaces "... still stops the schedule": the handler is built without
    its own error dialog, so the operator gets one dialog, and the hardware
    stays locked."""
    if fault == "handler cannot be built":

        def _broken(*_a, **_k):
            raise TypeError("no HAT library")

        monkeypatch.setattr("gpio.gpio_handler.RelayHandler", _broken)
    else:

        def _raises(_state):
            raise OSError("I2C bus error")

        monkeypatch.setattr(fake_relay_handler, "set_all_relays", _raises)
        monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    panel = _panel(_idle)

    panel._on_emergency_stop_clicked()

    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop Failed"), "one dialog"
    assert "schedule" not in text
    assert lock.held_by("emergency")


# --- the Settings tab hands the panel the Run/Stop section's job flag ----------------------


def _settings_tab(system_controller, database_handler, run_stop):
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    return SettingsTab(
        system_controller,
        login_system=login,
        run_stop_section=run_stop,
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
    )


def test_settings_hands_priming_the_run_stop_job_flag(
    relays, lock, dialogs, system_controller, database_handler
):
    """Replaces "settings stops a running schedule through the Stop button
    path": the panel only reads the job flag, and never stops a schedule."""
    run_stop = SimpleNamespace(job_in_progress=True, stop_program=MagicMock())
    tab = _settings_tab(system_controller, database_handler, run_stop)
    panel = tab.priming_widget

    assert panel._schedule_running() is True
    panel._on_emergency_stop_clicked()
    assert dialogs == [_refusal("CLOSE ALL RELAYS")]
    run_stop.stop_program.assert_not_called()

    run_stop.job_in_progress = False
    assert panel._schedule_running() is False


def test_settings_without_a_run_stop_section_reports_no_schedule(
    relays, lock, dialogs, system_controller, database_handler
):
    """Replaces "settings reports no schedule when none runs"."""
    tab = _settings_tab(system_controller, database_handler, None)
    assert tab.priming_widget._schedule_running() is False

    tab.priming_widget._on_emergency_stop_clicked()
    assert dialogs == [("information", "Emergency Stop", "All relays have been closed.")]


def _real_section(system_controller, database_handler, stop_sequence):
    from ui.run_stop_section import RunStopSection  # noqa: PLC0415

    login = MagicMock()
    login.is_logged_in.return_value = True
    return RunStopSection(
        MagicMock(),
        stop_sequence,  # main.stop_program
        MagicMock(),
        system_controller=system_controller,
        database_handler=database_handler,
        login_system=login,
    )


def _press_run(section, monkeypatch):
    """The Run click up to "Starting...": the job flag and the lock. The
    deferred schedule checks it queues are stubbed (no schedule is loaded
    here) and run at once, so that nothing queued outlives the test."""
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    monkeypatch.setattr(section, "_prepare_and_execute_schedule", lambda _token=None: None)
    section.schedule_drop_area.current_schedule = SimpleNamespace(name="AM water")
    section.run_program()
    QApplication.processEvents()


def test_close_all_is_greyed_from_the_run_click_to_the_end_of_stop(
    relays, lock, dialogs, monkeypatch, system_controller, database_handler
):
    """Replaces "the whole path with the real Run/Stop section": Settings,
    Priming and the real Run/Stop section, driven by Run and Stop."""
    section = _real_section(system_controller, database_handler, lambda: StopResult(True, True))
    panel = _settings_tab(system_controller, database_handler, section).priming_widget
    assert panel.emergency_btn.isEnabled() and panel.cage_close_btn.isEnabled()

    _press_run(section, monkeypatch)

    assert section.job_in_progress is True and lock.held_by("schedule")
    for button in (panel.emergency_btn, panel.cage_close_btn):
        assert button.isEnabled() is False
        assert button.toolTip() == RUNNING_TIP
    # Change Relay Hats is greyed at the click too, not once the queued start runs.
    assert section.relay_hats_button.isEnabled() is False
    panel._on_emergency_stop_clicked()
    assert relays.trace == [] and dialogs == [_refusal("CLOSE ALL RELAYS")]

    section.stop_program()

    assert dialogs == [_refusal("CLOSE ALL RELAYS")], "a clean Stop shows no dialog"
    assert section.job_in_progress is False and lock.is_busy() is False
    for button in (panel.emergency_btn, panel.cage_close_btn):
        assert button.isEnabled() is True
        assert button.toolTip() == ""


def test_close_all_is_greyed_until_a_run_ends_by_itself(
    relays, lock, monkeypatch, system_controller, database_handler
):
    section = _real_section(system_controller, database_handler, lambda: StopResult(True, True))
    panel = _settings_tab(system_controller, database_handler, section).priming_widget

    _press_run(section, monkeypatch)
    assert panel.emergency_btn.isEnabled() is False

    section.reset_ui()  # what worker.finished leads to (main._on_finished / cleanup)

    assert lock.is_busy() is False
    assert panel.emergency_btn.isEnabled() is True


def test_a_run_refused_by_a_priming_session_leaves_close_all_available(
    relays, lock, dialogs, monkeypatch, system_controller, database_handler
):
    """The job flag goes up before the lock is taken, and comes down again
    before the Hardware busy dialog when the lock is refused."""
    section = _real_section(system_controller, database_handler, lambda: StopResult(True, True))
    panel = _settings_tab(system_controller, database_handler, section).priming_widget
    panel._on_open_master_clicked()
    assert lock.held_by("priming")
    flags = []
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: flags.append((a[1], section.job_in_progress))),
    )

    _press_run(section, monkeypatch)

    assert flags == [("Hardware busy", False)]
    assert section.job_in_progress is False
    assert lock.held_by("priming")
    assert panel.emergency_btn.isEnabled() is True
    panel._on_emergency_stop_clicked()  # still ends the priming session
    assert lock.is_busy() is False


@pytest.mark.parametrize(
    "start, dialog",
    [
        (MagicMock(return_value=False), ("warning", "Schedule not started")),
        (MagicMock(side_effect=RuntimeError("no thread")), ("critical", "Error")),
    ],
    ids=["no worker started", "the start raised"],
)
def test_a_start_that_did_not_happen_leaves_close_all_available(
    relays, lock, dialogs, monkeypatch, system_controller, database_handler, start, dialog
):
    """Every end of a job lowers the job flag before it lets go of the lock:
    the panel reads the flag only when the lock's state_changed arrives, so a
    release that came first would leave CLOSE ALL RELAYS greyed out with
    nothing left to refresh it. Here _reset_run_button (the path of every
    refusal, and of No, before the start) and _execute_program's except
    branch."""
    section = _real_section(system_controller, database_handler, lambda: StopResult(True, True))
    section.run_program_callback = start  # main.run_program
    panel = _settings_tab(system_controller, database_handler, section).priming_widget
    _press_run(section, monkeypatch)
    assert panel.emergency_btn.isEnabled() is False

    section._execute_program(SimpleNamespace(name="AM water"), "Staggered", 0, 1)

    assert [shown[:2] for shown in dialogs] == [dialog]
    assert section.job_in_progress is False and lock.is_busy() is False
    for button in (panel.emergency_btn, panel.cage_close_btn):
        assert button.isEnabled() is True
        assert button.toolTip() == ""


@pytest.mark.parametrize(
    "result, stop_title",
    [
        (StopResult(False, True), "Relays Not Confirmed Off"),
        (StopResult(True, False), "Delivery Worker Did Not Stop"),
    ],
    ids=["relays not confirmed off", "worker did not exit"],
)
def test_after_a_stop_that_latched_close_all_is_available_and_clears_the_latch(
    relays, lock, dialogs, monkeypatch, system_controller, database_handler, result, stop_title
):
    """Replaces "an unconfirmed stop greys out Run until it is confirmed" and
    "the real stop path with a worker that does not exit": the real Stop
    hands the schedule's hold to EMERGENCY after it lowers the job flag. That
    reaches the panel through the lock's state_changed, so CLOSE ALL RELAYS
    is live to clear it, while Run stays greyed out until a press is
    confirmed with no worker left."""
    from utils import updater  # noqa: PLC0415

    alive = {"worker": not result.worker_exited}
    monkeypatch.setattr(updater, "_busy_check", lambda: alive["worker"])
    section = _real_section(system_controller, database_handler, lambda: result)
    tab = _settings_tab(system_controller, database_handler, section)
    panel = tab.priming_widget
    _press_run(section, monkeypatch)
    assert panel.emergency_btn.isEnabled() is False

    section.stop_program()

    assert [dialog[:2] for dialog in dialogs] == [("critical", stop_title)], "Stop's one dialog"
    assert section.job_in_progress is False and lock.held_by("emergency")
    for button in (panel.emergency_btn, panel.cage_close_btn):
        assert button.isEnabled() is True
        assert button.toolTip() == ""
    assert section.run_button.isEnabled() is False
    assert section.run_button.toolTip() == (
        "Unavailable while an unconfirmed emergency stop is in progress"
    )
    assert tab._hardware_change_blocked_reason() == "an unconfirmed emergency stop is in progress"
    relays.fail_all_off = not result.relays_confirmed_off

    panel._on_emergency_stop_clicked()

    if not result.relays_confirmed_off:
        assert dialogs[-1][:2] == ("critical", "Emergency Stop Failed")
    else:
        assert dialogs[-1][:2] == ("critical", "Emergency Stop")
        assert "delivery worker has not stopped" in dialogs[-1][2]
    assert lock.held_by("emergency")
    assert section.run_button.isEnabled() is False

    relays.fail_all_off = False  # the HAT answers, or the worker has exited
    alive["worker"] = False
    panel._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert section.run_button.isEnabled() is True
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")


@pytest.mark.parametrize(
    "latch, title",
    [("run", "Delivery Worker Did Not Stop"), ("stop", "Error")],
    ids=["a run refused beside a live worker", "a stop that raised"],
)
def test_the_other_latches_leave_close_all_available_to_clear_them(
    relays, lock, dialogs, monkeypatch, system_controller, database_handler, latch, title
):
    """The two other hand-overs to EMERGENCY lower the job flag first, as
    Stop's does: a Run refused beside a live worker, and a Stop that raised,
    so how it ended is not known. A hand-over that came first would leave
    CLOSE ALL RELAYS, the control their dialog says to press, greyed out
    under EMERGENCY with nothing left to refresh it: the hardware would stay
    locked until a restart."""
    from utils import updater  # noqa: PLC0415

    alive = {"worker": latch == "run"}
    monkeypatch.setattr(updater, "_busy_check", lambda: alive["worker"])

    def _stop_raises():
        raise RuntimeError("stop failed")

    section = _real_section(system_controller, database_handler, _stop_raises)
    section.run_program_callback = MagicMock(return_value=False)  # refused: the worker lives
    panel = _settings_tab(system_controller, database_handler, section).priming_widget
    _press_run(section, monkeypatch)
    assert panel.emergency_btn.isEnabled() is False

    if latch == "run":
        section._execute_program(SimpleNamespace(name="AM water"), "Staggered", 0, 1)
    else:
        section.stop_program()

    assert [shown[:2] for shown in dialogs] == [("critical", title)]
    assert section.job_in_progress is False and lock.held_by("emergency")
    for button in (panel.emergency_btn, panel.cage_close_btn):
        assert button.isEnabled() is True
        assert button.toolTip() == ""

    alive["worker"] = False  # the worker has exited
    panel._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")


def test_the_stop_button_stops_a_real_worker_thread_while_close_all_is_refused(
    relays, lock, dialogs, monkeypatch, system_controller, database_handler
):
    """Replaces "a real worker thread is stopped by the real stop sequence"
    (through CLOSE ALL): a thread pulsing a valve, the Stop button's real
    sequence (utils.stop_sequence) and the real Run/Stop section. CLOSE ALL
    RELAYS does nothing while it pulses; after Stop the thread has exited,
    no relay is energised, nothing pulses again and the panel is live."""
    from PyQt5.QtCore import QThread  # noqa: PLC0415
    from utils import stop_sequence, updater  # noqa: PLC0415

    class _Delivery(QThread):
        def __init__(self):
            super().__init__()
            self.cancelled = threading.Event()

        def request_cancel(self):
            self.cancelled.set()

        def run(self):
            while not self.cancelled.wait(0.005):
                relays.set_relays([CAGE], 1)
                relays.set_relays([CAGE], 0)

    worker = _Delivery()
    signals = SimpleNamespace(stop_requested=SimpleNamespace(emit=lambda: None))
    section = _real_section(
        system_controller,
        database_handler,
        lambda: stop_sequence.execute_stop_sequence(relays, worker, worker, signals),
    )
    panel = _settings_tab(system_controller, database_handler, section).priming_widget
    monkeypatch.setattr(updater, "_busy_check", worker.isRunning)
    _press_run(section, monkeypatch)
    worker.start()
    try:
        while not relays.writes:  # let it pulse at least once
            worker.wait(5)

        panel._on_emergency_stop_clicked()
        assert dialogs == [_refusal("CLOSE ALL RELAYS")]
        assert all(ids != ("all",) for ids, _state in relays.trace), "the panel did nothing"

        section.stop_program()

        assert worker.isRunning() is False
        writes = len(relays.writes)
        assert relays.trace[-1] == (("all",), 0)
        assert relays.energized() == set()
        assert lock.is_busy() is False
        assert section.job_in_progress is False
        assert dialogs == [_refusal("CLOSE ALL RELAYS")], "a clean Stop shows no dialog"
        assert panel.emergency_btn.isEnabled() is True
        worker.wait(50)
        assert len(relays.writes) == writes, "nothing pulsed after the stop"
    finally:
        worker.cancelled.set()
        worker.wait(2000)


# --- found by the re-review of the rework ------------------------------------------------------


def test_an_unconfirmed_stop_beside_a_live_worker_says_to_restart_the_pi(
    relays, lock, dialogs, monkeypatch
):
    """RRR refuses to quit while a delivery worker is alive, so "close and
    reopen RRR" is not a way out of that state."""
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)
    panel = _panel(_idle)
    assert lock.try_acquire("schedule")
    _latched_by_stop(lock)
    relays.fail_all_off = True

    panel._on_emergency_stop_clicked()

    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop Failed")
    assert "The schedule's delivery worker has not stopped and may open a valve again." in text
    assert "was stopped" not in text
    assert "restart the Raspberry Pi (RRR will not quit while that worker is alive)" in text
    assert "close and reopen RRR" not in text
    assert lock.held_by("emergency")


@pytest.mark.parametrize("topology", ["shared_manifold", "independent"])
def test_an_unconfirmed_stop_outlives_the_priming_session(relays, lock, dialogs, topology):
    """A second HAT is not answering, so the all-off is not confirmed, while
    the session's own valves (on the first HAT) still switch. Closing them
    ends the session; the hardware must stay locked, because nothing has
    confirmed the other HAT's relays."""
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    panel = PrimingControlWidget({**SETTINGS, "valve_topology": topology}, lambda *_: None)
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(CAGE))
    if topology == "shared_manifold":
        panel._on_open_master_clicked()
    panel._on_open_cage_clicked()
    assert lock.held_by("priming") and panel._model.is_cage_open(CAGE)
    relays.fail_all_off = True

    panel._on_emergency_stop_clicked()

    assert dialogs[-1][:2] == ("critical", "Emergency Stop Failed")
    assert lock.held_by("priming")

    # The operator closes the session's valves the ordinary way.
    if topology == "shared_manifold":
        panel._on_close_master_clicked()
    else:
        panel._on_close_cage_clicked()

    assert relays.energized() == set()
    assert lock.held_by("emergency"), "the session ended; the hardware stays locked"
    assert lock.try_acquire("schedule") is False

    relays.fail_all_off = False  # the other HAT answers; a press is confirmed
    panel._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")

    # From here a session ends the ordinary way again.
    if topology == "shared_manifold":
        panel._on_open_master_clicked()
        assert lock.held_by("priming")
        panel._on_close_master_clicked()
    else:
        panel._on_open_cage_clicked()
        assert lock.held_by("priming")
        panel._on_close_cage_clicked()
    assert lock.is_busy() is False


def test_the_retry_after_an_unconfirmed_stop_builds_a_fresh_relay_handler(
    monkeypatch, fake_relay_handler, lock, dialogs
):
    """A HAT that did not answer when the panel built its relay handler has
    no slot in it. Reseated, it would never be found by that handler, and
    "press CLOSE ALL RELAYS again" could not work."""
    built = []

    def _factory(*_a, **_k):
        handler = type(fake_relay_handler)()
        handler.fail_all_off = not built  # the first one never confirms
        built.append(handler)
        return handler

    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", _factory)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    panel = _panel(_idle)

    panel._on_emergency_stop_clicked()

    assert len(built) == 1
    assert dialogs[-1][:2] == ("critical", "Emergency Stop Failed")
    assert lock.held_by("emergency")

    panel._on_emergency_stop_clicked()  # the HAT has been reseated

    assert len(built) == 2, "a fresh handler, which looks for the HATs again"
    assert built[1].trace == [(("all",), 0)]
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")
    assert lock.is_busy() is False

    panel._on_emergency_stop_clicked()  # a healthy panel keeps its handler

    assert len(built) == 2


def test_the_first_press_after_a_stop_latch_builds_a_fresh_relay_handler(
    monkeypatch, fake_relay_handler, lock, dialogs
):
    """The EMERGENCY hold may come from a Stop, not from this panel: a HAT
    that was missing when the panel built its handler earlier has no slot in
    it, so the first press after the latch looks for the HATs again too."""
    built = []

    def _factory(*_a, **_k):
        handler = type(fake_relay_handler)()
        built.append(handler)
        return handler

    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", _factory)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    panel = _panel(_idle)
    panel._get_relay_handler()  # built earlier, e.g. for priming
    assert lock.try_acquire("schedule")
    _latched_by_stop(lock)

    panel._on_emergency_stop_clicked()

    assert len(built) == 2 and built[1].trace == [(("all",), 0)]
    assert lock.is_busy() is False


def test_a_session_opened_beside_an_abandoned_worker_does_not_keep_the_lock(
    relays, lock, dialogs, monkeypatch
):
    """Defence in depth: should the lock ever be free beside a live delivery
    worker and a priming session be opened, the button ends that session
    (every relay is confirmed off) and holds the hardware for the worker."""
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)
    panel = _panel(_idle)
    panel._on_open_master_clicked()
    assert lock.held_by("priming") and panel._model.is_master_open

    panel._on_emergency_stop_clicked()

    assert not panel._model.is_master_open
    assert lock.held_by("emergency"), "not a priming session with nothing open"
    assert dialogs[-1][:2] == ("critical", "Emergency Stop")
    assert "delivery worker has not stopped" in dialogs[-1][2]


# --- the panel follows Change Relay Hats ---------------------------------------------------------
#
# The panel builds its own relay handler on first use and kept it for the
# session. After Change Relay Hats raised the count, CLOSE ALL RELAYS still
# switched only the HATs of the old count and reported every relay closed.


def _counting_factory(monkeypatch, fake_relay_handler, missing_from=2):
    """RelayHandler stand-in: records each build's HAT count; a build for
    ``missing_from`` HATs or more cannot confirm the all-off (a HAT absent)."""
    built = []

    def _factory(_manager, num_hats=1):
        handler = type(fake_relay_handler)()
        handler.num_hats = num_hats
        handler.fail_all_off = num_hats >= missing_from
        built.append(handler)
        return handler

    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", _factory)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    return built


def test_after_change_relay_hats_close_all_relays_addresses_the_new_count(
    monkeypatch, fake_relay_handler, lock, dialogs
):
    built = _counting_factory(monkeypatch, fake_relay_handler)
    settings = dict(SETTINGS)
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    panel = PrimingControlWidget(settings, lambda *_: None, schedule_running=_idle)
    panel._on_open_master_clicked()  # first use: a handler for one HAT
    panel._on_close_master_clicked()
    assert [h.num_hats for h in built] == [1] and lock.is_busy() is False

    settings["num_hats"] = 2  # Change Relay Hats; the second HAT is not fitted

    panel._on_emergency_stop_clicked()

    assert [h.num_hats for h in built] == [1, 2], "a handler for the new count"
    assert dialogs[-1][:2] == ("critical", "Emergency Stop Failed")
    assert lock.held_by("emergency")


def test_a_valve_command_after_change_relay_hats_uses_the_new_count(
    monkeypatch, fake_relay_handler, lock, dialogs
):
    built = _counting_factory(monkeypatch, fake_relay_handler, missing_from=99)
    settings = dict(SETTINGS)
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    panel = PrimingControlWidget(settings, lambda *_: None)
    panel._on_open_master_clicked()
    panel._on_close_master_clicked()
    old_controller = panel._solenoid_controller

    settings["num_hats"] = 2
    panel._on_open_master_clicked()

    assert [h.num_hats for h in built] == [1, 2]
    assert panel._solenoid_controller is not old_controller
    assert built[1].trace == [((MASTER,), 1)], "the master opened through the new handler"
    panel._on_close_master_clicked()
    assert lock.is_busy() is False


def test_refresh_hardware_lists_the_cages_of_the_new_count(
    monkeypatch, fake_relay_handler, lock, dialogs
):
    built = _counting_factory(monkeypatch, fake_relay_handler, missing_from=99)
    settings = dict(SETTINGS)
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    panel = PrimingControlWidget(settings, lambda *_: None)
    panel._on_emergency_stop_clicked()
    assert panel.cage_selector.count() == 15

    settings["num_hats"] = 2
    settings["cage_relays"] = {}
    panel.refresh_hardware()

    assert panel.cage_selector.count() == 31
    assert panel.cage_selector.findText("Cage 16 (Relay 17)") >= 0
    assert panel._relay_handler is None, "the next use builds a handler for two HATs"
    panel._on_emergency_stop_clicked()
    assert [h.num_hats for h in built] == [1, 2]


def test_a_count_lowered_during_a_session_keeps_the_handler_that_opened_the_valves(
    monkeypatch, fake_relay_handler, lock, dialogs
):
    """The review's case: two HATs, the master and cage 20 (relay 21, on the
    second HAT) open in Priming, and the count drops to one by some way other
    than Change Relay Hats. A one-HAT handler would switch only the first HAT
    and report every relay closed while relay 21 stayed on."""
    built = _counting_factory(monkeypatch, fake_relay_handler, missing_from=99)
    settings = {**SETTINGS, "num_hats": 2}
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    panel = PrimingControlWidget(settings, lambda *_: None, schedule_running=_idle)
    panel._on_open_master_clicked()
    panel.cage_selector.setCurrentIndex(panel.cage_selector.findData(20))
    panel._on_open_cage_clicked()
    assert built[0].energized() == {MASTER, 21} and lock.held_by("priming")

    settings["num_hats"] = 1

    panel._on_emergency_stop_clicked()

    assert [h.num_hats for h in built] == [2], "the handler that opened the valves switched them"
    assert built[0].energized() == set(), "relay 21 on the second HAT is off"
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")
    assert lock.is_busy() is False

    # Nothing is open any more: the next use follows the new count.
    panel._on_open_master_clicked()
    assert [h.num_hats for h in built] == [2, 1]
    panel._on_close_master_clicked()


@pytest.mark.parametrize("state", ["unconfirmed", "master open", "cage open", "nothing"])
def test_a_handler_is_kept_while_a_relay_it_switched_may_be_on(
    monkeypatch, fake_relay_handler, lock, dialogs, state
):
    _counting_factory(monkeypatch, fake_relay_handler, missing_from=99)
    settings = {**SETTINGS, "num_hats": 2}
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    panel = PrimingControlWidget(settings, lambda *_: None)
    old = panel._get_relay_handler()
    assert lock.try_acquire("priming"), "the session's hold alone does not keep it"
    if state == "unconfirmed":
        panel._stop_unconfirmed = True
    elif state == "master open":
        panel._model.set_master_open(True)
    elif state == "cage open":
        # After a Close Master whose cage close did not confirm: the master
        # is closed, the cage may still be open.
        panel._model.set_cage_open(20, True)
    settings["num_hats"] = 1

    kept = panel._get_relay_handler() is old
    assert kept == (state != "nothing")
    lock.force_release()
