"""The Stop button keeps the hardware locked when it cannot confirm it is safe.

Stop used to release the schedule's hold on the hardware whatever the stop
sequence reported: with a relay HAT that did not confirm OFF, or a delivery
worker thread abandoned still running, Run, priming and calibration were
available again at once. It showed two dialogs for unconfirmed relays
(Relays Not Confirmed Off, then a vague Warning) and none for a worker that
did not stop. Run could then start a second worker beside one still running,
and a Stop pressed while Run was still "Starting..." let the start go ahead.

Now the hold passes to EMERGENCY until CLOSE ALL RELAYS confirms every relay
off (or RRR restarts), and one dialog says what happened and what to do. A
Stop that never reached the stop sequence leaves the job and Stop available.
Run refuses to start beside a live worker, and holds the hardware the same
way; a Stop cancels a start Run has queued.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from utils.stop_sequence import StopResult

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# The QApplication this module uses, kept for the rest of the session. When a
# QApplication is destroyed, PyQt5 deletes every QObject without a parent,
# main.control_signals and any SystemController a later test holds included.
_QAPP = []


@pytest.fixture(scope="module", autouse=True)
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


def _section(system_controller, database_handler, stop=None, run=None):
    from ui.run_stop_section import RunStopSection  # noqa: PLC0415

    login = MagicMock()
    login.is_logged_in.return_value = True
    return RunStopSection(
        run or MagicMock(return_value=True),  # main.run_program
        stop or (lambda: StopResult(True, True)),  # main.stop_program
        MagicMock(),
        system_controller=system_controller,
        database_handler=database_handler,
        login_system=login,
    )


def _running(section, lock):
    assert lock.try_acquire("schedule")  # as Run does
    section.job_in_progress = True
    section.update_button_states()


RELAYS_TEXT = (
    "The schedule stopped, but not every relay HAT confirmed OFF, so a valve may still be "
    "OPEN.\n\nDisconnect the valve power supply now, then check the relay HAT and its I²C "
    "connection.\n\nRun, priming and calibration stay unavailable until every relay is "
    "confirmed off. Once the relay HAT answers, press CLOSE ALL RELAYS in Settings > "
    "Priming; or close and reopen RRR."
)
WORKER_TEXT = (
    "All relays are off, but the schedule's delivery worker has not stopped and may open a "
    "valve again.\n\nRun, priming and calibration stay unavailable while it may still run. "
    "Wait a few seconds, then press CLOSE ALL RELAYS in Settings > Priming. If it says the "
    "worker has still not stopped, disconnect the valve power supply and restart the "
    "Raspberry Pi (RRR will not quit while that worker is alive)."
)
BOTH_TEXT = (
    "The schedule's delivery worker has not stopped and may open a valve again, and not "
    "every relay HAT confirmed OFF, so a valve may still be OPEN.\n\nDisconnect the valve "
    "power supply now, then check the relay HAT and its I²C connection.\n\nRun, priming and "
    "calibration stay unavailable until every relay is confirmed off and the worker has "
    "stopped. Once the relay HAT answers, press CLOSE ALL RELAYS in Settings > Priming. If "
    "the worker still has not stopped, restart the Raspberry Pi (RRR will not quit while "
    "that worker is alive)."
)


def test_a_clean_stop_frees_the_hardware_without_a_dialog(
    lock, dialogs, system_controller, database_handler
):
    section = _section(system_controller, database_handler)
    _running(section, lock)

    section.stop_program()

    assert dialogs == []
    assert lock.is_busy() is False
    assert section.job_in_progress is False
    assert section.run_button.isEnabled() is True


@pytest.mark.parametrize(
    "result, title, text",
    [
        (StopResult(False, True), "Relays Not Confirmed Off", RELAYS_TEXT),
        (StopResult(True, False), "Delivery Worker Did Not Stop", WORKER_TEXT),
        (StopResult(False, False), "Relays Not Confirmed Off", BOTH_TEXT),
    ],
    ids=["relays", "worker", "both"],
)
def test_an_unsafe_stop_latches_the_hardware_and_says_so_once(
    lock, dialogs, system_controller, database_handler, result, title, text
):
    section = _section(system_controller, database_handler, stop=lambda: result)
    _running(section, lock)
    # Every change of holder during the Stop. reset_ui releases SCHEDULE, so a
    # latch taken after it would leave the lock free in between, and priming
    # or calibration could start there.
    holders = []
    lock.state_changed.connect(lambda: holders.append(lock.active_operation()))

    section.stop_program()

    assert dialogs == [("critical", title, text)], "one dialog, not two"
    assert lock.held_by("emergency")
    assert holders == ["emergency"], "SCHEDULE handed to EMERGENCY in one step, before reset_ui"
    assert section.job_in_progress is False
    for button in (section.run_button, section.relay_hats_button, section.stop_button):
        assert button.isEnabled() is False
    assert section.run_button.toolTip() == (
        "Unavailable while an unconfirmed emergency stop is in progress"
    )
    assert lock.try_acquire("priming") is False and lock.try_acquire("calibration") is False


def test_the_latch_outlives_the_workers_queued_cleanup(
    lock, dialogs, system_controller, database_handler
):
    """main.cleanup and _on_finished call reset_ui, which releases SCHEDULE;
    they run in the dialog's event loop, after the hand-over."""
    section = _section(system_controller, database_handler, stop=lambda: StopResult(False, True))
    _running(section, lock)

    section.stop_program()
    section.reset_ui()

    assert lock.held_by("emergency")
    assert section.run_button.isEnabled() is False


