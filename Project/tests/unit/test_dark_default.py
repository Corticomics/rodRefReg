"""Dark is the default theme, every device switches to it once, and a revert stays
readable (v2.1.0).

The owner's decisions of 2026-10-22: "make the darkmode the default for the app", and for
the devices already in the lab, "switch everyone once": at its first start of 2.1.0 a
device switches to dark one time, and after that the operator's choice sticks. And of
2026-10-23, "keep reverts readable": 2.1.0 keeps its theme under a key of its own,
ui_theme (SystemController.THEME_KEY), and leaves the 'theme' row that 2.0.0 reads exactly
as 2.0.0 saved it, so a device reverted to 2.0.0 opens in 2.0.0's light theme, not in its
dark one, whose tables show every other row near-white. Pinned here against the real
SystemController and database, and main.py's own start-up, offscreen:

- dark is the default wherever a default lives: the settings (SystemController), the
  style layer (tokens.DEFAULT_THEME, StyleManager, theme_or_default) and Help's HTML;
- a device without ui_theme (a fresh install, or 2.0.0's lab device at its first start of
  2.1.0) starts dark and stores it there: that is the one-time switch, with one
  [SETTINGS] line when 2.0.0's theme was light. Once ui_theme is stored, the operator's
  choice stays, across restarts, a revert to 2.0.0 and the update back;
- 2.1.0 never writes, changes or deletes the 'theme' row, and never reads it as the
  theme: the row is compared whole, its updated_at included, so even a rewrite of the
  same value fails. A revert therefore opens 2.0.0 in the theme it saved. A marker row a
  pre-release build of 2.1.0 stored changes nothing;
- when the database refuses ui_theme, the device starts dark all the same, and the next
  start stores it. A read that fails is not taken for a device without ui_theme: the
  operator's choice stays, and a switch it puts off is made at the next start;
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
from contextlib import closing

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path  # noqa: E402

THEME_KEY = "ui_theme"  # 2.1.0's theme (test_the_theme_is_a_key_of_2_1_0s_own pins it)
LEGACY = "theme"  # the row v1.5.0 to 2.0.0 keep their theme in
MARKER = "ui_dark_default_applied"  # the row pre-release builds of 2.1.0 stored
STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"
SWITCHED = (
    "[SETTINGS] Switched the theme to 'dark', the default from 2.1.0, once (it was 'light', "
    "which is kept for a revert to 2.0.0); Settings > General > Appearance switches it "
    "back, and that choice is kept"
)
# When an older build saved a row: a fixed time in the past, so that a rewrite of the
# row, even with the value it had, changes it.
SAVED_EARLIER = "2026-10-19 09:00:00"

# The keys 2.0.0's save writes: its SystemController._get_persisted_keys (3b2a4202).
RELEASE_200_PERSISTED_KEYS = frozenset(
    {
        "cage_relays",
        "cycle_interval",
        "debug_mode",
        "flow_sampling_hz",
        "flow_sensor_type",
        "global_master_relay_id",
        "hardware_mode",
        "log_level",
        "max_consecutive_sensor_errors",
        "max_pulse_delivery_time_s",
        "max_pulses_per_delivery",
        "min_trigger_interval_ms",
        "num_hats",
        "predictive_close_ms",
        "pulse_settling_ms",
        "pulse_width_ms",
        "residual_check_ms",
        "residual_flow_threshold_ml_min",
        "round_doses_up",
        "stagger_interval",
        "theme",
        "uart_port",
        "use_pulse_delivery",
        "valve_topology",
    }
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


def _row(database_handler, key):
    """The whole system_settings row of `key`, updated_at included, or None."""
    with closing(sqlite3.connect(database_handler.db_path)) as conn:
        return conn.execute(
            "SELECT setting_key, setting_value, setting_type, updated_at "
            "FROM system_settings WHERE setting_key = ?",
            (key,),
        ).fetchone()


def _saved_earlier(database_handler, key, value, type_name="str"):
    """A row an older build saved (at SAVED_EARLIER), as its _write_setting_to_db wrote it:
    2.0.0's theme is the drop-down's text, a 'str'. Returns the row."""
    with closing(sqlite3.connect(database_handler.db_path)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO system_settings "
            "(setting_key, setting_value, setting_type, updated_at) VALUES (?, ?, ?, ?)",
            (key, str(value), type_name, SAVED_EARLIER),
        )
        conn.commit()
    return _row(database_handler, key)


def _controller(database_handler):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    return SystemController(database_handler)


def _press(controller, theme):
    """The theme button: SettingsTab._theme_changed puts the theme in the settings, and its
    auto-save saves the whole dict (test_settings_theme_button.py drives the button)."""
    controller.settings[THEME_KEY] = theme
    controller.save_settings(controller.settings)


def _theme_at_start(database_handler):
    """What main.py applies before any window shows."""
    from controllers.system_controller import SystemController  # noqa: PLC0415
    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    return SystemController.theme_at_start(
        DatabaseHandler.peek_system_settings(database_handler.db_path)
    )


class _Release200:
    """2.0.0's settings rules, as its SystemController has them (3b2a4202), for a revert.

    Its load migrates a legacy settings.json and the Slack secrets, then reads every row
    over its defaults, which have no theme. It has no settle step, so it switches,
    removes and forces nothing. Its save writes the keys it persists
    (RELEASE_200_PERSISTED_KEYS, with 'theme' and pulse_width_ms, without ui_theme) and
    deletes nothing. Its main.py applies settings.get('theme', 'light'), and its Settings
    tab's auto-save saves the whole dict with the Theme drop-down's text, which shows that
    theme. Built lazily, as a subclass of this release's controller with load_settings and
    save_settings as 2.0.0 has them, and its persisted keys and defaults.
    """

    def __new__(cls, database_handler):
        from controllers.system_controller import SystemController  # noqa: PLC0415

        class Release200(SystemController):
            def load_settings(self):
                try:
                    self._migrate_legacy_json_if_needed()
                    self._ensure_secrets_migrated()
                    settings = self._create_default_settings()
                    settings.update(self._load_database_settings())
                    settings.update(self._load_secrets())
                    return settings
                except Exception as e:
                    self.system_status.emit(f"Error loading settings: {str(e)}")
                    return self._create_default_settings()

            def save_settings(self, settings_dict):
                try:
                    self._save_secrets_if_present(settings_dict)
                    self._save_database_settings(settings_dict)
                    self.settings.update(settings_dict)
                    self.settings_updated.emit(self.settings)
                except Exception as e:
                    self.system_status.emit(f"Error saving settings: {str(e)}")

            def _get_persisted_keys(self):
                return set(RELEASE_200_PERSISTED_KEYS)

            def _create_default_settings(self):
                defaults = super()._create_default_settings()
                del defaults[SystemController.THEME_KEY]
                return defaults

            def theme_shown(self):
                """The theme 2.0.0's main.py applies at its start."""
                return self.settings.get("theme", "light")

            def auto_save(self, theme=None):
                """2.0.0's Settings tab saves the whole dict, with the drop-down's text: the
                theme it shows, or `theme` when the operator picks one."""
                self.settings["theme"] = theme or self.theme_shown()
                self.save_settings(self.settings)

        return Release200(database_handler)


