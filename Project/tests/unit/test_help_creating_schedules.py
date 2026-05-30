"""Regression test for the Creating Schedules help topic (QA item #16).

The topic used to describe a three-column drag-an-animal-onto-a-relay-unit
builder that no longer exists; users following it got stuck. It now describes
the Wizard flow and explains that a cage maps directly to a relay/solenoid
(QA item #15's point of confusion). Pure string test — no Qt required.
"""

from __future__ import annotations

from utils.help_content_manager import HelpContentManager


def test_creating_schedules_describes_wizard_not_drag_builder():
    html = HelpContentManager().get_content("Creating Schedules")

    # The obsolete manual drag-to-relay-unit builder is gone.
    assert "relay unit slot" not in html
    assert "Save Current Assignments" not in html
    assert "Clear All Assignments" not in html

    # The current Wizard flow is described.
    for step in ("Select Type", "Select Animals", "Configure", "Review"):
        assert step in html

    # The cage-to-relay mapping is spelled out (item #15).
    assert "cage 1 is relay 1" in html
