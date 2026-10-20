"""Qt can parse both generated stylesheets.

build_qss.py checks the template's own syntax (roles, placeholders, directives), not the
QSS it writes. Qt drops an application stylesheet it cannot parse, all of it, with one
warning, "Could not parse application stylesheet", and the app falls back to the native
look. A stray brace, or a template line copied out as text, does that. Offscreen.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"

# The QApplication this module uses, kept for the rest of the session. When a
# QApplication is destroyed, PyQt5 deletes every QObject without a parent.
_QAPP = []


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


def _parse_warnings(qapp, qss):
    """Qt's parse warnings while `qss` is the application stylesheet.

    Qt parses it when a widget is polished, not when it is set.
    """
    from PyQt5.QtCore import qInstallMessageHandler  # noqa: PLC0415
    from PyQt5.QtWidgets import QLabel  # noqa: PLC0415

    messages = []
    old = qapp.styleSheet()
    previous = qInstallMessageHandler(lambda _mode, _context, message: messages.append(message))
    try:
        qapp.setStyleSheet(qss)
        QLabel("probe").ensurePolished()
    finally:
        qInstallMessageHandler(previous)
        qapp.setStyleSheet(old)
    return [message for message in messages if "Could not parse" in message]


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_qt_parses_the_stylesheet(qapp, theme):
    qss = (STYLE_DIR / f"app-{theme}.qss").read_text(encoding="utf-8")
    assert _parse_warnings(qapp, qss) == [], (
        f"Qt cannot parse app-{theme}.qss, so it would drop all of it: look in "
        "app.qss.tmpl for an unbalanced brace or a line that is not QSS"
    )


@pytest.mark.parametrize(
    "broken",
    [
        "QLabel#Probe {\n    @dark\n}\n",  # an indented directive, copied out as text
        "QLabel#Probe {\n    color: #000000;\n",  # a brace never closed
        "}\n",  # a brace never opened
    ],
)
def test_a_stylesheet_qt_cannot_parse_is_noticed(qapp, broken):
    qss = (STYLE_DIR / "app-light.qss").read_text(encoding="utf-8") + broken
    assert _parse_warnings(qapp, qss) == ["Could not parse application stylesheet"]
