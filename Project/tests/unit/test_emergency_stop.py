"""Priming's CLOSE ALL RELAYS stops a running schedule, and frees the hardware
lock only when it is safe to.

The button used to switch every relay off and force-clear the operation lock,
whatever held it. Pressed while a schedule ran, the schedule carried on and
opened its valves again at its next pulse, and with the lock gone priming and
calibration could start beside it. When the relays were not confirmed off it
cleared the lock all the same, so a schedule could start onto a valve that
might be open.
"""

from __future__ import annotations

import os
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


def _stopper(lock, running=True):
    """What Settings hands the panel: stops the schedule the way Stop does
    (which releases the schedule's hold) and says whether one was running."""
    calls = []

    def stop():
        calls.append(1)
        if running:
            lock.release("schedule")
        return running

    return stop, calls


def test_close_all_relays_stops_a_running_schedule(relays, lock, dialogs):
    stop, calls = _stopper(lock)
    panel = _panel(stop)
    assert lock.try_acquire("schedule")

    panel._on_emergency_stop_clicked()

    assert calls == [1], "the schedule was stopped, once"
    assert relays.trace == [(("all",), 0), (("all",), 0)], "off at once, and again after the stop"
    assert lock.is_busy() is False
    assert dialogs == [
        ("information", "Emergency Stop", "All relays have been closed. The running schedule was stopped.")
    ]


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
    """The callback found no job to stop, yet a delivery worker is alive."""
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: True)
    stop, _calls = _stopper(lock, running=False)
    panel = _panel(stop)
    assert lock.try_acquire("schedule")

    panel._on_emergency_stop_clicked()

    assert lock.held_by("schedule")
    assert dialogs[-1][0] == "warning"


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
    assert lock.held_by("priming"), "no schedule can start onto a valve that may be open"
    assert lock.try_acquire("schedule") is False
    assert panel._model.is_master_open and panel._model.is_cage_open(CAGE)

    relays.fail_all_off = False  # the fault clears; the operator presses it again
    panel._on_emergency_stop_clicked()

    assert relays.energized() == set()
    assert lock.is_busy() is False
    assert not panel._model.is_master_open and not panel._model.is_cage_open(CAGE)


def test_relays_not_confirmed_off_still_stop_the_schedule(relays, lock, dialogs):
    stop, calls = _stopper(lock)
    panel = _panel(stop)
    assert lock.try_acquire("schedule")
    relays.fail_all_off = True

    panel._on_emergency_stop_clicked()

    assert calls == [1]
    ((kind, title, text),) = dialogs
    assert (kind, title) == ("critical", "Emergency Stop Failed")
    assert "Disconnect the valve power supply now" in text
    assert text.endswith("The running schedule was stopped.")


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
    assert dialogs[-1] == (
        "information",
        "Emergency Stop",
        "All relays have been closed. The running schedule was stopped.",
    )
