"""Structural test for the calibration Action-button cell wrapper (QA item #13).

A bare fixed-height button handed to setCellWidget gets stretched/anchored and
visually straddles the boundary between two rows. The button is now wrapped in
a centring container so it sits centred in its cell. Pixel centring depends on
a real display (the offscreen QPA cannot lay out cell widgets), so this test
only guards the structure: the cell is a container holding the button with a
centring layout.

Skips when PyQt5 is unavailable; CI installs python3-pyqt5 so it runs there.
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


def test_action_cell_wraps_and_centres_button(qapp):
    from PyQt5.QtCore import Qt  # noqa: PLC0415
    from PyQt5.QtWidgets import QPushButton, QWidget  # noqa: PLC0415
    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    button = QPushButton("Calibrate")
    cell = SettingsTab._make_action_cell(button)

    # The cell handed to setCellWidget is a container, not the bare button.
    assert isinstance(cell, QWidget)
    assert not isinstance(cell, QPushButton)

    layout = cell.layout()
    assert layout is not None
    # The button lives inside the container.
    assert button.parent() is cell
    # The layout centres its contents (so the fixed-height button is centred).
    assert layout.alignment() & Qt.AlignCenter
