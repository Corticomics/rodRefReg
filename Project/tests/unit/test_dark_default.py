"""Dark is the default theme, and every device switches to it once (v2.1.0).

The owner's decisions of 2026-10-22: "make the darkmode the default for the app", and for
the devices already in the lab, "switch everyone once": at its first start of 2.1.0 a
device switches to dark one time, and after that the operator's choice sticks. Pinned
here against the real SystemController and database:

- dark is the default wherever a default lives: the settings (SystemController), the
  style layer (tokens.DEFAULT_THEME, StyleManager, theme_or_default) and Help's HTML;
- a fresh install starts dark and records the switch (ui_dark_default_applied) without a
  journal line; a device whose stored theme is light, as 2.0.0 left it, is switched to
  dark at its first 2.1.0 start, once, with one [SETTINGS] line; from then on the
  operator's choice stays, across restarts and across a revert to 2.0.0 and back;
- the marker is stored before the theme: when the database refuses the marker nothing is
  switched and the next start tries again, and when it refuses the theme the switch is
  lost rather than made twice.
"""

from __future__ import annotations

import os

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


def _refuse(monkeypatch, database_handler, refused_key):
    """The database refuses writes of `refused_key` (DatabaseHandler returns False);
    returns a function that makes it work again."""
    update = database_handler.update_system_setting
    monkeypatch.setattr(
        database_handler,
        "update_system_setting",
        lambda key, *a: False if key == refused_key else update(key, *a),
    )
    # Not monkeypatch.undo(): that would also unset the RRR_DATA the data fixture set
    return lambda: monkeypatch.setattr(database_handler, "update_system_setting", update)


def test_when_the_marker_cannot_be_stored_nothing_is_switched(
    database_handler, monkeypatch, capsys
):
    _theme_saved(database_handler, "light")
    works_again = _refuse(monkeypatch, database_handler, MARKER)

    controller = _controller(database_handler)

    assert controller.settings["theme"] == "light", "as the database still says"
    assert _stored(database_handler)["theme"] == "light"
    assert MARKER not in _stored(database_handler)
    journal = capsys.readouterr().out
    assert (
        "[SETTINGS] Could not store ui_dark_default_applied, so the theme was not switched "
        "to 'dark', the default from 2.1.0: it stays 'light', and the next start tries again"
    ) in journal
    assert "Switched the theme" not in journal

    works_again()
    assert _controller(database_handler).settings["theme"] == "dark"
    assert SWITCHED in capsys.readouterr().out


def test_when_the_theme_cannot_be_stored_the_switch_is_not_made_twice(
    database_handler, monkeypatch, capsys
):
    """The marker is stored first, so a refused theme loses the switch: the device stays
    light, and a later start never switches it over the operator's choice."""
    _theme_saved(database_handler, "light")
    works_again = _refuse(monkeypatch, database_handler, "theme")

    controller = _controller(database_handler)

    assert controller.settings["theme"] == "light"
    assert _stored(database_handler)[MARKER] is True
    assert (
        "[SETTINGS] Could not store the theme 'dark': it stays 'light', and is not switched "
        "again (Settings > General > Appearance switches it)"
    ) in capsys.readouterr().out

    works_again()
    assert _controller(database_handler).settings["theme"] == "light"
    assert "[SETTINGS]" not in capsys.readouterr().out


def test_the_marker_is_a_persisted_bool(system_controller):
    assert MARKER in system_controller._get_persisted_keys()
    assert system_controller._get_setting_type(MARKER) is bool
    assert "theme" in system_controller._get_persisted_keys()
