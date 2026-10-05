"""The Updates tab renders a release's notes instead of showing raw Markdown.

Since the release workflow publishes each version's CHANGELOG.md entry as
the GitHub Release notes, the notes an operator reads before updating are
Markdown. Shown as plain text, the "Before you update" list came out as
literal asterisks and backticks.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

NOTES = """## 1.22.0 — something new

This release also carries 1.21.1.

**Before you update**

- **Calibrate every cage** your schedules use.
- Check `max_pulse_delivery_time_s`.

<b>not html</b>
"""


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


@pytest.fixture
def tab(qapp, monkeypatch):
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "has_previous_release", lambda: False)
    from ui.UpdatesTab import UpdatesTab  # noqa: PLC0415

    return UpdatesTab()


def _info(notes, available=True):
    from utils.updater import UpdateInfo  # noqa: PLC0415

    return UpdateInfo("1.22.0", "https://example.invalid/release", notes, available)


def _blocks(document):
    block = document.begin()
    while block.isValid():
        yield block
        block = block.next()


def _bold_text(document):
    from PyQt5.QtGui import QFont  # noqa: PLC0415

    found = []
    for block in _blocks(document):
        text = block.text()
        for run in block.textFormats():
            if run.format.fontWeight() >= QFont.Bold:
                found.append(text[run.start : run.start + run.length])
    return found


def test_the_notes_are_rendered_not_shown_as_raw_markdown(tab):
    tab._on_result(_info(NOTES))

    shown = tab.notes.toPlainText()
    assert not tab.notes.isHidden()
    assert "Before you update" in shown and "Calibrate every cage" in shown
    assert "**" not in shown and "`" not in shown and "## " not in shown

    document = tab.notes.document()
    assert "Before you update" in _bold_text(document)
    assert "Calibrate every cage" in _bold_text(document)
    blocks = list(_blocks(document))
    assert any(block.blockFormat().headingLevel() == 2 for block in blocks), "the version heading"
    listed = [block.text() for block in blocks if block.textList() is not None]
    assert listed == [
        "Calibrate every cage your schedules use.",
        "Check max_pulse_delivery_time_s.",
    ]


def test_the_notes_open_at_the_top(tab):
    """The "Before you update" list is at the top of the notes; the view must
    not open at the developer notes at the bottom of a long entry."""
    long_notes = NOTES + "".join(f"\n- developer note {n}\n" for n in range(200))
    tab._on_result(_info(long_notes))

    assert tab.notes.textCursor().position() == 0
    assert tab.notes.verticalScrollBar().value() == 0


def test_shown_notes_take_the_free_height_and_hidden_ones_give_it_back(tab, qapp):
    tab.resize(820, 640)
    tab.show()
    tab._on_result(_info(NOTES))
    qapp.processEvents()

    assert tab.notes.height() > 400, "the notes fill the tab instead of a small box"

    tab._on_result(_info(NOTES, available=False))
    qapp.processEvents()

    box = tab.notes.parentWidget()
    assert box.height() < 200, "with no notes the group box shrinks back"
    tab.hide()


def test_links_are_underlined_in_the_text_colour(tab):
    """Qt gives Markdown links a fixed blue that the dark theme does not
    change; on its background they are close to invisible."""
    from PyQt5.QtGui import QTextFormat  # noqa: PLC0415

    tab._on_result(_info(NOTES + "\nSee [the docs](https://example.com/docs) and <https://example.org>.\n"))

    anchors = []
    for block in _blocks(tab.notes.document()):
        text = block.text()
        for run in block.textFormats():
            if run.format.isAnchor():
                anchors.append((text[run.start : run.start + run.length], run.format))
    assert [label for label, _ in anchors] == ["the docs", "https://example.org"]
    for _label, fmt in anchors:
        assert not fmt.hasProperty(QTextFormat.ForegroundBrush), "no fixed link colour"
        assert fmt.fontUnderline(), "still shown to be a link"


def test_raw_html_in_the_notes_stays_text(tab):
    tab._on_result(_info(NOTES))

    assert "<b>not html</b>" in tab.notes.toPlainText()
    assert "not html" not in _bold_text(tab.notes.document())


def test_being_up_to_date_hides_the_notes(tab):
    tab._on_result(_info(NOTES))
    assert not tab.notes.isHidden()

    tab._on_result(_info(NOTES, available=False))

    assert tab.notes.isHidden()
    assert tab.status_label.text().startswith("You’re up to date")
