"""Priming's CLOSE ALL RELAYS stops a running schedule, and frees the hardware
lock only when it is safe to.

The button used to switch every relay off and force-clear the operation lock,
whatever held it. Pressed while a schedule ran, the schedule carried on and
opened its valves again at its next pulse, and with the lock gone priming and
calibration could start beside it. When the relays were not confirmed off it
cleared the lock all the same, so a schedule could start onto a valve that
might be open.

The lock is now cleared only when every relay is confirmed off and nothing
that can open a valve is still running. Otherwise its holder keeps it, and
when nobody holds it the emergency stop takes it itself.
"""

from __future__ import annotations

import os
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

MASTER = 16
CAGE = 1
SETTINGS = {"num_hats": 1, "global_master_relay_id": MASTER}


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


def _panel(stop_schedule=None):
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    return PrimingControlWidget(dict(SETTINGS), lambda *_: None, stop_schedule=stop_schedule)


# Run does not resume a stopped schedule (a new worker starts every animal
# from zero), so the dialog must not tell the operator to "press Run again".
STOPPED = (
    "All relays have been closed. The running schedule was stopped.\n\n"
    "It does not resume. Run starts the schedule over: a staggered schedule gives every "
    "animal its whole dose again, and an instant schedule skips the delivery times that "
    "have passed. Check what each animal has received before running it again."
)


def _stopper(lock, running=True, relays=None):
    """What Settings hands the panel: stops the schedule the way Stop does
    (which releases the schedule's hold) and says whether one was running.
    Each call records how many relay writes had got through by then."""
    calls = []

    def stop():
        calls.append(len(relays.writes) if relays is not None else 1)
        if running:
            lock.release("schedule")
        return running

    return stop, calls


def test_close_all_relays_stops_a_running_schedule(relays, lock, dialogs):
    stop, calls = _stopper(lock, relays=relays)
    panel = _panel(stop)
    assert lock.try_acquire("schedule")

    panel._on_emergency_stop_clicked()

    assert calls == [1], "the schedule was stopped once, after the first all-off"
    assert relays.trace == [(("all",), 0), (("all",), 0)], "off at once, and again after the stop"
    assert lock.is_busy() is False
    assert dialogs == [("information", "Emergency Stop", STOPPED)]


def test_with_nothing_running_it_is_unchanged(relays, lock, dialogs):
    stop, calls = _stopper(lock, running=False)
    panel = _panel(stop)
    panel._on_open_master_clicked()
    assert lock.held_by("priming")

    panel._on_emergency_stop_clicked()

    assert calls == [1], "asked, and there was no schedule to stop"
    assert relays.trace[-1] == (("all",), 0) and relays.trace.count((("all",), 0)) == 1
    assert relays.energized() == set()
    assert lock.is_busy() is False
    assert dialogs == [("information", "Emergency Stop", "All relays have been closed.")]


def test_a_schedule_it_cannot_stop_keeps_its_hold(relays, lock, dialogs):
    """A panel built without the stop callback must not free a schedule's lock."""
    panel = _panel()
    assert lock.try_acquire("schedule")

    panel._on_emergency_stop_clicked()

    assert relays.trace == [(("all",), 0)]
    assert lock.held_by("schedule"), "priming and calibration stay locked out"
    ((kind, _title, text),) = dialogs
    assert kind == "warning" and "Press Stop to end it" in text


def test_a_worker_still_running_keeps_the_hold(relays, lock, dialogs, monkeypatch):
    """The callback found no job to stop, yet a delivery worker is alive. The
    Stop button is greyed out in that state (no job in progress), so the
    dialog must not send the operator to it."""
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)
    stop, _calls = _stopper(lock, running=False)
    panel = _panel(stop)
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
    stop, _calls = _stopper(lock, running=False)
    panel = _panel(stop)
    assert lock.try_acquire("schedule")

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


def test_relays_not_confirmed_off_still_stop_the_schedule(relays, lock, dialogs):
    """The Stop path frees the schedule's hold; with a valve possibly open,
    the emergency stop takes the lock so nothing can start onto it."""
    stop, calls = _stopper(lock)
    panel = _panel(stop)
    assert lock.try_acquire("schedule")
    relays.fail_all_off = True

    panel._on_emergency_stop_clicked()

    assert calls == [1]
    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop Failed")
    assert "Disconnect the valve power supply now" in text
    assert "\n\nThe running schedule was stopped.\n\n" in text
    assert text.endswith(
        "Run, priming and calibration stay unavailable until every relay is confirmed off. "
        "Once the relay HAT answers, press CLOSE ALL RELAYS again; or close and reopen RRR."
    )
    assert lock.held_by("emergency")
    assert lock.active_label() == "an unconfirmed emergency stop"
    assert lock.try_acquire("schedule") is False, "Run cannot start onto a valve that may be open"

    relays.fail_all_off = False  # the HAT answers again; the operator presses it again
    panel._stop_schedule, _ = _stopper(lock, running=False)  # no schedule runs any more
    panel._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")


