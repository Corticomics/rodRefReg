"""The schedule wizard's steps follow the theme (v2.1.0).

Steps 2 to 4 wrote their colours into inline stylesheets, so the dark theme left them
light: the limit banner stayed pale yellow, each animal's row in step 3 a white box under
the theme's light text, and step 4's values dark on the dark page (1.10:1). The banner
also drew a box around its icon and its text (a QLabel is a QFrame). They now come from
tokens.py through the theme stylesheet (objectNames, and a dynamic property for the
selection counter), in the SCHEDULE WIZARD STEPS section of app.qss.tmpl. Rendered
offscreen in both themes; pixels and palettes are compared with the tokens.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

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


@pytest.fixture(autouse=True)
def _no_dialogs(qapp, monkeypatch):
    """No message box can block the run offscreen."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, kind, staticmethod(lambda *a, **k: QMessageBox.Ok))


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


def _wizard(qapp, windows, database_handler, system_controller):
    """The wizard in a tab pane, as the Wizard tab shows it, on step 2 with three animals."""
    from models.animal import Animal  # noqa: PLC0415
    from PyQt5.QtCore import QEvent  # noqa: PLC0415
    from PyQt5.QtWidgets import QTabWidget  # noqa: PLC0415
    from ui.schedule_wizard import ScheduleCreationWizard  # noqa: PLC0415

    database_handler.add_trainer("theme", "theme-pass")
    for lab_id in ("T1", "T2", "T3"):
        database_handler.add_animal(
            Animal(lab_animal_id=lab_id, name=lab_id, sex="female", initial_weight=25.0), 1
        )
    login = SimpleNamespace(get_current_trainer=lambda: {"trainer_id": 1})
    wizard = ScheduleCreationWizard(database_handler, login, system_controller)
    window = QTabWidget()
    window.addTab(wizard, "Wizard")
    window.resize(1115, 1000)
    window.show()
    wizard._step1._on_type_selected("staggered")
    wizard._wizard.set_current_step(1)
    qapp.processEvents()
    windows.append(window)

    def settle():
        qapp.processEvents()
        # A step clears its widgets with deleteLater, which processEvents leaves
        qapp.sendPostedEvents(None, QEvent.DeferredDelete)

    return window, wizard, settle


def _pixel(window, widget, x, y):
    from PyQt5.QtCore import QPoint  # noqa: PLC0415

    image = window.grab().toImage()
    return image.pixelColor(widget.mapTo(window, QPoint(x, y))).name().upper()


def _text(widget):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    return widget.palette().color(QPalette.WindowText).name().upper()


