"""The stylesheet rules the palette depends on, read as text from the template and the
generated stylesheets. No Qt.

Since v2.1.0 the base colours come from a QPalette (qt_palette.py) and the stylesheet sets
surfaces, borders and the colours that differ. That only works if the stylesheet keeps out
of the palette's way and covers the places the palette cannot reach:

- no universal QWidget or `*` background or colour: it painted the page colour inside
  every card, and with the grey page that shows as grey boxes;
- no `color` on a rule that matches an input, and no [placeholderText] rule: Qt draws an
  input's placeholder in such a colour, at half its alpha from Qt 5.15.12 (under 4.5:1 for
  any colour) and as typed text up to 5.15.11 (the Pi's 5.15.8);
- no QTextEdit:read-only rule: it would outrank QTextBrowser#HelpContent and grey the
  Help pane;
- a scroll area's content widget and stacked pages are transparent (Qt fills a scroll
  area's content with the page colour), and so are the table header and its corner, which
  stand on a rule, not a band;
- item views alternate rows in bg.alt; a selected fill always carries its on-accent text,
  and a hovered selected row keeps the selection colours;
- a tab pane is the content layer (bg.pane) the selected tab joins, and unselected tabs lie
  flat on the page with a separator between two of them;
- never a box inside a box: sections, strips and rows under a rule, a 1px separator.
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
    """A `color` on a rule that matches an input becomes its placeholder's colour: at half
    alpha from Qt 5.15.12, as typed text on the Pi's 5.15.8 (test_theme_palette.py)."""
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
        "draws them in the input's text colour, at half alpha from Qt 5.15.12"
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


# ---- Focus ----------------------------------------------------------------------------