def test_the_all_off_after_the_stop_decides(relays, lock, dialogs):
    """The HAT stops answering while the schedule is being stopped: the first
    all-off was confirmed, the one after the stop is not."""
    calls = []

    def stop():
        calls.append(1)
        lock.release("schedule")
        relays.fail_all_off = True
        return True

    panel = _panel(stop)
    assert lock.try_acquire("schedule")

    panel._on_emergency_stop_clicked()

    assert calls == [1]
    assert dialogs[-1][:2] == ("critical", "Emergency Stop Failed")
    assert lock.held_by("emergency")


def test_relays_not_confirmed_off_with_nothing_running_lock_the_hardware(relays, lock, dialogs):
    stop, _calls = _stopper(lock, running=False)
    panel = _panel(stop)
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


def test_a_worker_that_outlives_the_stop_is_not_reported_stopped(
    relays, lock, dialogs, monkeypatch
):
    """The Stop path abandons a worker thread that will not exit, and still
    releases the schedule's hold. The emergency stop must not call that
    stopped, nor leave the lock free beside a worker that can pulse again."""
    from utils import updater  # noqa: PLC0415

    alive = {"worker": True}
    monkeypatch.setattr(updater, "_busy_check", lambda: alive["worker"])
    stop, _calls = _stopper(lock)
    panel = _panel(stop)
    assert lock.try_acquire("schedule")

    panel._on_emergency_stop_clicked()

    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop")
    assert "delivery worker has not stopped" in text
    assert "was stopped" not in text
    assert lock.held_by("emergency")
    assert lock.try_acquire("priming") is False

    # Pressed again, as the dialog says, with the worker still alive: no job
    # is in progress any more, so Stop is greyed out. The same message comes
    # back, and it says what to do then.
    panel._stop_schedule, _ = _stopper(lock, running=False)
    panel._on_emergency_stop_clicked()

    assert dialogs[-1][:2] == ("critical", "Emergency Stop")
    assert "delivery worker has not stopped" in dialogs[-1][2]
    assert "disconnect the valve power supply and restart the Raspberry Pi" in dialogs[-1][2]
    assert "Press Stop" not in dialogs[-1][2]
    assert lock.held_by("emergency")

    alive["worker"] = False  # it exits; the operator presses the button again
    panel._stop_schedule, _ = _stopper(lock, running=False)
    panel._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")


def test_a_calibration_hold_is_not_freed(relays, lock, dialogs):
    """Its wizard is modal, so the button should be out of reach while a
    calibration pulses. A hold seen here is not known to be stale: Esc once
    closed the wizard and left its worker pulsing."""
    stop, _calls = _stopper(lock, running=False)
    panel = _panel(stop)
    assert lock.try_acquire("calibration")

    panel._on_emergency_stop_clicked()

    assert relays.trace == [(("all",), 0)]
    assert lock.held_by("calibration"), "a schedule cannot start beside a calibration"
    ((kind, title, text),) = dialogs
    assert (kind, title) == ("warning", "Emergency Stop")
    assert "a calibration holds the hardware" in text
    assert "close and reopen RRR" in text


@pytest.mark.parametrize("fault", ["handler cannot be built", "all-off raises"])
def test_a_panel_that_cannot_switch_the_relays_still_stops_the_schedule(
    monkeypatch, fake_relay_handler, lock, dialogs, fault
):
    """The schedule has a relay handler of its own: the Stop path can switch
    the relays off even when the panel's handler cannot."""
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
    stop, calls = _stopper(lock)
    panel = _panel(stop)
    assert lock.try_acquire("schedule")

    panel._on_emergency_stop_clicked()

    assert calls == [1], "the schedule was stopped"
    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop Failed"), "one dialog, after the stop"
    assert "The running schedule was stopped." in text
    assert lock.held_by("emergency")


def test_a_stop_callback_that_raises_does_not_break_the_emergency_stop(relays, lock, dialogs):
    def broken():
        raise RuntimeError("stop failed")

    panel = _panel(broken)
    panel._on_open_master_clicked()

    panel._on_emergency_stop_clicked()

    assert relays.energized() == set()
    assert lock.is_busy() is False
    assert dialogs[-1][:2] == ("information", "Emergency Stop")


# --- the Settings tab hands the panel the Stop button's own path ---------------------------


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


def test_settings_stops_a_running_schedule_through_the_stop_button_path(
    relays, system_controller, database_handler
):
    run_stop = SimpleNamespace(job_in_progress=True, stop_program=MagicMock())
    tab = _settings_tab(system_controller, database_handler, run_stop)

    assert tab.priming_widget._stop_schedule == tab._stop_running_schedule
    assert tab._stop_running_schedule() is True
    run_stop.stop_program.assert_called_once_with()


def test_settings_reports_no_schedule_when_none_runs(relays, system_controller, database_handler):
    run_stop = SimpleNamespace(job_in_progress=False, stop_program=MagicMock())
    tab = _settings_tab(system_controller, database_handler, run_stop)
    assert tab._stop_running_schedule() is False
    run_stop.stop_program.assert_not_called()

    assert _settings_tab(system_controller, database_handler, None)._stop_running_schedule() is False


