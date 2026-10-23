"""Settings > General's theme drop-down is a button (v2.1.0).

The owner's decision of 2026-10-22: "make the darkmode/light mode dropdown a button
instead". Appearance has one QPushButton, #ThemeButton, beside its Theme label. Its label
names what it does and the theme it leads to, as the User Mode button's does: "Switch to
light mode" while the dark theme is on screen, "Switch to dark mode" while the light one
is. A click, or the space bar, applies the other theme at once, saves it through the
auto-save the drop-down used, and relabels the button; the next start shows that theme.
It is a default button of the stylesheet: no rule of its own, no colour of its own.
Offscreen, against the real SystemController and database.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"
LABEL = {"dark": "Switch to light mode", "light": "Switch to dark mode"}

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
def _no_dialogs_and_a_fresh_lock(qapp, monkeypatch):
    """No message box can block the run offscreen; each test gets its own operation lock."""
    import utils.operation_lock as ol  # noqa: PLC0415
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, kind, staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))
    ol._singleton = None
    yield
    ol._singleton = None


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


def _general_tab(qapp, windows, system_controller, database_handler):
    """The Settings tab on its General page, in a tab pane as the main window shows it."""
    from PyQt5.QtWidgets import QTabWidget  # noqa: PLC0415
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    tab = SettingsTab(
        system_controller,
        login_system=login,
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
    )
    tab._slack_status_timer.stop()
    window = QTabWidget()
    window.addTab(tab, "Settings")
    window.resize(760, 820)
    pages = [tab.tab_widget.tabText(i) for i in range(tab.tab_widget.count())]
    tab.tab_widget.setCurrentIndex(pages.index("General"))
    window.show()
    qapp.processEvents()
    windows.append(window)
    return tab


def _sheet(theme):
    return (STYLE_DIR / f"app-{theme}.qss").read_text(encoding="utf-8")


def test_appearance_has_a_button_and_no_drop_down(
    qapp, style, system_controller, database_handler
):
    from PyQt5.QtWidgets import QComboBox, QFormLayout, QGroupBox, QPushButton  # noqa: PLC0415

    manager, windows = style
    manager.apply("dark")
    tab = _general_tab(qapp, windows, system_controller, database_handler)

    [appearance] = [box for box in tab.findChildren(QGroupBox) if box.title() == "Appearance"]
    assert appearance.findChildren(QComboBox) == []
    assert not hasattr(tab, "theme_combo")
    [button] = appearance.findChildren(QPushButton)
    assert button is tab.theme_button
    assert button.objectName() == "ThemeButton"
    assert button.text() == "Switch to light mode"
    form = appearance.layout()
    assert isinstance(form, QFormLayout)
    row, _role = form.getWidgetPosition(button)
    assert form.itemAt(row, QFormLayout.LabelRole).widget().text() == "Theme:"


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_theme_label_reads_level_with_the_button(
    qapp, style, system_controller, database_handler, theme
):
    """QFormLayout puts a label at the top of its row, and the button is 20px taller than a
    line of text: 'Theme:' sat 17px above the button's text. As tall as the button and
    centred, it reads level with it. The drawn text's middle rows are compared."""
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtWidgets import QFormLayout, QGroupBox  # noqa: PLC0415

    manager, windows = style
    manager.apply(theme)
    tab = _general_tab(qapp, windows, system_controller, database_handler)
    [appearance] = [box for box in tab.findChildren(QGroupBox) if box.title() == "Appearance"]
    button = tab.theme_button
    form = appearance.layout()
    row, _role = form.getWidgetPosition(button)
    label = form.itemAt(row, QFormLayout.LabelRole).widget()

    image = appearance.grab().toImage()

    def ink_rows(widget, x0, x1):
        """The rows of `widget` (in the group box) where its text is drawn: the pixels
        that are not its ground, the colour most of its columns x0 to x1 show."""
        from collections import Counter  # noqa: PLC0415

        top = widget.mapTo(appearance, QPoint(0, 0))
        pixels = {
            (x, y): image.pixelColor(top.x() + x, top.y() + y).name()
            for y in range(widget.height())
            for x in range(x0, x1)
        }
        ground = Counter(pixels.values()).most_common(1)[0][0]
        return sorted({y for (x, y), name in pixels.items() if name != ground})

    text_rows = ink_rows(label, 0, label.width())
    middle = button.width() // 2
    button_rows = ink_rows(button, middle - 40, middle + 40)
    button_rows = [y for y in button_rows if 3 <= y < button.height() - 3]  # not its edge
    label_top = label.mapTo(appearance, QPoint(0, 0)).y()
    button_top = button.mapTo(appearance, QPoint(0, 0)).y()
    label_middle = label_top + (text_rows[0] + text_rows[-1]) / 2
    button_middle = button_top + (button_rows[0] + button_rows[-1]) / 2
    assert abs(label_middle - button_middle) <= 2, (label_middle, button_middle)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_the_label_names_the_switch_away_from_the_theme_on_screen(
    qapp, style, system_controller, database_handler, theme
):
    from ui.style.theme import other_theme  # noqa: PLC0415

    assert other_theme(theme) == ("light" if theme == "dark" else "dark")
    assert other_theme("sepia") == "light", "an unknown theme is the default, dark"
    manager, windows = style
    manager.apply(theme)
    system_controller.settings["theme"] = theme  # as main.py loads it
    tab = _general_tab(qapp, windows, system_controller, database_handler)
    assert tab.theme_button.text() == LABEL[theme]

    # The button follows the theme on screen, whoever applies it
    manager.apply(other_theme(theme))
    assert tab.theme_button.text() == LABEL[other_theme(theme)]


