"""The Execution Monitor's progress cards follow the theme (v2.1.0).

ScheduleProgressTracker used to write its colours into inline stylesheets: in the dark
theme its cards stayed white, and the card's `QFrame {...}` sheet drew a box around every
label in it, since a QLabel is a QFrame. The card, its labels, the bar and the status word
now take their colours from tokens.py through the theme stylesheet (objectNames, plus a
dynamic property for a status and for a bar's state). A bar writes its value inside it,
over the fill and the groove alike, so each fill is a shade that value reads on.
Rendered offscreen in both themes; pixels and palettes are compared with the tokens.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

THEMES = ("light", "dark")

# The QApplication this module uses, kept for the rest of the session. When a
# QApplication is destroyed, PyQt5 deletes every QObject without a parent.
_QAPP = []


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


@pytest.fixture
def tokens():
    from ui.style.qt_palette import tokens as table  # noqa: PLC0415

    return table


@pytest.fixture
def style(qapp):
    """A StyleManager on the app, as main.py makes one, and a list for the test's windows.

    The app's palette, stylesheet, font and style_manager property come back afterwards.
    """
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from ui.style.theme import StyleManager  # noqa: PLC0415

    old = (QPalette(qapp.palette()), qapp.styleSheet(), qapp.font())
    manager = StyleManager(qapp)
    qapp.setProperty("style_manager", manager)
    windows = []
    yield manager, windows
    for window in windows:
        window.close()
        window.deleteLater()
    qapp.setProperty("style_manager", None)
    manager.deleteLater()
    qapp.setStyleSheet(old[1])
    qapp.setPalette(old[0])
    qapp.setFont(old[2])
    qapp.processEvents()


def _tracker(qapp, windows, animals=5):
    """The tracker in a tab pane, as the Execution Monitor shows it, with its cards."""
    from PyQt5.QtWidgets import QTabWidget  # noqa: PLC0415
    from ui.ScheduleProgressTracker import ScheduleProgressTracker  # noqa: PLC0415

    tabs = QTabWidget()
    tracker = ScheduleProgressTracker()
    tabs.addTab(tracker, "Execution Monitor")
    tabs.resize(1100, 420)
    tabs.show()
    qapp.processEvents()
    tracker.start_schedule(
        "Morning", {i: {"cage_id": i, "target_volume": 1.0} for i in range(1, animals + 1)}
    )
    tracker._stop_all_timers()
    qapp.processEvents()
    windows.append(tabs)
    return tabs, tracker


def _pixel(window, widget, x, y):
    from PyQt5.QtCore import QPoint  # noqa: PLC0415

    image = window.grab().toImage()
    return image.pixelColor(widget.mapTo(window, QPoint(x, y))).name().upper()


def _bar(window, bar, fraction):
    """The bar's colour at `fraction` of its width, on its middle row."""
    return _pixel(window, bar, int(bar.width() * fraction), bar.height() // 2)


def _text(widget, role_name="WindowText"):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    return widget.palette().color(getattr(QPalette, role_name)).name().upper()


@pytest.mark.parametrize("theme", THEMES)
def test_the_cards_follow_the_theme(qapp, tokens, style, theme):
    from PyQt5.QtGui import QFont  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    tabs, tracker = _tracker(qapp, windows)
    tracker.update_animal_progress(2, 0.5, status="Delivering")
    tracker.update_animal_progress(3, 1.0, status="Complete")
    tracker.update_animal_progress(4, 0.3, status="Failed")
    tracker.update_animal_progress(5, 0.6, status="Incomplete")
    manager.apply(theme)  # a theme applied after the cards exist reaches them
    qapp.processEvents()

    def colour(role):
        return tokens.value(role, theme)

    waiting, delivering, complete, failed, incomplete = (tracker.cards[i] for i in range(1, 6))
    for card in tracker.cards.values():
        assert _pixel(tabs, card, card.width() - 4, card.height() // 2) == colour("bg.surface")
        assert _text(card.animal_label) == _text(card.volume_label) == colour("text.primary")
        assert _pixel(tabs, card.cage_badge, 4, card.cage_badge.height() // 2) == colour(
            "accent.fill"
        )
        assert _text(card.cage_badge) == colour("text.on-accent")
        assert _text(card.progress_bar, "Text") == colour("text.primary")
        # No box around a label: its top row shows the card
        for label in (card.animal_label, card.volume_label, card.status_label):
            assert _pixel(tabs, label, label.width() // 2, 0) == colour("bg.surface"), label.text()

    # The status word: muted and regular until the first update, then bold in its colour
    assert _text(waiting.status_label) == colour("text.muted")
    assert waiting.status_label.font().weight() < QFont.DemiBold
    for card, role in (
        (delivering, "text.accent"),
        (complete, "success.text"),
        (failed, "danger.text"),
        (incomplete, "text.muted"),
    ):
        assert _text(card.status_label) == colour(role), card.status_label.text()
        assert card.status_label.font().weight() >= QFont.DemiBold

    # The bars: a fill the value reads on, over the groove of the bar's state
    assert _bar(tabs, delivering.progress_bar, 0.2) == colour("progress.fill")
    assert _bar(tabs, delivering.progress_bar, 0.85) == colour("bg.track")
    assert _bar(tabs, complete.progress_bar, 0.2) == colour("progress.fill.complete")
    assert _bar(tabs, failed.progress_bar, 0.1) == colour("progress.fill.failed")
    assert _bar(tabs, failed.progress_bar, 0.85) == colour("danger.tint")
    # Incomplete is not a bar state: the bar keeps the running colours
    assert _bar(tabs, incomplete.progress_bar, 0.2) == colour("progress.fill")


def test_a_label_keeps_the_frame_it_had_so_nothing_moves(qapp, style):
    """The card's old QFrame sheet gave each label a 1px border, and so QLabel's indent.

    The border stays, transparent (QFrame#MaterialCard QLabel): v2.1.0 changed colours,
    not the cards' layout. Removing it is a layout change for later.
    """
    manager, windows = style
    manager.apply("light")
    _tabs, tracker = _tracker(qapp, windows, animals=1)
    card = tracker.cards[1]
    for label in (card.animal_label, card.volume_label, card.status_label):
        assert label.frameWidth() == 1, label.objectName()
    assert card.progress_bar.height() == 10, "the app's QProgressBar max-height and its border"


def test_a_status_is_restyled_only_when_it_changes(qapp, style, monkeypatch):
    """Volume updates arrive many times a second; only a new status restyles the card."""
    import ui.ScheduleProgressTracker as module  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    _tabs, tracker = _tracker(qapp, windows, animals=1)
    restyled = []
    monkeypatch.setattr(module, "restyle", restyled.append)

    for millilitres in (0.1, 0.2, 0.3):
        tracker.update_animal_progress(1, millilitres, status="Delivering")
    assert restyled == [tracker.cards[1].status_label]

    tracker.update_animal_progress(1, 1.0, status="Complete")
    assert restyled[1:] == [tracker.cards[1].status_label, tracker.cards[1].progress_bar]
    tracker.update_animal_progress(1, 1.0, status="Complete")
    assert len(restyled) == 3
