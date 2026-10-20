"""No new raw colours in the UI code: a colour comes from a theme token.

A colour written into Python (a hex string, rgb()/hsv()/hsl() in a string, QColor(200, 0, 0)
or another QColor of literals, Qt.white, `color: white` in an inline stylesheet) ignores
the theme: it is the same in light and
dark, and a new palette misses it. Colours live in Project/ui/style/tokens.py and reach a
widget through the stylesheet: give the widget an objectName or a dynamic property and
style it in app.qss.tmpl with a ${role} (a colour code paints itself is a qproperty-*, as
the Animals tab's red cell does), then run build_qss.py.

Today's UI code still holds raw colours, so this is a ratchet: each file must hold exactly
its count in BASELINE, and a file not listed none. A file that gains a colour fails. So
does one that loses colours, until its count is lowered (an entry at 0 is deleted), so
that the allowance it freed cannot be spent on a new colour later. Never raise a count.
Comments and docstrings are not counted. Counting walks the syntax tree, so it is the
same on every Python version.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

import pytest

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
EXEMPT = ("style/",)  # where the tokens and the stylesheets live


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


colour_names = _load("rrr_colour_names", Path(__file__).with_name("colour_names.py"))

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
# The colour functions of Qt's stylesheets: rgb(), rgba(), hsv(), hsva(), hsl(), hsla()
RGB = re.compile(r"\b(?:rgb|hsv|hsl)a?\s*\(", re.IGNORECASE)
QSS_COLOUR_VALUE = re.compile(
    r"(?<![\w-])(?:color|background|background-color|border(?:-top|-right|-bottom|-left)?"
    r"(?:-color)?|selection-color|selection-background-color|gridline-color"
    r"|alternate-background-color|outline(?:-color)?)\s*:([^;{}\"'<>]*)",
    re.IGNORECASE,
)
COLOUR_NAME = re.compile(r"\b(?:" + "|".join(colour_names.COLOUR_NAMES) + r")\b", re.IGNORECASE)
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


def _is_qcolor(node):
    return (isinstance(node, ast.Name) and node.id == "QColor") or (
        isinstance(node, ast.Attribute) and node.attr == "QColor"
    )


def _qcolor_constructor(func):
    """The name of the QColor constructor a call makes (QColor, QColor.fromRgb...), or None."""
    if _is_qcolor(func):
        return "QColor"
    if isinstance(func, ast.Attribute) and func.attr.startswith("from") and _is_qcolor(func.value):
        return f"QColor.{func.attr}"
    return None


def _number(node):
    """A literal number (200, 0.5, -1, 0xC80000) as text; None for anything else."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _number(node.operand)
        return None if operand is None else f"-{operand}"
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return repr(node.value)
    return None


def _literal_numbers(call):
    """A call's arguments as text when each is a literal number, else None.

    A starred tuple or list of literals counts as its items: QColor(*(200, 0, 0)).
    """
    args = []
    for arg in call.args:
        if isinstance(arg, ast.Starred) and isinstance(arg.value, (ast.Tuple, ast.List)):
            args += arg.value.elts
        else:
            args.append(arg)
    texts = [_number(arg) for arg in args]
    for keyword in call.keywords:
        number = _number(keyword.value)
        texts.append(None if keyword.arg is None or number is None else f"{keyword.arg}={number}")
    if not texts or None in texts:
        return None
    return ", ".join(texts)


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
            constructor = _qcolor_constructor(node.func)
            if constructor is None:
                continue
            args = node.args
            numbers = _literal_numbers(node)
            if numbers is not None:  # QColor(200, 0, 0), QColor(0xC80000), fromHsv(...)
                hits.append((node.lineno, f"{constructor}({numbers})"))
            elif len(args) == 1 and not node.keywords and isinstance(args[0], ast.Constant):
                name = args[0].value
                if isinstance(name, str) and not _in_string(name):  # hex counts as a string
                    hits.append((node.lineno, f"{constructor}({name!r})"))
        elif isinstance(node, ast.Attribute) and node.attr in QT_COLOURS and _is_qt(node.value):
            hits.append((node.lineno, f"Qt.{node.attr}"))
    return sorted(hits)


def _ui_files():
    for path in sorted(UI_DIR.rglob("*.py")):
        relative = path.relative_to(UI_DIR).as_posix()
        if not relative.startswith(EXEMPT):
            yield relative, path


def _counts():
    """{relative path: raw colours found} for every UI file, listed or not."""
    return {
        relative: raw_colours(path.read_text(encoding="utf-8")) for relative, path in _ui_files()
    }


def test_no_ui_file_gains_a_raw_colour():
    over = []
    for relative, hits in _counts().items():
        allowed = BASELINE.get(relative, 0)
        if len(hits) > allowed:
            listing = ", ".join(f"line {line}: {colour}" for line, colour in hits)
            over.append(f"Project/ui/{relative}: {len(hits)} found, {allowed} allowed ({listing})")
    assert not over, (
        "New raw colours in the UI code. Use a token instead: give the widget an objectName "
        "or a dynamic property and colour it in Project/ui/style/app.qss.tmpl with a ${role} "
        "from tokens.py (add the role if none fits), then run "
        "python3 Project/ui/style/build_qss.py.\n" + "\n".join(over)
    )


def test_a_file_that_loses_raw_colours_lowers_its_baseline():
    counts = _counts()
    under = []
    for relative, allowed in sorted(BASELINE.items()):
        if relative not in counts:
            continue  # a deleted file: test_the_baseline_lists_only_existing_files
        found = len(counts[relative])
        if found < allowed:
            change = f"lower it to {found}" if found else "delete the entry"
            under.append(f"BASELINE[{relative!r}] is {allowed}, {found} found: {change}")
    assert not under, (
        "Raw colours were removed. Lower the counts in BASELINE to match, so that the "
        "allowance freed cannot take a new colour later.\n" + "\n".join(under)
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
    o = QColor.fromRgb(200, 0, 0)
    p = QColor.fromHsvF(0.5, 1.0, -0.25)
    q = QColor(0xC80000)
    r = QColor(200, 0, 0, alpha=255)
    s = QColor(*(200, 0, 0))
    t = "QLabel { color: hsv(0, 255, 200); background: hsla(0, 100%, 50%, 0.5) }"
    u = "QLabel { color: darkred; background: lightgray; border: 1px solid teal }"
    v = QColor(name, alpha=255)
    w = QColor(*value)
    x = "Dark red stops a run; teal is the accent"
    y = QColor()
    return a, b, c, d, e, f, g, h, i, j, k, m, n, o, p, q, r, s, t, u, v, w, x, y
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
        "QColor.fromRgb(200, 0, 0)",
        "QColor.fromHsvF(0.5, 1.0, -0.25)",
        "QColor(13107200)",
        "QColor(200, 0, 0, alpha=255)",
        "QColor(200, 0, 0)",
        "hsla(",
        "hsv(",
        "darkred",
        "lightgray",
        "teal",
    ]


def test_the_colour_names_are_the_ones_qt_knows():
    qtgui = pytest.importorskip("PyQt5.QtGui")
    known = set(qtgui.QColor.colorNames()) - {"transparent"}
    assert sorted(colour_names.COLOUR_NAMES) == sorted(known)
