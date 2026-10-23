"""Controls and Schedule Queue on screen (ui/run_stop_section.py), in both themes (v2.1.0).

They were group boxes, their titles above their boxes. They are the main screen's
permanent cards, so each is now an elevated Card, as Fluent 2 draws a card: its title
inside it (CardHeader) over a 1px rule that runs from one side of the box to the other
(Divider), then its body; in light the card shadow under the box (ui.style.elevation),
in dark none. Rendered offscreen on a page, as the main window's right column shows them;
pixels and palettes are compared with the tokens.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

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


@pytest.fixture(autouse=True)
def lock():
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


def _section(qapp, windows, system_controller, database_handler):
    """The run section alone on a page (the window paints bg.page), 700 x 420."""
    from PyQt5.QtWidgets import QVBoxLayout, QWidget  # noqa: PLC0415
    from ui.run_stop_section import RunStopSection  # noqa: PLC0415

    login = MagicMock()
    login.is_logged_in.return_value = True
    section = RunStopSection(
        MagicMock(return_value=True),
        MagicMock(),
        MagicMock(),
        system_controller=system_controller,
        database_handler=database_handler,
        login_system=login,
    )
    window = QWidget()
    QVBoxLayout(window).addWidget(section)
    window.resize(700, 420)
    window.show()
    qapp.processEvents()
    windows.append(window)
    return window, section


@pytest.mark.parametrize("theme", THEMES)
def test_controls_and_the_queue_are_cards_with_their_titles_inside(
    qapp, tokens, style, system_controller, database_handler, theme
):
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from ui.components.card import Card, CardHeader, Divider  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    window, section = _section(qapp, windows, system_controller, database_handler)
    manager.apply(theme)  # a theme applied after the section exists reaches it
    qapp.processEvents()

    def colour(role):
        return tokens.value(role, theme)

    cards = [card for card in section.findChildren(Card) if card.property("elevation")]
    titles = [card.findChild(CardHeader).text() for card in cards]
    assert titles == ["Controls", "Schedule Queue"]
    bodies = (section.run_button, section.schedule_drop_area)
    image = window.grab().toImage()

    def pixel(widget, x, y):
        return image.pixelColor(widget.mapTo(window, QPoint(x, y))).name().upper()

    for card, body in zip(cards, bodies):
        header, rule = card.findChild(CardHeader), card.findChild(Divider)
        assert header.palette().color(QPalette.WindowText).name().upper() == colour("text.primary")
        box = card.elevation_box()

        def top_of(widget, card=card):
            return widget.mapTo(card, QPoint(0, 0)).y()

        # The title sits inside the box, the rule under it, then the body
        assert box.top() < top_of(header) < top_of(rule) < top_of(body), titles
        assert rule.height() == 1
        # The rule runs from the box's stroke on one side to its stroke on the other
        y = top_of(rule)
        assert pixel(card, box.left(), y) == colour("border.subtle")
        for x in (box.left() + 1, box.center().x(), box.right() - 1):
            assert pixel(card, x, y) == colour("border.divider"), (card, x)
        assert pixel(card, box.right(), y) == colour("border.subtle")
        assert pixel(card, box.center().x(), y + 2) == colour("bg.surface")
        # The card shadow: under the box in light, none in dark
        under = pixel(card, box.center().x(), box.bottom() + 1)
        if theme == "light":
            assert under != colour("bg.page"), "the card's shadow, under its box"
        else:
            assert under == colour("bg.page"), "no shadow in dark"
