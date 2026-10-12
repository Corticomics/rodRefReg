"""Run asks before a start that will not go as scheduled.

An instant schedule some of whose delivery times have passed: Run skips those
deliveries, never makes them up, and the run's record plans the whole
schedule, so the Animals tab shows the run in red as incomplete. Run lists the
passed deliveries for each animal and asks Start Run or Cancel.

A schedule that ran before and gave water: Run does not resume a schedule, it
starts it over, so every animal gets its full amount again. When that last
run ended early (stopped, ended short, or RRR closed during it), Run lists
what each animal got and what is missing (Last Run Ended Early); when it
completed, what each animal got and when (Last Run Completed). Both ask Start
Over or Cancel. Run reads the last run of this schedule, so a later run of
another one does not hide it, and a history it cannot read never blocks Run.
At most one question per Run (docs/STOP_AND_PARTIAL_DELIVERY.md §9).

Cancel is the default and the Esc button, and leaves the operation lock free
and the job flag down, like every refusal.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from utils.dose_rounding import whole_pulses
from utils.last_run_text import remaining_ml
from utils.run_warnings import (
    COMPLETED_RUN_TITLE,
    LAST_RUN_TITLE,
    MAX_ANIMALS,
    PASSED_TITLE,
    START_OVER,
    START_RUN,
    completed_run_lines,
    completed_run_message,
    last_run_lines,
    last_run_message,
    passed_deliveries_message,
    start_over_question,
    window_note,
)

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


# --- the last run's wording ----------------------------------------------------------------------

LOG = "cd ~/rrr/current/Project && ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py daily"


def _last(outcome, delivered, cage=3, lab="M-11", **fields):
    """An animal's latest run of the schedule as get_latest_runs_of_schedule
    reads it: the Animal.last_run keys plus lab_animal_id. Run 5, staggered,
    1.000 mL scheduled and 0.991 planned, today 08:00 to 10:32."""
    return {
        'run_id': 5,
        'schedule_name': "AM water",
        'delivery_mode': "staggered",
        'started_at': "2026-10-09T08:00:00",
        'ended_at': "2026-10-09T10:32:00",
        'outcome': outcome,
        'relay_unit_id': cage,
        'requested_ml': 1.0,
        'planned_ml': 0.991,
        'delivered_ml': delivered,
        'lab_animal_id': lab,
        **fields,
    }


def test_no_question_without_a_last_run_that_gave_water():
    """No run of this schedule, or one that gave nothing: the full amount is
    what each animal needs."""
    assert last_run_lines({}, [1], NOW) == [] and completed_run_lines({}, [1], NOW) == []
    nothing = {1: _last('stopped', 0.0), 2: _last('incomplete', 0.0, cage=4, lab="M-12")}
    assert last_run_lines(nothing, [1, 2], NOW) == []
    assert completed_run_lines(nothing, [1, 2], NOW) == []
    assert completed_run_lines({1: _last('completed', 0.0)}, [1], NOW) == []


def test_a_last_run_that_completed_gets_the_completed_run_question():
    """Not Last Run Ended Early, but its own question (the owner's choice,
    design record §14, item 7): each line says when that run completed."""
    done = {1: _last('completed', 0.991), 2: _last('completed', 0.991, cage=4, lab="M-12")}
    assert last_run_lines(done, [1, 2], NOW) == []
    assert completed_run_lines(done, [1, 2], NOW) == [
        "M-11, cage 3: 0.991 of the planned 0.991 mL, completed at 10:32",
        "M-12, cage 4: 0.991 of the planned 0.991 mL, completed at 10:32",
    ]


def test_an_animal_that_completed_is_listed_when_another_ended_early():
    """Starting over gives it its full amount again too; one that got
    nothing is left out. Its line gives no time: that run ended when it was
    stopped, not when this animal completed."""
    runs = {1: _last('completed', 0.991), 2: _last('stopped', 0.0, cage=4, lab="M-12")}
    assert last_run_lines(runs, [1, 2], NOW) == [
        "M-11, cage 3: 0.991 of the planned 0.991 mL, complete"
    ]
    assert completed_run_lines(runs, [1, 2], NOW) == [], "one question, not two"


def test_a_stopped_or_short_animal_shows_what_went_out_what_is_missing_and_when():
    runs = {
        1: _last('stopped', 0.41),
        2: _last('incomplete', 0.8, cage=4, lab="M-12", ended_at=None),
    }
    assert last_run_lines(runs, [1, 2], NOW) == [
        "M-11, cage 3: 0.410 of the planned 0.991 mL, stopped at 10:32; "
        "remaining 0.590 of the 1.000 mL scheduled",
        "M-12, cage 4: 0.800 of the planned 0.991 mL, ended short; "
        "remaining 0.200 of the 1.000 mL scheduled",
    ]


def test_the_remainder_is_what_was_scheduled_less_what_was_delivered():
    """Under round_doses_up 1.000 mL plans 30 pulses at 0.034164 mL. After
    12 pulses a new schedule for the remaining 0.590 mL rounds up to the 18
    pulses that did not fire; one for planned minus delivered, 0.615 mL,
    would fire 19. The Animals tab gives the same remainder."""
    q = 0.034164
    run = _last('stopped', 12 * q, planned_ml=30 * q)
    (line,) = last_run_lines({1: run}, [1], NOW)
    assert line.endswith(", stopped at 10:32; remaining 0.590 of the 1.000 mL scheduled")
    assert f"{remaining_ml(run):.3f}" == "0.590"
    assert whole_pulses(0.590, q, round_up=True) == 18
    assert whole_pulses(0.615, q, round_up=True) == 19

    short = _last('stopped', 0.9997, planned_ml=30 * q)
    assert last_run_lines({1: short}, [1], NOW) == [
        "M-11, cage 3: 1.000 of the planned 1.025 mL, stopped at 10:32"
    ], "a remainder that shows as 0.000 mL is not offered, as on the Animals tab"


@pytest.mark.parametrize(
    ("outcome", "what"),
    [
        ('interrupted', "RRR closed during that run"),
        ('running', "the end of that run was not recorded"),
    ],
)
def test_a_run_whose_end_was_not_recorded_points_to_the_delivery_log(outcome, what):
    """Interrupted: RRR closed during it. Still 'running' when Run is
    pressed: the database did not take its end."""
    (line,) = last_run_lines({1: _last(outcome, None, ended_at=None)}, [1], NOW)
    assert line == (
        f"M-11, cage 3: {what} (started 08:00); how much of the planned 0.991 mL it "
        f"delivered is in the delivery log: {LOG} --since 2026-10-09 --cage 3"
    )


def test_an_amount_never_recorded_points_to_the_delivery_log():
    """finish_schedule_run closes an animal missing from its results as
    'incomplete' with no amount."""
    run = _last(
        'incomplete', None, started_at="2026-10-08T20:00:00", ended_at="2026-10-08T23:10:00"
    )
    assert last_run_lines({1: run}, [1], NOW) == [
        "M-11, cage 3: ended short at 2026-10-08 23:10; how much of the planned 0.991 mL it "
        f"delivered is in the delivery log: {LOG} --since 2026-10-08 --cage 3"
    ]


def test_a_completed_animal_without_a_recorded_amount_keeps_the_warning():
    """Each line on its own: what was not recorded is said to be so, and
    the other lines stay."""
    runs = {1: _last('completed', None), 2: _last('stopped', 0.41, cage=4, lab="M-12")}
    assert last_run_lines(runs, [1, 2], NOW) == [
        "M-11, cage 3: complete (amount not recorded)",
        "M-12, cage 4: 0.410 of the planned 0.991 mL, stopped at 10:32; "
        "remaining 0.590 of the 1.000 mL scheduled",
    ]
    assert completed_run_lines({1: _last('completed', None)}, [1], NOW) == [
        "M-11, cage 3: completed at 10:32 (amount not recorded)"
    ]


def test_a_plan_or_a_time_that_was_not_recorded_is_left_out():
    runs = {
        1: _last('stopped', 0.41, planned_ml=None, ended_at=None),
        2: _last('interrupted', None, cage=4, lab=None, planned_ml=None, started_at=None),
        3: _last('stopped', 0.41, cage=5, lab="M-13", requested_ml=None, ended_at="soon"),
    }
    assert last_run_lines(runs, [1, 2, 3], NOW) == [
        "M-11, cage 3: 0.410 mL, stopped; remaining 0.590 of the 1.000 mL scheduled",
        f"cage 4: RRR closed during that run; how much it delivered is in the delivery log: "
        f"{LOG} --cage 4",
        "M-13, cage 5: 0.410 of the planned 0.991 mL, stopped",
    ]


def test_a_line_from_an_older_run_of_the_schedule_carries_its_date():
    """An animal that was not in the schedule's last run (taken off the
    schedule and put back) keeps its own latest run of it: its line says
    when, with the date even when it is today. Run 3 was stopped at 07:10
    after M-12 had completed, so M-12's line says when that run started: its
    end was the Stop, not when M-12 completed."""
    run_3 = {'run_id': 3, 'started_at': "2026-10-09T06:00:00", 'ended_at': "2026-10-09T07:10:00"}
    run_2 = {'run_id': 2, 'started_at': "2026-10-09T05:00:00", 'ended_at': None}
    runs = {
        1: _last('stopped', 0.41),  # the last run of the schedule, run 5
        2: _last('completed', 0.991, cage=4, lab="M-12", **run_3),
        3: _last('stopped', 0.2, cage=5, lab="M-13", **run_3),
        4: _last('interrupted', None, cage=6, lab="M-14", **run_2),
    }
    assert last_run_lines(runs, [1, 2, 3, 4], NOW) == [
        "M-11, cage 3: 0.410 of the planned 0.991 mL, stopped at 10:32; "
        "remaining 0.590 of the 1.000 mL scheduled",
        "M-12, cage 4: 0.991 of the planned 0.991 mL, complete in the run started "
        "2026-10-09 06:00",
        "M-13, cage 5: 0.200 of the planned 0.991 mL, stopped at 2026-10-09 07:10; "
        "remaining 0.800 of the 1.000 mL scheduled",
        "M-14, cage 6: RRR closed during that run (started 2026-10-09 05:00); how much of "
        f"the planned 0.991 mL it delivered is in the delivery log: {LOG} --since 2026-10-09 "
        "--cage 6",
    ]


def test_a_completed_line_from_an_older_run_says_when_that_run_started():
    """In Last Run Completed too: an older run of the schedule may have been
    stopped after the animal completed, so its end does not say when the
    animal completed. The schedule's last run completed, so its lines do."""
    run_3 = {'run_id': 3, 'started_at': "2026-10-09T06:00:00", 'ended_at': "2026-10-09T07:10:00"}
    runs = {
        1: _last('completed', 0.991),  # the last run of the schedule, run 5
        2: _last('completed', 0.991, cage=4, lab="M-12", **run_3),
        3: _last('completed', None, cage=5, lab="M-13", **run_3),
        4: _last('completed', 0.991, cage=6, lab="M-14", run_id=3, started_at=None),
    }
    assert completed_run_lines(runs, [1, 2, 3, 4], NOW) == [
        "M-11, cage 3: 0.991 of the planned 0.991 mL, completed at 10:32",
        "M-12, cage 4: 0.991 of the planned 0.991 mL, complete in the run started "
        "2026-10-09 06:00",
        "M-13, cage 5: complete in the run started 2026-10-09 06:00 (amount not recorded)",
        "M-14, cage 6: 0.991 of the planned 0.991 mL, complete",
    ], "a start that was not recorded is left out"


