"""Help opens a real topic on first view, not the redundant landing (QA #10).

The landing page repeated the same category/topic list already shown in the
left tree, so the centre and left panes were redundant on first open. HelpTab
now selects and loads the first topic instead.

Skips when PyQt5 is unavailable; CI installs python3-pyqt5 so it runs there.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


def test_first_open_loads_first_topic(qapp):
    from ui.HelpTab import HelpTab  # noqa: PLC0415

    h = HelpTab()
    h.show()  # fires showEvent -> _select_first_topic
    qapp.processEvents()

    # A real topic is loaded, not the landing page.
    assert h.current_topic_key, "no topic selected on first open"
    first_category_topics = next(iter(h.help_manager.get_categories().values()))
    assert h.current_topic_key == first_category_topics[0]
    # Breadcrumb shows the topic path rather than the bare 'Help' landing label.
    assert "›" in h.breadcrumb.text()
