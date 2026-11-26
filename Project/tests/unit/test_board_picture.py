"""The Cages tab's board picture is in the tree.

Six images that no code or doc loaded were deleted. One picture is loaded: BOARD_PICTURE,
the relay HAT board's picture beside its terminals on the Cages tab. When its file is
missing the tab shows "[Board Diagram Not Found]" in its place and the app raises no error.
This test fails then, or when a rename leaves BOARD_PICTURE behind, with a message that
names the file. (The Cages tab's pixel test fails too, with "assert (None is not None)".)
A Mac's disk ignores case and the Pi's does not, so the test checks the name as spelled:
a rename that changes only a letter's case fails it on a Mac too, where the pixel test passes.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5")


def test_board_picture_exists():
    """The file BOARD_PICTURE names is there, and Qt reads it as a picture.

    A file can be there and not be a picture: one of the deleted images was 139 bytes of
    text holding a web address. So the test loads it, as the tab does.
    """
    from PyQt5.QtGui import QImage  # noqa: PLC0415
    from ui.cages_visualization_tab import BOARD_PICTURE  # noqa: PLC0415

    assert os.path.isfile(BOARD_PICTURE), f"the Cages tab loads {BOARD_PICTURE}"
    # A Mac's disk ignores case and the Pi's does not, so the name is checked as spelled
    folder, name = os.path.split(BOARD_PICTURE)
    assert name in os.listdir(folder), f"the Cages tab loads {name!r}, as spelled, from {folder}"
    picture = QImage(BOARD_PICTURE)
    assert not picture.isNull(), f"Qt cannot read {BOARD_PICTURE} as a picture"
