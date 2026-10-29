"""RRR keeps the desktop's Qt platform theme out of its own window (theme.detach_from_desktop_theme).

Raspberry Pi OS's desktop sets QT_QPA_PLATFORMTHEME=qt5ct, and its qt5ct names the gtk2
style. In the 2.1.0 dry run on the home Pi (2026-10-28) one of the two RRRs restart_app
relaunched on the desktop came out of a dark start with a light page around dark panes, and
RRR started from the desktop crashed as it quit in 9 of 16 starts: qt5ct made a gtk2-based
style the application's first style, which starts GTK, and put the desktop's font over
RRR's a second after start-up. Started without QT_QPA_PLATFORMTHEME and with Fusion as the
first style, 14 starts of 14 stayed dark, kept RRR's font and quit cleanly.

The application here is the test's, so each start that matters runs in a subprocess, with a
desktop that asks for another style: the start must come out in Fusion all the same, and,
without the detach, in the desktop's style, which shows the check can fail.
"""

import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]


def test_the_platform_theme_goes_and_fusion_becomes_the_first_style():
    from ui.style.theme import FUSION, detach_from_desktop_theme

    env = {
        "QT_QPA_PLATFORMTHEME": "qt5ct",
        "QT_STYLE_OVERRIDE": "gtk2",
        "HOME": "/home/pi",
        "DISPLAY": ":0",
    }
    detach_from_desktop_theme(env)
    assert env == {"QT_STYLE_OVERRIDE": FUSION, "HOME": "/home/pi", "DISPLAY": ":0"}

    bare = {"HOME": "/home/pi"}
    detach_from_desktop_theme(bare)  # a desktop without a platform theme: nothing to take out
    assert bare == {"QT_STYLE_OVERRIDE": FUSION, "HOME": "/home/pi"}


def test_it_changes_the_process_environment_and_qt_by_default(monkeypatch):
    from PyQt5.QtGui import QGuiApplication
    from ui.style.theme import FUSION, detach_from_desktop_theme

    monkeypatch.setenv("QT_QPA_PLATFORMTHEME", "qt5ct")
    monkeypatch.setenv("QT_STYLE_OVERRIDE", "Windows")
    aware = QGuiApplication.desktopSettingsAware()
    try:
        detach_from_desktop_theme()
        assert "QT_QPA_PLATFORMTHEME" not in os.environ
        assert os.environ["QT_STYLE_OVERRIDE"] == FUSION
        assert QGuiApplication.desktopSettingsAware() is False
    finally:
        QGuiApplication.setDesktopSettingsAware(aware)  # the session's other tests run as before


def test_a_test_mapping_leaves_qt_as_it_is():
    from PyQt5.QtGui import QGuiApplication
    from ui.style.theme import detach_from_desktop_theme

    aware = QGuiApplication.desktopSettingsAware()
    detach_from_desktop_theme({"QT_QPA_PLATFORMTHEME": "qt5ct"})
    assert QGuiApplication.desktopSettingsAware() is aware


CHILD = """
import sys
sys.path.insert(0, {project!r})
if {detach!r}:
    from ui.style.theme import detach_from_desktop_theme
    detach_from_desktop_theme()
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication
app = QApplication([])
print("STYLE=" + app.style().objectName().lower())
print("AWARE=" + str(QGuiApplication.desktopSettingsAware()))
"""


def _first_start(detach):
    """The style of an application made in a fresh process, and whether it takes the
    desktop's settings, with a desktop that asks for qt5ct and the Windows style (built
    into every Qt)."""
    env = dict(
        os.environ,
        QT_QPA_PLATFORM="offscreen",
        QT_QPA_PLATFORMTHEME="qt5ct",
        QT_STYLE_OVERRIDE="Windows",
    )
    out = subprocess.run(
        [sys.executable, "-c", CHILD.format(project=str(PROJECT), detach=detach)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    facts = dict(line.split("=", 1) for line in out.stdout.splitlines() if "=" in line)
    assert out.returncode == 0 and "STYLE" in facts, out.stderr[-2000:]
    return facts["STYLE"], facts.get("AWARE")


@pytest.mark.parametrize(
    ("detach", "expected"), [(True, ("fusion", "False")), (False, ("windows", "True"))]
)
def test_an_application_made_after_it_draws_in_fusion_whatever_the_desktop_asks(detach, expected):
    assert _first_start(detach) == expected


DIALOG = """
import sys
sys.path.insert(0, {project!r})
from PyQt5.QtWidgets import QApplication, QMessageBox, QProxyStyle, QStyle

class GenericThemeStyle(QProxyStyle):
    # Fusion as Qt's generic Unix theme leaves it: icons on a dialog's standard buttons
    def styleHint(self, hint, option=None, widget=None, data=None):
        if hint == QStyle.SH_DialogButtonBox_ButtonsHaveIcons:
            return 1
        return super().styleHint(hint, option, widget, data)

app = QApplication([])
app.setStyle(GenericThemeStyle("Fusion"))
if {sheet!r}:
    from pathlib import Path
    app.setStyleSheet((Path({project!r}) / "ui" / "style" / {sheet!r}).read_text())
box = QMessageBox(QMessageBox.Question, "Revert", "Revert to the previous version?", QMessageBox.Yes | QMessageBox.No)
box.show()
app.processEvents()
print("ICONS=" + ",".join(str(not b.icon().isNull()) for b in box.buttons()))
"""


def _button_icons(sheet):
    """Whether a message box's Yes and No buttons have icons, under a style that asks for
    them as Qt's generic Unix theme does, with RRR's stylesheet `sheet` (or none)."""
    out = subprocess.run(
        [sys.executable, "-c", DIALOG.format(project=str(PROJECT), sheet=sheet)],
        env=dict(os.environ, QT_QPA_PLATFORM="offscreen"),
        capture_output=True,
        text=True,
        timeout=60,
    )
    lines = [line for line in out.stdout.splitlines() if line.startswith("ICONS=")]
    assert out.returncode == 0 and lines, out.stderr[-2000:]
    return lines[-1].split("=", 1)[1]


@pytest.mark.parametrize(
    ("sheet", "expected"),
    [("app-dark.qss", "False,False"), ("app-light.qss", "False,False"), ("", "True,True")],
)
def test_a_dialogs_standard_buttons_have_no_icons_in_either_theme(sheet, expected):
    """Without the desktop's theme, the Pi's Qt takes its generic Unix theme, which asks for
    icons on Yes, No, OK, Save and Cancel; the stylesheet turns them off. The last case,
    without the stylesheet, shows the style here does ask for them."""
    assert _button_icons(sheet) == expected


def test_main_detaches_before_it_makes_the_application(monkeypatch):
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # main installs its own on import
    import main as module  # noqa: PLC0415

    source = inspect.getsource(module.main)
    detach, make = (
        source.find("detach_from_desktop_theme()"),
        source.find("SafeQApplication(sys.argv)"),
    )
    assert (
        0 <= detach < make
    ), "main() detaches from the desktop's theme before it makes the application"
