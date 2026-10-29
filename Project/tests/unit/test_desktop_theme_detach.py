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


def test_it_changes_the_process_environment_by_default(monkeypatch):
    from ui.style.theme import FUSION, detach_from_desktop_theme

    monkeypatch.setenv("QT_QPA_PLATFORMTHEME", "qt5ct")
    monkeypatch.setenv("QT_STYLE_OVERRIDE", "Windows")
    detach_from_desktop_theme()
    assert "QT_QPA_PLATFORMTHEME" not in os.environ
    assert os.environ["QT_STYLE_OVERRIDE"] == FUSION


CHILD = """
import sys
sys.path.insert(0, {project!r})
if {detach!r}:
    from ui.style.theme import detach_from_desktop_theme
    detach_from_desktop_theme()
from PyQt5.QtWidgets import QApplication
app = QApplication([])
print("STYLE=" + app.style().objectName().lower())
"""


def _first_style(detach):
    """The style of an application made in a fresh process, with a desktop that asks for
    qt5ct and the Windows style (built into every Qt)."""
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
    lines = [line for line in out.stdout.splitlines() if line.startswith("STYLE=")]
    assert out.returncode == 0 and lines, out.stderr[-2000:]
    return lines[-1].split("=", 1)[1]


@pytest.mark.parametrize(("detach", "expected"), [(True, "fusion"), (False, "windows")])
def test_an_application_made_after_it_draws_in_fusion_whatever_the_desktop_asks(detach, expected):
    assert _first_style(detach) == expected


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
