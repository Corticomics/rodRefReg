"""The Cages tab follows the theme (v2.1.0).

Its title, the hint on its board card and the missing-picture placeholder had inline
colours, and the board card its own `QFrame#Card {...}` sheet, which outranked the
theme's card rule: in the dark theme the card stayed white and the title was dark on the
dark page (1.06:1). They now come from tokens.py through the theme stylesheet: the
theme's QFrame#Card rule, and QLabel#CagesTitle, #CagesSubtitle and
#CagesBoardPlaceholder. Rendered offscreen in both themes; pixels and palettes are
compared with the tokens.
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


def _cages_tab(qapp, windows, database_handler, system_controller):
    """The Cages tab in a tab pane, as ProjectsSection shows it."""
    from PyQt5.QtWidgets import QTabWidget  # noqa: PLC0415
    from ui.cages_visualization_tab import CagesVisualizationTab  # noqa: PLC0415

    system_controller.settings["num_hats"] = 1
    tab = CagesVisualizationTab(database_handler, system_controller, lambda _msg: None)
    window = QTabWidget()
    window.addTab(tab, "Cages")
    window.resize(1115, 760)
    window.show()
    qapp.processEvents()
    windows.append(window)
    return window, tab


def _pixel(window, widget, x, y):
    from PyQt5.QtCore import QPoint  # noqa: PLC0415

    image = window.grab().toImage()
    return image.pixelColor(widget.mapTo(window, QPoint(x, y))).name().upper()


def _text(widget):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    return widget.palette().color(QPalette.WindowText).name().upper()


@pytest.mark.parametrize("theme", THEMES)
def test_the_cages_tab_follows_the_theme(
    qapp, tokens, style, database_handler, system_controller, theme
):
    from PyQt5.QtGui import QFont  # noqa: PLC0415
    from PyQt5.QtWidgets import QFrame, QLabel  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    window, tab = _cages_tab(qapp, windows, database_handler, system_controller)
    manager.apply(theme)  # a theme applied after the tab exists reaches it
    qapp.processEvents()

    def colour(role):
        return tokens.value(role, theme)

    title = tab.findChild(QLabel, "CagesTitle")
    assert title.text() == "Relay Board Layout"
    assert _text(title) == colour("text.primary")
    assert title.font().pixelSize() == 18 and title.font().weight() >= QFont.Bold

    card = tab.findChild(QFrame, "Card")
    middle = card.height() // 2
    assert _pixel(window, card, 0, middle) == colour("border.subtle")
    assert _pixel(window, card, 8, middle) == colour("bg.surface")  # its 16px side margin

    hint = tab.findChild(QLabel, "CagesSubtitle")
    assert hint.text() == "Double-click a cage to rename it"
    assert _text(hint) == colour("text.secondary")
    assert (hint.font().pixelSize(), hint.font().italic()) == (13, True)

    # The legend's dots key the terminals' colours, on the page (M1, M14)
    legend = tab._master_legend_dot
    assert legend.objectName() == "MasterStatusDot"
    assert _text(legend) == colour("warning.indicator.status-dot")


@pytest.mark.parametrize("theme", THEMES)
def test_the_board_placeholder_follows_the_theme(
    qapp, tokens, style, database_handler, system_controller, theme, monkeypatch
):
    """Shown in place of the board's picture when its file is missing."""
    import ui.cages_visualization_tab as module  # noqa: PLC0415
    from PyQt5.QtWidgets import QLabel  # noqa: PLC0415

    exists = module.os.path.exists
    monkeypatch.setattr(
        module.os.path, "exists", lambda path: not path.endswith(".png") and exists(path)
    )
    manager, windows = style
    manager.apply(theme)
    _window, tab = _cages_tab(qapp, windows, database_handler, system_controller)

    placeholder = tab.findChild(QLabel, "CagesBoardPlaceholder")
    assert placeholder.text() == "[Board Diagram Not Found]"
    assert _text(placeholder) == tokens.value("text.muted", theme)
    assert placeholder.font().pixelSize() == 14


@pytest.mark.parametrize("theme", THEMES)
def test_the_cage_name_editor_keeps_its_teal_edge(
    qapp, tokens, style, database_handler, system_controller, theme
):
    """Double-clicking a cage opens its name editor with the focus; it hides again when
    editing ends. Its own rule outranks QLineEdit:focus, so its 1px edge is its focus cue:
    focus.ring, as it was teal before v2.1.0."""
    from PyQt5.QtWidgets import QFrame  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    window, tab = _cages_tab(qapp, windows, database_handler, system_controller)
    manager.apply(theme)  # a theme applied after the tab exists reaches it
    terminal = next(
        frame
        for frame in tab.findChildren(QFrame, "RelayTerminal")
        if getattr(frame, "_name_edit", None) is not None
    )
    terminal._start_editing()
    qapp.processEvents()

    edit = terminal._name_edit
    assert edit.isVisible()
    ring = tokens.value("focus.ring", theme)
    assert _pixel(window, edit, edit.width() // 2, 0) == ring  # top edge
    assert _pixel(window, edit, 0, edit.height() // 2) == ring  # left edge