# Inputs the keyboard reaches: a rule that names one by its id outranks QLineEdit:focus and
# its kin, so when it takes the input's border away, focus changes nothing on screen unless
# the input's own :focus rule draws an edge again
FOCUSABLE_INPUTS = {
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
# Those that show no focus edge, and why
NO_FOCUS_EDGE = {
    # The Help page has no frame of its own (the content pane is its box). v2.0.0's showed
    # no change on focus either: its :focus rule kept the resting 1px stroke. Tab moves
    # through the page's links, and the browser selects each one it reaches.
    "QTextBrowser#HelpContent",
}


def _takes_the_border_away(decls):
    return decls.get("border", "").split()[:1] in (["none"], ["0"], ["0px"])


@pytest.mark.parametrize("theme", THEMES)
def test_an_input_without_a_border_still_shows_the_focus(theme):
    """An input whose own rule removes its border (the Terminal log, which its tab pane
    frames) draws the focus stroke in its own :focus rule (WCAG 2.4.7). F+'s first rule for
    the log covered its :focus state too: Tab reached the log, and nothing on screen
    changed."""
    merged = {}
    for selectors, decls in _template_rules(theme):
        for selector in selectors:
            merged.setdefault(selector, {}).update(decls)
    checked, missing = [], []
    for selector, decls in merged.items():
        subject = _subject(selector)
        if _type(subject) not in FOCUSABLE_INPUTS or "#" not in subject or "::" in subject:
            continue
        if ":" in subject or not _takes_the_border_away(decls):
            continue
        checked.append(selector)
        focus = merged.get(f"{selector}:focus", {})
        edge = f"{focus.get('border', '')} {focus.get('border-color', '')}"
        if "<focus.ring" not in edge and subject not in NO_FOCUS_EDGE:
            missing.append(selector)
    assert "QPlainTextEdit#TerminalLog" in checked
    assert not missing, (
        f"{missing} take the border away and draw no focus stroke when focused: give each a "
        ":focus rule with a ${focus.ring} border, or say in NO_FOCUS_EDGE why it shows none"
    )
    for subject in NO_FOCUS_EDGE:
        assert subject in checked, f"{subject} no longer takes its border away"


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
def test_the_header_and_its_corner_stand_on_a_rule(theme):
    """No band under the column titles (Fluent's TableHeader): the header, its sections
    and its corner are transparent over the table, over one 1px rule in the outline's
    colour, a step stronger than the row rules under it. Each row is ruled once: no grid
    as well, which drew a second rule under every row and slits between zebra cells.
    (Palette B's header was a bg.inset band, which this test pinned; v2.1.0's layers have
    no band, so the test pins the rule and the rows instead.)"""
    rules = _stylesheet_rules(theme)
    assert _find(rules, "QHeaderView")[0].get("background") == "transparent"
    rule = f"1px solid {tokens.value('border.subtle', theme)}"
    for selector in ("QHeaderView::section", "QTableCornerButton::section"):
        decls = _find(rules, selector)[0]
        assert decls.get("background") == "transparent", selector
        assert decls.get("border-bottom") == rule, selector
    divider = f"1px solid {tokens.value('border.divider', theme)}"
    rows = [d for names, d in rules if "QTableView::item" in names and "border-bottom" in d]
    assert rows and rows[0]["border-bottom"] == divider
    tables = [d for selectors, d in rules if "QTableView" in selectors and "background" in d]
    assert tables[0].get("qproperty-showGrid") == "false", "each row is ruled once, no grid"


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


# ---- Layers, tabs and division (v2.1.0, Fluent 2 / WinUI) ---------------------------------


def _decls(rules, selector):
    """The declarations of every rule naming `selector`, merged in order."""
    merged = {}
    for selectors, decls in rules:
        if selector in selectors:
            merged.update(decls)
    assert merged, f"no rule names {selector!r}"
    return merged


@pytest.mark.parametrize("theme", THEMES)
def test_tabs_open_onto_the_content_layer(theme):
    """A tab pane is the content layer (bg.pane) in one stroke, its corners at the container
    radius but the top-left one, which is square: the first tab sits on it, and the
    selected one meets the pane in one straight edge (WinUI's TabView; test_tab_pane_corner
    .py checks the pixels). The selected tab joins it in the same colour, stroked and
    marked by its 3px bar; unselected tabs are flat on the base layer with no outline, and
    the separator between two of them is the stroke's colour, inset top and bottom (WinUI
    TabView's TabSeparator)."""
    rules = _stylesheet_rules(theme)
    stroke = tokens.value("border.subtle", theme)
    pane = _decls(rules, "QTabWidget::pane")
    assert pane["background"] == tokens.value("bg.pane", theme)
    assert pane["border"] == f"1px solid {stroke}"
    assert pane["border-radius"] == "8px"
    assert pane["border-top-left-radius"] == "0"
    corners = list(pane)  # Qt applies them in order: the corner after the shorthand
    assert corners.index("border-top-left-radius") > corners.index("border-radius")
    tab = _find(rules, "QTabBar::tab")[0]
    assert tab["border"] == "1px solid transparent" and tab["background"] == tokens.value(
        "bg.rail", theme
    )
    selected = _find(rules, "QTabBar::tab:selected")[0]
    assert selected["background"] == tokens.value("bg.pane", theme)
    assert selected["border-color"] == stroke
    assert selected["border-top"] == f"3px solid {tokens.value('accent.indicator', theme)}"
    unselected = _find(rules, "QTabBar::tab:!selected")[0]
    separator = unselected["border-right-color"]
    assert separator.startswith("qlineargradient(") and stroke in separator
    assert "stop: 0.25 transparent" in separator and "stop: 0.7501 transparent" in separator
    # Beside the selected tab, after the last one and under the pointer: no separator
    for state in ("next-selected", "last", "hover"):
        decls = _decls(rules, f"QTabBar::tab:!selected:{state}")
        assert decls["border-right-color"] == "transparent", state


@pytest.mark.parametrize("theme", THEMES)
def test_what_lies_inside_a_panes_square_corner_is_square_too(theme):
    """What lies just inside a container's 1px stroke takes 7px, so its corners follow the
    container's, and under a tab pane's square top-left it is square: Help's sidebar, and
    the Terminal log's focus stroke, whose corner comes after its shorthand, as Qt applies
    them in order (test_tab_pane_corner.py checks the pixels)."""
    rules = _stylesheet_rules(theme)
    sidebar = _decls(rules, "QWidget#HelpSidebar")
    assert sidebar["border-top-left-radius"] == "0"
    assert sidebar["border-bottom-left-radius"] == "7px"
    focus = _decls(rules, "QPlainTextEdit#TerminalLog:focus")
    assert focus["border-radius"] == "7px"
    assert focus["border-top-left-radius"] == "0"
    corners = list(focus)
    assert corners.index("border-top-left-radius") > corners.index("border-radius")


@pytest.mark.parametrize("theme", THEMES)
def test_boxes_inside_boxes_are_sections_and_strips(theme):
    """Never a box inside a box: a group box in a group box or a card is a section (its
    title over a rule), a nested tab widget a strip over a rule, the tracker header and an
    animal's row a strip or a row over a rule, a table or a list in a box has no frame of
    its own. Every one of those rules is the divider's colour."""
    rules = _stylesheet_rules(theme)
    rule = f"1px solid {tokens.value('border.divider', theme)}"
    section = _decls(rules, "QGroupBox QGroupBox")
    assert section["background"] == "transparent" and section["border"] == "none"
    assert section["border-top"] == rule
    for selector in ("QFrame#Card QGroupBox", 'QFrame[card="true"] QGroupBox'):
        assert _decls(rules, selector)["border-top"] == rule, selector
    nested = _decls(rules, "QTabWidget QTabWidget::pane")
    assert nested["border"] == "none" and nested["border-top"] == rule
    for selector in ("QFrame#TrackerHeader", "QFrame#AnimalConfigRow"):
        strip = _decls(rules, selector)
        assert strip["border"] == "none" and strip["border-bottom"] == rule, selector
    for selector in ("QGroupBox QTableView", "QGroupBox QListWidget", "QFrame#Card QTableView"):
        assert _decls(rules, selector)["border"] == "none", selector


@pytest.mark.parametrize("theme", THEMES)
def test_dividers_are_one_pixel_of_the_divider(theme):
    """QFrame#Divider (ui.components.card.Divider, the rule under a card's header) and
    #WizardSeparator (an HLine, which Qt drew 3px tall in near-black WindowText) paint
    border.divider with no frame: with no border, Qt draws no line of its own. The
    separator's rule holds it to 1px; a Divider fixes its 1px in code."""
    rules = _stylesheet_rules(theme)
    for selector in ("QFrame#Divider", "QFrame#WizardSeparator"):
        decls = _decls(rules, selector)
        assert decls["background"] == tokens.value("border.divider", theme), selector
        assert decls["border"] == "none", selector
    separator = _decls(rules, "QFrame#WizardSeparator")
    assert separator["min-height"] == separator["max-height"] == "1px"
