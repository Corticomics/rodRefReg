"""The stylesheet rules the palette depends on, read as text from the template and the
generated stylesheets. No Qt.

Since v2.1.0 the base colours come from a QPalette (qt_palette.py) and the stylesheet sets
surfaces, borders and the colours that differ. That only works if the stylesheet keeps out
of the palette's way and covers the places the palette cannot reach:

- no universal QWidget or `*` background or colour: it painted the page colour inside
  every card, and with the grey page that shows as grey boxes;
- no `color` on a rule that matches an input, and no [placeholderText] rule: Qt draws an
  input's placeholder at half the alpha of such a colour, under 4.5:1 for any colour;
- no QTextEdit:read-only rule: it would outrank QTextBrowser#HelpContent and grey the
  Help pane;
- a scroll area's content widget and stacked pages are transparent (Qt fills a scroll
  area's content with the page colour), and so are the header band and its corner;
- item views alternate rows in bg.alt; a selected fill always carries its on-accent text,
  and a hovered selected row keeps the selection colours.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_qss = _load("rrr_build_qss_structure", STYLE_DIR / "build_qss.py")
tokens = _load("rrr_tokens_structure", STYLE_DIR / "tokens.py")

PLACEHOLDER = re.compile(r"\$\{([^}]*)\}")
COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
COMBINATOR = re.compile(r"\s*>\s*|\s+")

# An input, or a class an input inherits, so a rule on it reaches inputs
INPUT_TYPES = {
    "QWidget",
    "QFrame",
    "QAbstractScrollArea",
    "QAbstractSpinBox",
    "QLineEdit",
    "QTextEdit",
    "QPlainTextEdit",
    "QTextBrowser",
    "QSpinBox",
    "QDoubleSpinBox",
    "QDateTimeEdit",
    "QDateEdit",
    "QTimeEdit",
    "QComboBox",
}


def _rules(text):
    """[(selectors, {property: value})] in order, comments removed, whitespace collapsed."""
    rules = []
    for selector_text, body in re.findall(r"([^{}]+)\{([^{}]*)\}", COMMENT.sub("", text)):
        declarations = {}
        for declaration in body.split(";"):
            prop, colon, value = declaration.partition(":")
            if colon:
                declarations[prop.strip()] = " ".join(value.split())
        selectors = [" ".join(s.split()) for s in selector_text.split(",")]
        rules.append((selectors, declarations))
    return rules


def _template_rules(theme):
    """The template's rules for `theme`, with each colour left as its role: <bg.page>."""
    lines = build_qss.theme_lines(build_qss.TEMPLATE.read_text(encoding="utf-8"), theme)
    text = "\n".join(line for _, line in lines)
    return _rules(PLACEHOLDER.sub(r"<\1>", text))


def _stylesheet_rules(theme):
    return _rules(build_qss.OUTPUTS[theme].read_text(encoding="utf-8"))


def _subject(selector):
    """The last compound of a selector: the part that names the styled widget."""
    return [part for part in COMBINATOR.split(selector) if part][-1]


def _type(compound):
    """A compound's type selector, or None when it has none (it then matches any type)."""
    match = re.match(r"[A-Za-z_]\w*|\*", compound)
    return match.group(0) if match else None


def _reaches_an_enabled_input(selector):
    subject = _subject(selector)
    if "::" in subject or ":disabled" in subject:
        return False  # a sub-control, or only a disabled widget
    kind = _type(subject)
    return kind is None or kind == "*" or kind in INPUT_TYPES


def _find(rules, selector):
    found = [decls for selectors, decls in rules if selectors == [selector]]
    assert found, f"no rule for {selector!r}"
    return found


THEMES = build_qss.THEMES


# ---- What the reading helpers see ----------------------------------------------------


def test_the_helpers_read_selectors_as_qt_does():
    assert _subject("QScrollArea > QWidget > QWidget") == "QWidget"
    assert _subject("QComboBox QAbstractItemView::item:selected") == (
        "QAbstractItemView::item:selected"
    )
    assert _type('QWidget#DropArea[state="idle"]') == "QWidget"
    assert _type("#CageNameEdit") is None and _type("*") == "*"
    assert _reaches_an_enabled_input("QLineEdit#CageNameEdit")
    assert _reaches_an_enabled_input("QGroupBox QLineEdit")
    assert _reaches_an_enabled_input("#Anything")
    assert not _reaches_an_enabled_input("QLineEdit:disabled")
    assert not _reaches_an_enabled_input("QComboBox QAbstractItemView::item")
    assert not _reaches_an_enabled_input("QGroupBox QLabel")
    rules = _rules("/* a, b { color: red } */ a, b > c { color : x ; border: 1px  solid y }")
    assert rules == [(["a", "b > c"], {"color": "x", "border": "1px solid y"})]


