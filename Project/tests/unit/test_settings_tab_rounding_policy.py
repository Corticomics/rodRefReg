"""The "Round doses up" checkbox reaches the persisted settings (v1.19.0).

Headless (``QT_QPA_PLATFORM=offscreen``). Constructs the real
``SettingsTab`` against the test ``SystemController`` and checks the whole
path the operator relies on: the checkbox reflects the stored value, and
toggling it auto-saves ``round_doses_up`` through ``save_settings`` so the
next ``RelayWorker`` (which copies ``system_controller.settings``) sees it.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    # SettingsTab subscribes to the OperationLock singleton; other test
    # modules leave it as a QObject whose C++ side is gone. Same seam the
    # other UI test modules use: a fresh singleton per test.
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


def _settings_tab(system_controller, database_handler):
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    # Auto-save is gated on a logged-in operator.
    login = SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None)
    return SettingsTab(
        system_controller,
        login_system=login,
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
    )


def test_checkbox_reflects_and_persists_the_setting(qapp, database_handler, system_controller):
    tab = _settings_tab(system_controller, database_handler)
    assert tab.round_doses_up.isChecked() is False, "off by default"

    tab.round_doses_up.setChecked(True)  # stateChanged -> _auto_save_settings

    assert system_controller.settings["round_doses_up"] is True
    assert database_handler.get_system_settings()["round_doses_up"] is True

    tab.round_doses_up.setChecked(False)
    assert system_controller.settings["round_doses_up"] is False


def test_checkbox_loads_a_stored_true(qapp, database_handler, system_controller):
    system_controller.save_settings({"round_doses_up": True})
    tab = _settings_tab(system_controller, database_handler)
    assert tab.round_doses_up.isChecked() is True
