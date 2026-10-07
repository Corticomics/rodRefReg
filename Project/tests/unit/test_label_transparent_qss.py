"""Labels are transparent by default in both themes (QA: grey label boxes).

QLabels inherit the grey app background, so on white Cards (login form, profile
"Welcome" card) the field labels painted grey boxes. A base
`QLabel { background: transparent; }` makes them blend into their surface.
Guard the rule stays in both themes. Pure file read — no Qt.
"""

from __future__ import annotations

import re
from pathlib import Path

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"


def test_both_themes_make_labels_transparent():
    pattern = re.compile(r"QLabel\s*\{[^}]*background:\s*transparent", re.DOTALL)
    for name in ("app-light.qss", "app-dark.qss"):
        text = (STYLE_DIR / name).read_text(encoding="utf-8")
        assert pattern.search(text), f"{name} missing transparent QLabel base rule"
