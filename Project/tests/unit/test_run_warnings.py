"""Run asks before a start that will not go as scheduled.

An instant schedule some of whose delivery times have passed: Run skips those
deliveries, never makes them up, and the run's record plans the whole
schedule, so the Animals tab shows the run in red as incomplete. Run lists the
passed deliveries for each animal and asks Start Run or Cancel (the default
and the Esc button); Cancel leaves the operation lock free and the job flag
down, like every refusal.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from utils.run_warnings import MAX_ANIMALS, PASSED_TITLE, START_RUN, passed_deliveries_message

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

NOW = datetime(2026, 10, 9, 12, 0)


def _delivery(animal_id, hours, volume, cage):
    return {
        'animal_id': animal_id,
        'datetime': NOW + timedelta(hours=hours),
        'volume': volume,
        'relay_unit_id': cage,
    }


# --- the wording -------------------------------------------------------------------------------


def test_passed_deliveries_are_listed_for_each_animal_with_what_is_left():
    """The design record's example (docs/STOP_AND_PARTIAL_DELIVERY.md §9): one
    delivery per animal, the only shape RRR creates, in time order as Run
    reads them."""
    deliveries = [
        _delivery(11, -4, 0.25, 3),
        _delivery(12, -1, 0.3, 4),
        _delivery(13, 1, 0.25, 5),
        _delivery(14, 2, 0.35, 6),
    ]
    labels = {11: "M-011", 12: "M-012", 13: "M-013", 14: "M-014"}

    text = passed_deliveries_message("PM water", deliveries, labels, NOW)

    assert text == (
        '2 of 4 deliveries of "PM water" have already passed. This run skips them:\n'
        "• M-011, cage 3: 08:00 passed, nothing from this run (0.250 mL scheduled)\n"
        "• M-012, cage 4: 11:00 passed, nothing from this run (0.300 mL scheduled)\n"
        "\n"
        "This run delivers 0.600 of the 1.150 mL scheduled. For the animals above, the "
        "Animals tab will show this run in red as incomplete.\n"
        "\n"
        "Start the 2 deliveries still ahead?"
    ), "an animal that loses nothing is not listed"


def test_nothing_from_this_run_unless_the_animal_has_deliveries_ahead():
    """A schedule with several deliveries for one animal (RRR cannot create
    one today) still says what is left for an animal with some ahead."""
    deliveries = [
        _delivery(1, -3, 0.25, 3),
        _delivery(2, -2, 0.25, 4),
        _delivery(2, -1, 0.25, 4),
        _delivery(3, -1, 0.25, 5),
        _delivery(3, 1, 0.25, 5),
        _delivery(3, 2, 0.3, 5),
    ]
    labels = {1: "M-11", 2: "M-12", 3: "M-13"}

    text = passed_deliveries_message("PM water", deliveries, labels, NOW)

    assert text.split("\n\n")[0].splitlines()[1:] == [
        "• M-11, cage 3: 09:00 passed, nothing from this run (0.250 mL scheduled)",
        "• M-12, cage 4: 10:00, 11:00 passed, nothing from this run (0.500 mL scheduled)",
        "• M-13, cage 5: 11:00 passed; 0.550 of 0.800 mL still to deliver",
    ]


def test_times_from_another_day_carry_their_date():
    """Per line: a line whose times are all today shows only times of day.
    An animal's times are listed in time order, whatever order they come in."""
    deliveries = [
        _delivery(1, -2, 0.1, 3),
        _delivery(2, -13, 0.2, 4),
        _delivery(1, -26, 0.1, 3),
        _delivery(3, -1, 0.2, 5),
        _delivery(1, 1, 0.1, 3),
    ]
    labels = {1: "M-11", 2: "M-12", 3: "M-13"}

    text = passed_deliveries_message("PM water", deliveries, labels, NOW)

    assert "• M-11, cage 3: 2026-10-08 10:00, 2026-10-09 10:00 passed;" in text
    assert "• M-12, cage 4: 2026-10-08 23:00 passed, nothing from this run" in text
    assert "• M-13, cage 5: 11:00 passed, nothing from this run" in text


def test_long_lists_are_cut_short():
    deliveries = [
        _delivery(animal, hours, 0.1, animal)
        for animal in range(1, MAX_ANIMALS + 3)
        for hours in (-6, -5, -4, -3, -2, -1, 1)
    ]
    text = passed_deliveries_message("Big", deliveries, {}, NOW)
    assert "• cage 1: 06:00, 07:00, 08:00, 09:00 and 2 more passed;" in text
    assert "...and 2 more animals" in text
    assert "cage 11" not in text

    one_more = deliveries[: 7 * (MAX_ANIMALS + 1)]
    lines = passed_deliveries_message("Big", one_more, {}, NOW).splitlines()
    assert lines[MAX_ANIMALS + 1] == "...and 1 more animal"


