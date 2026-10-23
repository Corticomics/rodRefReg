"""Card elevation on screen (ui/style/elevation.py): the shadow an elevated card paints.

A card mixes in ElevatedMixin, which sets its `elevation` property; the stylesheet's
QFrame[elevation="card"] rule reserves room round the card's box (build_qss.py writes it
from tokens.SHADOWS), Qt draws the box inside it, and the mixin paints a cached 9-slice
shadow tile round the box, in the recipe tokens.ELEVATION names for the current theme. These
tests render offscreen with the app's StyleManager and compare pixels with the CSS
definition of the recipe (shadow.py). No QGraphicsDropShadowEffect anywhere: on the Pi's Qt
5.15.8 an effect composites its shadow over its own output (QTBUG-102374).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT = Path(__file__).resolve().parents[2]
STYLE_DIR = PROJECT / "ui" / "style"

_QAPP = []


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


@pytest.fixture
def style(qapp):
    """A StyleManager on the app, as main.py makes one; the app's palette, stylesheet,
    font and style_manager property come back afterwards."""
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


def _pixel(image, x, y):
    return image.pixelColor(x, y).name().upper()


def _page(qapp, widgets, card, width=420, height=260):
    """`card` alone on a plain page (the window paints bg.page), at (40, 40)."""
    from PyQt5.QtWidgets import QWidget  # noqa: PLC0415

    page = QWidget()
    page.resize(width, height)
    card.setParent(page)
    card.setGeometry(40, 40, width - 80, height - 80)
    widgets.append(page)
    page.show()
    qapp.processEvents()
    return page


def _card(**kw):
    from ui.components.card import Card  # noqa: PLC0415

    return Card(elevated=True, **kw)


def test_the_room_is_the_stylesheets_margin(qapp, style):
    """The box Qt draws lands on elevation_box(): its stroke is the first pixel inside it,
    and the room round it is the margin build_qss.py wrote."""
    from ui.style import elevation  # noqa: PLC0415
    from ui.style.qt_palette import tokens  # noqa: PLC0415

    manager, widgets = style
    manager.apply("light")
    card = _card()
    page = _page(qapp, widgets, card)
    box = card.elevation_box().translated(card.pos())
    image = page.grab().toImage()
    stroke = tokens.value("border.subtle", "light")
    middle_x, middle_y = box.center().x(), box.center().y()
    assert _pixel(image, middle_x, box.top()) == stroke
    assert _pixel(image, middle_x, box.bottom()) == stroke
    assert _pixel(image, box.left(), middle_y) == stroke
    assert _pixel(image, box.right(), middle_y) == stroke
    room = elevation.ROOM
    assert (
        box.left() - card.x() == room.left
        and card.geometry().bottom() - box.bottom() == room.bottom
    )


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_the_shadow_follows_the_theme(qapp, style, theme):
    """Light paints the recipe's CSS profile under the box (each row within 1/255 of it);
    dark paints nothing, and the card keeps its geometry across the switch."""
    from ui.style import shadow  # noqa: PLC0415
    from ui.style.qt_palette import tokens  # noqa: PLC0415

    manager, widgets = style
    manager.apply("light" if theme == "dark" else "dark")  # switch into the theme under test
    card = _card()
    page = _page(qapp, widgets, card)
    geometry = card.geometry()
    manager.apply(theme)
    qapp.processEvents()
    assert card.geometry() == geometry
    box = card.elevation_box().translated(card.pos())
    image = page.grab().toImage()
    page_colour = tokens.value("bg.page", theme)
    x = box.center().x()
    rows = [_pixel(image, x, box.bottom() + 1 + n) for n in range(4)]
    if theme == "dark":
        assert rows == [page_colour] * 4
        return
    layers = tokens.SHADOWS[tokens.ELEVATION["card"][0]]
    ink = tokens.value("shadow.ink", "light")
    for n, got in enumerate(rows):
        want = shadow.over(page_colour, ink, shadow.edge_alpha(layers, "bottom", n))
        assert all(
            abs(int(got[i : i + 2], 16) - int(want[i : i + 2], 16)) <= 1 for i in (1, 3, 5)
        ), (n, got, want)
    assert rows[0] != page_colour


def test_an_update_inside_the_card_paints_no_shadow(qapp, style, monkeypatch):
    """A label changing inside the box repaints the label, not the tile round the box."""
    from PyQt5.QtWidgets import QLabel, QVBoxLayout  # noqa: PLC0415
    from ui.style import elevation  # noqa: PLC0415

    manager, widgets = style
    manager.apply("light")
    card = _card()
    label = QLabel("0", card)
    QVBoxLayout(card).addWidget(label)
    _page(qapp, widgets, card)
    paints = []
    original = elevation.paint_tile
    monkeypatch.setattr(elevation, "paint_tile", lambda *a: (paints.append(1), original(*a)))
    for n in range(5):
        label.setText(str(n + 1))
        qapp.processEvents()
    assert paints == []
    card.update()
    qapp.processEvents()
    assert paints, "a repaint of the whole card paints its shadow"


def test_a_card_that_lifts_shows_its_shadow_under_the_pointer(qapp, style):
    """at_rest=False (the schedule cards): no shadow until the pointer is on the card."""
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtTest import QTest  # noqa: PLC0415
    from ui.style.qt_palette import tokens  # noqa: PLC0415

    manager, widgets = style
    manager.apply("light")
    card = _card()
    card.init_elevation("card", 8, at_rest=False)
    card.setStyleSheet("")  # the property changed after construction: polish again
    page = _page(qapp, widgets, card)
    box = card.elevation_box().translated(card.pos())
    probe = QPoint(box.center().x(), box.bottom() + 2)
    page_colour = tokens.value("bg.page", "light")

    def under_the_card():
        qapp.processEvents()
        return _pixel(page.grab().toImage(), probe.x(), probe.y())

    QTest.mouseMove(page, QPoint(5, 5))
    assert under_the_card() == page_colour
    QTest.mouseMove(page, box.center())
    QTest.qWait(30)
    assert card.underMouse() and under_the_card() != page_colour
    QTest.mouseMove(page, QPoint(5, 5))
    QTest.qWait(30)
    assert under_the_card() == page_colour


def _radius(qss, selector):
    """The border-radius of the rule whose selector list starts with `selector`."""
    for selectors, body in re.findall(
        r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", qss, flags=re.S)
    ):
        if [s.strip() for s in selectors.split(",")][0] == selector:
            found = re.search(r"border-radius:\s*(\d+)px", body)
            if found:
                return int(found.group(1))
    raise AssertionError(f"no radius for {selector}")


def test_each_elevated_card_draws_its_tile_for_its_own_radius(qapp):
    """The tile is drawn for the radius each elevated card's rule has, so the shadow's
    corners follow the box's."""
    from ui.components.card import CARD_RADIUS  # noqa: PLC0415
    from ui.components.interactive_card import InteractiveCard  # noqa: PLC0415
    from ui.schedules_hub import ScheduleCard  # noqa: PLC0415

    for theme in ("light", "dark"):
        qss = (STYLE_DIR / f"app-{theme}.qss").read_text(encoding="utf-8")
        assert _radius(qss, "QFrame#Card") == CARD_RADIUS
        assert _radius(qss, "QFrame#ScheduleCard") == ScheduleCard.RADIUS
        assert _radius(qss, "QFrame#InteractiveCard") == InteractiveCard.RADIUS


def test_the_tile_is_made_once(qapp):
    from ui.style import elevation  # noqa: PLC0415
    from ui.style.qt_palette import tokens  # noqa: PLC0415

    layers = tokens.SHADOWS["fluent.shadow4"]
    first = elevation.cached_tile(layers, 8.0, 1.0, "#000000")
    assert elevation.cached_tile(layers, 8.0, 1.0, "#000000") is first
    assert first.ext == (6, 4, 6, 8)


def test_no_graphics_effect_outside_the_splash():
    """QGraphicsEffect re-renders a widget and its children on every change, fills the
    global QPixmapCache, and on Qt 5.15.8 (the Pi's) composites a drop shadow over its own
    output until it turns near-black (QTBUG-102374). Elevation is ui.style.elevation's."""
    allowed = {"ui/splash_screen.py"}
    found = sorted(
        path.relative_to(PROJECT).as_posix()
        for path in (PROJECT / "ui").rglob("*.py")
        if "setGraphicsEffect" in path.read_text(encoding="utf-8")
    )
    assert set(found) <= allowed, found