def test_ids_are_matched_as_numbers():
    assert last_run_lines({"1": _last('stopped', 0.41)}, ["1"], NOW)
    assert last_run_lines({1: _last('stopped', 0.41)}, [None, "x"], NOW) == []
    assert len(last_run_lines({1: _last('stopped', 0.41)}, [1, "1"], NOW)) == 1, "listed once"


def test_an_outcome_this_release_does_not_know_counts_as_ended_early():
    """A newer release's value, read after a revert: the Animals tab shows
    it red, and Run warns as for a run that ended short."""
    runs = {1: _last('paused', 0.41), 2: _last('completed', 0.991, cage=4, lab="M-12")}
    assert last_run_lines(runs, [1, 2], NOW)[0] == (
        "M-11, cage 3: 0.410 of the planned 0.991 mL, ended short at 10:32; "
        "remaining 0.590 of the 1.000 mL scheduled"
    )
    assert completed_run_lines(runs, [1, 2], NOW) == []


def test_an_instant_run_gives_no_remainder():
    """Running an instant schedule again skips its passed times, so the
    Animals tab sends the operator to the delivery log first."""
    run = _last('stopped', 0.1, delivery_mode="instant", requested_ml=0.25, planned_ml=0.239)
    assert last_run_lines({1: run}, [1], NOW) == [
        "M-11, cage 3: 0.100 of the planned 0.239 mL, stopped at 10:32"
    ]


