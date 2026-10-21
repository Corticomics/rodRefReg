"""The calibration wizard's warning line follows the theme (v2.1.0).

Its first step wrote "Before proceeding, ensure:" in a fixed red (#d32f2f), 2.42:1 on the
dark card. The rich text now takes the theme's danger.text when the step is built; the
wizard is modal, so the theme cannot change while the step shows. Rendered offscreen in
both themes; colours are compared with the tokens.
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


@pytest.mark.parametrize("theme", THEMES)
def test_the_first_steps_warning_line_is_in_the_themes_danger_colour(qapp, tokens, style, theme):
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtWidgets import QLabel  # noqa: PLC0415
    from ui.CalibrationWizard import CalibrationWizard  # noqa: PLC0415

    manager, windows = style
    manager.apply(theme)
    controller = MagicMock()
    controller.settings = {"valve_topology": "shared_manifold"}
    database = MagicMock()
    database.get_all_valve_calibrations.return_value = {}
    wizard = CalibrationWizard(cage_id=3, database_handler=database, system_controller=controller)
    wizard.resize(720, 760)
    wizard.show()
    qapp.processEvents()
    windows.append(wizard)

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