# --- Dark is the default ------------------------------------------------------------------


def test_dark_is_the_default_in_every_layer(qapp, tokens, database_handler):
    from controllers.system_controller import SystemController  # noqa: PLC0415
    from ui.style import theme  # noqa: PLC0415
    from utils.help_content_manager import HelpContentManager  # noqa: PLC0415

    assert tokens.DEFAULT_THEME == theme.DEFAULT_THEME == "dark"
    assert SystemController.DEFAULT_THEME == tokens.DEFAULT_THEME, "one default, two layers"
    settings = SystemController(database_handler).settings
    assert settings[THEME_KEY] == "dark"
    assert LEGACY not in settings, "no default for 2.0.0's key"

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


def test_the_theme_is_a_key_of_2_1_0s_own(system_controller):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    assert SystemController.THEME_KEY == THEME_KEY
    assert SystemController.LEGACY_THEME_KEY == LEGACY
    assert THEME_KEY not in RELEASE_200_PERSISTED_KEYS, "2.0.0 never writes it"
    persisted = system_controller._get_persisted_keys()
    assert THEME_KEY in persisted
    assert system_controller._get_setting_type(THEME_KEY) is str
    assert LEGACY not in persisted, "2.1.0 never writes 2.0.0's row"
    assert MARKER not in persisted, "nor a pre-release build's"