def test_a_confirmed_close_all_relays_clears_the_latch(
    lock, dialogs, monkeypatch, fake_relay_handler, system_controller, database_handler
):
    monkeypatch.setattr("gpio.gpio_handler.RelayHandler", lambda *a, **k: fake_relay_handler)
    monkeypatch.setattr("models.relay_unit_manager.RelayUnitManager", MagicMock())
    from ui.PrimingControlWidget import PrimingControlWidget  # noqa: PLC0415

    section = _section(system_controller, database_handler, stop=lambda: StopResult(False, True))
    panel = PrimingControlWidget({"num_hats": 1, "global_master_relay_id": 16}, lambda *_: None)
    _running(section, lock)
    section.stop_program()
    assert lock.held_by("emergency")

    panel._on_emergency_stop_clicked()

    assert lock.is_busy() is False
    assert section.run_button.isEnabled() is True
    assert dialogs[-1] == ("information", "Emergency Stop", "All relays have been closed.")


def test_an_error_during_stop_keeps_the_hardware_locked(
    lock, dialogs, system_controller, database_handler
):
    def broken():
        raise RuntimeError("boom")

    section = _section(system_controller, database_handler, stop=broken)
    _running(section, lock)

    section.stop_program()

    assert dialogs == [
        (
            "critical",
            "Error",
            "Failed to stop schedule: boom\n\nRun, priming and calibration stay unavailable "
            "until CLOSE ALL RELAYS in Settings > Priming confirms every relay off; or close "
            "and reopen RRR.",
        )
    ]
    assert lock.held_by("emergency")
    assert section.job_in_progress is False


