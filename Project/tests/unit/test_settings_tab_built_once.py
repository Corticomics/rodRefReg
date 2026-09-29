"""The Settings tab is built once, by the main window.

main.setup() (and the splash path) used to build a second SettingsTab with
the same arguments and assign it to gui.settings_tab after the window had
already added its own to the tab bar. Everything routed through
gui.settings_tab then reached an invisible, unparented copy: the
calibration-table refresh after a hat-count change, the mode-button
refresh on login/logout, and the window's own `current is
self.settings_tab` check. Both copies shared one settings dict and each
subscribed to the hardware lock and built its own priming panel.

main.setup() cannot run headless (it blocks on a dialog), so this pins the
bug statically: main.py must not construct a SettingsTab at all.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def test_main_never_constructs_a_settings_tab():
    tree = ast.parse((PROJECT / "main.py").read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SettingsTab"
    ]
    assert calls == [], f"main.py builds SettingsTab at line(s) {[c.lineno for c in calls]}"