# --- The one-time switch ----------------------------------------------------------------


def test_a_fresh_install_starts_dark_and_stores_its_theme(database_handler, capsys):
    controller = _controller(database_handler)

    assert controller.settings[THEME_KEY] == "dark"
    assert _stored(database_handler)[THEME_KEY] == "dark"
    assert _row(database_handler, LEGACY) is None, "and no row for 2.0.0"
    assert "[SETTINGS]" not in capsys.readouterr().out

    row = _row(database_handler, THEME_KEY)
    assert _controller(database_handler).settings[THEME_KEY] == "dark"
    assert _row(database_handler, THEME_KEY) == row, "stored once"
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_2_0_0s_light_theme_is_switched_to_dark_once_and_left_as_2_0_0_saved_it(
    database_handler, capsys
):
    """2.0.0 stored the theme an operator picked ('light' in the lab). 2.1.0's first start
    shows dark and stores it under ui_theme, with one journal line; 2.0.0's row stays as it
    was, for a revert."""
    saved = _saved_earlier(database_handler, LEGACY, "light")

    controller = _controller(database_handler)

    assert controller.settings[THEME_KEY] == "dark"
    assert _stored(database_handler)[THEME_KEY] == "dark"
    assert _row(database_handler, LEGACY) == saved
    journal = capsys.readouterr().out
    assert journal.count("[SETTINGS]") == 1
    assert SWITCHED in journal

    again = _controller(database_handler)  # every later start
    assert again.settings[THEME_KEY] == "dark"
    assert _row(database_handler, LEGACY) == saved
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_a_dark_theme_2_0_0_saved_is_switched_without_a_line(database_handler, capsys):
    saved = _saved_earlier(database_handler, LEGACY, "dark")

    assert _controller(database_handler).settings[THEME_KEY] == "dark"
    assert _stored(database_handler)[THEME_KEY] == "dark"
    assert _row(database_handler, LEGACY) == saved
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_a_legacy_settings_json_theme_is_not_copied(
    database_handler, write_legacy_settings, capsys
):
    """A device still on a pre-v1.5.0 settings.json has its settings copied into the
    database at its first start. 'theme' is not 2.1.0's key: it is not copied, and the
    device starts dark, the default, with nothing to say."""
    write_legacy_settings({"num_hats": 2, "theme": "light"})

    controller = _controller(database_handler)

    assert controller.settings[THEME_KEY] == "dark"
    assert _stored(database_handler)["num_hats"] == 2, "the migration ran"
    assert _row(database_handler, LEGACY) is None
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_light_chosen_with_the_button_is_kept_under_ui_theme(database_handler, capsys):
    """The button's choice is saved under ui_theme. Every later start keeps it, and so does
    ensure_solenoid_defaults, which main.setup() runs at every start and which saves the
    whole settings dict. 2.0.0's row stays as it was throughout."""
    saved = _saved_earlier(database_handler, LEGACY, "light")
    controller = _controller(database_handler)  # the first start of 2.1.0
    assert SWITCHED in capsys.readouterr().out

    _press(controller, "light")

    for _ in range(2):
        assert _theme_at_start(database_handler) == "light"
        later = _controller(database_handler)
        later.ensure_solenoid_defaults()
        assert later.settings[THEME_KEY] == "light"
        assert _stored(database_handler)[THEME_KEY] == "light"
        assert _row(database_handler, LEGACY) == saved
    assert "[SETTINGS]" not in capsys.readouterr().out


