"""The Schedules hub follows the theme (v2.1.0).

The hub's colours used to be written into inline stylesheets, so the dark theme left them
light. The title was dark on the dark page, and the search field and the cards were white
boxes under the dark theme's light text. The Select button stayed light too. They now come
from tokens.py through the theme stylesheet (objectNames and dynamic properties, in the
SCHEDULES HUB section of app.qss.tmpl). The drag pixmap asks the theme for its colours
when it paints. Rendered offscreen in both themes; pixels and palettes are compared with
the tokens.
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


def _schedules():
    from models.Schedule import Schedule  # noqa: PLC0415

    staggered = Schedule(1, "Morning", 1.0, "2030-01-15T09:00:00", "2030-01-15T11:00:00", 1, 0)
    instant = Schedule(
        2, "Top-up", 1.0, "2030-01-14T13:30:00", "2030-01-14T13:30:00", 1, 0, "instant"
    )
    for schedule in (staggered, instant):
        schedule.animals = [1, 2]
    return [staggered, instant]


def _hub(qapp, windows):
    """The hub in a tab pane, as ProjectsSection shows it, with two schedules."""
    from PyQt5.QtCore import QObject, pyqtSignal  # noqa: PLC0415
    from PyQt5.QtWidgets import QTabWidget  # noqa: PLC0415
    from ui.schedules_hub import SchedulesHub  # noqa: PLC0415

    schedules = _schedules()

    class Login(QObject):
        login_status_changed = pyqtSignal()

        def get_current_trainer(self):
            return None

    class Database:
        def get_all_schedules(self):
            return list(schedules)

        def get_schedules_by_trainer(self, _trainer_id):
            return list(schedules)

        def get_schedule_details(self, schedule_id):
            schedule = next(s for s in schedules if s.schedule_id == schedule_id)
            return [{"delivery_mode": schedule.delivery_mode, "animal_ids": schedule.animals}]

    tabs = QTabWidget()
    hub = SchedulesHub({}, lambda *_: None, Database(), Login())
    tabs.addTab(hub, "Schedules")
    tabs.resize(1000, 420)
    tabs.show()
    qapp.processEvents()
    windows.append(tabs)
    return tabs, hub


def _fill(window, widget, x=4):
    """The colour of `widget` at `x` on its middle row: clear of text, border and corner."""
    from PyQt5.QtCore import QPoint  # noqa: PLC0415

    image = window.grab().toImage()
    point = widget.mapTo(window, QPoint(x, widget.height() // 2))
    return image.pixelColor(point).name().upper()


def _text(widget):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    return widget.palette().color(QPalette.WindowText).name().upper()


@pytest.mark.parametrize("theme", THEMES)
def test_the_hub_follows_the_theme(qapp, tokens, style, theme):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import QLabel  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    tabs, hub = _hub(qapp, windows)
    manager.apply(theme)  # a theme applied after the hub exists reaches it
    qapp.processEvents()

    def colour(role):
        return tokens.value(role, theme)

    card = hub._schedule_cards[0]
    assert _fill(tabs, card, card.width() - 4) == colour("bg.surface")
    labels = {label.objectName(): label for label in card.findChildren(QLabel)}
    assert _text(labels["ScheduleCardName"]) == colour("text.primary")
    assert _text(labels["ScheduleCardMeta"]) == colour("text.secondary")
    assert _text(labels["ScheduleCardHint"]) == colour("text.muted")
    assert _text(labels["ScheduleCardCreated"]) == colour("text.accent")

    staggered, instant = (c.findChild(QLabel, "ScheduleModeBadge") for c in hub._schedule_cards)
    assert (staggered.text(), instant.text()) == ("Staggered", "Instant")
    assert _fill(tabs, staggered) == colour("accent.fill")
    assert _text(staggered) == colour("text.on-accent")
    assert _fill(tabs, instant) == colour("instant.fill")
    assert _text(instant) == colour("text.on-instant")

    assert _text(hub.findChild(QLabel, "SchedulesHubTitle")) == colour("text.primary")
    assert _fill(tabs, hub._search_input) == colour("bg.field")
    assert _fill(tabs, hub._select_btn) == colour("bg.surface")
    assert hub._select_btn.palette().color(QPalette.ButtonText).name().upper() == colour(
        "text.primary"
    )
    new = next(b for b in hub.findChildren(type(hub._select_btn)) if b.text() == "+ New Schedule")
    assert _fill(tabs, new) == colour("accent.fill")


@pytest.mark.parametrize("theme", THEMES)
def test_select_mode_and_a_selected_card(qapp, tokens, style, theme):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    manager, windows = style
    manager.apply(theme)
    tabs, hub = _hub(qapp, windows)

    def colour(role):
        return tokens.value(role, theme)

    hub._toggle_select_mode()
    qapp.processEvents()
    assert hub._select_btn.text() == "Cancel"
    assert _fill(tabs, hub._select_btn) == colour("danger.tint")
    assert hub._select_btn.palette().color(QPalette.ButtonText).name().upper() == colour(
        "danger.on-tint"
    )
    # Nothing selected: Edit and Delete are greyed out like every disabled button
    assert _fill(tabs, hub._edit_selected_btn) == colour("bg.disabled")
    assert _fill(tabs, hub._delete_selected_btn) == colour("bg.disabled")

    card = hub._schedule_cards[0]
    card._checkbox.setChecked(True)
    qapp.processEvents()
    assert _fill(tabs, card, card.width() - 5) == colour("accent.tint")  # inside its 2px border
    assert _fill(tabs, hub._edit_selected_btn) == colour("accent.fill")
    assert _fill(tabs, hub._delete_selected_btn) == colour("danger.fill")

    hub._toggle_select_mode()  # Cancel
    qapp.processEvents()
    assert hub._select_btn.text() == "Select"
    assert _fill(tabs, hub._select_btn) == colour("bg.surface")
    assert _fill(tabs, hub._schedule_cards[0], card.width() - 4) == colour("bg.surface")


def test_a_selected_card_keeps_its_content_inside_its_2px_border(qapp, style):
    """The selected border is 2px: the card's frame re-reads it, as a stylesheet change does."""
    manager, windows = style
    manager.apply("light")
    _tabs, hub = _hub(qapp, windows)
    card = hub._schedule_cards[0]
    assert card.contentsRect().left() == 1

    hub._toggle_select_mode()
    card._checkbox.setChecked(True)
    qapp.processEvents()
    assert card.contentsRect().left() == 2

    card._checkbox.setChecked(False)
    qapp.processEvents()
    assert card.contentsRect().left() == 1