def test_a_delivery_due_now_is_still_ahead():
    deliveries = [_delivery(1, -1, 0.2, 3), _delivery(2, 0, 0.2, 4)]
    text = passed_deliveries_message("t", deliveries, {1: "M-11", 2: "M-12"}, NOW)
    assert text.startswith('1 of 2 deliveries of "t" has already passed. This run skips it:')
    assert "M-12" not in text
    assert text.endswith("Start the 1 delivery still ahead?")


def test_an_animal_without_a_lab_id_is_named_by_its_cage():
    deliveries = [_delivery(1, -1, 0.2, 9), _delivery(2, 1, 0.2, 4)]
    for lab_id in (None, " "):
        text = passed_deliveries_message("t", deliveries, {1: lab_id}, NOW)
        assert "\n• cage 9: 11:00 passed, nothing from this run (0.200 mL scheduled)" in text


# --- the Run path --------------------------------------------------------------------------------

# The QApplication this module uses, kept for the rest of the session. When a
# QApplication is destroyed, PyQt5 deletes every QObject without a parent.
_QAPP = []


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PyQt5")
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


@pytest.fixture
def run(qapp, database_handler, system_controller, monkeypatch):
    """The real RunStopSection with an operator logged in, so Stop is enabled
    exactly while the job flag is up. ``run.start`` presses Run, and
    ``run.answer`` answers Run's own question."""
    import utils.operation_lock as ol  # noqa: PLC0415
    from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: PLC0415
    from ui.run_stop_section import RunStopSection  # noqa: PLC0415

    ol._singleton = None
    record = SimpleNamespace(
        shown=[], questions=[], asked=[], while_asked=[], started=[], hidden=[], answer=True
    )
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: record.shown.append(a[1]))
    )
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *a, **k: record.shown.append(a[1]))
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: record.questions.append(a[1]) or QMessageBox.Yes),
    )
    system_controller.settings["hardware_mode"] = "pump"  # no calibration gate here
    gui = type(
        "RodentRefreshmentGUI", (), {"hide_execution_monitor": lambda _gui: record.hidden.append(1)}
    )
    monkeypatch.setattr(RunStopSection, "_get_parent_gui", lambda self: gui())
    login = MagicMock()
    login.is_logged_in.return_value = True
    section = RunStopSection(
        lambda *args: record.started.append(args) or True,  # main.run_program: started
        MagicMock(),
        MagicMock(),
        system_controller=system_controller,
        database_handler=database_handler,
        login_system=login,
    )
    monkeypatch.setattr(section, "show_progress_tracker", lambda _schedule: None)

    def confirm_start(title, text, label):
        record.asked.append((title, text, label))
        record.while_asked.append(
            (
                section.job_in_progress,
                ol.get_operation_lock().held_by("schedule"),
                section.stop_button.isEnabled(),
            )
        )
        return record.answer

    monkeypatch.setattr(section, "_confirm_start", confirm_start)

    def start(schedule):
        """The Run click (the job flag, the lock, "Starting..."), then the
        checks it queues, which ask the question."""
        section.schedule_drop_area.current_schedule = schedule
        section.run_program()
        QApplication.processEvents()
        return section

    record.start, record.lock = start, ol.get_operation_lock
    yield record
    ol._singleton = None


def _instant(database_handler, plan):
    """An instant schedule saved as the wizard saves one, one delivery per
    animal: ``plan`` is [(lab ID, cage, hours from now, mL)]."""
    from models.animal import Animal  # noqa: PLC0415
    from models.Schedule import Schedule  # noqa: PLC0415

    now = datetime.now()
    times = [(now + timedelta(hours=hours)).isoformat() for _lab, _cage, hours, _ml in plan]
    schedule = Schedule(None, "PM water", 1.0, min(times), max(times), 1, False, "instant")
    for (lab_id, cage, _hours, ml), time in zip(plan, times):
        animal = Animal(lab_animal_id=lab_id, name=lab_id)
        animal_id = database_handler.add_animal(animal, trainer_id=None)
        schedule.add_animal(animal_id, cage, ml)
        schedule.add_instant_delivery(animal_id, time, ml, cage)
    assert database_handler.add_schedule(schedule)
    return schedule


