"""The Settings tab's colours follow the theme (v2.1.0).

The Calibration table wrote its status words and CV% in fixed QColors (green, amber, red,
grey), the tab's description and the User Mode text were #666, and the Slack status took
one of three literals once a second. In the dark theme the red and the greys read at 2:1
or less. Now the table's words and the description take a role of tokens.py from the
current theme and are painted again when StyleManager applies a theme (theme_changed);
the Slack status and the User Mode text are stylesheet rules (QLabel#SlackStatus[status],
QLabel#GroupDescription). Rendered offscreen in both themes; colours are compared with
the tokens.
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


# cage: (volume per pulse, CV %, measured under the device's topology)
CALIBRATIONS = {
    1: (0.034164, 0.8, True),  # [OK], an excellent CV
    2: (0.034264, 1.9, True),  # a good CV
    3: (0.034364, 3.4, True),  # an acceptable CV
    4: (0.034464, 6.1, True),  # a poor CV
    5: (0.034564, None, True),  # no CV
    6: (0.034664, 2.6, False),  # Stale
    7: (0.0, 1.2, True),  # Invalid: no usable volume per pulse
}  # cage 8 on: Not Calibrated


def _calibrate(database_handler, system_controller):
    device = system_controller.settings.get("valve_topology") or "shared_manifold"
    other = "independent" if device == "shared_manifold" else "shared_manifold"
    for cage, (volume, cv, current) in CALIBRATIONS.items():
        database_handler.save_valve_calibration(
            cage_id=cage,
            relay_id=cage,
            pulse_width_ms=30,
            volume_per_pulse_ml=volume,
            stddev_ml=0.0009,
            cv_pct=1.0 if cv is None else cv,  # the save's log line cannot format None
            num_samples=250,
            inter_pulse_interval_ms=1000,
            topology=device if current else other,
        )
        if cv is None:
            with database_handler.connect() as conn:
                conn.execute(
                    "UPDATE valve_calibration SET coefficient_of_variation_pct = NULL "
                    "WHERE cage_id = ?",
                    (cage,),
                )
                conn.commit()


def _settings_tab(qapp, windows, database_handler, system_controller, page="Calibration"):
    """The Settings tab in a tab pane, as the main window shows it, on one of its pages."""
    from PyQt5.QtWidgets import QTabWidget  # noqa: PLC0415
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    system_controller.settings["num_hats"] = 1
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
    tab.tab_widget.setCurrentIndex(pages.index(page))
    window.show()
    qapp.processEvents()
    windows.append(window)
    return window, tab


def _text(widget):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    return widget.palette().color(QPalette.WindowText).name().upper()


def _expected_tones(tab):
    """{(row, column): role} for every cell the table colours, by the seeded calibrations."""
    status, cv = tab.CAL_COL_STATUS, tab.CAL_COL_CV
    tones = {
        (0, cv): "success.text",
        (1, cv): "success.text",
        (2, cv): "warning.text",
        (3, cv): "danger.text",
        (4, cv): "text.muted",
        (5, cv): "success.text",
        (6, cv): "success.text",
        (5, status): "warning.text",  # Stale
        (6, status): "danger.text",  # Invalid
    }
    for row in range(5):
        tones[(row, status)] = "success.text"  # [OK]
    for row in range(7, tab.calibration_table.rowCount()):
        tones[(row, status)] = "danger.text"  # Not Calibrated
        for column in (tab.CAL_COL_PROFILE, tab.CAL_COL_VOLUME, cv, tab.CAL_COL_DATE):
            tones[(row, column)] = "text.muted"  # its dashes
    return tones


@pytest.mark.parametrize("theme", THEMES)
def test_the_calibration_table_follows_the_theme(
    qapp, tokens, style, database_handler, system_controller, theme
):
    from PyQt5.QtCore import Qt  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    _calibrate(database_handler, system_controller)
    _window, tab = _settings_tab(qapp, windows, database_handler, system_controller)
    table = tab.calibration_table
    assert [table.item(row, tab.CAL_COL_STATUS).text() for row in (0, 5, 6, 7)] == [
        "[OK]",
        "Stale",
        "Invalid",
        "Not Calibrated",
    ]
    tones = _expected_tones(tab)

    def check():
        for row in range(table.rowCount()):
            for column in range(tab.CAL_COL_ACTION):
                item = table.item(row, column)
                role = tones.get((row, column))
                if role is None:  # the table's own text colour
                    assert item.foreground().style() == Qt.NoBrush, (row, column, item.text())
                    continue
                assert item.data(tab.CAL_TONE_ROLE) == role, (row, column, item.text())
                assert item.foreground().color().name().upper() == tokens.value(role, theme), (
                    row,
                    column,
                    item.text(),
                )
        # The description under the title, in secondary text
        colour = tokens.value("text.secondary", theme).lower()
        assert f"color: {colour};" in tab._calibration_header.text()

    manager.apply(theme)  # a theme applied after the table is filled repaints it
    check()
    tab._populate_calibration_table()  # and a refresh reads the theme applied last
    check()


@pytest.mark.parametrize("theme", THEMES)
def test_a_selected_row_writes_its_words_in_the_selection_colours(
    qapp, tokens, style, database_handler, system_controller, theme
):
    """A cell's own colour gives way to the selection's text (::item:selected), so the
    status colours need no contrast pair on bg.selected."""
    manager, windows = style
    manager.apply(theme)
    _calibrate(database_handler, system_controller)
    window, tab = _settings_tab(qapp, windows, database_handler, system_controller)
    table = tab.calibration_table
    row = 7  # Not Calibrated, in danger.text when not selected
    table.selectRow(row)
    qapp.processEvents()

    image = window.grab().toImage()
    rect = table.visualItemRect(table.item(row, tab.CAL_COL_STATUS))
    origin = table.viewport().mapTo(window, rect.topLeft())
    found = {
        image.pixelColor(origin.x() + x, origin.y() + y).name().upper()
        for x in range(rect.width())
        for y in range(rect.height())
    }
    assert tokens.value("bg.selected", theme) in found
    assert tokens.value("text.on-accent", theme) in found
    assert tokens.value("danger.text", theme) not in found


@pytest.mark.parametrize("theme", THEMES)
def test_the_slack_status_and_the_user_mode_text_follow_the_theme(
    qapp, tokens, style, database_handler, system_controller, theme
):
    from PyQt5.QtWidgets import QLabel  # noqa: PLC0415

    manager, windows = style
    manager.apply("light")
    _window, tab = _settings_tab(qapp, windows, database_handler, system_controller, "General")
    manager.apply(theme)
    qapp.processEvents()

    def colour(role):
        return tokens.value(role, theme)

    label = tab.slack_status_label
    assert label.text().startswith("•  Status unknown")  # nothing sent yet
    assert _text(label) == colour("text.muted")
    for last_status, glyph, role in (
        ({"ok": True, "detail": "ok", "timestamp": "2030-01-15T08:00:00"}, "✓", "success.text"),
        ({"ok": False, "detail": "x", "timestamp": "2030-01-15T08:00:00"}, "⚠", "warning.text"),
    ):
        tab.notification_handler = SimpleNamespace(last_status=last_status)
        tab._refresh_slack_status()
        assert label.text().startswith(glyph)
        assert _text(label) == colour(role), glyph

    description = tab.findChild(QLabel, "GroupDescription")
    assert description.text().startswith("Switch between Normal and Super mode")
    assert _text(description) == colour("text.secondary")
    assert description.font().pixelSize() == 11


def test_the_slack_status_is_restyled_only_when_it_changes(
    qapp, style, database_handler, system_controller, monkeypatch
):
    """The status is read once a second; only a new status restyles the label."""
    import importlib  # noqa: PLC0415

    # The module: ui/__init__.py makes the name ui.SettingsTab the class
    module = importlib.import_module("ui.SettingsTab")

    manager, windows = style
    manager.apply("light")
    _window, tab = _settings_tab(qapp, windows, database_handler, system_controller, "General")
    restyled = []
    monkeypatch.setattr(module, "restyle", restyled.append)

    for _ in range(3):
        tab._refresh_slack_status()
    assert restyled == []  # still unknown, as when the tab was built

    tab.notification_handler = SimpleNamespace(
        last_status={"ok": True, "detail": "ok", "timestamp": "2030-01-15T08:00:00"}
    )
    for _ in range(3):
        tab._refresh_slack_status()
    assert restyled == [tab.slack_status_label]
