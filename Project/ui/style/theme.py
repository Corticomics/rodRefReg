from __future__ import annotations

from pathlib import Path
from typing import Dict

from PyQt5.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QTextCharFormat
from PyQt5.QtWidgets import QApplication, QCalendarWidget

from .qt_palette import build_palette, tokens

THEMES = tokens.THEMES
# The theme without a saved one: dark (v2.1.0)
DEFAULT_THEME = tokens.DEFAULT_THEME

# The days a calendar marks as the weekend, in Qt's own red, which no stylesheet reaches
WEEKEND = (Qt.Saturday, Qt.Sunday)


def theme_or_default(theme) -> str:
    """`theme` when it is one of THEMES, else DEFAULT_THEME (a stored value RRR has no
    theme for, or none)."""
    return theme if theme in THEMES else DEFAULT_THEME


def other_theme(theme) -> str:
    """The theme Settings > General's theme button switches to from `theme`."""
    return "light" if theme_or_default(theme) == "dark" else "dark"


def style_manager():
    """The application's StyleManager, or None before there is one.

    main.py keeps it as the application's style_manager property. Content painted from
    the theme connects to its theme_changed signal to repaint after every theme applied.
    """
    app = QApplication.instance()
    return app.property("style_manager") if app is not None else None


def current_theme() -> str:
    """The theme the application's StyleManager applied last; DEFAULT_THEME without one."""
    return theme_or_default(getattr(style_manager(), "theme", None))


def theme_colour(role: str) -> QColor:
    """The colour of a tokens.py role in the current theme, for code that paints itself.

    Call it when painting, never at import: the theme can change while the app runs.
    KeyError for an unknown role.
    """
    return QColor(tokens.value(role, current_theme()))


def tone_weekend(calendar, theme: str) -> None:
    """Write a calendar's weekend dates, and their weekday names, in `theme`'s text.weekend
    instead of Qt's red (#FF0000: 4.0:1 on a light card, 3.0:1 on a dark one)."""
    weekend = QTextCharFormat()
    weekend.setForeground(QBrush(QColor(tokens.value("text.weekend", theme))))
    for day in WEEKEND:
        calendar.setWeekdayTextFormat(day, weekend)


def restyle(widget) -> None:
    """Apply the stylesheet to `widget` again after a dynamic property its rules select on
    changed, e.g. setProperty("selected", True) for QFrame#ScheduleCard[selected="true"].

    It also sends the StyleChange event setStyleSheet would send, so a QFrame re-reads its
    frame width when the new rule changes the border's width.
    """
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    QApplication.sendEvent(widget, QEvent(QEvent.StyleChange))


class StyleManager(QObject):
    """
    Centralized styling for the application (light/dark).
    - Sets the theme's QPalette, then its stylesheet: one QSS for the whole app
      (Qt-recommended for maintainability and performance). Both come from tokens.py.
    - Sets a readable, widely available font for Raspberry Pi.
    - Emits theme_changed after every apply, so content the stylesheet cannot reach
      (the Help tab's HTML) can redraw itself.
    - Writes every calendar's weekend dates in the theme's colour (tone_weekend). A date
      field makes its calendar popup on the first click, and the popup takes the focus as it
      opens, before it paints: a calendar takes the colour then, and again after every
      apply. Focus changes are rare: unlike an application event filter, this adds nothing
      to the handling of every event.
    """

    theme_changed = pyqtSignal(str)

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app
        self._theme = DEFAULT_THEME
        self._base_dir = Path(__file__).resolve().parent
        app.focusChanged.connect(self._on_focus_changed)

    @property
    def theme(self) -> str:
        return self._theme

    def tokens(self) -> Dict[str, str]:
        """Every colour role of the current theme: {role: "#RRGGBB"}."""
        return {name: tokens.value(name, self._theme) for name in tokens.TOKENS}

    def colour(self, role: str) -> str:
        """The current theme's colour for a role of tokens.py (KeyError if unknown)."""
        return tokens.value(role, self._theme)

    def _on_focus_changed(self, _old, now) -> None:
        """The focus moved into a calendar (a date field's popup opening): it takes the
        theme's weekend colour before it paints."""
        owner = style_manager()
        if owner is not None and owner is not self:  # the application's StyleManager tones
            return
        widget = now
        while widget is not None and not isinstance(widget, QCalendarWidget):
            widget = widget.parentWidget()
        if widget is not None:
            tone_weekend(widget, self._theme)

    def apply(self, theme: str = DEFAULT_THEME) -> None:
        """Apply `theme`, or the default theme when it is not one of THEMES."""
        theme = theme_or_default(theme)
        self._theme = theme

        # Font: fast and present in most Raspberry Pi images
        self._app.setFont(QFont("DejaVu Sans", 10))

        # The palette first. Setting the stylesheet polishes every widget against the palette
        # it has then: in the other order, what no rule colours (a plain label, typed text,
        # a placeholder) keeps the previous theme's colours after a switch.
        # A failure is printed (the log and System Messages show it): without the palette
        # the stylesheet runs over Qt's own light one, unreadable under the dark theme.
        try:
            self._app.setPalette(build_palette(theme))
        except Exception as exc:
            print(f"[THEME ERROR] the {theme} palette was not applied: {exc}")

        qss_path = self._base_dir / f"app-{theme}.qss"
        try:
            with qss_path.open("r", encoding="utf-8") as f:
                self._app.setStyleSheet(f.read())
        except Exception as exc:
            print(f"[THEME ERROR] the {theme} stylesheet was not applied: {exc}")
            self._app.setStyleSheet("")

        for widget in QApplication.allWidgets():
            if isinstance(widget, QCalendarWidget):
                tone_weekend(widget, theme)

        self.theme_changed.emit(theme)
