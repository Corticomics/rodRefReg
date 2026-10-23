from __future__ import annotations

from PyQt5.QtWidgets import QFrame, QLabel

from ..style.elevation import ElevatedMixin

# QFrame#Card's border-radius in app.qss.tmpl: an elevated card's shadow tile is drawn for
# it (tests/unit/test_elevation.py compares the two)
CARD_RADIUS = 12


class Card(ElevatedMixin, QFrame):
    """
    Simple, reusable surface container styled via app QSS.

    elevated=True gives it the card shadow (ui.style.elevation): the primary cards that sit
    on a pane or on the page (Profile, the Cages board, Controls, Schedule Queue). The card
    is then bigger than its box by the room the shadow takes (elevation.ROOM): a parent that
    lines the box up with other edges gives that room back in its own margins.
    """

    def __init__(self, parent=None, elevated: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("card", True)
        self.setContentsMargins(12, 12, 12, 12)
        if elevated:
            self.init_elevation("card", CARD_RADIUS)


class CardHeader(QLabel):
    """A card's title, inside the card at its top (QLabel#CardHeader), with a Divider under
    it: Fluent's card header, where a QGroupBox put its title outside the box."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("CardHeader")


class Divider(QFrame):
    """A 1px rule in border.divider (QFrame#Divider), where two parts of a card meet with no
    title or strip of their own (Qt Creator's createRule; Fluent's Divider). Never stack it
    above a section title, a tab strip or a table header: those bring their own rule."""

    def __init__(self, parent=None, vertical: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFrameShape(QFrame.NoFrame)
        if vertical:
            self.setFixedWidth(1)
        else:
            self.setFixedHeight(1)
