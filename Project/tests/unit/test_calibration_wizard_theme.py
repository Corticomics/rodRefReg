"""The calibration wizard follows the theme (v2.1.0).

Its first step wrote "Before proceeding, ensure:" in a fixed red (#d32f2f), 2.42:1 on the
dark card. The rich text now takes the theme's danger.text when the step is built; the
wizard is modal, so the theme cannot change while the step shows. The run's progress bar
and the log sit on the dialog's page, whose colour their fills share: their outlines show
them. Rendered offscreen in both themes; colours are compared with the tokens.
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


def _wizard(qapp, windows):
    from ui.CalibrationWizard import CalibrationWizard  # noqa: PLC0415

    controller = MagicMock()
    controller.settings = {"valve_topology": "shared_manifold"}
    database = MagicMock()
    database.get_all_valve_calibrations.return_value = {}
    wizard = CalibrationWizard(cage_id=3, database_handler=database, system_controller=controller)
    wizard.resize(720, 760)
    wizard.show()
    qapp.processEvents()
    windows.append(wizard)
    return wizard


@pytest.mark.parametrize("theme", THEMES)
def test_the_first_steps_warning_line_is_in_the_themes_danger_colour(qapp, tokens, style, theme):
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtWidgets import QLabel  # noqa: PLC0415

    manager, windows = style
    manager.apply(theme)
    wizard = _wizard(qapp, windows)

    danger = tokens.value("danger.text", theme)
    intro = next(
        label
        for label in wizard.content_widget.findChildren(QLabel)
        if "Before proceeding, ensure:" in label.text()
    )
    assert f"<b style='color: {danger.lower()};'>Before proceeding, ensure:</b>" in intro.text()

    # Drawn on the step's card, where the contrast test pairs the two (T14d)
    image = wizard.grab().toImage()
    card = wizard.content_widget
    inside = card.mapTo(wizard, QPoint(4, card.height() // 2))
    assert image.pixelColor(inside).name().upper() == tokens.value("bg.surface", theme)
    top = intro.mapTo(wizard, QPoint(0, 0))
    drawn = {
        image.pixelColor(top.x() + x, top.y() + y).name().upper()
        for x in range(intro.width())
        for y in range(intro.height())
    }
    assert danger in drawn


@pytest.mark.parametrize("theme", THEMES)
def test_the_runs_progress_bar_shows_its_length_on_the_page(qapp, tokens, style, theme):
    """The bar's outline shows how long it is on the page: 2px of the bar's 8px, which it
    had before the outline. In dark the groove (bg.track) is the page's colour, so the
    outline alone shows it; in light the groove is also a step darker than the page."""
    from PyQt5.QtCore import QPoint  # noqa: PLC0415

    manager, windows = style
    manager.apply(theme)
    wizard = _wizard(qapp, windows)
    bar = wizard.progress_bar
    bar.setVisible(True)  # as the run shows it, 100 pulses into 250
    bar.setRange(0, 250)
    bar.setValue(100)
    qapp.processEvents()

    def colour(role):
        return tokens.value(role, theme)

    image = wizard.grab().toImage()

    def pixel(widget, x, y):
        return image.pixelColor(widget.mapTo(wizard, QPoint(x, y))).name().upper()

    assert bar.height() == 8
    middle = bar.height() // 2
    assert pixel(bar, bar.width() // 2, -3) == colour("bg.page")  # the dialog around it
    assert pixel(bar, bar.width() - 1, middle) == colour("border.subtle")  # its far end
    assert pixel(bar, bar.width() * 3 // 4, middle) == colour("bg.track")  # still to go
    assert pixel(bar, bar.width() // 5, middle) == colour("accent.indicator")  # done
    if theme == "light":
        assert colour("bg.track") != colour("bg.page")
    else:
        assert colour("bg.track") == colour("bg.page"), "the outline is what shows the groove"

    log = wizard.log_output
    assert pixel(log, 0, log.height() // 2) == colour("border.subtle")
    assert pixel(log, 6, log.height() // 2) == colour("bg.inset")