@pytest.mark.parametrize("saved", ["light", "dark", None], ids=["light", "dark", "no-row"])
def test_no_save_writes_the_theme_row(database_handler, saved):
    """Not the load, not a save of the whole dict (the auto-save, Change Relay Hats,
    ensure_solenoid_defaults), not a save that names 'theme' itself: 2.0.0's row stays as
    it was, and where there was none, none is made."""
    row = _saved_earlier(database_handler, LEGACY, saved) if saved else None
    controller = _controller(database_handler)
    if saved:
        assert controller.settings[LEGACY] == saved, "loaded like any row, and read by nothing"

    controller.save_settings(controller.settings)
    controller.save_settings({LEGACY: "dark", THEME_KEY: "light"})
    controller.settings[LEGACY] = "light"
    controller.save_settings(controller.settings)
    controller.ensure_solenoid_defaults()

    assert _row(database_handler, LEGACY) == row
    assert _stored(database_handler)[THEME_KEY] == "light"


# --- A revert to 2.0.0, and the update back ------------------------------------------------


@pytest.mark.parametrize("chosen", [None, "light", "dark"], ids=["none", "light", "dark"])
@pytest.mark.parametrize(
    ("saved", "shown"),
    [("light", "light"), (None, "light"), ("dark", "dark")],
    ids=["light-saved", "none-saved", "dark-saved"],
)
def test_a_revert_opens_2_0_0_in_the_theme_it_saved(database_handler, saved, shown, chosen):
    """The owner's "keep reverts readable". A lab device saved light in 2.0.0. 2.1.0 starts
    it dark, and the operator may choose either theme with the button, but the revert opens
    2.0.0 in light, its readable theme, not in its dark one. A device that never saved a
    theme opens in 2.0.0's own default, light, and one that saved dark in 2.0.0's dark
    theme, as before the update."""
    row = _saved_earlier(database_handler, LEGACY, saved) if saved else None
    first = _controller(database_handler)  # 2.1.0's first start
    assert first.settings[THEME_KEY] == "dark"
    if chosen:
        _press(first, chosen)
    first.ensure_solenoid_defaults()  # main.setup() runs it at every start
    assert _row(database_handler, LEGACY) == row, "as 2.0.0 saved it"

    old = _Release200(database_handler)  # reverted to 2.0.0

    assert old.theme_shown() == shown
    assert old.settings[THEME_KEY] == (chosen or "dark"), "loaded like any row, and unused"


