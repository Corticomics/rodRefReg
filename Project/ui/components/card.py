from __future__ import annotations

from PyQt5.QtWidgets import QFrame

from ..style.elevation import ElevatedMixin

# QFrame#Card's border-radius in app.qss.tmpl: an elevated card's shadow tile is drawn for
# it (tests/unit/test_elevation.py compares the two)
CARD_RADIUS = 12


class Card(ElevatedMixin, QFrame):
    """
    Simple, reusable surface container styled via app QSS.

    elevated=True gives it the card shadow (ui.style.elevation). The card is then bigger
    than its box by the room the shadow takes (elevation.ROOM): a parent that lines the box
    up with other edges gives that room back in its own margins.
    """

    def __init__(self, parent=None, elevated: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("card", True)
        self.setContentsMargins(12, 12, 12, 12)
        if elevated:
            self.init_elevation("card", CARD_RADIUS)
