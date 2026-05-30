"""Regression guard for the logged-out login prompt (QA items #1, #3).

Item #3: the prompt used to carry a "Login" button that only re-selected the
already-current Profile tab, so it appeared to do nothing — it has been removed.
Item #1: the prompt now carries the ``LoginGatePrompt`` objectName that the
theme QSS uses to paint it with the card surface instead of the grey app
background.

Skips when PyQt5 is unavailable; CI installs ``python3-pyqt5`` so it runs there.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


def _make_gate(qapp):
    from PyQt5.QtCore import QObject, pyqtSignal  # noqa: PLC0415
    from PyQt5.QtWidgets import QWidget  # noqa: PLC0415
    from ui.login_gate_widget import LoginGateWidget  # noqa: PLC0415

    class StubLoginSystem(QObject):
        login_status_changed = pyqtSignal()

        def is_logged_in(self):
            return False

    return LoginGateWidget(QWidget(), StubLoginSystem())


def test_login_prompt_has_no_button(qapp):
    """The needless 'Login' button is gone from the logged-out prompt."""
    from PyQt5.QtWidgets import QPushButton  # noqa: PLC0415

    gate = _make_gate(qapp)
    assert gate.login_prompt.findChildren(QPushButton) == []


def test_login_prompt_uses_card_surface_objectname(qapp):
    """The prompt is tagged for the card-coloured background in the theme QSS."""
    gate = _make_gate(qapp)
    assert gate.login_prompt.objectName() == "LoginGatePrompt"
