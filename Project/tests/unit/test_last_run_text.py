"""The words of the Animals tab's "Last schedule delivered amount" cell.

utils.last_run_text turns Animal.last_run, the animal's latest schedule run,
into the cell's text, its tooltip and whether it is red. Red follows the
outcome the run recorded, never a comparison of delivered with scheduled. An
amount that was not recorded is "?", never the planned amount. The advice
for a run that ended short follows its delivery mode: run again, a staggered
schedule starts over, so the tooltip gives the remainder for a new schedule;
an instant one skips the delivery times that have passed, and a run started
late counts them as not delivered, so the tooltip sends the operator to the
delivery log first. The remainder is a measured figure, to three decimals;
the amount to schedule for it is one the schedule wizard takes, to two
decimals and at least 0.10 mL. Qt-free.
"""

from __future__ import annotations

import pytest

from utils.dose_rounding import whole_pulses
from utils.last_run_text import (
    NO_RUN_TEXT,
    SKIPS_PASSED_INSTANT,
    STARTS_OVER_STAGGERED,
    amount_to_schedule,
    delivery_log_command,
    last_run_cell,
    outcome_word,
    owed_ml,
    remaining_ml,
)

PLANNED_LINE = "Planned: 0.991 mL (rounded to whole valve pulses at this cage's calibration)"
COMMAND = (
    "cd ~/rrr/current/Project && ~/rrr/shared/venv/bin/python3 "
    "tools/gravimetric_check.py daily --since 2026-10-09 --cage 5"
)
STARTS_OVER = "Running this schedule again starts it over and delivers the full amount again."
SKIPS_PASSED = (
    "Running this schedule again skips every delivery time that has passed; it does not "
    "give those deliveries again."
)


def _run(outcome, delivered=0.991, **fields):
    """Animal.last_run as the animal readers return it: a staggered run of
    1.000 mL, planned at 0.991 mL in whole pulses, on cage 5."""
    run = {
        'run_id': 1,
        'schedule_name': "AM water",
        'delivery_mode': 'staggered',
        'started_at': "2026-10-09T07:00:00",
        'ended_at': "2026-10-09T07:30:00",
        'outcome': outcome,
        'relay_unit_id': 5,
        'requested_ml': 1.0,
        'planned_ml': 0.991,
        'delivered_ml': delivered,
    }
    run.update(fields)
    return run


def _when(timestamp):
    return f"<{timestamp}>"


def _cell(run):
    return last_run_cell(run, _when)


def test_no_run_is_a_dash_and_not_red():
    assert NO_RUN_TEXT == "—"
    assert _cell(None) == (
        "—",
        "No schedule run has been recorded for this animal yet.",
        False,
    )


def test_completed_shows_the_delivered_amount_which_is_the_planned_one():
    text, tooltip, red = _cell(_run('completed'))
    assert (text, red) == ("0.991 mL", False)
    assert tooltip.splitlines() == [
        'Schedule "AM water" completed <2026-10-09T07:30:00>.',
        "Scheduled: 1.000 mL",
        PLANNED_LINE,
        "Delivered: 0.991 mL",
    ]


def test_a_completed_run_below_the_scheduled_amount_is_not_red():
    """Whole pulses can land a full delivery under the schedule: completed is
    the run's own verdict, and the cell never compares the two figures."""
    text, _tooltip, red = _cell(_run('completed', delivered=0.975))
    assert (text, red) == ("0.975 mL", False)


def test_planned_equal_to_scheduled_needs_no_rounding_note():
    """Pump and continuous modes plan the scheduled amount itself."""
    _text, tooltip, _red = _cell(_run('completed', delivered=1.0, planned_ml=1.0))
    assert tooltip.splitlines()[1:3] == ["Scheduled: 1.000 mL", "Planned: 1.000 mL"]
    assert "whole valve pulses" not in tooltip


def test_running_shows_the_plan_and_is_not_red():
    text, tooltip, red = _cell(_run('running', delivered=None, ended_at=None))
    assert (text, red) == ("Running · 0.991 mL planned", False)
    assert tooltip.splitlines() == [
        'Schedule "AM water" is running. It started <2026-10-09T07:00:00>.',
        "Scheduled: 1.000 mL",
        PLANNED_LINE,
        "The delivered amount appears here when the schedule ends.",
    ]


def test_stopped_is_red_with_delivered_over_planned_and_the_remainder():
    """The remainder starts from the scheduled amount (1.000 − 0.400), not the
    planned one: a new schedule is rounded again at the cage's calibration."""
    text, tooltip, red = _cell(_run('stopped', delivered=0.4))
    assert (text, red) == ("Stopped · 0.400 / 0.991 mL", True)
    assert tooltip.splitlines() == [
        'Schedule "AM water" was stopped <2026-10-09T07:30:00>, '
        "before this animal received its full amount.",
        "Scheduled: 1.000 mL",
        PLANNED_LINE,
        "Delivered: 0.400 mL",
        STARTS_OVER,
        "To deliver only the remaining 0.600 mL, create a new schedule for 0.60 mL.",
    ]
    assert STARTS_OVER_STAGGERED == STARTS_OVER


