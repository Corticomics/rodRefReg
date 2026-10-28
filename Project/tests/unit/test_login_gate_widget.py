"""Regression guard for the logged-out login prompt (QA items #1, #3).

Item #3: the prompt used to carry a "Login" button that only re-selected the
already-current Profile tab, so it appeared to do nothing — it has been removed.
Item #1: the prompt now carries the ``LoginGatePrompt`` objectName that the
theme QSS styles. Since v2.1.0 it is drawn as the tab pane it stands in for (the
content layer's fill and stroke): in the dark theme, now the default, it was a
raised card slab that turned into a page-coloured pane on login.

Skips when PyQt5 is unavailable; CI installs ``python3-pyqt5`` so it runs there.
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


@pytest.fixture
def style(qapp):
    """A StyleManager on the app, as main.py makes one; the app's palette, stylesheet, font
    and style_manager property come back afterwards."""
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


def _make_gate(qapp):
    from PyQt5.QtCore import QObject, pyqtSignal  # noqa: PLC0415
    from PyQt5.QtWidgets import QWidget  # noqa: PLC0415
    from ui.login_gate_widget import LoginGateWidget  # noqa: PLC0415

    class StubLoginSystem(QObject):
        login_status_changed = pyqtSignal()

        def is_logged_in(self):
            return False

    return LoginGateWidget(QWidget(), StubLoginSystem())


def test_login_prompt_has_no_button(qapp):
    """The needless 'Login' button is gone from the logged-out prompt."""
    from PyQt5.QtWidgets import QPushButton  # noqa: PLC0415

    gate = _make_gate(qapp)
    assert gate.login_prompt.findChildren(QPushButton) == []


def test_login_prompt_carries_the_objectname_the_theme_styles(qapp):
    """The prompt is tagged for its rule in the theme QSS."""
    gate = _make_gate(qapp)
    assert gate.login_prompt.objectName() == "LoginGatePrompt"


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_login_prompt_is_drawn_as_the_pane_it_stands_in_for(qapp, style, theme):
    """Logged out, the prompt stands where the Projects tab pane stands once logged in: the
    content layer's fill (bg.pane) inside the content layer's stroke, its message in body
    text (T1p). Not a raised card (bg.surface), which in dark is a step lighter than the
    pane that replaces it on login."""
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget  # noqa: PLC0415
    from ui.style.qt_palette import tokens  # noqa: PLC0415

    manager, windows = style
    manager.apply(theme)
    window = QWidget()
    layout = QVBoxLayout(window)
    gate = _make_gate(qapp)
    layout.addWidget(gate)
    window.resize(600, 400)
    window.show()
    qapp.processEvents()
    windows.append(window)

    prompt = gate.login_prompt
    assert gate.currentWidget() is prompt
    image = window.grab().toImage()

    def pixel(x, y):
        return image.pixelColor(prompt.mapTo(window, QPoint(x, y))).name().upper()

    middle = prompt.height() // 2
    assert pixel(0, middle) == tokens.value("border.subtle", theme)
    assert pixel(12, middle) == tokens.value("bg.pane", theme)
    assert pixel(prompt.width() // 2, 12) == tokens.value("bg.pane", theme)
    if theme == "dark":
        assert tokens.value("bg.pane", theme) != tokens.value("bg.surface", theme)
    message = prompt.findChild(QLabel)
    assert message.text() == "Please log in to access projects"
    assert message.palette().color(QPalette.WindowText).name().upper() == tokens.value(
        "text.primary", theme
    )
    behind = message.mapTo(window, QPoint(2, 2))
    assert image.pixelColor(behind).name().upper() == tokens.value("bg.pane", theme)
