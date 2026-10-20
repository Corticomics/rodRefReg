"""Help explains the Animals tab's Last schedule delivered amount column.

The Animals topic is where an operator reads, without hovering, what a red
cell means and what to do about it: a staggered schedule run again starts
over, an instant one skips the delivery times that have passed. It, and
Troubleshooting's Last Run Ended Early entry, quote the amount to schedule
for the rest of a run as RRR gives it, at the schedule wizard's two
decimals. Help's search ranks title hits, then keyword hits (any keyword
that contains the query), then body hits. The topic is found through its
text and gets no new keyword, so a search for "stop" still lists Safety
Features first. Pure string tests, no Qt.
"""

from __future__ import annotations

import re

from utils.help_content_manager import HelpContentManager

TOPIC = "Adding & Managing Animals"


def _text(html):
    return re.sub(r"\s+", " ", html)


def test_the_animals_topic_explains_the_column_and_what_red_means():
    html = _text(HelpContentManager().get_content(TOPIC))
    assert "<strong>Last schedule delivered amount</strong>" in html
    for word in ("Scheduled", "Planned", "Delivered", "Stopped", "Incomplete", "Interrupted"):
        assert f"<strong>{word}</strong>" in html, word
    assert (
        "Running a staggered schedule again starts it over and gives every animal its full "
        "amount again; running an instant schedule again skips the delivery times that have "
        "passed." in html
    )
    assert "for an instant run, check the delivery log first." in html
    assert "tools/gravimetric_check.py daily --since YYYY-MM-DD --cage N" in html
    assert "Use the <strong>Filter</strong> field" in html, "the field's label"
    assert "appears in the table immediately, unless the filter hides it." in html


def test_help_quotes_the_amount_to_schedule_as_rrr_writes_it():
    """The Animals topic quotes the tooltip, and Troubleshooting the Last Run
    Ended Early line, for lab run 37 (0.6 mL, stopped after 12 pulses of
    0.019212 mL), with the amount at the schedule wizard's two decimals.
    Troubleshooting then says what to do instead of starting over in the
    question's own words. All of it is taken from the code that writes it,
    so Help cannot drift."""
    from datetime import datetime  # noqa: PLC0415

    from utils.last_run_text import BELOW_SMALLEST_SCHEDULE, last_run_cell  # noqa: PLC0415
    from utils.run_warnings import last_run_lines, start_over_question  # noqa: PLC0415

    run_37 = {
        'run_id': 37,
        'schedule_name': "AM water",
        'delivery_mode': 'staggered',
        'started_at': "2026-10-19T07:00:00",
        'ended_at': "2026-10-19T07:10:00",
        'outcome': 'stopped',
        'relay_unit_id': 3,
        'lab_animal_id': "M-11",
        'requested_ml': 0.6,
        'planned_ml': 31 * 0.019212,
        'delivered_ml': 12 * 0.019212,
    }
    _cell, tooltip, _red = last_run_cell(run_37, str)
    (line,) = last_run_lines({1: run_37}, [1], datetime(2026, 10, 19, 8, 0))
    animals = _text(HelpContentManager().get_content(TOPIC))
    assert f"<em>{tooltip.splitlines()[-1]}</em>" in animals
    assert f"the remainder is {BELOW_SMALLEST_SCHEDULE}" in animals
    troubleshooting = _text(HelpContentManager().get_content("Troubleshooting"))
    assert f"<em>{line.split('; ', 1)[1]}</em>" in troubleshooting
    assert f"says it is {BELOW_SMALLEST_SCHEDULE}" in troubleshooting
    _title, question = start_over_question("AM water", [line])
    instead = question[question.index("press Cancel") : question.index("\n\nStart")]
    assert instead.endswith(
        f"where one says the remainder is {BELOW_SMALLEST_SCHEDULE}, there is none to create."
    )
    assert instead.replace("Cancel", "<strong>Cancel</strong>") in troubleshooting, (
        "Help tells what to do instead of starting over as the question does"
    )


def test_searching_for_the_column_finds_the_animals_topic():
    for query in ("delivered amount", "last schedule", "interrupted"):
        keys = [key for key, _snippet in HelpContentManager().search(query)]
        assert TOPIC in keys, query


def test_searching_for_stop_lists_safety_features_before_the_animals_topic():
    """The topic says Stop and Stopped, so "stop" finds it, in the body: a
    keyword such as "stopped" would rank it above the emergency-stop topic."""
    keys = [key for key, _snippet in HelpContentManager().search("stop")]
    assert TOPIC in keys
    assert keys.index("Safety Features") < keys.index(TOPIC)
