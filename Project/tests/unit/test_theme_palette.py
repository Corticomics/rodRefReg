"""The theme's QPalette on screen: what the stylesheet does not paint follows the theme.

StyleManager.apply sets a QPalette built from tokens.py (qt_palette.py), then the theme's
stylesheet. Before v2.1.0 there was no palette: Qt kept its own light one under the dark
stylesheet, so dark tables alternated with near-white rows under light text. A
universal QWidget rule also painted the page colour into every container, which the grey
page would show as boxes inside white cards. Rendered offscreen; pixels are compared with
the tokens.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"
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
    """A StyleManager on the app, as main.py makes one, and a list for the test's widgets.

    The app's palette, stylesheet, font and style_manager property come back afterwards.
    """
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from ui.style.theme import StyleManager  # noqa: PLC0415

    old = (QPalette(qapp.palette()), qapp.styleSheet(), qapp.font())
    manager = StyleManager(qapp)
    qapp.setProperty("style_manager", manager)
    widgets = []
    yield manager, widgets
    for widget in widgets:
        widget.close()
        widget.deleteLater()
    qapp.setProperty("style_manager", None)
    manager.deleteLater()
    qapp.setStyleSheet(old[1])
    qapp.setPalette(old[0])
    qapp.setFont(old[2])
    qapp.processEvents()


def _show(qapp, widgets, widget, width=420, height=320):
    widgets.append(widget)
    widget.resize(width, height)
    widget.show()
    qapp.processEvents()
    return widget


def _pixel(image, x, y):
    return image.pixelColor(x, y).name().upper()


# ---- The palette -----------------------------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_the_palette_takes_its_roles_from_the_tokens(qapp, tokens, theme):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from ui.style.qt_palette import build_palette  # noqa: PLC0415

    palette = build_palette(theme)
    for role_name, token in tokens.QPALETTE.items():
        role = getattr(QPalette, role_name)
        disabled = tokens.QPALETTE_DISABLED.get(role_name, token)
        for group, name in (
            (QPalette.Active, token),
            (QPalette.Inactive, token),
            (QPalette.Disabled, disabled),
        ):
            colour = palette.color(group, role)
            assert colour.name().upper() == tokens.value(name, theme), (role_name, group)
            assert colour.alpha() == 255, (role_name, group)


def test_apply_sets_the_palette_and_the_stylesheet_and_says_so(qapp, tokens, style):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    manager, _ = style
    seen = []
    manager.theme_changed.connect(seen.append)

    manager.apply("dark")
    assert manager.theme == "dark"
    window = qapp.palette().color(QPalette.Window).name().upper()
    assert window == tokens.value("bg.page", "dark")
    assert qapp.styleSheet() == (STYLE_DIR / "app-dark.qss").read_text(encoding="utf-8")
    assert manager.colour("bg.alt") == tokens.value("bg.alt", "dark")
    assert manager.tokens()["text.primary"] == tokens.value("text.primary", "dark")

    manager.apply("sepia")  # unknown: light
    assert manager.theme == "light"
    assert qapp.styleSheet() == (STYLE_DIR / "app-light.qss").read_text(encoding="utf-8")
    assert seen == ["dark", "light"]


# ---- Containers, tables, placeholders --------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_a_plain_container_in_a_card_shows_the_card(qapp, tokens, style, theme):
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtWidgets import (  # noqa: PLC0415
        QFrame,
        QLabel,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )

    manager, widgets = style
    manager.apply(theme)

    window = QWidget()
    card = QFrame()
    card.setObjectName("Card")
    plain = QWidget()  # a layout container, as the UI uses everywhere
    plain.setMinimumSize(200, 60)
    QVBoxLayout(plain).addWidget(QLabel("in a plain container"))
    scroll = QScrollArea()  # its content widget gets autoFillBackground
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidgetResizable(True)
    content = QWidget()
    content.setMinimumSize(200, 60)
    scroll.setWidget(content)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(16, 16, 16, 16)
    card_layout.addWidget(plain)
    card_layout.addWidget(scroll)
    QVBoxLayout(window).addWidget(card)
    _show(qapp, widgets, window)

    image = window.grab().toImage()

    def at(widget, x=4, y=4):
        point = widget.mapTo(window, QPoint(x, y))
        return _pixel(image, point.x(), point.y())

    assert _pixel(image, 2, 2) == tokens.value("bg.page", theme), "the window is the page"
    assert at(card, 40, 8) == tokens.value("bg.surface", theme)  # clear of the round corner
    assert at(plain) == tokens.value("bg.surface", theme), "a plain container shows the card"
    assert at(content) == tokens.value("bg.surface", theme), "so does a scroll area's content"


@pytest.mark.parametrize("theme", THEMES)
def test_zebra_rows_are_the_themes_alternate_colour(qapp, tokens, style, theme):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import (  # noqa: PLC0415
        QTableWidget,
        QTableWidgetItem,
        QTreeWidget,
        QTreeWidgetItem,
    )

    manager, widgets = style
    manager.apply(theme)
    surface, alternate = tokens.value("bg.surface", theme), tokens.value("bg.alt", theme)

    table = QTableWidget(4, 2)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setDefaultSectionSize(40)
    for row in range(4):
        for column in range(2):
            table.setItem(row, column, QTableWidgetItem(""))
    _show(qapp, widgets, table)
    assert table.palette().color(QPalette.AlternateBase).name().upper() == alternate
    image = table.viewport().grab().toImage()
    rows = [_pixel(image, 10, table.rowViewportPosition(row) + 8) for row in range(4)]
    assert rows == [surface, alternate, surface, alternate]

    # A view no stylesheet rule names alternates in the palette's AlternateBase
    tree = QTreeWidget()
    tree.setAlternatingRowColors(True)
    tree.setHeaderHidden(True)
    tree.addTopLevelItems([QTreeWidgetItem([""]) for _ in range(4)])
    _show(qapp, widgets, tree)
    first, second = (tree.visualItemRect(tree.topLevelItem(i)) for i in (0, 1))
    image = tree.viewport().grab().toImage()
    assert _pixel(image, first.right() - 4, second.center().y()) == alternate


@pytest.mark.parametrize("theme", THEMES)
def test_a_placeholder_keeps_its_full_colour(qapp, tokens, style, theme):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import QFrame, QGroupBox, QLineEdit, QVBoxLayout  # noqa: PLC0415

    manager, widgets = style
    manager.apply(theme)

    card = QFrame()
    card.setObjectName("Card")
    group = QGroupBox("Filter")  # its stylesheet rule sets a colour
    edit = QLineEdit()
    edit.setPlaceholderText("Search animals...")
    QVBoxLayout(group).addWidget(edit)
    QVBoxLayout(card).addWidget(group)
    _show(qapp, widgets, card)

    placeholder = edit.palette().color(QPalette.PlaceholderText)
    assert placeholder.alpha() == 255, "a stylesheet colour reached the input"
    assert placeholder.name().upper() == tokens.value("text.muted", theme)
    assert edit.palette().color(QPalette.Text).name().upper() == tokens.value(
        "text.primary", theme
    )


def test_a_colour_on_an_input_would_halve_its_placeholder(qapp, tokens, style):
    """Why no rule colours an input: Qt draws the placeholder at half that colour's alpha."""
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import QLineEdit  # noqa: PLC0415

    manager, widgets = style
    manager.apply("light")
    edit = QLineEdit()
    edit.setPlaceholderText("Search animals...")
    edit.setStyleSheet(f"QLineEdit {{ color: {tokens.value('text.primary', 'light')}; }}")
    _show(qapp, widgets, edit, 240, 40)
    assert edit.palette().color(QPalette.PlaceholderText).alpha() == 128