def test_the_start_over_question():
    """Last Run Ended Early, as the design record words it (§9), with the
    window note when the start has passed."""
    runs = {11: _last('stopped', 0.41, lab="M-011"), 12: _last('completed', 0.991, 4, "M-012")}
    lines = last_run_lines(runs, [11, 12], NOW)
    window = window_note(datetime(2026, 10, 9, 8, 0), datetime(2026, 10, 9, 20, 0), NOW)

    assert last_run_message("AM water", lines, window) == (
        'The last run of "AM water" ended early. These animals already got water in it:\n'
        "• M-011, cage 3: 0.410 of the planned 0.991 mL, stopped at 10:32; remaining 0.590 "
        "of the 1.000 mL scheduled\n"
        "• M-012, cage 4: 0.991 of the planned 0.991 mL, complete\n"
        "\n"
        "Run does not resume a schedule: it starts this one over, so the animals above get "
        "their full amount again, on top of what they already got. If the missing water has "
        "not been given since, press Cancel and create a new schedule for the remaining "
        "amount.\n"
        "\n"
        "The scheduled start time (2026-10-09 08:00) has already passed: the full amount "
        "goes out in the 480 minutes left until 20:00.\n"
        "\n"
        'Start "AM water" over?'
    )
    assert last_run_message("AM water", lines) == (
        last_run_message("AM water", lines, window).replace(window + "\n\n", "")
    ), "a window still ahead: no note"
    assert start_over_question("AM water", lines, []) == (
        LAST_RUN_TITLE,
        last_run_message("AM water", lines),
    )


