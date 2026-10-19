"""No new raw colours in the UI code: a colour comes from a theme token.

A colour written into Python (a hex string, rgb()/rgba(), QColor(200, 0, 0), Qt.white,
`color: white` in an inline stylesheet) ignores the theme: it is the same in light and
dark, and a new palette misses it. Colours live in Project/ui/style/tokens.py and reach a
widget through the stylesheet: give the widget an objectName or a dynamic property and
style it in app.qss.tmpl with a ${role} (a colour code paints itself is a qproperty-*, as
the Animals tab's red cell does), then run build_qss.py.

Today's UI code still holds raw colours, so this is a ratchet: each file may keep at most
the count it had when the test was written (BASELINE), and a file not listed may have
none. Lower a count when you remove colours; never raise one. Comments and docstrings are
not counted. Counting walks the syntax tree, so it is the same on every Python version.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
EXEMPT = ("style/",)  # where the tokens and the stylesheets live

# Raw colours per file (path relative to Project/ui) on 2026-10-19, v2.0.0.
BASELINE = {
    "CalibrationWizard.py": 1,
    "HelpTab.py": 2,
    "ScheduleProgressTracker.py": 28,
    "SettingsTab.py": 18,
    "SuggestSettingsTab.py": 2,
    "animals_tab.py": 2,
    "available_animals_list.py": 5,
    "cages_visualization_tab.py": 5,
    "components/wizard.py": 3,
    "relay_unit_widget.py": 1,
    "schedule_wizard.py": 16,
    "schedules_hub.py": 60,
    "splash_screen.py": 8,
    "staggered_delivery_slot.py": 4,
}

HEX = re.compile(r"(?<![\w#&])#(?:[0-9A-Fa-f]{8}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?!\w)")
# "#170" in "PR #170" is a number: three digits count only where a colour goes.
COLOUR_POSITION = re.compile(r"(?:^|[:(,]|\b(?:solid|dashed|dotted|double))\s*$")
RGB = re.compile(r"\brgba?\s*\(", re.IGNORECASE)
QSS_COLOUR_VALUE = re.compile(
    r"(?<![\w-])(?:color|background|background-color|border(?:-top|-right|-bottom|-left)?"
    r"(?:-color)?|selection-color|selection-background-color|gridline-color"
    r"|alternate-background-color|outline(?:-color)?)\s*:([^;{}\"'<>]*)",
    re.IGNORECASE,
)
COLOUR_NAME = re.compile(
    r"\b(?:white|black|red|green|blue|gray|grey|yellow|orange|cyan|magenta|navy|silver"
    r"|maroon|teal|purple|lime|olive|aqua|fuchsia|pink|brown|gold)\b",
    re.IGNORECASE,
)
# Qt's global colours, but Qt.transparent, which is not a colour
QT_COLOURS = frozenset(
    "white black red darkRed green darkGreen blue darkBlue cyan darkCyan magenta "
    "darkMagenta yellow darkYellow gray darkGray lightGray color0 color1".split()
)


def _docstrings(tree):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                found.add(id(first.value))
    return found


def _in_string(text):
    """Raw colours in the text of one string literal."""
    hits = []
    for match in HEX.finditer(text):
        digits = match.group(0)[1:]
        if len(digits) == 3 and digits.isdigit():
            if not COLOUR_POSITION.search(text[: match.start()]):
                continue
        hits.append(match.group(0))
    hits += [match.group(0) for match in RGB.finditer(text)]
    for value in QSS_COLOUR_VALUE.findall(text):
        hits += COLOUR_NAME.findall(value)
    return hits


def _is_qt(node):
    return (isinstance(node, ast.Name) and node.id == "Qt") or (
        isinstance(node, ast.Attribute) and node.attr in ("Qt", "GlobalColor")
    )


def raw_colours(source):
    """[(line, colour)] for every raw colour in a Python source."""
    tree = ast.parse(source)
    docstrings = _docstrings(tree)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                hits += [(node.lineno, colour) for colour in _in_string(node.value)]
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            args = node.args
            if name != "QColor" or node.keywords:
                continue
            literal = [isinstance(a, ast.Constant) for a in args]
            if len(args) in (3, 4) and all(literal) and all(type(a.value) is int for a in args):
                numbers = ", ".join(str(a.value) for a in args)
                hits.append((node.lineno, f"QColor({numbers})"))
            elif len(args) == 1 and literal[0] and isinstance(args[0].value, str):
                if not _in_string(args[0].value):  # a hex string is counted as a string
                    hits.append((node.lineno, f"QColor({args[0].value!r})"))
        elif isinstance(node, ast.Attribute) and node.attr in QT_COLOURS and _is_qt(node.value):
            hits.append((node.lineno, f"Qt.{node.attr}"))
    return sorted(hits)


def _ui_files():
    for path in sorted(UI_DIR.rglob("*.py")):
        relative = path.relative_to(UI_DIR).as_posix()
        if not relative.startswith(EXEMPT):
            yield relative, path


def test_no_ui_file_gains_a_raw_colour():
    over = []
    for relative, path in _ui_files():
        hits = raw_colours(path.read_text(encoding="utf-8"))
        allowed = BASELINE.get(relative, 0)
        if len(hits) > allowed:
            listing = ", ".join(f"line {line}: {colour}" for line, colour in hits)
            over.append(
                f"Project/ui/{relative}: {len(hits)} raw colours, {allowed} allowed ({listing})"
            )
    assert not over, (
        "New raw colours in the UI code. Use a token instead: give the widget an objectName "
        "or a dynamic property and colour it in Project/ui/style/app.qss.tmpl with a ${role} "
        "from tokens.py (add the role if none fits), then run "
        "python3 Project/ui/style/build_qss.py.\n" + "\n".join(over)
    )


def test_the_baseline_lists_only_existing_files():
    gone = [relative for relative in BASELINE if not (UI_DIR / relative).is_file()]
    assert not gone, f"remove these from BASELINE, the files are gone: {gone}"
    assert all(count > 0 for count in BASELINE.values())


def test_what_counts_as_a_raw_colour():
    source = '''
"""A docstring may name #FFFFFF."""
# so may a comment: #FFFFFF, Qt.white
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


def paint(name, value):
    """Neither is counted here: #000000."""
    a = "#FFF"
    b = "color: #1A2B3C; border: 1px solid #80FFFFFF"
    c = f"background: {value}; color: #abcdef"
    d = "background: rgba(0, 0, 0, 0.5)"
    e = QColor(200, 0, 0)
    f = QColor(0, 0, 0, 100)
    g = QColor("#DC2626")
    h = QColor("red")
    i = Qt.white
    j = "QLabel { color: white; border: 2px solid #666 }"
    k = Qt.transparent
    m = "Cage #12, PR #170, QLabel#Title, &#123;, Relay #100"
    n = QColor(name)
    return a, b, c, d, e, f, g, h, i, j, k, m, n
'''
    assert [colour for _, colour in raw_colours(source)] == [
        "#FFF",
        "#1A2B3C",
        "#80FFFFFF",
        "#abcdef",
        "rgba(",
        "QColor(200, 0, 0)",
        "QColor(0, 0, 0, 100)",
        "#DC2626",
        "QColor('red')",
        "Qt.white",
        "#666",
        "white",
    ]