# ---- The palette's way kept clear ----------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_no_universal_background_or_colour(theme):
    for selectors, decls in _stylesheet_rules(theme):
        for selector in selectors:
            if selector in ("*", "QWidget"):
                painted = {"background", "background-color", "color"} & set(decls)
                assert not painted, (
                    f"{selector} sets {sorted(painted)}: base colours come from the QPalette, "
                    "and a universal background paints the page inside every card"
                )


@pytest.mark.parametrize("theme", THEMES)
def test_no_colour_on_an_input(theme):
    """A `color` on a rule that matches an input halves its placeholder's alpha."""
    offenders = [
        selector
        for selectors, decls in _stylesheet_rules(theme)
        if "color" in decls
        for selector in selectors
        if _reaches_an_enabled_input(selector)
    ]
    assert not offenders, (
        f"rules that colour an input: {offenders}. Inputs take their text and placeholder "
        "colours from the QPalette (qt_palette.py)."
    )


@pytest.mark.parametrize("theme", THEMES)
def test_no_placeholder_rule(theme):
    text = build_qss.OUTPUTS[theme].read_text(encoding="utf-8")
    assert "placeholderText" not in COMMENT.sub("", text), (
        "placeholders are the palette's PlaceholderText (text.muted): a stylesheet rule "
        "can only draw them at half alpha"
    )


@pytest.mark.parametrize("theme", THEMES)
def test_no_read_only_rule_on_text_edits(theme):
    for selectors, _ in _stylesheet_rules(theme):
        for selector in selectors:
            subject = _subject(selector)
            if ":read-only" in subject:
                assert _type(subject) not in INPUT_TYPES | {None, "*"}, (
                    f"{selector}: a :read-only rule on a text edit outranks "
                    "QTextBrowser#HelpContent and greys the Help pane; style a read-only "
                    "view by its objectName (#WizardLog)"
                )


# ---- What the palette cannot reach -----------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_scroll_content_and_stacked_pages_are_transparent(theme):
    rules = _stylesheet_rules(theme)
    transparent = [
        selectors for selectors, decls in rules if decls.get("background") == "transparent"
    ]
    for selector in ("QScrollArea", "QScrollArea > QWidget > QWidget", "QStackedWidget"):
        assert any(selector in selectors for selectors in transparent), selector


@pytest.mark.parametrize("theme", THEMES)
def test_the_header_band_and_its_corner_are_styled(theme):
    rules = _stylesheet_rules(theme)
    assert _find(rules, "QHeaderView")[0].get("background") == "transparent"
    section = _find(rules, "QHeaderView::section")[0]
    corner = _find(rules, "QTableCornerButton::section")[0]
    assert corner.get("background") == section.get("background") == tokens.value("bg.inset", theme)


@pytest.mark.parametrize("theme", THEMES)
def test_item_views_alternate_rows_in_bg_alt(theme):
    rules = _stylesheet_rules(theme)
    for selector in ("QTableView", "QListWidget"):
        decls = [d for selectors, d in rules if selector in selectors and "background" in d]
        assert decls, selector
        assert decls[0].get("alternate-background-color") == tokens.value("bg.alt", theme)


# ---- Selection ---------------------------------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_a_selected_fill_carries_on_accent_text(theme):
    for selectors, decls in _template_rules(theme):
        fill = decls.get("background") or decls.get("background-color")
        if fill == "<bg.selected>":
            assert decls.get("color") == "<text.on-accent>", selectors
        if decls.get("selection-background-color") == "<bg.selected>":
            assert decls.get("selection-color") == "<text.on-accent>", selectors


@pytest.mark.parametrize("theme", THEMES)
def test_a_hovered_selected_item_keeps_the_selection(theme):
    """:hover and :selected have the same specificity: the later rule wins."""
    rules = _template_rules(theme)

    def position(state):
        return [
            index
            for index, (selectors, _) in enumerate(rules)
            for selector in selectors
            if selector.endswith(f"::item:{state}") and "QComboBox" not in selector
        ]

    hovers, selections = position("hover"), position("selected")
    assert hovers and selections
    for view in ("QTableView", "QTableWidget", "QListWidget", "QTreeWidget#HelpTree"):
        hover = [i for i in hovers if any(s.startswith(view + "::") for s in rules[i][0])]
        selected = [i for i in selections if any(s.startswith(view + "::") for s in rules[i][0])]
        assert hover and selected, view
        assert max(hover) < min(selected), f"{view}: ::item:hover must come before :selected"


@pytest.mark.parametrize("theme", THEMES)
def test_disabled_menu_items_stay_grey(theme):
    rules = _template_rules(theme)
    if any("color" in d for d in _find(rules, "QMenu::item")):
        assert _find(rules, "QMenu::item:disabled")[0].get("color") == "<text.disabled>"