@pytest.mark.parametrize("on_2_0_0", ["saves-nothing", "auto-saves", "picks-dark"])
@pytest.mark.parametrize("chosen", ["dark", "light"])
def test_the_update_after_a_revert_keeps_the_theme_chosen_in_2_1_0(
    database_handler, capsys, chosen, on_2_0_0
):
    """2.0.0 does not know ui_theme: its load reads the row into memory with every other,
    and its save writes only its own keys. Whatever 2.0.0 does with its own theme after
    the revert, the next 2.1.0 starts in the theme chosen in 2.1.0 (dark when the button
    was never pressed), with no second switch, and 2.0.0's choice waits in its own row
    for the next revert."""
    _saved_earlier(database_handler, LEGACY, "light")  # the lab device
    first = _controller(database_handler)  # 2.1.0's first start: switched
    if chosen == "light":
        _press(first, "light")
    choice = _row(database_handler, THEME_KEY)

    old = _Release200(database_handler)  # reverted to 2.0.0
    assert old.theme_shown() == "light"
    if on_2_0_0 == "auto-saves":
        old.auto_save()  # another setting changed: the drop-down's text is saved with it
    elif on_2_0_0 == "picks-dark":
        old.auto_save("dark")
    capsys.readouterr()

    assert _theme_at_start(database_handler) == chosen  # updated to 2.1.0 again
    new = _controller(database_handler)
    assert new.settings[THEME_KEY] == chosen
    assert _row(database_handler, THEME_KEY) == choice, "2.0.0 left it as it was"
    assert "[SETTINGS]" not in capsys.readouterr().out, "no second switch"
    kept = "dark" if on_2_0_0 == "picks-dark" else "light"
    assert _Release200(database_handler).theme_shown() == kept, "the next revert"


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("marker", [True, False])
def test_a_marker_row_from_a_pre_release_build_changes_nothing(
    database_handler, capsys, marker, theme
):
    """Builds of 2.1.0 before 2026-10-23 recorded the one-time switch in a row of their own,
    ui_dark_default_applied, and kept their theme in 'theme' (the owner's test Pis ran
    them). 2.1.0 reads no such row and writes none: the device starts as one without
    ui_theme does, and both rows stay as they were."""
    theme_row = _saved_earlier(database_handler, LEGACY, theme)
    marker_row = _saved_earlier(database_handler, MARKER, marker, "bool")

    assert _theme_at_start(database_handler) == "dark"
    controller = _controller(database_handler)

    assert controller.settings[THEME_KEY] == "dark"
    assert _stored(database_handler)[THEME_KEY] == "dark"
    assert _row(database_handler, MARKER) == marker_row
    assert _row(database_handler, LEGACY) == theme_row
    journal = capsys.readouterr().out
    assert (SWITCHED in journal) is (theme == "light")
    assert MARKER not in journal


# --- When the database refuses the row ----------------------------------------------------


def _refuse(database_handler, key):
    """The database refuses every write of the row `key`, as a full or locked database
    refuses a write: a trigger aborts the INSERT, so DatabaseHandler sees an sqlite3 error.
    Returns a function that makes it accept the row again."""
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


REFUSED = (
    "[SETTINGS] Could not store ui_theme='dark'; RRR starts in it all the same, and the "
    "next start tries again"
)


def test_a_refused_theme_still_starts_dark_and_the_next_start_stores_it(database_handler, capsys):
    """A device without ui_theme starts in the default, so a refused row changes nothing on
    screen: the device is dark at that start too. The next start stores the row and says
    the switch, once."""
    saved = _saved_earlier(database_handler, LEGACY, "light")
    works_again = _refuse(database_handler, THEME_KEY)

    controller = _controller(database_handler)

    assert controller.settings[THEME_KEY] == "dark"
    assert _theme_at_start(database_handler) == "dark"
    assert THEME_KEY not in _stored(database_handler)
    assert _row(database_handler, LEGACY) == saved
    journal = capsys.readouterr().out
    assert journal.count("[SETTINGS]") == 1
    assert REFUSED in journal

    works_again()
    assert _controller(database_handler).settings[THEME_KEY] == "dark"
    assert _stored(database_handler)[THEME_KEY] == "dark"
    assert _row(database_handler, LEGACY) == saved
    assert SWITCHED in capsys.readouterr().out
    assert _controller(database_handler).settings[THEME_KEY] == "dark"
    assert "[SETTINGS]" not in capsys.readouterr().out, "and only once"


def test_a_fresh_install_that_cannot_store_its_theme_stores_it_later(database_handler, capsys):
    works_again = _refuse(database_handler, THEME_KEY)

    assert _controller(database_handler).settings[THEME_KEY] == "dark", "the default"
    assert THEME_KEY not in _stored(database_handler)
    assert REFUSED in capsys.readouterr().out

    works_again()
    assert _controller(database_handler).settings[THEME_KEY] == "dark"
    assert _stored(database_handler)[THEME_KEY] == "dark"
    assert "[SETTINGS]" not in capsys.readouterr().out


# --- When a read fails ----------------------------------------------------------------------