def test_a_stop_that_fails_after_the_sequence_latches_before_its_dialog(
    lock, monkeypatch, system_controller, database_handler
):
    """The worker's queued cleanup can run inside the Error dialog's event
    loop and calls reset_ui, which releases SCHEDULE: the hand-over to
    EMERGENCY must already have happened when that dialog opens."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    stops = []

    def sequence_then_error():
        stops.append(1)  # the stop sequence ran
        raise RuntimeError("boom")

    section = _section(system_controller, database_handler, stop=sequence_then_error)
    _running(section, lock)
    opened = []

    def _critical(*args, **_kwargs):
        opened.append((args[1], lock.held_by("emergency")))
        section.reset_ui()  # what the worker's queued cleanup does in there

    monkeypatch.setattr(QMessageBox, "critical", staticmethod(_critical))

    section.stop_program()

    assert stops == [1]
    assert opened == [("Error", True)], "latched before the dialog opened"
    assert lock.held_by("emergency")
    assert section.run_button.isEnabled() is False


def test_a_stop_that_did_not_run_leaves_stop_available(
    lock, dialogs, monkeypatch, system_controller, database_handler
):
    """Nothing was stopped: the job, its hold and the Stop button stay."""
    section = _section(system_controller, database_handler)
    _running(section, lock)

    def _broken():
        raise RuntimeError("boom")

    monkeypatch.setattr(section, "_execute_stop", _broken)

    section.stop_program()

    assert dialogs == [
        (
            "critical",
            "Error",
            "Failed to stop schedule: boom\n\nThe schedule may still be running: press Stop "
            "again.",
        )
    ]
    assert section.job_in_progress is True
    assert lock.held_by("schedule")
    assert section.stop_button.isEnabled() is True
    assert section.stop_button.text() == "Stop"


def test_a_failure_before_the_stop_callback_keeps_the_job_and_stop(
    lock, dialogs, monkeypatch, system_controller, database_handler
):
    """The Stopping box could not be shown: the stop sequence never ran, so
    nothing was stopped and Stop must stay available, not greyed beside a
    schedule that may still be running."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    stops = []
    section = _section(
        system_controller, database_handler, stop=lambda: stops.append(1) or StopResult(True, True)
    )
    _running(section, lock)

    def _show_fails(_box):
        raise RuntimeError("show failed")

    monkeypatch.setattr(QMessageBox, "show", _show_fails)

    section.stop_program()

    assert stops == [], "the stop sequence never ran"
    assert dialogs == [
        (
            "critical",
            "Error",
            "Failed to stop schedule: show failed\n\nThe schedule may still be running: press "
            "Stop again.",
        )
    ]
    assert section.job_in_progress is True
    assert lock.held_by("schedule")
    assert section.stop_button.isEnabled() is True
    assert section.stop_button.text() == "Stop"


# --- Run when no worker could be started ------------------------------------------------


NOT_STARTED = (
    "warning",
    "Schedule not started",
    "This schedule was not started. RRR could not start its delivery worker; the Terminal tab "
    "shows why. Press Run to try again.",
)
WORKER_AT_RUN_TEXT = (
    "The previous schedule's delivery worker has not stopped and may open a valve again, so "
    "this schedule was not started.\n\nRun, priming and calibration stay unavailable while it "
    "may still run. Wait a few seconds, then press CLOSE ALL RELAYS in Settings > Priming. If "
    "it says the worker has still not stopped, disconnect the valve power supply and restart "
    "the Raspberry Pi (RRR will not quit while that worker is alive)."
)


def test_a_run_that_did_not_start_is_not_shown_running(
    lock, dialogs, system_controller, database_handler
):
    run = MagicMock(return_value=False)
    section = _section(system_controller, database_handler, run=run)
    _running(section, lock)

    section._execute_program(SimpleNamespace(name="t"), "Staggered", 0.0, 1.0)

    run.assert_called_once()
    assert dialogs == [NOT_STARTED]
    assert section.run_button.text() == "Run"
    assert section.job_in_progress is False
    assert lock.is_busy() is False


def test_a_run_that_started_shows_running(lock, dialogs, system_controller, database_handler):
    section = _section(system_controller, database_handler)
    _running(section, lock)

    section._execute_program(SimpleNamespace(name="t"), "Staggered", 0.0, 1.0)

    assert dialogs == []
    assert section.run_button.text() == "Running"
    assert lock.held_by("schedule")


