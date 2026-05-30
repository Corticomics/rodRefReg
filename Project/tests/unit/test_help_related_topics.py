"""Regression test for Related-topics link spacing in help pages (QA item #12).

The CSS uses ``margin-right`` on the inline ``<a>`` links, but QTextBrowser's
rich-text engine ignores margins on inline elements, so the links rendered
concatenated with no gap (e.g. "First Time SetupBasic OperationsExecution
Monitor"). The generator now joins them with an explicit non-breaking-space
separator. This is a pure string test — no Qt required.
"""

from __future__ import annotations

from utils.help_content_manager import HelpContentManager


def test_related_topic_links_are_separated():
    mgr = HelpContentManager()

    # System Overview has several related topics.
    related = mgr.get_related("System Overview")
    assert len(related) > 1

    html = mgr.get_content("System Overview")
    # No two links are rendered directly adjacent (the old concatenation bug).
    assert "</a><a" not in html
    # An explicit separator sits between the links.
    assert "&middot;" in html