def test_the_completed_run_question():
    """In the style of Last Run Ended Early: what each animal got of its
    plan and when, then that starting over gives it again on top."""
    done = {
        11: _last('completed', 0.991, lab="M-011", ended_at="2026-10-08T20:00:00"),
        12: _last('completed', 0.991, 4, "M-012", ended_at="2026-10-08T20:00:00"),
    }
    lines = completed_run_lines(done, [11, 12], NOW)
    window = window_note(datetime(2026, 10, 9, 8, 0), datetime(2026, 10, 9, 20, 0), NOW)

    assert completed_run_message("AM water", lines, window) == (
        'The last run of "AM water" completed. These animals already got their full amount '
        "in it:\n"
        "• M-011, cage 3: 0.991 of the planned 0.991 mL, completed at 2026-10-08 20:00\n"
        "• M-012, cage 4: 0.991 of the planned 0.991 mL, completed at 2026-10-08 20:00\n"
        "\n"
        "Run starts this schedule over, so the animals above get their full amount again, "
        "on top of what they already got.\n"
        "\n"
        "The scheduled start time (2026-10-09 08:00) has already passed: the full amount "
        "goes out in the 480 minutes left until 20:00.\n"
        "\n"
        'Start "AM water" over?'
    )
    assert "scheduled start time" not in completed_run_message("AM water", lines)
    assert start_over_question("AM water", [], lines) == (
        COMPLETED_RUN_TITLE,
        completed_run_message("AM water", lines),
    )


def test_the_window_note_counts_the_minutes_left():
    start = datetime(2026, 10, 9, 8, 0)
    assert window_note(start, NOW + timedelta(seconds=61), NOW).endswith(
        "the full amount goes out in the 1 minute left until 12:01."
    )


@pytest.mark.parametrize("outcome", ['stopped', 'completed'])
def test_the_passed_deliveries_question_carries_the_last_run(outcome):
    """The same header and lines, with no remainder (an instant run gives
    none), then the passed deliveries' own paragraph, before the question."""
    deliveries = [_delivery(1, -2, 0.25, 3), _delivery(2, 1, 0.25, 4)]
    instant = {'delivery_mode': "instant", 'requested_ml': 0.25, 'planned_ml': 0.239}
    done = outcome == 'completed'
    runs = {
        1: _last(outcome, 0.239 if done else 0.1, **instant),
        2: _last(outcome, 0.239 if done else 0.0, 4, "M-12", **instant),
    }
    lines = {
        'last_run': last_run_lines(runs, [1, 2], NOW),
        'completed_run': completed_run_lines(runs, [1, 2], NOW),
    }

    text = passed_deliveries_message("PM water", deliveries, {1: "M-11", 2: "M-12"}, NOW, **lines)

    first, totals, last_run, skipped, question = text.split("\n\n")
    assert first.startswith('1 of 2 deliveries of "PM water" has already passed.')
    assert totals.startswith("This run delivers 0.250 of the 0.500 mL scheduled.")
    if done:
        assert last_run == (
            'The last run of "PM water" completed. These animals already got their full '
            "amount in it:\n"
            "• M-11, cage 3: 0.239 of the planned 0.239 mL, completed at 10:32\n"
            "• M-12, cage 4: 0.239 of the planned 0.239 mL, completed at 10:32"
        )
    else:
        assert last_run == (
            'The last run of "PM water" ended early. These animals already got water in it:\n'
            "• M-11, cage 3: 0.100 of the planned 0.239 mL, stopped at 10:32"
        )
    assert skipped == "Passed deliveries are skipped, never repeated."
    assert question == "Start the 1 delivery still ahead?"


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


