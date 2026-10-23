"""The first tab meets its pane in one straight line (v2.1.0).

The owner's decision of 2026-10-23, "straighten it": where a tab bar's first tab is
selected (Terminal, Schedules, Profile), the pane's rounded top-left corner made the tab's
left edge bend into a small arc where it met the pane. The pane's top-left corner, where
the first tab sits, is now square, as in WinUI's TabView, so the selected first tab and the
pane share one straight edge. The other three corners keep the container radius, 8px.

A top-level tab widget on the page, as RRR's three are, rendered offscreen in both themes
under StyleManager; pixels are compared with the tokens. A tab widget inside a pane is a
strip over a rule with no corners at all (test_theme_structure.py).
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

THEMES = ("light", "dark")
RADIUS = 8  # a container's, the pane's other corners and the selected tab's top ones

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


def _tabs_on_the_page(qapp, widgets, selected):
    """A tab widget with three tabs on a plain page, tab `selected` current. Returns the
    page's grab, the tab widget's left x, the selected tab's top y, the pane's top y (the
    tab bar overlaps it by its margin-top of -1px), and the tab widget's right x and
    bottom y."""
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget  # noqa: PLC0415

    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    tabs = QTabWidget()
    for title in ("Schedules", "Animals", "Wizard"):
        tabs.addTab(QLabel(f"{title} pane"), title)
    tabs.setCurrentIndex(selected)
    layout.addWidget(tabs)
    widgets.append(page)
    page.resize(420, 240)
    page.show()
    qapp.processEvents()

    bar = tabs.tabBar()
    origin = tabs.mapTo(page, QPoint(0, 0))
    tab_top = bar.mapTo(page, bar.tabRect(selected).topLeft()).y()
    pane_top = bar.mapTo(page, QPoint(0, bar.height())).y() - 1
    right = origin.x() + tabs.width() - 1
    bottom = origin.y() + tabs.height() - 1
    return page.grab().toImage(), origin.x(), tab_top, pane_top, right, bottom


def _pixel(image, x, y):
    return image.pixelColor(x, y).name().upper()


@pytest.mark.parametrize("theme", THEMES)
def test_the_selected_first_tab_and_its_pane_share_one_straight_edge(qapp, tokens, style, theme):
    """Below the tab's own rounded top corner, the tab's left edge and the pane's are one
    column of stroke pixels, through the row where they meet and down the pane. With the
    pane's corner rounded, the column broke for 7 rows under that row: the arc."""
    manager, widgets = style
    manager.apply(theme)
    image, left, tab_top, pane_top, _right, bottom = _tabs_on_the_page(qapp, widgets, 0)
    stroke = tokens.value("border.subtle", theme)

    column = {y: _pixel(image, left, y) for y in range(tab_top + RADIUS, bottom - RADIUS)}

    assert pane_top - tab_top > RADIUS, "the column runs through the tab, then the pane"
    assert {y: name for y, name in column.items() if name != stroke} == {}
    assert _pixel(image, left - 1, pane_top + 1) == tokens.value("bg.page", theme)
    assert _pixel(image, left + 1, pane_top + 1) == tokens.value("bg.pane", theme)


@pytest.mark.parametrize("theme", THEMES)
def test_the_panes_corner_under_the_first_tab_is_square_whichever_tab_is_selected(
    qapp, tokens, style, theme
):
    """With another tab selected, the first tab lies flat on the page with no edge, and
    the pane's top-left corner under it is square: its stroke turns the corner, and its
    left edge runs straight up to its top one."""
    manager, widgets = style
    manager.apply(theme)
    image, left, _tab_top, pane_top, _right, bottom = _tabs_on_the_page(qapp, widgets, 1)
    stroke = tokens.value("border.subtle", theme)

    assert _pixel(image, left, pane_top) == stroke, "the corner itself"
    assert _pixel(image, left + RADIUS, pane_top) == stroke, "the top edge"
    assert {_pixel(image, left, y) for y in range(pane_top, bottom - RADIUS)} == {stroke}
    assert _pixel(image, left, pane_top - 4) == tokens.value("bg.page", theme), "no tab edge"


@pytest.mark.parametrize("theme", THEMES)
def test_the_panes_other_three_corners_keep_the_container_radius(qapp, tokens, style, theme):
    """Top-right, bottom-left and bottom-right are rounded at 8px: each corner pixel is the
    page, outside the arc, and the edges are straight stroke from 8px along."""
    manager, widgets = style
    manager.apply(theme)
    image, left, _tab_top, pane_top, right, bottom = _tabs_on_the_page(qapp, widgets, 0)
    page = tokens.value("bg.page", theme)
    stroke = tokens.value("border.subtle", theme)

    for x, y in ((right, pane_top), (left, bottom), (right, bottom)):
        assert _pixel(image, x, y) == page, (x, y)
    assert _pixel(image, right, pane_top + RADIUS) == stroke
    assert _pixel(image, right - RADIUS, pane_top) == stroke
    assert _pixel(image, left, bottom - RADIUS) == stroke
    assert _pixel(image, left + RADIUS, bottom) == stroke
    assert _pixel(image, right, bottom - RADIUS) == stroke
    assert _pixel(image, right - RADIUS, bottom) == stroke
