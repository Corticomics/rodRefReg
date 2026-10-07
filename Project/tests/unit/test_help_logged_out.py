"""Help is available to guests (QA item #2).

The Settings tab stays gated on login (it controls the device), but Help is
static read-only documentation and should be reachable while logged out. This
exercises the real _update_tab_access logic against a real QTabWidget, and
checks the help copy no longer claims Help is disabled.

Skips when PyQt5 is unavailable; CI installs python3-pyqt5 so it runs there.
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

    return QApplication.instance() or QApplication([])


def _tab_access(qapp, *, logged_in):
    from PyQt5.QtWidgets import QTabWidget, QWidget  # noqa: PLC0415

    from ui.gui import RodentRefreshmentGUI  # noqa: PLC0415

    tabs = QTabWidget()
    profile, settings, help_ = QWidget(), QWidget(), QWidget()
    tabs.addTab(profile, "Profile")
    settings_idx = tabs.addTab(settings, "Settings")
    help_idx = tabs.addTab(help_, "Help")

    fake = SimpleNamespace(
        login_system=SimpleNamespace(is_logged_in=lambda: logged_in),
        main_tab_widget=tabs,
        settings_tab_index=settings_idx,
        help_tab_index=help_idx,
        user_tab=profile,
    )
    # Call the real method logic, unbound, against the fake instance.
    RodentRefreshmentGUI._update_tab_access(fake)
    return tabs, settings_idx, help_idx


def test_guest_sees_help_but_not_settings(qapp):
    tabs, settings_idx, help_idx = _tab_access(qapp, logged_in=False)
    assert tabs.isTabVisible(help_idx) is True
    assert tabs.isTabEnabled(help_idx) is True
    # Settings is hidden entirely for guests (not just disabled).
    assert tabs.isTabVisible(settings_idx) is False


def test_settings_visible_when_logged_in(qapp):
    tabs, settings_idx, help_idx = _tab_access(qapp, logged_in=True)
    assert tabs.isTabVisible(help_idx) is True
    assert tabs.isTabVisible(settings_idx) is True
    assert tabs.isTabEnabled(settings_idx) is True


def test_help_copy_does_not_say_help_is_disabled():
    from utils.help_content_manager import HelpContentManager  # noqa: PLC0415

    html = HelpContentManager().get_content("System Overview")
    assert "Help</strong> tabs are disabled" not in html
