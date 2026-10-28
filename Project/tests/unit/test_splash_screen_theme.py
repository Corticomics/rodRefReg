"""The splash screen takes its colours from the theme (v2.1.0).

It painted a fixed teal gradient (#0D9488 to #0F766E) under white text (3.74:1 where it
starts), a status line at 80% white (2.96:1) and an error in #FCA5A5 (1.97:1). Now the
gradient is accent.fill to accent.fill.hover, read as it paints, and the stylesheet gives
the title, the status and an error text.on-accent, and the bar a text.on-accent chunk on
an accent.fill.pressed groove (QLabel#SplashTitle, #SplashStatus, QProgressBar#SplashProgress).
main.py applies the saved theme (dark by default) before it shows the splash; both
themes are checked. Rendered offscreen; pixels and palettes are compared with the tokens.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

THEMES = ("light", "dark")

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
def tokens():
    from ui.style.qt_palette import tokens as table  # noqa: PLC0415

    return table


@pytest.fixture
def style(qapp):
    """A StyleManager on the app, as main.py makes one, and a list for the test's windows.

    The app's palette, stylesheet, font and style_manager property come back afterwards.
    """
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from ui.style.theme import StyleManager  # noqa: PLC0415

    old = (QPalette(qapp.palette()), qapp.styleSheet(), qapp.font())
    manager = StyleManager(qapp)
    qapp.setProperty("style_manager", manager)
    windows = []
    yield manager, windows
    for window in windows:
        window.close()
        window.deleteLater()
    qapp.setProperty("style_manager", None)
    manager.deleteLater()
    qapp.setStyleSheet(old[1])
    qapp.setPalette(old[0])
    qapp.setFont(old[2])
    qapp.processEvents()


def _near(found, expected, tolerance=3):
    """Two colours within `tolerance` per channel (a gradient's end, a step or two in)."""
    from PyQt5.QtGui import QColor  # noqa: PLC0415

    want = QColor(expected)
    return all(abs(a - b) <= tolerance for a, b in zip(found.getRgb()[:3], want.getRgb()[:3]))


@pytest.mark.parametrize("theme", THEMES)
def test_the_splash_screen_takes_the_themes_colours(qapp, tokens, style, theme, monkeypatch):
    import ui.splash_screen as module  # noqa: PLC0415
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    # The error schedules a hand-over two seconds later: not in a test
    monkeypatch.setattr(module.QTimer, "singleShot", staticmethod(lambda *a, **k: None))
    manager, windows = style
    manager.apply(theme)
    splash = module.SplashScreen()
    splash.show()
    splash._on_progress(45, "Initializing relay system...")
    qapp.processEvents()
    windows.append(splash)

    def colour(role):
        return tokens.value(role, theme)

    def pixel(widget, x, y):
        return image.pixelColor(widget.mapTo(splash, QPoint(x, y)))

    image = splash.grab().toImage()
    width, height = splash.width(), splash.height()
    assert _near(image.pixelColor(8, 8), colour("accent.fill"))
    assert _near(image.pixelColor(width - 9, height - 9), colour("accent.fill.hover"))

    for label in (splash.title_label, splash.status_label):
        assert label.palette().color(QPalette.WindowText).name().upper() == colour(
            "text.on-accent"
        ), label.text()
    bar = splash.progress_bar
    assert bar.height() == 8  # no outline: its own rule keeps the app's 8px
    middle = bar.height() // 2
    assert pixel(bar, 6, middle).name().upper() == colour("text.on-accent")  # the 45 %
    assert pixel(bar, bar.width() - 6, middle).name().upper() == colour("accent.fill.pressed")

    splash._on_error("probe")
    qapp.processEvents()
    assert splash.status_label.text() == "Error during startup"
    assert splash.status_label.palette().color(QPalette.WindowText).name().upper() == colour(
        "text.on-accent"
    )

    shadow = splash.graphicsEffect().color()
    assert (shadow.name(), shadow.alpha()) == ("#000000", 100)  # the palette's Shadow