def _the_settling_read_fails(monkeypatch, database_handler):
    """The read the load settles the stored settings from fails, as a read of a locked
    database fails once its busy timeout runs out: the real get_system_settings gets a
    connection whose execute raises sqlite3.OperationalError, prints the error and returns
    {}. Every other read, and every write, is real. Returns a function that ends the
    fault."""
    from controllers.system_controller import SystemController  # noqa: PLC0415

    class Locked:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def cursor(self):
            return self

        def execute(self, *args):
            raise sqlite3.OperationalError("database is locked")

    fault = {"on": True, "settling": False}
    settle = SystemController._settle_stored_settings
    read = database_handler.get_system_settings

    def settling(self):
        fault["settling"] = True
        try:
            return settle(self)
        finally:
            fault["settling"] = False

    def reading():
        if not (fault["on"] and fault["settling"]):
            return read()
        database_handler.connect = Locked
        try:
            return read()
        finally:
            del database_handler.connect

    monkeypatch.setattr(SystemController, "_settle_stored_settings", settling)
    monkeypatch.setattr(database_handler, "get_system_settings", reading)
    return lambda: fault.update(on=False)


LOCKED = "Error retrieving system settings: database is locked"


def test_a_failed_read_is_not_taken_for_a_device_without_its_theme(
    monkeypatch, database_handler, capsys
):
    """get_system_settings returns {} when its read fails. When the read the load settles
    from fails so, the one-time switch stores nothing: the operator's light stays, its row
    unchanged to the second, and this start shows it, from the load's own read a moment
    later. Taken for a device without ui_theme, that {} would have stored dark over the
    operator's choice for good, with no line to say why."""
    _saved_earlier(database_handler, LEGACY, "light")  # 2.0.0's
    choice = _saved_earlier(database_handler, THEME_KEY, "light")  # the button's
    fault_ends = _the_settling_read_fails(monkeypatch, database_handler)

    controller = _controller(database_handler)

    journal = capsys.readouterr().out
    assert LOCKED in journal, "the read failed"
    assert "[SETTINGS]" not in journal
    assert _row(database_handler, THEME_KEY) == choice
    assert controller.settings[THEME_KEY] == "light"

    fault_ends()
    assert _theme_at_start(database_handler) == "light"
    assert _controller(database_handler).settings[THEME_KEY] == "light"
    assert _row(database_handler, THEME_KEY) == choice
    assert "[SETTINGS]" not in capsys.readouterr().out


@pytest.mark.parametrize("saved", ["light", None], ids=["2.0.0-light", "fresh"])
def test_a_switch_a_failed_read_puts_off_is_made_at_the_next_start(
    monkeypatch, database_handler, capsys, saved
):
    """A device without ui_theme whose settling read fails starts dark all the same: the
    load's own read finds no ui_theme. The next start makes the switch, with its line
    where 2.0.0 saved light, and only once."""
    if saved:
        _saved_earlier(database_handler, LEGACY, saved)
    fault_ends = _the_settling_read_fails(monkeypatch, database_handler)

    assert _controller(database_handler).settings[THEME_KEY] == "dark"
    journal = capsys.readouterr().out
    assert LOCKED in journal, "the read failed"
    assert "[SETTINGS]" not in journal

    fault_ends()
    assert _controller(database_handler).settings[THEME_KEY] == "dark"
    assert _stored(database_handler)[THEME_KEY] == "dark"
    assert (SWITCHED in capsys.readouterr().out) is (saved == "light")
    assert _controller(database_handler).settings[THEME_KEY] == "dark"
    assert "[SETTINGS]" not in capsys.readouterr().out, "and only once"


# --- What main.py reads before the first window --------------------------------------------


@pytest.fixture
def main(monkeypatch):
    """The main module (it installs its own excepthook on import)."""
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    import main as module  # noqa: PLC0415

    return module