# --- the last run, on the Run path ---------------------------------------------------------------


def _animals(database_handler, *lab_ids):
    from models.animal import Animal  # noqa: PLC0415

    return [
        database_handler.add_animal(Animal(lab_animal_id=lab, name=lab), trainer_id=None)
        for lab in lab_ids
    ]


def _record(
    database_handler, schedule_id, results, mode="staggered", requested=1.0, planned=0.991
):
    """One run of the schedule as RRR records it, through the facade:
    ``results`` is [(animal_id, cage, delivered or None, outcome)]."""
    animals = [
        {'animal_id': a, 'relay_unit_id': cage, 'requested_ml': requested, 'planned_ml': planned}
        for a, cage, _delivered, _outcome in results
    ]
    run_id = database_handler.start_schedule_run(schedule_id, "AM water", mode, None, animals)
    outcomes = {outcome for *_rest, outcome in results}
    end_reason = (
        'completed'
        if outcomes == {'completed'}
        else ('stopped' if 'stopped' in outcomes else 'ended_short')
    )
    assert database_handler.finish_schedule_run(
        run_id, end_reason, {a: (delivered, outcome) for a, _cage, delivered, outcome in results}
    )
    return run_id


def _staggered(animals, start_in_hours=1.0):
    """Staggered schedule 7 for ``animals`` (cage = id + 2), 1.0 mL each, over
    three hours from ``start_in_hours`` from now."""
    from models.Schedule import Schedule  # noqa: PLC0415

    now = datetime.now()
    start = now + timedelta(hours=start_in_hours)
    schedule = Schedule(
        7,
        "AM water",
        1.0,
        start.isoformat(),
        (start + timedelta(hours=3)).isoformat(),
        1,
        False,
        "staggered",
    )
    for animal_id in animals:
        schedule.add_animal(animal_id, animal_id + 2, 1.0)
    return schedule


@pytest.fixture
def staggered_run(run, database_handler, monkeypatch):
    """``run`` for a staggered schedule: its delivery windows are not read here."""
    monkeypatch.setattr(
        database_handler, "get_schedule_staggered_windows", lambda _sid: [{"window": 1}]
    )
    return run


def test_a_stopped_schedule_asks_once_to_start_over(staggered_run, database_handler):
    """Its start has passed too: one question, with the window note in it."""
    run = staggered_run
    a, b = _animals(database_handler, "M-11", "M-12")
    _record(database_handler, 7, [(a, a + 2, 0.41, 'stopped'), (b, b + 2, 0.991, 'completed')])

    section = run.start(_staggered([a, b], start_in_hours=-1))

    ((title, text, label),) = run.asked
    assert (title, label) == (LAST_RUN_TITLE, START_OVER)
    assert f"\n• M-11, cage {a + 2}: 0.410 of the planned 0.991 mL, stopped at " in text
    assert "; remaining 0.590 of the 1.000 mL scheduled\n" in text
    assert f"\n• M-12, cage {b + 2}: 0.991 of the planned 0.991 mL, complete\n" in text
    assert "\n\nThe scheduled start time (" in text, "the window is in the same question"
    assert run.questions == [], "no second question about the start time"
    ((_schedule, mode, window_start, _window_end),) = run.started
    assert mode == "Staggered"
    assert abs(window_start - datetime.now().timestamp()) < 60, "what is left of the window"
    assert section.run_button.text() == "Running"