def test_incomplete_is_red_and_says_why():
    text, tooltip, red = _cell(_run('incomplete', delivered=0.8))
    assert (text, red) == ("Incomplete · 0.800 / 0.991 mL", True)
    assert tooltip.splitlines() == [
        'Schedule "AM water" ended <2026-10-09T07:30:00> without this animal\'s full amount.',
        "Some deliveries failed, or their times had already passed when it was started.",
        "Scheduled: 1.000 mL",
        PLANNED_LINE,
        "Delivered: 0.800 mL",
        STARTS_OVER,
        "To deliver only the remaining 0.200 mL, create a new schedule for 0.20 mL.",
    ]


def test_interrupted_shows_a_question_mark_and_points_to_the_delivery_log():
    """RRR closed during the run: the amount is unknown, and the run is dated
    by its start (its end is when the next start found it open)."""
    text, tooltip, red = _cell(_run('interrupted', delivered=None))
    assert (text, red) == ("Interrupted · ? / 0.991 mL", True)
    assert tooltip.splitlines() == [
        'RRR closed unexpectedly or lost power while schedule "AM water" was running.',
        "It started <2026-10-09T07:00:00>.",
        "Scheduled: 1.000 mL",
        PLANNED_LINE,
        "Delivered: not recorded.",
        "To see what cage 5 received, run this in a terminal on the Pi:",
        COMMAND,
    ]


def test_an_outcome_this_release_does_not_know_is_red():
    """A newer release may record an outcome this one does not know, read after
    a revert: it shows by name, in red, so someone checks it."""
    text, tooltip, red = _cell(_run('cancelled', delivered=0.5))
    assert (text, red) == ("Cancelled · 0.500 / 0.991 mL", True)
    lines = tooltip.splitlines()
    assert lines[0] == (
        'Schedule "AM water" ended <2026-10-09T07:30:00> without this animal\'s full amount.'
    )
    assert lines[1] == "Scheduled: 1.000 mL", "no cause line for an outcome it does not know"


@pytest.mark.parametrize("outcome", ["stopped", "incomplete"])
def test_an_instant_run_that_ended_short_sends_the_operator_to_the_delivery_log(outcome):
    """Run again, an instant schedule skips the passed delivery times, and a run
    started late counts them as not delivered even when an earlier run gave
    them: no exact remainder, the delivery log first."""
    text, tooltip, red = _cell(_run(outcome, delivered=0.4, delivery_mode='instant'))
    assert red and text == f"{outcome.capitalize()} · 0.400 / 0.991 mL"
    lines = tooltip.splitlines()
    assert lines[-4:] == [
        "Delivered: 0.400 mL",
        SKIPS_PASSED,
        "0.600 mL was not delivered in this run. If it started after some delivery times "
        "had passed, an earlier run may already have given them. Check the delivery log "
        "first, then create a new schedule for what is missing (0.60 mL if all of it is "
        "missing):",
        COMMAND,
    ]
    assert SKIPS_PASSED_INSTANT == SKIPS_PASSED
    assert STARTS_OVER not in lines
    assert not [line for line in lines if line.startswith("To deliver only the remaining")]


@pytest.mark.parametrize(
    "outcome, text, red",
    [
        ('completed', "? mL", False),
        ('stopped', "Stopped · ? / 0.991 mL", True),
        ('incomplete', "Incomplete · ? / 0.991 mL", True),
    ],
    ids=['completed', 'stopped', 'incomplete'],
)
def test_an_amount_that_was_not_recorded_is_a_question_mark_whatever_the_outcome(
    outcome, text, red
):
    """Unknown means unknown: never the planned amount, never 0. A run closed
    without a figure for an animal records it as not known."""
    cell, tooltip, alert = _cell(_run(outcome, delivered=None))
    assert (cell, alert) == (text, red)
    lines = tooltip.splitlines()
    assert lines[-3:] == [
        "Delivered: not recorded.",
        "To see what cage 5 received, run this in a terminal on the Pi:",
        COMMAND,
    ]
    assert "Delivered: 0.991 mL" not in lines


REMAINDER_0_001 = "The remaining 0.001 mL is below the smallest schedule (0.10 mL)."
NOT_DELIVERED_0_001 = (
    "0.001 mL was not delivered in this run, below the smallest schedule (0.10 mL)."
)


