"""Dark is the default theme, and every device switches to it once (v2.1.0).

The owner's decisions of 2026-10-22: "make the darkmode the default for the app", and for
the devices already in the lab, "switch everyone once": at its first start of 2.1.0 a
device switches to dark one time, and after that the operator's choice sticks. Pinned
here against the real SystemController and database, and main.py's own start-up,
offscreen:

- dark is the default wherever a default lives: the settings (SystemController), the
  style layer (tokens.DEFAULT_THEME, StyleManager, theme_or_default) and Help's HTML;
- a fresh install starts dark and records the switch (ui_dark_default_applied) without a
  journal line; a device whose stored theme is light, as 2.0.0 left it, is switched to
  dark at its first 2.1.0 start, once, with one [SETTINGS] line; from then on the
  operator's choice stays, across restarts and across a revert to 2.0.0 and back;
- the marker and the theme are stored in one transaction: when the database refuses
  either, nothing is stored, the theme stays for that start, and the next start makes the
  switch, so it is never half made;
- main.py reads the saved theme before any window shows (SystemController.theme_at_start
  over DatabaseHandler.peek_system_settings), so the splash and the main window show in
  it from their first frame: no light frame on a dark device, no dark one on a device
  set to light, and the main window is built in it, not restyled.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
import uuid

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path  # noqa: E402

MARKER = "ui_dark_default_applied"
STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"
SWITCHED = (
    "[SETTINGS] Switched the theme to 'dark', the default from 2.1.0, once (it was 'light'); "
    "Settings > General > Appearance switches it back, and that choice is kept"
)

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


def _stored(database_handler):
    return database_handler.get_system_settings()


def _theme_saved(database_handler, theme, marker=None):
    """The rows a release wrote: its theme ('str', as _write_setting_to_db writes it) and,
    from 2.1.0 on, the marker."""
    database_handler.update_system_setting("theme", theme, "str")
    if marker is not None:
        database_handler.update_system_setting(MARKER, marker, "bool")


def _controller(database_handler):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    return SystemController(database_handler)


# --- Dark is the default ------------------------------------------------------------------


def test_dark_is_the_default_in_every_layer(qapp, tokens, database_handler):
    from controllers.system_controller import SystemController  # noqa: PLC0415
    from ui.style import theme  # noqa: PLC0415
    from utils.help_content_manager import HelpContentManager  # noqa: PLC0415

    assert tokens.DEFAULT_THEME == theme.DEFAULT_THEME == "dark"
    assert SystemController.DEFAULT_THEME == tokens.DEFAULT_THEME, "one default, two layers"
    assert SystemController(database_handler).settings["theme"] == "dark"

    manager = theme.StyleManager(qapp)
    try:
        assert manager.theme == "dark", "before anything is applied"
    finally:
        manager.deleteLater()
    for name in (None, "", "sepia", "Light"):
        assert theme.theme_or_default(name) == "dark", name
    assert theme.theme_or_default("light") == "light"

    # Help without a theme, or with one RRR does not have, is the dark page
    help_ = HelpContentManager()
    dark = help_.get_content("System Overview", "dark")
    assert help_.get_content("System Overview") == dark
    assert help_.get_content("System Overview", "sepia") == dark
    assert help_.get_landing_page() == help_.get_landing_page("dark")
    assert tokens.value("text.primary", "dark").lower() in dark.lower()


# --- The one-time switch ----------------------------------------------------------------


def test_a_fresh_install_starts_dark_and_records_the_switch(database_handler, capsys):
    controller = _controller(database_handler)

    assert controller.settings["theme"] == "dark"
    assert _stored(database_handler)[MARKER] is True
    assert "theme" not in _stored(database_handler), "nothing to switch: the default is dark"
    assert "[SETTINGS]" not in capsys.readouterr().out

    _controller(database_handler)
    assert "[SETTINGS]" not in capsys.readouterr().out


@pytest.mark.parametrize("source", ["database", "settings.json"])
def test_a_light_theme_an_older_release_saved_is_switched_to_dark_once(
    database_handler, write_legacy_settings, capsys, source
):
    """2.0.0 stored the theme an operator picked ('light' in the lab). A device still on a
    pre-v1.5.0 settings.json migrates it at the same first start, and is switched too."""
    if source == "database":
        _theme_saved(database_handler, "light")
    else:
        write_legacy_settings({"num_hats": 1, "theme": "light"})

    controller = _controller(database_handler)

    assert controller.settings["theme"] == "dark"
    assert _stored(database_handler)["theme"] == "dark"
    assert _stored(database_handler)[MARKER] is True
    journal = capsys.readouterr().out
    assert journal.count("[SETTINGS]") == 1
    assert SWITCHED in journal

    again = _controller(database_handler)  # every later start
    assert again.settings["theme"] == "dark"
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_a_stored_dark_theme_only_records_the_switch(database_handler, capsys):
    _theme_saved(database_handler, "dark")

    assert _controller(database_handler).settings["theme"] == "dark"
    assert _stored(database_handler)[MARKER] is True
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_light_chosen_after_the_switch_is_kept(database_handler, capsys):
    """The theme button's auto-save writes the theme; every later start keeps it, and so
    does ensure_solenoid_defaults, which main.setup() runs at every start and which saves
    the whole settings dict."""
    _theme_saved(database_handler, "light")
    controller = _controller(database_handler)  # the first start of 2.1.0
    assert SWITCHED in capsys.readouterr().out

    controller.settings["theme"] = "light"  # as SettingsTab._theme_changed does
    controller.save_settings(controller.settings)

    for _ in range(2):
        later = _controller(database_handler)
        later.ensure_solenoid_defaults()
        assert later.settings["theme"] == "light"
        assert _stored(database_handler)["theme"] == "light"
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_a_marker_stored_as_false_is_no_marker(database_handler, capsys):
    _theme_saved(database_handler, "light", marker=False)

    assert _controller(database_handler).settings["theme"] == "dark"
    assert _stored(database_handler)[MARKER] is True
    assert SWITCHED in capsys.readouterr().out


class _Release200:
    """2.0.0's settings rules, as its SystemController has them (3b2a4202), for a revert.

    Its load reads every row, the marker included, with no settle step: it switches,
    removes and forces nothing. Its save writes only its own keys (pulse_width_ms is one,
    the marker is not) and deletes nothing. Its default settings have no theme: main.py
    falls back to 'light'. Built lazily, as a subclass of this release's controller with
    those three rules put back.
    """

    def __new__(cls, database_handler):
        from controllers.system_controller import SystemController  # noqa: PLC0415

        class Release200(SystemController):
            def _settle_stored_settings(self):
                pass

            def _normalised(self, settings_dict, only_present=False):
                return dict(settings_dict)

            def _get_persisted_keys(self):
                keys = set(super()._get_persisted_keys())
                keys.discard(self.DARK_DEFAULT_MARKER)
                return keys | {"pulse_width_ms"}

            def _create_default_settings(self):
                defaults = super()._create_default_settings()
                defaults.pop("theme")
                return defaults

        return Release200(database_handler)


@pytest.mark.parametrize("operator_picks_light_on_2_0_0", [False, True])
def test_a_revert_to_2_0_0_and_the_next_update_do_not_switch_again(
    database_handler, capsys, operator_picks_light_on_2_0_0
):
    _theme_saved(database_handler, "light")  # 2.0.0's lab device
    _controller(database_handler)  # 2.1.0's first start: switched
    assert SWITCHED in capsys.readouterr().out

    old = _Release200(database_handler)  # reverted to 2.0.0
    assert old.settings.get("theme", "light") == "dark", "2.0.0 shows its own dark theme"
    assert old.settings[MARKER] is True, "loaded like any row, and unused"
    old.save_settings(old.settings)  # its Settings auto-save: every key it manages
    assert _stored(database_handler)[MARKER] is True, "2.0.0 neither writes nor deletes it"
    if operator_picks_light_on_2_0_0:
        old.settings["theme"] = "light"  # its Theme drop-down
        old.save_settings(old.settings)

    new = _controller(database_handler)  # updated to 2.1.0 again
    expected = "light" if operator_picks_light_on_2_0_0 else "dark"
    assert new.settings["theme"] == expected
    assert _stored(database_handler)["theme"] == expected
    assert "[SETTINGS]" not in capsys.readouterr().out, "no second switch"


def _refuse(database_handler, key):
    """The database refuses every write of the row `key`, as a full or locked database
    refuses a write: a trigger aborts the INSERT, so DatabaseHandler sees an sqlite3 error.
    Returns a function that makes it accept the row again."""
    from contextlib import closing  # noqa: PLC0415

    name = f"refuse_{key}"
    with closing(sqlite3.connect(database_handler.db_path)) as conn:
        conn.execute(
            f"CREATE TRIGGER {name} BEFORE INSERT ON system_settings "
            f"WHEN NEW.setting_key = '{key}' BEGIN SELECT RAISE(ABORT, 'refused'); END"
        )
        conn.commit()

    def works_again():
        with closing(sqlite3.connect(database_handler.db_path)) as conn:
            conn.execute(f"DROP TRIGGER {name}")
            conn.commit()

    return works_again


def test_settings_stored_together_are_stored_whole_or_not_at_all(database_handler):
    """DatabaseHandler.update_system_settings: one transaction. A refused row leaves none
    of the others behind."""
    rows = [(MARKER, True, "bool"), ("theme", "dark", "str")]
    works_again = _refuse(database_handler, "theme")

    assert database_handler.update_system_settings(rows) is False
    assert MARKER not in _stored(database_handler) and "theme" not in _stored(database_handler)

    works_again()
    assert database_handler.update_system_settings(rows) is True
    assert _stored(database_handler)[MARKER] is True
    assert _stored(database_handler)["theme"] == "dark"


@pytest.mark.parametrize("refused", [MARKER, "theme"])
def test_a_refused_switch_stores_nothing_and_the_next_start_makes_it(
    database_handler, capsys, refused
):
    """The marker and the theme go in one transaction, so whichever row the database
    refuses, neither is stored: the device keeps its theme for that start, and the next
    start switches it, once. The switch is never half made (a stored marker over a theme
    that was never switched would have kept the device light for good)."""
    _theme_saved(database_handler, "light")
    works_again = _refuse(database_handler, refused)

    controller = _controller(database_handler)

    assert controller.settings["theme"] == "light", "as the database still says"
    assert _stored(database_handler)["theme"] == "light"
    assert MARKER not in _stored(database_handler)
    journal = capsys.readouterr().out
    assert journal.count("[SETTINGS]") == 1
    assert (
        "[SETTINGS] Could not store ui_dark_default_applied and the theme, so the theme was "
        "not switched to 'dark', the default from 2.1.0: it stays 'light', and the next start "
        "tries again"
    ) in journal
    assert "Switched the theme" not in journal

    works_again()
    assert _controller(database_handler).settings["theme"] == "dark"
    assert _stored(database_handler)["theme"] == "dark"
    assert _stored(database_handler)[MARKER] is True
    assert SWITCHED in capsys.readouterr().out
    assert _controller(database_handler).settings["theme"] == "dark"
    assert "[SETTINGS]" not in capsys.readouterr().out, "and only once"


def test_a_fresh_install_that_cannot_store_the_marker_records_it_later(database_handler, capsys):
    works_again = _refuse(database_handler, MARKER)

    assert _controller(database_handler).settings["theme"] == "dark", "the default"
    assert MARKER not in _stored(database_handler)
    assert (
        "[SETTINGS] Could not store ui_dark_default_applied; the next start tries again"
    ) in capsys.readouterr().out

    works_again()
    assert _controller(database_handler).settings["theme"] == "dark"
    assert _stored(database_handler)[MARKER] is True
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_the_marker_is_a_persisted_bool(system_controller):
    assert MARKER in system_controller._get_persisted_keys()
    assert system_controller._get_setting_type(MARKER) is bool
    assert "theme" in system_controller._get_persisted_keys()


# --- What main.py reads before the first window --------------------------------------------


@pytest.fixture
def main(monkeypatch):
    """The main module (it installs its own excepthook on import)."""
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    import main as module  # noqa: PLC0415

    return module


@pytest.mark.parametrize(
    ("theme", "marker", "expected"),
    [
        (None, None, "dark"),  # a fresh install
        ("light", None, "dark"),  # 2.0.0's lab device: switched by the load
        ("dark", None, "dark"),
        ("light", False, "dark"),
        ("light", True, "light"),  # the operator's choice after the switch
        ("dark", True, "dark"),
        (None, True, "dark"),
        ("sepia", True, "dark"),  # no such theme: StyleManager applies the default
    ],
)
def test_main_reads_the_theme_the_settings_load_with(
    main, database_handler, theme, marker, expected
):
    from ui.style.theme import theme_or_default  # noqa: PLC0415

    if theme is not None:
        database_handler.update_system_setting("theme", theme, "str")
    if marker is not None:
        database_handler.update_system_setting(MARKER, marker, "bool")

    before = theme_or_default(main._startup_theme())  # read before the settings load
    loaded = theme_or_default(_controller(database_handler).settings["theme"])

    assert before == loaded == expected


def test_the_read_creates_nothing_and_never_raises(isolated_data_dir, tmp_path):
    from models.database_handler import DatabaseHandler  # noqa: PLC0415
    from utils import paths  # noqa: PLC0415

    path = Path(paths.database_path())
    assert DatabaseHandler.peek_system_settings() == {}, "no database yet"
    assert not path.exists(), "and none is created"

    junk = tmp_path / "not a database.db"
    junk.write_bytes(b"this is not sqlite")
    assert DatabaseHandler.peek_system_settings(junk) == {}

    no_table = tmp_path / "empty.db"
    sqlite3.connect(no_table).close()
    assert DatabaseHandler.peek_system_settings(no_table) == {}

    handler = DatabaseHandler()
    handler.update_system_setting("theme", "light", "str")
    handler.update_system_setting(MARKER, True, "bool")
    handler.update_system_setting("num_hats", 2, "int")
    before = path.read_bytes()
    peeked = DatabaseHandler.peek_system_settings()
    assert peeked == handler.get_system_settings()
    assert (peeked["theme"], peeked[MARKER], peeked["num_hats"]) == ("light", True, 2)
    assert path.read_bytes() == before, "read-only"

    spaced = tmp_path / "a folder #1" / "rrr database.db"
    spaced.parent.mkdir()
    spaced.write_bytes(before)
    assert DatabaseHandler.peek_system_settings(spaced)["theme"] == "light"


# --- Start-up: the first frame of every window ------------------------------------------


@pytest.fixture
def startup(qapp, main, monkeypatch, isolated_data_dir, tokens, fake_relay_handler):
    """Runs main.main() as the launcher does, on this test's QApplication, and records
    every window when it is first shown: its class, the theme applied then, the stylesheet
    and the window colour on screen. Left out: the relay hardware (FakeRelayHandler),
    hardware detection, the update check, the single-instance server and the real GUI,
    which is a stand-in window built with main's arguments. The event loop is a loop that
    runs until the main window shows."""
    import controllers.system_controller as system_controller_module  # noqa: PLC0415
    import gpio.gpio_handler as gpio_handler  # noqa: PLC0415
    import ui.gui as gui_module  # noqa: PLC0415
    import ui.splash_screen as splash_module  # noqa: PLC0415
    import ui.update_notifier as update_notifier  # noqa: PLC0415
    from PyQt5.QtCore import QEvent, QObject, pyqtSignal  # noqa: PLC0415
    from PyQt5.QtGui import QGuiApplication, QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import QWidget  # noqa: PLC0415
    from ui.style import theme as theme_module  # noqa: PLC0415

    relays = type(fake_relay_handler)  # conftest's FakeRelayHandler, for RelayHandler
    sheets = {
        theme: (STYLE_DIR / f"app-{theme}.qss").read_text(encoding="utf-8")
        for theme in tokens.THEMES
    }
    record = {"shown": [], "built": [], "applied": [], "windows": [], "splashes": []}

    def on_screen():
        sheet = qapp.styleSheet()
        manager = theme_module.style_manager()
        return {
            "theme": getattr(manager, "theme", None),
            "sheet": next((name for name, text in sheets.items() if text == sheet), None),
            "window": qapp.palette().color(QPalette.Window).name().upper(),
        }

    class Shows(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Show and obj.isWidgetType() and obj.isWindow():
                record["shown"].append((type(obj).__name__, on_screen()))
            return False

    class MainWindow(QWidget):
        """Stands in for RodentRefreshmentGUI: records the theme it was built in, and shows
        itself as it is built, as RodentRefreshmentGUI's constructor does (showMaximized):
        inside setup(), before main() reaches gui.show()."""

        system_message_signal = pyqtSignal(str)

        def __init__(self, *args, **kwargs):
            super().__init__()
            record["built"].append(on_screen())
            record["windows"].append(self)
            self.showMaximized()

    class KeptSplash(splash_module.SplashScreen):
        """The splash, kept alive by the test (main keeps no reference once it returns)."""

        def __init__(self):
            super().__init__()
            record["splashes"].append(self)

    apply = theme_module.StyleManager.apply

    def recording_apply(manager, theme=theme_module.DEFAULT_THEME):
        record["applied"].append(theme)
        return apply(manager, theme)

    def event_loop():
        deadline = time.monotonic() + 30
        while not record["windows"] or not record["windows"][-1].isVisible():
            if time.monotonic() > deadline:
                raise TimeoutError(f"the main window never showed: {record}")
            qapp.processEvents()
            time.sleep(0.005)
        return 0

    for name in (
        "gui",
        "system_controller",
        "database_handler",
        "login_system",
        "relay_handler",
        "notification_handler",
        "controller",
        "app_settings",
    ):
        monkeypatch.setattr(main, name, None, raising=False)
    monkeypatch.setattr(main, "__version__", f"test-{uuid.uuid4().hex[:12]}")  # its own key
    monkeypatch.setattr(main, "SafeQApplication", lambda argv: qapp)
    monkeypatch.setattr(qapp, "exec_", event_loop)
    monkeypatch.setattr(main, "_dbg", lambda message: None)
    monkeypatch.setattr(main.updater, "set_busy_check", lambda check: None)
    monkeypatch.setattr(main, "_start_single_instance_server", lambda key, gui: None)
    monkeypatch.setattr(main, "RelayHandler", relays)
    monkeypatch.setattr(gpio_handler, "RelayHandler", relays)
    monkeypatch.setattr(
        system_controller_module.SystemController, "ensure_solenoid_defaults", lambda self: None
    )
    monkeypatch.setattr(main, "RodentRefreshmentGUI", MainWindow)
    monkeypatch.setattr(gui_module, "RodentRefreshmentGUI", MainWindow)
    monkeypatch.setattr(splash_module, "SplashScreen", KeptSplash)
    monkeypatch.setattr(
        update_notifier.UpdateNotifier, "check_for_updates", classmethod(lambda cls, gui: None)
    )
    monkeypatch.setattr(theme_module.StyleManager, "apply", recording_apply)
    # main() points stdout and stderr at the System Messages panel
    monkeypatch.setattr(sys, "stdout", sys.stdout)
    monkeypatch.setattr(sys, "stderr", sys.stderr)

    old = (QPalette(qapp.palette()), qapp.styleSheet(), qapp.font())
    quits = QGuiApplication.quitOnLastWindowClosed()
    shows = Shows()
    qapp.installEventFilter(shows)

    def run(splash):
        monkeypatch.setattr(main, "USE_SPLASH_SCREEN", splash)
        with pytest.raises(SystemExit) as exited:
            main.main()
        assert exited.value.code == 0
        return record

    yield run

    qapp.removeEventFilter(shows)
    for splash in record["splashes"]:
        splash.close()
        if splash._worker is not None:
            splash._worker.wait(10000)
        splash.deleteLater()
    for window in record["windows"]:
        window.close()
        window.deleteLater()
    manager = qapp.property("style_manager")
    qapp.setProperty("style_manager", None)
    if manager is not None:
        manager.deleteLater()
    QGuiApplication.setQuitOnLastWindowClosed(quits)
    qapp.setStyleSheet(old[1])
    qapp.setPalette(old[0])
    qapp.setFont(old[2])
    qapp.processEvents()


@pytest.mark.parametrize("splash", [False, True], ids=["no-splash", "splash"])
@pytest.mark.parametrize(
    ("saved", "expected"),
    [
        ({}, "dark"),  # a fresh install
        ({"theme": "light"}, "dark"),  # 2.0.0's lab device, at its first 2.1.0 start
        ({"theme": "light", MARKER: True}, "light"),  # the operator chose light since
    ],
    ids=["fresh", "light-before-2.1.0", "light-chosen"],
)
def test_every_window_shows_in_the_saved_theme_from_its_first_frame(
    startup, tokens, isolated_data_dir, saved, expected, splash
):
    """main.USE_SPLASH_SCREEN is False on the devices (no splash); both paths are run."""
    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    if saved:
        database = DatabaseHandler()  # the database a previous start left
        for key, value in saved.items():
            database.update_system_setting(key, value, "bool" if key == MARKER else "str")

    record = startup(splash)

    shown = [name for name, _ in record["shown"]]
    assert shown == (["KeptSplash", "MainWindow"] if splash else ["MainWindow"]), "shown once"
    screen = {"theme": expected, "sheet": expected, "window": tokens.value("bg.page", expected)}
    for name, seen in record["shown"]:
        assert seen == screen, name
    assert record["built"] == [screen], "the main window is built in its theme"
    assert record["applied"] == [expected], "one theme, applied once, before any window"


@pytest.mark.parametrize("splash", [False, True], ids=["no-splash", "splash"])
def test_when_the_first_read_fails_the_window_is_built_in_the_loaded_theme(
    startup, tokens, monkeypatch, isolated_data_dir, splash
):
    """main.py's early read finds nothing (here: it is made to fail), so the start-up
    theme is the default, dark; the settings then load light, the operator's choice. The
    main window is still built and shown in light: _apply_loaded_theme applies it once
    the settings have loaded, before the window is built."""
    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    database = DatabaseHandler()
    database.update_system_setting("theme", "light", "str")
    database.update_system_setting(MARKER, True, "bool")
    monkeypatch.setattr(DatabaseHandler, "peek_system_settings", staticmethod(lambda *a: {}))

    record = startup(splash)

    light = {"theme": "light", "sheet": "light", "window": tokens.value("bg.page", "light")}
    assert record["applied"] == ["dark", "light"]
    assert record["built"] == [light]
    assert record["shown"][-1] == ("MainWindow", light)
