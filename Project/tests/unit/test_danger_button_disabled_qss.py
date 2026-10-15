"""A greyed-out danger button looks greyed out, in both themes.

CLOSE ALL RELAYS (and Close Master, and Log Out) carry the "danger" variant.
Its red rule came after the generic ``QPushButton:disabled`` rule with the
same specificity, so a disabled danger button was painted exactly like an
enabled one: CLOSE ALL RELAYS greyed out during a schedule still looked
pressable. Rendered offscreen; compares colours, not hex values, so a new
palette keeps the guarantee.
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


@pytest.fixture
def theme_qss(qapp):
    old = qapp.styleSheet()

    def _apply(theme):
        qapp.setStyleSheet((STYLE_DIR / f"app-{theme}.qss").read_text(encoding="utf-8"))

    yield _apply
    qapp.setStyleSheet(old)


def _background(enabled, variant="danger"):
    from PyQt5.QtWidgets import QPushButton  # noqa: PLC0415

    button = QPushButton("CLOSE ALL RELAYS")
    button.setProperty("variant", variant)
    button.setEnabled(enabled)
    button.resize(220, 40)
    image = button.grab().toImage()
    return image.pixelColor(6, image.height() // 2).name()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_a_disabled_danger_button_is_painted_like_any_disabled_button(theme_qss, theme):
    theme_qss(theme)

    assert _background(enabled=False) != _background(enabled=True), "still looks pressable"
    assert _background(enabled=False) == _background(enabled=False, variant="none"), (
        "greyed out like every other disabled button"
    )