def test_passed_deliveries_ask_once_and_start_runs_the_whole_schedule(run, database_handler):
    plan = [("M-011", 3, -1, 0.25), ("M-012", 4, 1, 0.3), ("M-013", 5, 2, 0.5)]
    section = run.start(_instant(database_handler, plan))

    ((title, text, label),) = run.asked
    assert (title, label) == (PASSED_TITLE, START_RUN)
    assert text.startswith('1 of 3 deliveries of "PM water" has already passed.')
    assert "\n• M-011, cage 3: " in text, "named by the lab ID the schedule's reader gives"
    assert "passed, nothing from this run (0.250 mL scheduled)" in text
    assert "This run delivers 0.800 of the 1.050 mL scheduled." in text
    assert run.questions == [], "the old Yes/No question is gone"
    assert run.shown == []
    ((schedule, mode, window_start, _window_end),) = run.started
    assert mode == "Instant"
    assert len(schedule.instant_deliveries) == 3, "the worker gets every delivery"
    ahead = min(d['datetime'] for d in schedule.instant_deliveries if d['datetime'] > datetime.now())
    assert window_start == ahead.timestamp(), "the window opens at the first delivery ahead"
    assert section.run_button.text() == "Running"


def test_cancel_starts_nothing_and_frees_the_lock(run, database_handler):
    run.answer = False
    plan = [("M-011", 3, -1, 0.25), ("M-012", 4, 1, 0.25)]
    section = run.start(_instant(database_handler, plan))

    assert run.while_asked == [(True, True, True)], "asked inside the job: flag, lock, Stop"
    assert run.started == []
    assert run.lock().is_busy() is False
    assert section.job_in_progress is False
    assert section.run_button.text() == "Run"
    assert section.run_button.isEnabled() is True
    assert section.stop_button.isEnabled() is False
    assert run.hidden == [1], "the loading Execution Monitor is taken down"
    assert run.shown == [], "Cancel is not an error"


def test_no_question_when_every_delivery_is_ahead(run, database_handler):
    run.start(_instant(database_handler, [("M-011", 3, 1, 0.25), ("M-012", 4, 2, 0.25)]))
    assert run.asked == [] and run.questions == []
    assert len(run.started) == 1


def test_a_schedule_whose_deliveries_have_all_passed_is_still_refused(run, database_handler):
    plan = [("M-011", 3, -1, 0.25), ("M-012", 4, -2, 0.25)]
    section = run.start(_instant(database_handler, plan))
    assert run.asked == []
    assert run.shown == ["Expired Schedule"]
    assert run.started == [] and run.lock().is_busy() is False
    assert section.job_in_progress is False


# --- the question itself --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("clicked", "starts"), [("AcceptRole", True), ("RejectRole", False), (None, False)]
)
def test_the_question_names_its_buttons_and_defaults_to_cancel(
    qapp, database_handler, system_controller, monkeypatch, clicked, starts
):
    """Start Run starts; Cancel, Enter, Esc, or a box closed without a click
    does not."""
    from PyQt5.QtCore import Qt  # noqa: PLC0415
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from ui.run_stop_section import RunStopSection  # noqa: PLC0415

    seen = {}
    # macOS ignores QMessageBox titles (windowTitle() reads ""), so keep the one set.
    set_title = QMessageBox.setWindowTitle

    def set_window_title(box, title):
        seen['title'] = title
        set_title(box, title)

    def exec_(box):
        seen['buttons'] = {box.buttonRole(b): b.text() for b in box.buttons()}
        seen['default'] = box.defaultButton().text()
        seen['escape'] = box.escapeButton().text()
        seen['format'] = box.textFormat()
        seen['icon'] = box.icon()
        seen['text'] = box.text()
        if clicked is not None:
            role = getattr(QMessageBox, clicked)
            next(b for b in box.buttons() if box.buttonRole(b) == role).click()
        return 0

    monkeypatch.setattr(QMessageBox, "setWindowTitle", set_window_title)
    monkeypatch.setattr(QMessageBox, "exec_", exec_)
    section = RunStopSection(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        system_controller=system_controller,
        database_handler=database_handler,
    )

    text = '<b>"AM" water</b>'
    assert section._confirm_start(PASSED_TITLE, text, START_RUN) is starts
    assert seen['title'] == PASSED_TITLE
    assert seen['icon'] == QMessageBox.Warning
    assert seen['buttons'] == {QMessageBox.AcceptRole: START_RUN, QMessageBox.RejectRole: "Cancel"}
    assert seen['default'] == "Cancel" and seen['escape'] == "Cancel", "Enter or Esc never starts"
    assert seen['format'] == Qt.PlainText and seen['text'] == text, "a schedule name is not markup"