def test_without_a_style_manager_the_label_follows_the_saved_theme(
    qapp, system_controller, database_handler
):
    """Nothing can be applied without a StyleManager: the button still names the switch
    away from the saved theme, and a click relabels it and saves the other theme."""
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    assert qapp.property("style_manager") is None
    for theme in ("light", "dark"):
        system_controller.settings["theme"] = theme
        tab = SettingsTab(
            system_controller,
            login_system=SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=dict),
            print_to_terminal=lambda _msg: None,
            database_handler=database_handler,
        )
        tab._slack_status_timer.stop()
        assert tab.theme_button.text() == LABEL[theme]
        tab.theme_button.click()
        other = "dark" if theme == "light" else "light"
        assert tab.theme_button.text() == LABEL[other]
        assert database_handler.get_system_settings()["theme"] == other
        tab.deleteLater()


def test_a_click_applies_the_other_theme_at_once_and_keeps_it(
    qapp, tokens, style, system_controller, database_handler
):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    manager, windows = style
    manager.apply("dark")
    tab = _general_tab(qapp, windows, system_controller, database_handler)
    applied = []
    manager.theme_changed.connect(applied.append)

    for theme in ("light", "dark", "light"):
        tab.theme_button.click()
        assert manager.theme == theme
        assert qapp.styleSheet() == _sheet(theme)
        window = qapp.palette().color(QPalette.Window).name().upper()
        assert window == tokens.value("bg.page", theme)
        assert tab.theme_button.text() == LABEL[theme]
        assert system_controller.settings["theme"] == theme
        assert database_handler.get_system_settings()["theme"] == theme
    assert applied == ["light", "dark", "light"]


