"""Help explains the Animals tab's Last schedule delivered amount column.

The Animals topic is where an operator reads, without hovering, what a red
cell means and what to do about it: a staggered schedule run again starts
over, an instant one skips the delivery times that have passed. Help's
search ranks title hits, then keyword hits (any keyword that contains the
query), then body hits. The topic is found through its text and gets no new
keyword, so a search for "stop" still lists Safety Features first. Pure
string tests, no Qt.
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