def test_a_run_refused_beside_a_live_worker_latches_and_says_so(
    lock, monkeypatch, system_controller, database_handler
):
    """main.run_program refuses while the previous schedule's worker thread
    is alive. That worker may still open a valve, so the hardware is held as
    after a Stop that could not end it, not freed for priming and
    calibration; and held before the dialog opens."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)  # the old thread is alive
    opened = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        staticmethod(lambda *a, **k: opened.append((a[1], a[2], lock.active_operation()))),
    )
    section = _section(system_controller, database_handler, run=MagicMock(return_value=False))
    _running(section, lock)

    section._execute_program(SimpleNamespace(name="t"), "Staggered", 0.0, 1.0)

    assert opened == [("Delivery Worker Did Not Stop", WORKER_AT_RUN_TEXT, "emergency")]
    assert lock.held_by("emergency")
    assert section.job_in_progress is False
    assert section.run_button.text() == "Run"
    assert section.run_button.isEnabled() is False
    assert section.run_button.toolTip() == (
        "Unavailable while an unconfirmed emergency stop is in progress"
    )
    assert lock.try_acquire("priming") is False and lock.try_acquire("calibration") is False


# --- Stop while Run is still "Starting..." ------------------------------------------------


def _load_a_schedule(section, monkeypatch, database_handler):
    """A staggered schedule an hour ahead in the queue, ready to start (the
    calibration gate is test_calibration_gate.py's)."""
    now = datetime.now()
    section.schedule_drop_area.current_schedule = SimpleNamespace(
        name="t",
        schedule_id=1,
        delivery_mode="staggered",
        water_volume=0.6,
        animals=[1],
        relay_unit_assignments={"1": 1},
        desired_water_outputs={"1": 0.6},
        start_time=(now + timedelta(hours=1)).isoformat(),
        end_time=(now + timedelta(hours=2)).isoformat(),
    )
    monkeypatch.setattr(
        database_handler, "get_schedule_staggered_windows", lambda _sid: [{"window": 1}]
    )
    monkeypatch.setattr(section, "_passes_calibration_gate", lambda *_a: True)
    monkeypatch.setattr(section, "show_progress_tracker", lambda _schedule: None)


def test_run_starts_the_schedule_it_queued(
    lock, dialogs, monkeypatch, system_controller, database_handler
):
    """Unchanged: with no Stop, the start Run queues goes ahead."""
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    run = MagicMock(return_value=True)
    section = _section(system_controller, database_handler, run=run)
    _load_a_schedule(section, monkeypatch, database_handler)

    section.run_program()
    QApplication.processEvents()

    run.assert_called_once()
    assert dialogs == []
    assert section.run_button.text() == "Running"
    assert lock.held_by("schedule")


@pytest.mark.parametrize("when", ["before", "inside"])
def test_a_stop_during_starting_cancels_the_start(
    lock, dialogs, monkeypatch, capsys, system_controller, database_handler, when
):
    """Run queues the start; a Stop pressed before it runs cancels it. That
    includes a start run inside the Stop: the Stopping dialog pumps events,
    and job_in_progress is still True in there. Started anyway, the worker
    would run with the lock free and Stop greyed, and nothing could end it."""
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    def stop():
        if when == "inside":
            QApplication.processEvents()  # as main._show_stopping_dialog does
        return StopResult(True, True)

    run = MagicMock(return_value=True)
    section = _section(system_controller, database_handler, stop=stop, run=run)
    _load_a_schedule(section, monkeypatch, database_handler)

    section.run_program()  # the Run click: job, lock, the start queued
    assert section.job_in_progress is True and lock.held_by("schedule")
    section.stop_program()  # dispatched before the queued start
    QApplication.processEvents()

    run.assert_not_called()
    assert lock.is_busy() is False
    assert section.job_in_progress is False
    assert section.run_button.text() == "Run"
    assert (
        "[RUN] Start cancelled: Stop was pressed before the schedule started"
        in capsys.readouterr().out
    )


# --- the latch, as the Settings tab explains it -------------------------------------------


@pytest.mark.parametrize("change", ["mode", "topology"])
def test_a_hardware_change_refused_under_the_latch_names_close_all(
    lock, dialogs, system_controller, database_handler, change
):
    """Waiting never clears the latch: the refusal says what does."""
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    tab = SettingsTab(
        system_controller,
        login_system=login,
        run_stop_section=None,
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
    )
    title, what = {
        "mode": ("Cannot Change Mode", "The hardware mode"),
        "topology": ("Cannot Change Topology", "The valve topology"),
    }[change]

    def attempt():
        if change == "mode":
            tab.hardware_mode_combo.setCurrentIndex(tab.hardware_mode_combo.findData("pump"))
        else:
            tab._on_valve_topology_chosen("independent")
        return dialogs[-1]

    lock.hold_until_safe()  # a Stop or CLOSE ALL RELAYS that could not confirm it is safe
    assert attempt() == (
        "warning",
        title,
        f"{what} cannot change while an unconfirmed emergency stop is in progress.\n\n"
        "Once every relay HAT answers, press CLOSE ALL RELAYS in Settings > Priming, or close "
        "and reopen RRR; then try again.",
    )

    lock.force_release()
    assert lock.try_acquire("priming")
    assert attempt() == (
        "warning",
        title,
        f"{what} cannot change while a priming session is in progress.\n\n"
        "Wait for it to finish, then try again.",
    ), "unchanged for an operation that ends by itself"


# --- through main.run_program, main.cleanup and main.stop_program --------------------------


@pytest.fixture
def main_module(monkeypatch):
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # main installs its own on import
    import main  # noqa: PLC0415

    monkeypatch.setattr(main, "system_controller", SimpleNamespace(settings={}), raising=False)
    monkeypatch.setattr(main, "database_handler", MagicMock(), raising=False)
    monkeypatch.setattr(main, "controller", SimpleNamespace(pump_controller=None), raising=False)
    monkeypatch.setattr(main, "notification_handler", None, raising=False)
    return main


def _staggered():
    return SimpleNamespace(
        name="t",
        schedule_id=1,
        water_volume=0.6,
        relay_unit_assignments={"1": 1},
        desired_water_outputs={"1": 0.6},
    )


def test_run_program_refuses_while_the_previous_worker_thread_runs(
    main_module, monkeypatch, capsys
):
    alive = MagicMock()
    alive.isRunning.return_value = True
    alive.wait.return_value = False
    old_worker = object()
    monkeypatch.setattr(main_module, "thread", alive)
    monkeypatch.setattr(main_module, "worker", old_worker)

    assert main_module.run_program(_staggered(), "Staggered", 0.0, 1.0) is False

    alive.wait.assert_called_once_with(5000)
    assert main_module.thread is alive, "a running QThread is never dropped"
    assert main_module.worker is old_worker
    assert (
        "[RUN] Refused: the previous schedule's delivery worker is still running"
        in capsys.readouterr().out
    )


def test_run_program_reports_a_failed_start(main_module, monkeypatch):
    """system_controller must be a QObject: the start fails, and says so."""
    monkeypatch.setattr(main_module, "thread", None)
    monkeypatch.setattr(main_module, "worker", None)

    assert main_module.run_program(_staggered(), "Staggered", 0.0, 1.0) is False


def test_cleanup_keeps_a_thread_that_is_still_running(main_module, monkeypatch, capsys):
    """Dropping the last reference to a running QThread can abort RRR, and
    without it _schedule_is_running() reports idle beside a live worker:
    Run, an update and quitting would no longer be refused."""
    alive = MagicMock()
    alive.isRunning.return_value = True
    alive.wait.return_value = False
    monkeypatch.setattr(main_module, "thread", alive)
    monkeypatch.setattr(main_module, "worker", None)
    monkeypatch.setattr(main_module, "relay_handler", None, raising=False)
    monkeypatch.setattr(main_module, "gui", None, raising=False)

    main_module.cleanup()

    alive.wait.assert_called_once_with(5000)
    assert main_module.thread is alive
    assert main_module._schedule_is_running() is True
    assert (
        "[CLEANUP] The delivery worker thread is still running; keeping it"
        in capsys.readouterr().out
    )

    alive.isRunning.return_value = False  # it has exited: the next cleanup lets it go
    main_module.cleanup()
    assert main_module.thread is None


def test_stop_program_passes_the_result_on(main_module, monkeypatch):
    from utils import stop_sequence  # noqa: PLC0415

    handler = MagicMock()
    handler.set_all_relays.return_value = False
    monkeypatch.setattr(main_module, "relay_handler", handler, raising=False)
    monkeypatch.setattr(main_module, "worker", None)
    monkeypatch.setattr(main_module, "thread", None)
    monkeypatch.setattr(main_module, "_show_stopping_dialog", lambda: None)

    result = main_module.stop_program()

    assert result == stop_sequence.StopResult(relays_confirmed_off=False, worker_exited=True)


def test_the_real_stop_keeps_the_latch_through_the_workers_queued_cleanup(
    lock, monkeypatch, main_module, fake_relay_handler, system_controller, database_handler
):
    """main.stop_program, a worker thread that finishes when stopped, and the
    real main.cleanup, connected as main.run_program connects it: queued to
    the GUI thread, cleanup runs inside the Stop dialog's event loop and
    calls reset_ui, after the hand-over."""
    import threading  # noqa: PLC0415

    from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot  # noqa: PLC0415
    from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: PLC0415

    class _Worker(QObject):
        finished = pyqtSignal()

        def __init__(self):
            super().__init__()
            self.cancelled = threading.Event()
            self._is_running = True

        def request_cancel(self):
            self.cancelled.set()

        @pyqtSlot()
        def run(self):
            self.cancelled.wait(5)  # a delivery, until Stop cancels it

        @pyqtSlot()
        def stop(self):
            self._is_running = False
            self.finished.emit()

    shown = []

    def _critical(*args, **_kwargs):
        opened_with = lock.active_operation()
        QApplication.processEvents()  # what the dialog's own event loop does
        shown.append((args[1], opened_with, main_module.worker is None))

    monkeypatch.setattr(QMessageBox, "critical", staticmethod(_critical))
    fake_relay_handler.fail_all_off = True
    thread, worker = QThread(), _Worker()
    worker.moveToThread(thread)
    worker.finished.connect(thread.quit, Qt.DirectConnection)
    worker.finished.connect(main_module.cleanup)
    # A fresh one: main's module-level instance does not outlive another test
    # module's QApplication.
    signals = main_module.ControlSignals()
    monkeypatch.setattr(main_module, "control_signals", signals)
    signals.stop_requested.connect(worker.stop, Qt.QueuedConnection)
    thread.started.connect(worker.run)
    section = _section(system_controller, database_handler, stop=main_module.stop_program)
    monkeypatch.setattr(main_module, "gui", SimpleNamespace(run_stop_section=section), raising=False)
    monkeypatch.setattr(main_module, "relay_handler", fake_relay_handler, raising=False)
    monkeypatch.setattr(main_module, "_show_stopping_dialog", lambda: None)
    monkeypatch.setattr(main_module, "worker", worker)
    monkeypatch.setattr(main_module, "thread", thread)
    _running(section, lock)
    thread.start()
    try:
        section.stop_program()

        assert shown == [("Relays Not Confirmed Off", "emergency", True)], (
            "one dialog, opened with the hardware latched; cleanup ran inside it"
        )
        assert main_module.worker is None and main_module.thread is None
        assert lock.held_by("emergency")
        assert section.run_button.isEnabled() is False
    finally:
        worker.cancelled.set()
        thread.wait(2000)