def test_a_staggered_question_with_a_future_window_has_no_window_note(
    staggered_run, database_handler
):
    run = staggered_run
    (a,) = _animals(database_handler, "M-11")
    _record(database_handler, 7, [(a, a + 2, 0.41, 'stopped')])
    schedule = _staggered([a])

    run.start(schedule)

    ((title, text, _label),) = run.asked
    assert title == LAST_RUN_TITLE
    assert "scheduled start time" not in text
    assert text.endswith('remaining amount.\n\nStart "AM water" over?'), "no window note"
    ((_schedule, _mode, window_start, _window_end),) = run.started
    assert window_start == datetime.fromisoformat(schedule.start_time).timestamp()


@pytest.mark.parametrize("start_in_hours", [-1, 1], ids=["start passed", "start ahead"])
def test_a_completed_schedule_asks_before_it_gives_the_water_again(
    staggered_run, database_handler, start_in_hours
):
    run = staggered_run
    a, b = _animals(database_handler, "M-11", "M-12")
    _record(database_handler, 7, [(a, a + 2, 0.991, 'completed'), (b, b + 2, 0.991, 'completed')])

    run.start(_staggered([a, b], start_in_hours=start_in_hours))

    ((title, text, label),) = run.asked
    assert (title, label) == (COMPLETED_RUN_TITLE, START_OVER)
    assert text.startswith(
        'The last run of "AM water" completed. These animals already got their full amount '
        "in it:\n"
    )
    assert f"\n• M-12, cage {b + 2}: 0.991 of the planned 0.991 mL, completed at " in text
    assert ("\n\nThe scheduled start time (" in text) == (start_in_hours < 0)
    assert run.questions == []
    assert len(run.started) == 1


@pytest.mark.parametrize(
    ("outcome", "delivered"),
    [('stopped', 0.41), ('completed', 0.991)],
    ids=["stopped", "completed"],
)
def test_cancel_on_start_over_starts_nothing_and_frees_the_lock(
    staggered_run, database_handler, outcome, delivered
):
    run = staggered_run
    run.answer = False
    (a,) = _animals(database_handler, "M-11")
    _record(database_handler, 7, [(a, a + 2, delivered, outcome)])

    section = run.start(_staggered([a]))

    assert run.while_asked == [(True, True, True)], "asked inside the job: flag, lock, Stop"
    assert run.started == []
    assert run.lock().is_busy() is False
    assert section.job_in_progress is False
    assert section.run_button.text() == "Run"
    assert section.stop_button.isEnabled() is False
    assert run.hidden == [1], "the loading Execution Monitor is taken down"
    assert run.shown == [], "Cancel is not an error"


@pytest.mark.parametrize("history", ["no run", "no water"])
@pytest.mark.parametrize("start_in_hours", [-1, 1], ids=["start passed", "start ahead"])
def test_without_a_run_that_gave_water_only_the_start_time_question_is_asked(
    staggered_run, database_handler, history, start_in_hours
):
    run = staggered_run
    (a,) = _animals(database_handler, "M-11")
    if history == "no water":
        _record(database_handler, 7, [(a, a + 2, 0.0, 'stopped')])

    run.start(_staggered([a], start_in_hours=start_in_hours))

    assert run.asked == []
    assert run.questions == (["Schedule Start Time Passed"] if start_in_hours < 0 else [])
    assert len(run.started) == 1


def test_a_later_run_of_another_schedule_does_not_hide_the_stopped_one(
    staggered_run, database_handler
):
    """Say the missing water was given by a new schedule: running the
    stopped one again would still give the full amount, so Run still asks."""
    run = staggered_run
    (a,) = _animals(database_handler, "M-11")
    _record(database_handler, 7, [(a, a + 2, 0.41, 'stopped')])
    _record(database_handler, 8, [(a, a + 2, 0.581, 'completed')])

    run.start(_staggered([a]))

    assert [title for title, _text, _label in run.asked] == [LAST_RUN_TITLE]


def test_a_later_completed_run_of_this_schedule_replaces_the_stopped_one(
    staggered_run, database_handler
):
    run = staggered_run
    (a,) = _animals(database_handler, "M-11")
    _record(database_handler, 7, [(a, a + 2, 0.41, 'stopped')])
    _record(database_handler, 7, [(a, a + 2, 0.991, 'completed')])

    run.start(_staggered([a]))

    assert [title for title, _text, _label in run.asked] == [COMPLETED_RUN_TITLE]