@pytest.mark.parametrize(
    "mode, delivered, last_line",
    [
        ('staggered', 0.9996, STARTS_OVER),
        ('staggered', 0.9994, REMAINDER_0_001),
        ('instant', 0.9996, SKIPS_PASSED),
        ('instant', 0.9994, NOT_DELIVERED_0_001),
    ],
    ids=['staggered-0.0004', 'staggered-0.0006', 'instant-0.0004', 'instant-0.0006'],
)
def test_a_remainder_too_small_to_show_is_not_offered(mode, delivered, last_line):
    """Below 0.0005 mL the remainder would read 0.000 mL: nothing is said of it.
    From 0.0005 mL it is said, and that it is below the smallest schedule."""
    _text, tooltip, _red = _cell(_run('stopped', delivered=delivered, delivery_mode=mode))
    assert tooltip.splitlines()[-1] == last_line


def _run_37(mode='staggered'):
    """Lab run 37 (2026-10-19): 0.6 mL scheduled, stopped after 12 pulses of
    0.019212 mL, 0.230544 mL delivered. Its plan does not enter the
    remainder."""
    return _run(
        'stopped',
        delivered=12 * 0.019212,
        requested_ml=0.6,
        planned_ml=31 * 0.019212,
        delivery_mode=mode,
    )


def test_run_37_gives_the_remainder_and_an_amount_the_wizard_takes():
    """The tooltip said "the remaining 0.369 mL", which the wizard's two
    decimals cannot take, and the operator typed 0.36. The remainder stays
    a measured figure, to three decimals; the amount to schedule for it is
    at the wizard's two, rounded half up."""
    _text, tooltip, red = _cell(_run_37())
    assert red
    assert tooltip.splitlines()[-3:] == [
        "Delivered: 0.231 mL",
        STARTS_OVER,
        "To deliver only the remaining 0.369 mL, create a new schedule for 0.37 mL.",
    ]
    assert amount_to_schedule(0.6 - 12 * 0.019212) == "0.37"


@pytest.mark.parametrize(
    ("requested", "delivered", "shown", "amount"),
    [
        (1.0, 0.635, "0.365", "0.37"),
        (0.3, 0.025, "0.275", "0.28"),
        (1.0, 0.636, "0.364", "0.36"),
        (1.0, 0.634, "0.366", "0.37"),
    ],
    ids=["0.365", "0.275-in-floating-point", "0.364", "0.366"],
)
def test_an_exact_half_at_the_third_decimal_rounds_up(requested, delivered, shown, amount):
    """Half up, on the figure the operator reads. 1.0 − 0.635 is 0.365,
    stored as 0.36499999999999999, which float formatting rounds to 0.36: it
    is scheduled as 0.37. 0.3 − 0.025 is 0.27499999999999997 in floating
    point and shows as 0.275, so it is scheduled as 0.28, not 0.27."""
    _text, tooltip, _red = _cell(_run('stopped', delivered=delivered, requested_ml=requested))
    assert tooltip.splitlines()[-1] == (
        f"To deliver only the remaining {shown} mL, create a new schedule for {amount} mL."
    )
    assert amount_to_schedule(requested - delivered) == amount


def test_the_amount_is_the_figure_shown_rounded_half_up():
    """amount_to_schedule() rounds the remainder as shown, to three decimals,
    so the two figures on one line agree: 0.3649 shows as 0.365 and is
    scheduled as 0.37, as the operator reading 0.365 rounds it, not 0.36."""
    assert amount_to_schedule(0.369456) == "0.37"
    assert amount_to_schedule(0.365) == "0.37"
    assert amount_to_schedule(0.3649) == "0.37", "0.3649 shows as 0.365"
    assert amount_to_schedule(0.3644) == "0.36", "0.3644 shows as 0.364"
    assert amount_to_schedule(0.1) == "0.10"
    assert amount_to_schedule(0.0949) == "0.10", "0.0949 shows as 0.095"
    assert amount_to_schedule(0.0944) is None, "0.0944 shows as 0.094: below 0.10 mL"
    assert amount_to_schedule(None) is None


def test_the_amount_agrees_with_the_remainder_on_its_line():
    """Run 37's schedule stopped after 19 pulses instead of 12: 0.6 − 19 ×
    0.019212 is 0.234972 mL, shown as 0.235 and scheduled as 0.24. Rounding
    the float would put 0.23 beside 0.235. Either plans the 12 pulses that
    did not fire."""
    q = 0.019212
    run = _run('stopped', delivered=19 * q, requested_ml=0.6, planned_ml=31 * q)
    _text, tooltip, _red = _cell(run)
    assert tooltip.splitlines()[-1] == (
        "To deliver only the remaining 0.235 mL, create a new schedule for 0.24 mL."
    )
    assert whole_pulses(0.24, q) == whole_pulses(0.23, q) == 31 - 19