def test_the_whole_path_with_the_real_run_stop_section(
    relays, lock, dialogs, system_controller, database_handler
):
    """Settings tab, Priming panel and the real Run/Stop section together: the
    emergency stop runs the Stop button's flow, which calls the stop sequence
    and releases the schedule's hold itself."""
    from ui.run_stop_section import RunStopSection  # noqa: PLC0415

    stops = []
    section = RunStopSection(
        MagicMock(),
        lambda: stops.append(1) or True,  # main.stop_program
        MagicMock(),
        system_controller=system_controller,
        database_handler=database_handler,
    )
    tab = _settings_tab(system_controller, database_handler, section)
    assert lock.try_acquire("schedule")  # as Run does
    section.job_in_progress = True

    tab.priming_widget._on_emergency_stop_clicked()

    assert stops == [1], "the stop sequence ran once"
    assert section.job_in_progress is False
    assert lock.is_busy() is False
    assert relays.trace == [(("all",), 0), (("all",), 0)]
    assert dialogs[-1] == ("information", "Emergency Stop", STOPPED)


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


def test_the_real_stop_path_with_a_worker_that_does_not_exit(
    relays, lock, dialogs, monkeypatch, system_controller, database_handler
):
    """The Stop button's flow releases the schedule's hold whether or not the
    worker thread exited. The emergency stop then holds the lock itself, and
    Run stays greyed out."""
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)  # the thread is still alive
    section = _real_section(system_controller, database_handler, lambda: True)
    tab = _settings_tab(system_controller, database_handler, section)
    assert lock.try_acquire("schedule")  # as Run does
    section.job_in_progress = True

    tab.priming_widget._on_emergency_stop_clicked()

    assert section.job_in_progress is False
    assert dialogs[-1][:2] == ("critical", "Emergency Stop")
    assert "delivery worker has not stopped" in dialogs[-1][2]
    assert lock.held_by("emergency")
    assert section.run_button.isEnabled() is False
    assert section.run_button.toolTip() == (
        "Unavailable while an unconfirmed emergency stop is in progress"
    )


def test_an_unconfirmed_stop_greys_out_run_until_it_is_confirmed(
    relays, lock, dialogs, system_controller, database_handler
):
    section = _real_section(system_controller, database_handler, lambda: False)
    tab = _settings_tab(system_controller, database_handler, section)
    assert lock.try_acquire("schedule")
    section.job_in_progress = True
    relays.fail_all_off = True

    tab.priming_widget._on_emergency_stop_clicked()

    assert dialogs[-1][:2] == ("critical", "Emergency Stop Failed")
    assert lock.held_by("emergency")
    assert section.run_button.isEnabled() is False
    assert "an unconfirmed emergency stop" in section.run_button.toolTip()
    assert tab._hardware_change_blocked_reason() == "an unconfirmed emergency stop is in progress"

    relays.fail_all_off = False
    tab.priming_widget._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert section.run_button.isEnabled() is True
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")


def test_a_real_worker_thread_is_stopped_by_the_real_stop_sequence(
    relays, lock, dialogs, monkeypatch, system_controller, database_handler
):
    """A thread pulsing a valve, the Stop button's real sequence
    (utils.stop_sequence) and the real Run/Stop section: after the button the
    thread has exited, no relay is energised and nothing pulses again."""
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
    tab = _settings_tab(system_controller, database_handler, section)
    monkeypatch.setattr(updater, "_busy_check", worker.isRunning)
    assert lock.try_acquire("schedule")  # as Run does
    section.job_in_progress = True
    worker.start()
    try:
        while not relays.writes:  # let it pulse at least once
            worker.wait(5)

        tab.priming_widget._on_emergency_stop_clicked()

        assert worker.isRunning() is False
        writes = len(relays.writes)
        assert relays.trace[-1] == (("all",), 0)
        assert relays.energized() == set()
        assert lock.is_busy() is False
        assert section.job_in_progress is False
        assert dialogs[-1] == ("information", "Emergency Stop", STOPPED)
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
    stop, _calls = _stopper(lock)
    panel = _panel(stop)
    assert lock.try_acquire("schedule")
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
    stop, _calls = _stopper(lock, running=False)
    panel = _panel(stop)

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


def test_a_session_opened_beside_an_abandoned_worker_does_not_keep_the_lock(
    relays, lock, dialogs, monkeypatch
):
    """An ordinary Stop abandoned its worker and freed the lock; the operator
    then opened a priming session. The button ends that session (every relay
    is confirmed off) and holds the hardware for the worker that is alive."""
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)
    stop, _calls = _stopper(lock, running=False)
    panel = _panel(stop)
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
    stop, _calls = _stopper(lock, running=False)
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    panel = PrimingControlWidget(settings, lambda *_: None, stop_schedule=stop)
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
    stop, _calls = _stopper(lock, running=False)
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    panel = PrimingControlWidget(settings, lambda *_: None, stop_schedule=stop)
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
