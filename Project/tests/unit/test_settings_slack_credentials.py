"""Settings auto-save keeps the Slack credentials it did not change.

Since February 2025 the Settings tab still called Fernet encrypt/decrypt on
the Slack token although the key was no longer created (``self.fernet``
never assigned). Decrypting failed silently, so the field always loaded
empty, and every auto-save (any Settings change) wrote that empty token to
secrets.json, which stopped Slack notifications. Typing a token made the
encrypt call raise, so every later auto-save failed and no Settings change
was stored for the rest of the session. The credentials live in the
mode-0600 secrets.json (Phase 2.5b) and are now shown and saved as stored.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TOKEN = "xoxb-000-test-token"


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


@pytest.fixture
def stored(isolated_data_dir):
    """Credentials already on the device, as the Phase 2.5b file holds them."""
    from utils import secrets  # noqa: PLC0415

    assert secrets.save_credentials(slack_token=TOKEN, channel_id="C9")
    return isolated_data_dir / "secrets.json"


def _tab(database_handler):
    from controllers.system_controller import SystemController  # noqa: PLC0415
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    controller = SystemController(database_handler)
    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    messages = []
    tab = SettingsTab(
        controller,
        login_system=login,
        print_to_terminal=messages.append,
        database_handler=database_handler,
    )
    return tab, controller, messages


def _secrets(path):
    return json.loads(path.read_text())


def test_the_stored_token_is_shown(qapp, stored, database_handler):
    tab, _controller, _messages = _tab(database_handler)
    assert tab.slack_token.text() == TOKEN
    assert tab.slack_channel.text() == "C9"


def test_changing_another_setting_keeps_the_token(qapp, stored, database_handler):
    tab, controller, messages = _tab(database_handler)
    tab.round_doses_up.setChecked(True)  # any auto-save

    assert _secrets(stored) == {"slack_token": TOKEN, "channel_id": "C9"}
    assert controller.settings["round_doses_up"] is True
    assert not any("Auto-save failed" in m for m in messages)


def test_a_typed_token_is_saved_and_does_not_break_later_saves(
    qapp, stored, database_handler
):
    tab, controller, messages = _tab(database_handler)
    tab.slack_token.setText("xoxb-new")
    tab.slack_token.editingFinished.emit()
    assert _secrets(stored)["slack_token"] == "xoxb-new"

    tab.round_doses_up.setChecked(True)
    assert database_handler.get_system_settings()["round_doses_up"] is True
    assert _secrets(stored)["slack_token"] == "xoxb-new"
    assert not any("Auto-save failed" in m for m in messages)


def test_the_tab_writes_no_key_file(qapp, stored, database_handler, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tab, _controller, _messages = _tab(database_handler)
    tab.round_doses_up.setChecked(True)
    assert not (tmp_path / "settings_key.key").exists()
