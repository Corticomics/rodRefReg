from __future__ import annotations

from PyQt5.QtWidgets import QFrame


class Card(QFrame):
    """
    Simple, reusable surface container styled via app QSS.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("card", True)
        self.setContentsMargins(12, 12, 12, 12)
