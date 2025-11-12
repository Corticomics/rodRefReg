from __future__ import annotations

from pathlib import Path
from typing import Dict

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication


class StyleManager:
    """
    Centralized styling loader for the application (light/dark).
    - Loads a single QSS at app startup (Qt-recommended for maintainability and performance).
    - Sets a readable, widely available font for Raspberry Pi.
    """

    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._theme = "light"
        self._base_dir = Path(__file__).resolve().parent
        self._tokens: Dict[str, Dict[str, str]] = {
            # Palette inspired by the provided reference; tuned for accessibility contrast.
            "light": {
                "bg": "#F9F9F8",
                "surface": "#FFFFFF",
                "surfaceBorder": "#DBDBD9",
                "text": "#131313",
                "mutedText": "#919A9F",
                "primary": "#F9A51B",
                "primarySoft": "#FAC95A",
                "focus": "#131313",
            },
            "dark": {
                "bg": "#131313",
                "surface": "#1C1C1C",
                "surfaceBorder": "#2A2A2A",
                "text": "#F9F9F8",
                "mutedText": "#919A9F",
                "primary": "#F9A51B",
                "primarySoft": "#FAC95A",
                "focus": "#F9F9F8",
            },
        }

    @property
    def theme(self) -> str:
        return self._theme

    def tokens(self) -> Dict[str, str]:
        return self._tokens[self._theme]

    def apply(self, theme: str = "light") -> None:
        if theme not in self._tokens:
            theme = "light"
        self._theme = theme

        # Font: fast and present in most Raspberry Pi images
        self._app.setFont(QFont("DejaVu Sans", 10))

        qss_file = "app-light.qss" if theme == "light" else "app-dark.qss"
        qss_path = self._base_dir / qss_file
        try:
            with qss_path.open("r", encoding="utf-8") as f:
                self._app.setStyleSheet(f.read())
        except Exception:
            self._app.setStyleSheet("")