@pytest.mark.parametrize("theme", THEMES)
def test_step_two_follows_the_theme(
    qapp, tokens, style, database_handler, system_controller, theme
):
    from PyQt5.QtWidgets import QFrame, QLabel  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    window, wizard, settle = _wizard(qapp, windows, database_handler, system_controller)
    manager.apply(theme)  # a theme applied after the wizard exists reaches it
    settle()

    def colour(role):
        return tokens.value(role, theme)

    step = wizard._step2
    banner = step.findChild(QFrame, "WizardLimitBanner")
    assert _pixel(window, banner, banner.width() - 4, banner.height() // 2) == colour(
        "warning.tint"
    )
    assert _pixel(window, banner, banner.width() // 2, 0) == colour("warning.indicator")
    assert _text(step._limit_label) == colour("warning.on-tint")
    for label in banner.findChildren(QLabel):
        # Each label keeps the 1px frame it had (nothing moves), and draws no box with it
        assert label.frameWidth() == 1, label.text()
        assert _pixel(window, label, label.width() // 2, 0) == colour("warning.tint")

    counter = step._selection_counter
    assert counter.text() == "0 selected"
    assert _text(counter) == colour("text.muted")
    assert counter.font().pixelSize() == 11
    step._animals_list.item(0).setSelected(True)
    step._animals_list.item(1).setSelected(True)
    settle()
    assert counter.text() == "2 of 15 max selected"
    assert (_text(counter), counter.font().pixelSize()) == (colour("success.text"), 12)
    step._animals_list.clearSelection()
    settle()
    assert (_text(counter), counter.font().pixelSize()) == (colour("text.muted"), 12)
    # More than the relays allow cannot stay selected; its rule is the danger colour
    from ui.style.theme import restyle  # noqa: PLC0415

    counter.setProperty("count", "over")
    restyle(counter)
    assert (_text(counter), counter.font().pixelSize()) == (colour("danger.text"), 12)


def test_the_counter_is_restyled_only_when_its_colour_changes(
    qapp, style, database_handler, system_controller, monkeypatch
):
    import ui.schedule_wizard as module  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    _window, wizard, settle = _wizard(qapp, windows, database_handler, system_controller)
    restyled = []
    monkeypatch.setattr(module, "restyle", restyled.append)

    animals = wizard._step2._animals_list
    for row in range(3):
        animals.item(row).setSelected(True)
        settle()
    assert restyled == [wizard._step2._selection_counter]  # none, then some, three times


@pytest.mark.parametrize("theme", THEMES)
def test_steps_three_and_four_follow_the_theme(
    qapp, tokens, style, database_handler, system_controller, theme
):
    from PyQt5.QtWidgets import QFrame, QLabel  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    window, wizard, settle = _wizard(qapp, windows, database_handler, system_controller)
    manager.apply(theme)

    def colour(role):
        return tokens.value(role, theme)

    step3 = wizard._step3
    wizard._wizard.set_current_step(2)
    settle()
    empty = step3.findChild(QLabel, "WizardEmptyState")
    assert empty.text().startswith("No animals selected")
    assert (_text(empty), empty.font().pixelSize()) == (colour("text.muted"), 14)

    for row in range(2):
        wizard._step2._animals_list.item(row).setSelected(True)
    for mode in ("staggered", "instant"):
        step3.set_animals(wizard._step2.get_selected_animals_data())
        step3.set_schedule_type(mode)
        settle()
        rows = [w for w in step3.findChildren(QFrame, "AnimalConfigRow") if w.isVisible()]
        assert len(rows) == 2, mode
        for row in rows:
            # Inside its 4px margin: the edge, then the fill (clear of the fields)
            assert _pixel(window, row, row.width() // 2, 4) == colour("border.subtle"), mode
            assert _pixel(window, row, row.width() - 12, row.height() // 2) == colour(
                "bg.surface"
            ), mode

    step3.set_schedule_type("staggered")
    step3._name_input.setText("Morning")
    wizard._wizard.set_current_step(3)
    wizard._step4.set_config(wizard._build_config())
    settle()
    step4 = wizard._step4
    section = step4.findChild(QLabel, "WizardSummarySection")
    assert section.text() == "Animal Configurations"
    assert _text(section) == colour("text.accent")
    assert _pixel(window, section, section.width() // 2, section.height() - 1) == colour(
        "border.subtle"
    )
    labels = step4.findChildren(QLabel, "WizardSummaryLabel")
    values = step4.findChildren(QLabel, "WizardSummaryValue")
    assert [label.text() for label in labels][:2] == ["Schedule Type:", "Name:"]
    assert [value.text() for value in values][:2] == ["Staggered Delivery", "Morning"]
    for label in labels:
        assert (_text(label), label.font().pixelSize()) == (colour("text.secondary"), 11)
    for value in values:
        assert (_text(value), value.font().pixelSize()) == (colour("text.primary"), 11)


@pytest.mark.parametrize("theme", THEMES)
def test_start_over_is_a_default_button_of_the_theme(
    qapp, tokens, style, database_handler, system_controller, theme
):
    """Start Over had a light grey inline fill, so in the dark theme it was a pale box
    under the theme's light text."""
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtTest import QTest  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    window, wizard, settle = _wizard(qapp, windows, database_handler, system_controller)
    manager.apply(theme)
    settle()

    def colour(role):
        return tokens.value(role, theme)

    button = wizard._wizard._start_over_button
    middle = button.height() // 2
    assert button.palette().color(QPalette.ButtonText).name().upper() == colour("text.primary")
    assert _pixel(window, button, 4, middle) == colour("bg.surface")
    assert _pixel(window, button, 0, middle) == colour("border.control")
    QTest.mouseMove(button, QPoint(button.width() // 2, middle))
    settle()
    assert _pixel(window, button, 4, middle) == colour("bg.hover")
    assert _pixel(window, button, 0, middle) == colour("border.control"), "its edge stays"
    QTest.mouseMove(window, QPoint(2, window.height() - 2))
    settle()