@pytest.mark.parametrize(
    ("legacy", "theme", "expected"),
    [
        (None, None, "dark"),  # a fresh install
        ("light", None, "dark"),  # 2.0.0's lab device: switched by the load
        ("dark", None, "dark"),
        ("light", "light", "light"),  # the operator chose light in 2.1.0
        ("dark", "light", "light"),  # 2.0.0's row is never the theme
        ("light", "dark", "dark"),
        (None, "light", "light"),
        ("light", "sepia", "dark"),  # no such theme: StyleManager applies the default
    ],
)
def test_main_reads_the_theme_the_settings_load_with(
    main, database_handler, legacy, theme, expected
):
    from ui.style.theme import theme_or_default  # noqa: PLC0415

    if legacy is not None:
        database_handler.update_system_setting(LEGACY, legacy, "str")
    if theme is not None:
        database_handler.update_system_setting(THEME_KEY, theme, "str")

    before = theme_or_default(main._startup_theme())  # read before the settings load
    loaded = theme_or_default(_controller(database_handler).settings[THEME_KEY])

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
    handler.update_system_setting(THEME_KEY, "light", "str")
    handler.update_system_setting("debug_mode", True, "bool")
    handler.update_system_setting("num_hats", 2, "int")
    before = path.read_bytes()
    peeked = DatabaseHandler.peek_system_settings()
    assert peeked == handler.get_system_settings()
    assert (peeked[THEME_KEY], peeked["debug_mode"], peeked["num_hats"]) == ("light", True, 2)
    assert path.read_bytes() == before, "read-only"

    spaced = tmp_path / "a folder #1" / "rrr database.db"
    spaced.parent.mkdir()
    spaced.write_bytes(before)
    assert DatabaseHandler.peek_system_settings(spaced)[THEME_KEY] == "light"


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
        ({LEGACY: "light"}, "dark"),  # 2.0.0's lab device, at its first 2.1.0 start
        ({LEGACY: "light", THEME_KEY: "light"}, "light"),  # the operator chose light since
    ],
    ids=["fresh", "light-before-2.1.0", "light-chosen"],
)
def test_every_window_shows_in_the_saved_theme_from_its_first_frame(
    startup, tokens, isolated_data_dir, saved, expected, splash
):
    """main.USE_SPLASH_SCREEN is False on the devices (no splash); both paths are run. The
    start leaves 2.0.0's row as it was."""
    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    database = DatabaseHandler()  # the database a previous start left
    rows = {key: _saved_earlier(database, key, value) for key, value in saved.items()}

    record = startup(splash)

    shown = [name for name, _ in record["shown"]]
    assert shown == (["KeptSplash", "MainWindow"] if splash else ["MainWindow"]), "shown once"
    screen = {"theme": expected, "sheet": expected, "window": tokens.value("bg.page", expected)}
    for name, seen in record["shown"]:
        assert seen == screen, name
    assert record["built"] == [screen], "the main window is built in its theme"
    assert record["applied"] == [expected], "one theme, applied once, before any window"
    assert _row(database, LEGACY) == rows.get(LEGACY)


@pytest.mark.parametrize("splash", [False, True], ids=["no-splash", "splash"])
def test_when_the_first_read_fails_the_window_is_built_in_the_loaded_theme(
    startup, tokens, monkeypatch, isolated_data_dir, splash
):
    """main.py's early read finds nothing (here: it is made to fail), so the start-up
    theme is the default, dark; the settings then load light, the operator's choice. The
    main window is still built and shown in light: _apply_loaded_theme applies it once
    the settings have loaded, before the window is built. 2.0.0's dark row is not read."""
    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    database = DatabaseHandler()
    database.update_system_setting(THEME_KEY, "light", "str")
    database.update_system_setting(LEGACY, "dark", "str")
    monkeypatch.setattr(DatabaseHandler, "peek_system_settings", staticmethod(lambda *a: {}))

    record = startup(splash)

    light = {"theme": "light", "sheet": "light", "window": tokens.value("bg.page", "light")}
    assert record["applied"] == ["dark", "light"]
    assert record["built"] == [light]
    assert record["shown"][-1] == ("MainWindow", light)
