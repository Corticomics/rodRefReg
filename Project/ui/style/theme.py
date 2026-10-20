from __future__ import annotations

from pathlib import Path
from typing import Dict

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

from .qt_palette import build_palette, tokens

THEMES = tokens.THEMES


class StyleManager(QObject):
    """
    Centralized styling for the application (light/dark).
    - Sets the theme's QPalette, then its stylesheet: one QSS for the whole app
      (Qt-recommended for maintainability and performance). Both come from tokens.py.
    - Sets a readable, widely available font for Raspberry Pi.
    - Emits theme_changed after every apply, so content the stylesheet cannot reach
      (the Help tab's HTML) can redraw itself.
    """

    theme_changed = pyqtSignal(str)

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app
        self._theme = "light"
        self._base_dir = Path(__file__).resolve().parent

    @property
    def theme(self) -> str:
        return self._theme

    def tokens(self) -> Dict[str, str]:
        """Every colour role of the current theme: {role: "#RRGGBB"}."""
        return {name: tokens.value(name, self._theme) for name in tokens.TOKENS}

    def colour(self, role: str) -> str:
        """The current theme's colour for a role of tokens.py (KeyError if unknown)."""
        return tokens.value(role, self._theme)

    def apply(self, theme: str = "light") -> None:
        if theme not in THEMES:
            theme = "light"
        self._theme = theme

        # Font: fast and present in most Raspberry Pi images
        self._app.setFont(QFont("DejaVu Sans", 10))

        # The palette first: the stylesheet is then polished against it.
        try:
            self._app.setPalette(build_palette(theme))
        except Exception:
            pass

        qss_path = self._base_dir / f"app-{theme}.qss"
        try:
            with qss_path.open("r", encoding="utf-8") as f:
                self._app.setStyleSheet(f.read())
        except Exception:
            self._app.setStyleSheet("")

        self.theme_changed.emit(theme)