@pytest.mark.parametrize("theme", THEMES)
def test_the_drag_pixmap_takes_the_theme_when_it_paints(qapp, tokens, style, theme, monkeypatch):
    from PyQt5.QtCore import Qt  # noqa: PLC0415
    from PyQt5.QtGui import QDrag  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    _tabs, hub = _hub(qapp, windows)
    manager.apply(theme)

    pixmaps = []

    def exec_(drag, *_args):
        pixmaps.append(drag.pixmap())
        return Qt.IgnoreAction

    monkeypatch.setattr(QDrag, "exec_", exec_)
    hub._schedule_cards[0]._start_drag()

    assert len(pixmaps) == 1
    image = pixmaps[0].toImage()
    assert image.pixelColor(185, 25).name().upper() == tokens.value("accent.tint", theme)
    assert image.pixelColor(1, 25).name().upper() == tokens.value("accent.indicator", theme)


def test_theme_colour_reads_the_theme_applied_last(qapp, tokens, style):
    from ui.style.theme import current_theme, theme_colour  # noqa: PLC0415

    manager, _ = style
    manager.apply("dark")
    assert current_theme() == "dark"
    assert theme_colour("accent.tint").name().upper() == tokens.value("accent.tint", "dark")
    manager.apply("light")
    assert theme_colour("accent.tint").name().upper() == tokens.value("accent.tint", "light")

    qapp.setProperty("style_manager", None)  # no StyleManager: the light theme
    assert current_theme() == "light"
    with pytest.raises(KeyError):
        theme_colour("no.such.role")