def test_the_choice_is_what_the_next_start_shows(
    qapp, style, monkeypatch, database_handler, capsys
):
    """A device's first start of 2.1.0 is dark (the one-time switch); the operator presses
    the button; at the next start main.py reads light before any window shows, the
    settings load light, and the button offers dark."""
    from controllers.system_controller import SystemController  # noqa: PLC0415

    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # main installs its own
    import main  # noqa: PLC0415

    database_handler.update_system_setting("theme", "light", "str")  # 2.0.0's lab device
    manager, windows = style
    first = SystemController(database_handler)
    assert "Switched the theme to 'dark'" in capsys.readouterr().out
    manager.apply(main._startup_theme())
    assert manager.theme == "dark"
    tab = _general_tab(qapp, windows, first, database_handler)
    assert tab.theme_button.text() == "Switch to light mode"

    tab.theme_button.click()

    # The next start
    assert main._startup_theme() == "light"
    manager.apply(main._startup_theme())
    second = SystemController(database_handler)
    assert second.settings["theme"] == "light"
    assert "[SETTINGS]" not in capsys.readouterr().out, "not switched again"
    again = _general_tab(qapp, windows, second, database_handler)
    assert again.theme_button.text() == "Switch to dark mode"


def test_the_space_bar_presses_it(qapp, style, system_controller, database_handler):
    from PyQt5.QtCore import Qt  # noqa: PLC0415
    from PyQt5.QtTest import QTest  # noqa: PLC0415

    manager, windows = style
    manager.apply("dark")
    tab = _general_tab(qapp, windows, system_controller, database_handler)
    button = tab.theme_button
    assert button.focusPolicy() & Qt.TabFocus, "the Tab key reaches it"
    button.setFocus(Qt.TabFocusReason)

    QTest.keyClick(button, Qt.Key_Space)

    assert manager.theme == "light"
    assert button.text() == "Switch to dark mode"
    assert database_handler.get_system_settings()["theme"] == "light"


def test_an_auto_save_from_another_control_keeps_the_theme_on_screen(
    qapp, style, system_controller, database_handler
):
    """The auto-saved dict takes the theme from the button, as it took it from the
    drop-down: a later save of another setting must not put the old theme back."""
    manager, windows = style
    manager.apply("dark")
    tab = _general_tab(qapp, windows, system_controller, database_handler)
    tab.theme_button.click()

    tab.round_doses_up.setChecked(not tab.round_doses_up.isChecked())  # auto-saves

    stored = database_handler.get_system_settings()
    assert stored["round_doses_up"] is tab.round_doses_up.isChecked(), "the save ran"
    assert stored["theme"] == "light"


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_it_is_a_default_button_of_the_stylesheet(
    qapp, tokens, style, system_controller, database_handler, theme
):
    """Drawn by QPushButton's own rule: the surface fill, the control edge, primary text.
    The template names no #ThemeButton: the stylesheet has no rule of its own for it."""
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    manager, windows = style
    manager.apply(theme)
    tab = _general_tab(qapp, windows, system_controller, database_handler)
    button = tab.theme_button
    button.clearFocus()
    qapp.processEvents()

    assert "ThemeButton" not in (STYLE_DIR / "app.qss.tmpl").read_text(encoding="utf-8")
    assert button.property("variant") is None
    assert button.palette().color(QPalette.ButtonText).name().upper() == tokens.value(
        "text.primary", theme
    )
    image = button.grab().toImage()
    middle = button.height() // 2
    assert image.pixelColor(6, middle).name().upper() == tokens.value("bg.surface", theme)
    assert image.pixelColor(0, middle).name().upper() == tokens.value("border.control", theme)


def test_help_says_where_the_button_is():
    """An operator surprised by the dark screens after the update finds the way back in
    Help: a search for the theme lands on System Overview, which names the button."""
    import re  # noqa: PLC0415

    from utils.help_content_manager import HelpContentManager  # noqa: PLC0415

    help_ = HelpContentManager()
    for query in ("theme", "dark mode", "light mode"):
        assert help_.search(query)[0][0] == "System Overview", query
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", help_.get_content("System Overview")))
    assert (
        "RRR starts in the dark theme. After you log in, Settings → General → Appearance has "
        "a button that switches to the light theme (Switch to light mode) and back; RRR keeps "
        "the choice."
    ) in text
