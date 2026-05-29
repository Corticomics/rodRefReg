from __future__ import annotations

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QPushButton


class PrimaryButton(QPushButton):
    """
    A QPushButton that exposes a 'primary' variant for QSS to style.
    """

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setProperty("variant", "primary")
        self.setMinimumHeight(32)

    def sizeHint(self) -> QSize:  # pragma: no cover
        base = super().sizeHint()
        return QSize(max(base.width(), 96), max(base.height(), 32))