def test_a_history_that_cannot_be_read_does_not_block_run(
    staggered_run, database_handler, monkeypatch, capsys
):
    """Advisory: Run goes on as if the schedule never ran, and the Terminal
    tab says why it did not check."""
    run = staggered_run

    def broken(*_args):
        raise RuntimeError("disk I/O error")

    monkeypatch.setattr(database_handler, "get_latest_runs_of_schedule", broken)
    (a,) = _animals(database_handler, "M-11")

    run.start(_staggered([a], start_in_hours=-1))

    assert run.asked == [] and run.questions == ["Schedule Start Time Passed"]
    assert len(run.started) == 1
    assert (
        "[RUN] Could not check the last run of this schedule: disk I/O error"
        in capsys.readouterr().out
    )


@pytest.mark.parametrize(
    ("outcome", "header"),
    [
        ('stopped', 'The last run of "PM water" ended early. These animals already got water'),
        ('completed', 'The last run of "PM water" completed. These animals already got their'),
    ],
    ids=["stopped", "completed"],
)
def test_an_instant_rerun_with_passed_deliveries_asks_one_question_with_the_last_run(
    run, database_handler, outcome, header
):
    schedule = _instant(database_handler, [("M-011", 3, -1, 0.25), ("M-012", 4, 1, 0.3)])
    a, b = schedule.animals
    got = 0.239 if outcome == 'completed' else 0.1
    _record(
        database_handler,
        schedule.schedule_id,
        [(a, 3, got, outcome), (b, 4, got if outcome == 'completed' else 0.0, outcome)],
        mode="instant",
        requested=0.25,
        planned=0.239,
    )

    run.start(schedule)

    ((title, text, label),) = run.asked
    assert (title, label) == (PASSED_TITLE, START_RUN)
    assert f"\n\n{header}" in text
    assert f"\n• M-011, cage 3: {got:.3f} of the planned 0.239 mL, " in text
    assert "remaining" not in text, "an instant run's lines give no remainder"
    assert text.endswith(
        "\n\nPassed deliveries are skipped, never repeated.\n\nStart the 1 delivery still ahead?"
    )
    assert len(run.started) == 1


@pytest.mark.parametrize(
    ("outcome", "title"), [('stopped', LAST_RUN_TITLE), ('completed', COMPLETED_RUN_TITLE)]
)
def test_an_instant_rerun_with_every_delivery_ahead_asks_to_start_over(
    run, database_handler, outcome, title
):
    """The schedule's times were moved after that run: every delivery goes
    out again."""
    schedule = _instant(database_handler, [("M-011", 3, 1, 0.25), ("M-012", 4, 2, 0.3)])
    a, b = schedule.animals
    _record(
        database_handler,
        schedule.schedule_id,
        [(a, 3, 0.239 if outcome == 'completed' else 0.1, outcome), (b, 4, 0.239, 'completed')],
        mode="instant",
        requested=0.25,
        planned=0.239,
    )

    run.start(schedule)

    ((asked_title, text, label),) = run.asked
    assert (asked_title, label) == (title, START_OVER)
    assert "Passed deliveries" not in text and text.endswith('Start "PM water" over?')
    assert len(run.started) == 1


@pytest.mark.parametrize("mode", ["staggered", "instant"])
def test_an_expired_schedule_is_refused_before_its_last_run_is_read(
    run, database_handler, monkeypatch, mode
):
    """An instant schedule whose last run completed has every time behind
    it, so Expired Schedule refuses it first, as it refuses a staggered one
    whose window has ended."""
    read = database_handler.get_latest_runs_of_schedule
    reads = []
    monkeypatch.setattr(
        database_handler,
        "get_latest_runs_of_schedule",
        lambda *args: reads.append(args) or read(*args),
    )
    monkeypatch.setattr(
        database_handler, "get_schedule_staggered_windows", lambda _sid: [{"window": 1}]
    )
    if mode == "instant":
        schedule = _instant(database_handler, [("M-011", 3, -2, 0.25), ("M-012", 4, -1, 0.3)])
    else:
        schedule = _staggered(_animals(database_handler, "M-011", "M-012"), start_in_hours=-4)
    cages = {int(a): int(cage) for a, cage in schedule.relay_unit_assignments.items()}
    _record(
        database_handler,
        schedule.schedule_id,
        [(a, cages[a], 0.239, 'completed') for a in schedule.animals],
        mode=mode,
    )

    section = run.start(schedule)

    assert run.shown == ["Expired Schedule"]
    assert run.asked == [] and run.questions == []
    assert reads == [], "refused before the history is read"
    assert run.started == [] and run.lock().is_busy() is False
    assert section.job_in_progress is False