@pytest.mark.parametrize(
    ("mode", "delivered", "last_line"),
    [
        ('staggered', 0.551, "The remaining 0.049 mL is below the smallest schedule (0.10 mL)."),
        ('staggered', 0.506, "The remaining 0.094 mL is below the smallest schedule (0.10 mL)."),
        (
            'instant',
            0.551,
            "0.049 mL was not delivered in this run, below the smallest schedule (0.10 mL).",
        ),
        (
            'staggered',
            0.505,
            "To deliver only the remaining 0.095 mL, create a new schedule for 0.10 mL.",
        ),
    ],
    ids=['staggered-0.049', 'staggered-0.094', 'instant-0.049', 'staggered-0.095'],
)
def test_a_remainder_below_the_smallest_schedule_offers_no_schedule(mode, delivered, last_line):
    """The wizard takes 0.10 mL or more. A remainder whose amount at two
    decimals is below that gets no schedule, and the tooltip says why. 0.6 −
    0.505 is 0.09499999999999997 in floating point and shows as 0.095, so
    it is scheduled as 0.10."""
    run = _run('stopped', delivered=delivered, requested_ml=0.6, delivery_mode=mode)
    _text, tooltip, _red = _cell(run)
    assert tooltip.splitlines()[-1] == last_line
    if "below" in last_line:
        assert "create a new schedule" not in tooltip
        assert "delivery log" not in tooltip, "nothing to check before a schedule"


def test_an_instant_run_checks_the_delivery_log_first_and_gives_the_amount_the_same_way():
    """Run 37 as an instant run: what was not delivered to three decimals,
    the delivery log first, and the amount to schedule if all of it is
    missing, at the wizard's two decimals."""
    _text, tooltip, _red = _cell(_run_37('instant'))
    assert tooltip.splitlines()[-3:] == [
        SKIPS_PASSED,
        "0.369 mL was not delivered in this run. If it started after some delivery times "
        "had passed, an earlier run may already have given them. Check the delivery log "
        "first, then create a new schedule for what is missing (0.37 mL if all of it is "
        "missing):",
        COMMAND,
    ]
    run = _run('stopped', delivered=0.505, requested_ml=0.6, delivery_mode='instant')
    _text, tooltip, _red = _cell(run)
    assert "(0.10 mL if all of it is missing):" in tooltip, "0.095 shows, 0.10 is offered"


def test_the_remainder_is_scheduled_minus_delivered_and_unknown_when_not_recorded():
    assert remaining_ml(_run('stopped', delivered=0.4)) == pytest.approx(0.6)
    assert remaining_ml(_run('stopped', delivered=0.0)) == pytest.approx(1.0)
    assert remaining_ml(_run('completed', delivered=1.025)) == 0.0, "never below 0"
    assert remaining_ml(_run('interrupted', delivered=None)) is None


def test_the_remainder_offered_for_a_new_schedule_is_one_that_shows():
    """owed_ml(): the remainder, unless it was not recorded or would show as
    0.000 mL. The tooltip and Run's question offer only this one."""
    assert owed_ml(_run('stopped', delivered=0.4)) == pytest.approx(0.6)
    assert owed_ml(_run('stopped', delivered=0.9994)) == pytest.approx(0.0006)
    assert owed_ml(_run('stopped', delivered=0.9996)) is None
    assert owed_ml(_run('completed', delivered=1.025)) is None
    assert owed_ml(_run('interrupted', delivered=None)) is None


def test_the_delivery_log_command_lists_the_cage_from_the_runs_day():
    assert delivery_log_command("2026-10-09T07:00:00", 5) == COMMAND
    every_cage = delivery_log_command("2026-10-09T07:00:00", None)
    assert every_cage.endswith("tools/gravimetric_check.py daily --since 2026-10-09")
    assert delivery_log_command(None, 5).endswith("tools/gravimetric_check.py daily --cage 5")
    _text, tooltip, _red = _cell(_run('interrupted', delivered=None, relay_unit_id=None))
    assert tooltip.splitlines()[-2:] == [
        "To see what each cage received, run this in a terminal on the Pi:",
        every_cage,
    ]


@pytest.mark.parametrize(
    "outcome, word",
    [
        ('running', "Running"),
        ('stopped', "Stopped"),
        ('incomplete', "Incomplete"),
        ('interrupted', "Interrupted"),
        ('cancelled', "Cancelled"),
    ],
)
def test_the_outcome_word_is_the_one_the_cell_starts_with(outcome, word):
    """The animal export writes this word as the run's result, so the file and
    the cell say the same."""
    text, _tooltip, _red = _cell(_run(outcome))
    assert outcome_word(outcome) == word
    assert text.startswith(f"{word} · ")


def test_a_completed_run_has_a_word_too_and_no_run_has_none():
    """A completed cell shows only the amount; the export still names the result."""
    assert outcome_word('completed') == "Completed"
    assert outcome_word(None) == ""
