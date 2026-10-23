"""The theme's QPalette on screen: what the stylesheet does not paint follows the theme.

StyleManager.apply sets a QPalette built from tokens.py (qt_palette.py), then the theme's
stylesheet. Before v2.1.0 there was no palette: Qt kept its own light one under the dark
stylesheet, so dark tables alternated with near-white rows under light text, and the Help
pane, which asked the palette whether the theme was dark, always rendered light. A
universal QWidget rule also painted the page colour into every container, which the grey
page would show as boxes inside white cards. Rendered offscreen; pixels are compared with
the tokens.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"
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
    """A StyleManager on the app, as main.py makes one, and a list for the test's widgets.

    The app's palette, stylesheet, font and style_manager property come back afterwards.
    """
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from ui.style.theme import StyleManager  # noqa: PLC0415

    old = (QPalette(qapp.palette()), qapp.styleSheet(), qapp.font())
    manager = StyleManager(qapp)
    qapp.setProperty("style_manager", manager)
    widgets = []
    yield manager, widgets
    for widget in widgets:
        widget.close()
        widget.deleteLater()
    qapp.setProperty("style_manager", None)
    manager.deleteLater()
    qapp.setStyleSheet(old[1])
    qapp.setPalette(old[0])
    qapp.setFont(old[2])
    qapp.processEvents()


def _show(qapp, widgets, widget, width=420, height=320):
    widgets.append(widget)
    widget.resize(width, height)
    widget.show()
    qapp.processEvents()
    return widget


def _pixel(image, x, y):
    return image.pixelColor(x, y).name().upper()


# ---- The palette -----------------------------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_the_palette_takes_its_roles_from_the_tokens(qapp, tokens, theme):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from ui.style.qt_palette import build_palette  # noqa: PLC0415

    palette = build_palette(theme)
    for role_name, token in tokens.QPALETTE.items():
        role = getattr(QPalette, role_name)
        disabled = tokens.QPALETTE_DISABLED.get(role_name, token)
        for group, name in (
            (QPalette.Active, token),
            (QPalette.Inactive, token),
            (QPalette.Disabled, disabled),
        ):
            colour = palette.color(group, role)
            assert colour.name().upper() == tokens.value(name, theme), (role_name, group)
            assert colour.alpha() == 255, (role_name, group)


def test_apply_sets_the_palette_and_the_stylesheet_and_says_so(qapp, tokens, style):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415

    manager, _ = style
    seen = []
    manager.theme_changed.connect(seen.append)

    manager.apply("dark")
    assert manager.theme == "dark"
    window = qapp.palette().color(QPalette.Window).name().upper()
    assert window == tokens.value("bg.page", "dark")
    assert qapp.styleSheet() == (STYLE_DIR / "app-dark.qss").read_text(encoding="utf-8")
    assert manager.colour("bg.alt") == tokens.value("bg.alt", "dark")
    assert manager.tokens()["text.primary"] == tokens.value("text.primary", "dark")

    manager.apply("light")
    assert manager.theme == "light"
    assert qapp.styleSheet() == (STYLE_DIR / "app-light.qss").read_text(encoding="utf-8")

    # An unknown theme, or none, gives the default: dark from v2.1.0 (it was light)
    manager.apply("sepia")
    assert manager.theme == tokens.DEFAULT_THEME == "dark"
    assert qapp.styleSheet() == (STYLE_DIR / "app-dark.qss").read_text(encoding="utf-8")
    manager.apply("light")
    manager.apply()
    assert manager.theme == "dark"
    assert seen == ["dark", "light", "dark", "light", "dark"]


def test_apply_says_when_the_palette_or_the_stylesheet_fails(
    qapp, style, capsys, monkeypatch, tmp_path
):
    """Without the palette the dark stylesheet would run over Qt's own light palette, the
    unreadable state the palette exists to prevent: apply() prints why, and still applies
    the rest and announces the theme."""
    import ui.style.theme as theme_module  # noqa: PLC0415

    manager, _ = style
    seen = []
    manager.theme_changed.connect(seen.append)

    def broken(theme):
        raise KeyError("bg.page")

    monkeypatch.setattr(theme_module, "build_palette", broken)
    manager.apply("dark")
    out = capsys.readouterr().out
    assert "[THEME ERROR] the dark palette was not applied: 'bg.page'" in out
    assert qapp.styleSheet() == (STYLE_DIR / "app-dark.qss").read_text(encoding="utf-8")
    monkeypatch.undo()

    manager._base_dir = tmp_path  # no stylesheets there
    manager.apply("light")
    out = capsys.readouterr().out
    assert "[THEME ERROR] the light stylesheet was not applied:" in out
    assert qapp.styleSheet() == ""
    assert seen == ["dark", "light"]


@pytest.mark.parametrize("first", THEMES)
def test_a_theme_switch_reaches_what_only_the_palette_colours(qapp, tokens, style, first):
    """main.py applies light, builds the GUI, then applies the saved theme, and Settings
    switches the theme while the app runs. Setting the stylesheet polishes every widget
    against the palette it has then, so apply() sets the palette first: in the other order a
    plain label, typed text and a placeholder keep the previous theme's colours."""
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import QFrame, QLabel, QLineEdit, QVBoxLayout  # noqa: PLC0415

    manager, widgets = style
    manager.apply(first)
    card = QFrame()
    card.setObjectName("Card")
    label = QLabel("A plain label")  # no rule colours it
    edit = QLineEdit()
    edit.setPlaceholderText("Search animals...")
    layout = QVBoxLayout(card)
    layout.addWidget(label)
    layout.addWidget(edit)
    _show(qapp, widgets, card)

    other = "dark" if first == "light" else "light"
    for theme in (other, first):
        manager.apply(theme)
        qapp.processEvents()
        primary = tokens.value("text.primary", theme)
        assert label.palette().color(QPalette.WindowText).name().upper() == primary, theme
        assert edit.palette().color(QPalette.Text).name().upper() == primary, theme
        placeholder = edit.palette().color(QPalette.PlaceholderText)
        assert placeholder.name().upper() == tokens.value("text.muted", theme), theme
        assert placeholder.alpha() == 255, theme


# ---- Containers, tables, placeholders --------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_a_plain_container_in_a_card_shows_the_card(qapp, tokens, style, theme):
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtWidgets import (  # noqa: PLC0415
        QFrame,
        QLabel,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )

    manager, widgets = style
    manager.apply(theme)

    window = QWidget()
    card = QFrame()
    card.setObjectName("Card")
    plain = QWidget()  # a layout container, as the UI uses everywhere
    plain.setMinimumSize(200, 60)
    QVBoxLayout(plain).addWidget(QLabel("in a plain container"))
    scroll = QScrollArea()  # its content widget gets autoFillBackground
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidgetResizable(True)
    content = QWidget()
    content.setMinimumSize(200, 60)
    scroll.setWidget(content)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(16, 16, 16, 16)
    card_layout.addWidget(plain)
    card_layout.addWidget(scroll)
    QVBoxLayout(window).addWidget(card)
    _show(qapp, widgets, window)

    image = window.grab().toImage()

    def at(widget, x=4, y=4):
        point = widget.mapTo(window, QPoint(x, y))
        return _pixel(image, point.x(), point.y())

    assert _pixel(image, 2, 2) == tokens.value("bg.page", theme), "the window is the page"
    assert at(card, 40, 8) == tokens.value("bg.surface", theme)  # clear of the round corner
    assert at(plain) == tokens.value("bg.surface", theme), "a plain container shows the card"
    assert at(content) == tokens.value("bg.surface", theme), "so does a scroll area's content"


@pytest.mark.parametrize("theme", THEMES)
def test_zebra_rows_are_the_themes_alternate_colour(qapp, tokens, style, theme):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import (  # noqa: PLC0415
        QTableWidget,
        QTableWidgetItem,
        QTreeWidget,
        QTreeWidgetItem,
    )

    manager, widgets = style
    manager.apply(theme)
    surface, alternate = tokens.value("bg.surface", theme), tokens.value("bg.alt", theme)

    table = QTableWidget(4, 2)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setDefaultSectionSize(40)
    for row in range(4):
        for column in range(2):
            table.setItem(row, column, QTableWidgetItem(""))
    _show(qapp, widgets, table)
    assert table.palette().color(QPalette.AlternateBase).name().upper() == alternate
    image = table.viewport().grab().toImage()
    rows = [_pixel(image, 10, table.rowViewportPosition(row) + 8) for row in range(4)]
    assert rows == [surface, alternate, surface, alternate]

    # A view no stylesheet rule names alternates in the palette's AlternateBase
    tree = QTreeWidget()
    tree.setAlternatingRowColors(True)
    tree.setHeaderHidden(True)
    tree.addTopLevelItems([QTreeWidgetItem([""]) for _ in range(4)])
    _show(qapp, widgets, tree)
    first, second = (tree.visualItemRect(tree.topLevelItem(i)) for i in (0, 1))
    image = tree.viewport().grab().toImage()
    assert _pixel(image, first.right() - 4, second.center().y()) == alternate


@pytest.mark.parametrize("theme", THEMES)
def test_a_placeholder_keeps_its_full_colour(qapp, tokens, style, theme):
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import QFrame, QGroupBox, QLineEdit, QVBoxLayout  # noqa: PLC0415

    manager, widgets = style
    manager.apply(theme)

    card = QFrame()
    card.setObjectName("Card")
    group = QGroupBox("Filter")  # its stylesheet rule sets a colour
    edit = QLineEdit()
    edit.setPlaceholderText("Search animals...")
    QVBoxLayout(group).addWidget(edit)
    QVBoxLayout(card).addWidget(group)
    _show(qapp, widgets, card)

    placeholder = edit.palette().color(QPalette.PlaceholderText)
    assert placeholder.alpha() == 255, "a stylesheet colour reached the input"
    assert placeholder.name().upper() == tokens.value("text.muted", theme)
    assert edit.palette().color(QPalette.Text).name().upper() == tokens.value(
        "text.primary", theme
    )


def test_a_colour_on_an_input_takes_its_placeholder_colour_away(qapp, tokens, style):
    """Why no rule colours an input. A stylesheet `color` on an input sets the palette's
    PlaceholderText to that colour too, so the hint is no longer drawn in text.muted. What
    Qt draws instead depends on its version (qstylesheetstyle.cpp, configurePalette):
    - from 5.15.12, the colour at half its alpha: the hint falls under 4.5:1;
    - up to 5.15.11, the Pi's and CI's Debian 5.15.8 among them, the colour itself: the
      hint is drawn exactly as typed text is, so an empty field reads as filled in.
    Without the rule the hint is text.muted, drawn at full strength."""
    from PyQt5.QtCore import QT_VERSION, Qt  # noqa: PLC0415
    from PyQt5.QtGui import QPalette  # noqa: PLC0415
    from PyQt5.QtWidgets import QLineEdit  # noqa: PLC0415
    from ui.style import contrast  # noqa: PLC0415

    manager, widgets = style
    manager.apply("light")
    primary, muted = tokens.value("text.primary", "light"), tokens.value("text.muted", "light")
    field = tokens.value("bg.field", "light")

    def darkest_ink(edit, text):
        """The darkest pixel the words draw: their fully covered pixels' colour."""
        edit.setText(text)
        qapp.processEvents()
        image = edit.grab().toImage()
        inks = {
            image.pixelColor(x, y).name().upper()
            for x in range(4, image.width() - 4)
            for y in range(4, image.height() - 4)
        } - {field}
        return min(inks, key=lambda ink: contrast.relative_luminance(ink))

    def field_with(sheet):
        edit = QLineEdit()
        edit.setFocusPolicy(Qt.NoFocus)  # no focus ring and no text cursor in the picture
        edit.setPlaceholderText("Search animals...")
        edit.setStyleSheet(sheet)
        return _show(qapp, widgets, edit, 240, 40)

    plain = field_with("")
    assert darkest_ink(plain, "") == muted, "the hint, drawn in text.muted"

    edit = field_with(f"QLineEdit {{ color: {primary}; }}")
    placeholder = edit.palette().color(QPalette.PlaceholderText)
    assert placeholder.name().upper() == primary, "the rule's colour, not text.muted"
    hint, typed = darkest_ink(edit, ""), darkest_ink(edit, "Search animals...")
    assert typed == primary
    if QT_VERSION >= 0x050F0C:  # 5.15.12
        assert placeholder.alpha() == 128
        assert contrast.contrast_ratio(hint, field) < 4.5, hint
    else:
        assert placeholder.alpha() == 255
        assert hint == typed, "the hint is drawn as typed text"


# ---- Focus ------------------------------------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_focus_changes_a_controls_edge_by_3_to_1(qapp, tokens, style, theme):
    """Fluent's focus stroke on screen. A focused input, spin box, combo box, default or
    primary button draws its edge in its focus role, 2px of it, and the Schedules hub's
    search field its 1px edge: each at least 3:1 from the edge it had unfocused (F7, F8). A
    primary button's ring is black in both themes: in dark the white stroke changed its
    light teal edge by 1.86:1. The focus rules are v2.0.0's; only their colours changed.

    The Terminal log, which its tab pane frames, has no edge of its own: focus draws the
    2px stroke where the pane showed through (F3p), and the padding gives the 2px back, so
    its text does not move."""
    from PyQt5.QtCore import QPoint, Qt  # noqa: PLC0415
    from PyQt5.QtWidgets import (  # noqa: PLC0415
        QComboBox,
        QLineEdit,
        QPlainTextEdit,
        QPushButton,
        QSpinBox,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
    from ui.style import contrast  # noqa: PLC0415
    from ui.style.theme import restyle  # noqa: PLC0415

    manager, widgets = style
    manager.apply(theme)
    window = QWidget()
    layout = QVBoxLayout(window)
    sink = QLineEdit()  # holds the focus while a control is drawn unfocused
    layout.addWidget(sink)
    search = QLineEdit()
    search.setObjectName("SchedulesHubSearch")
    primary = QPushButton("Run")
    primary.setProperty("variant", "primary")
    combo = QComboBox()
    combo.addItems(["One", "Two"])
    # The Terminal, as gui.py builds it: a read-only log filling its tab's page
    log = QPlainTextEdit("System Messages")
    log.setObjectName("TerminalLog")
    log.setReadOnly(True)
    terminal = QTabWidget()
    page = QWidget()
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(0, 0, 0, 0)
    page_layout.addWidget(log)
    terminal.addTab(page, "Terminal")
    controls = [
        (QLineEdit("12.5"), "focus.ring", 2),
        (QSpinBox(), "focus.ring", 2),
        (combo, "focus.ring", 2),
        (QPushButton("Save"), "focus.ring", 2),
        (primary, "focus.ring.primary", 2),
        (search, "focus.ring", 1),
        (log, "focus.ring", 2),
    ]
    for control, _role, _width in controls:
        layout.addWidget(terminal if control is log else control)
    _show(qapp, widgets, window, 360, 600)
    assert log.focusPolicy() & Qt.TabFocus, "Tab reaches the log"
    text_area = log.viewport().geometry()

    def edge(control, width):
        image = window.grab().toImage()
        start = control.mapTo(window, QPoint(0, control.height() // 2))
        return [_pixel(image, start.x() + x, start.y()) for x in range(width)]

    for control, role, width in controls:
        sink.setFocus(Qt.OtherFocusReason)
        qapp.processEvents()
        before = edge(control, width)
        control.setFocus(Qt.OtherFocusReason)
        qapp.processEvents()
        assert control.hasFocus()
        after = edge(control, width)
        name = control.objectName() or type(control).__name__
        assert after == [tokens.value(role, theme)] * width, (name, before, after)
        if control is log:
            assert before == [tokens.value("bg.pane", theme)] * width, "the pane shows through"
            # A focus change alone does not lay the log out again; a stylesheet applied while
            # it has the focus does, with the focused rule's border and padding
            restyle(log)
            qapp.processEvents()
            assert log.viewport().geometry() == text_area, "the text stays where it was"
        for old, new in zip(before, after):
            assert contrast.contrast_ratio(old, new) >= 3, (name, old, new)


# ---- Date fields ------------------------------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_a_date_fields_frame_is_fusions_until_the_input_rule_takes_it(qapp, tokens, style, theme):
    """A known contrast failure, reported by the contrast test as I14 and I15: QDateTimeEdit
    is not in the input rule, so Fusion draws its frame in the palette's Window made
    darker(140), under 3:1 on a card and on the page. When the field joins the input rule,
    this test gives way to that rule's check."""
    from PyQt5.QtCore import QDateTime, QPoint  # noqa: PLC0415
    from PyQt5.QtGui import QColor  # noqa: PLC0415
    from PyQt5.QtWidgets import (  # noqa: PLC0415
        QDateTimeEdit,
        QFrame,
        QLineEdit,
        QVBoxLayout,
        QWidget,
    )

    manager, widgets = style
    manager.apply(theme)
    window = QWidget()
    layout = QVBoxLayout(window)
    sink = QLineEdit()  # takes the focus: a focused date field draws Fusion's focus frame
    layout.addWidget(sink)
    card = QFrame()
    card.setObjectName("Card")
    QVBoxLayout(card).setContentsMargins(16, 16, 16, 16)
    on_card = QDateTimeEdit(QDateTime(2030, 1, 15, 9, 0))
    on_card.setCalendarPopup(True)
    card.layout().addWidget(on_card)
    layout.addWidget(card)
    on_page = QDateTimeEdit(QDateTime(2030, 1, 15, 9, 0))
    on_page.setCalendarPopup(True)
    layout.addWidget(on_page)
    _show(qapp, widgets, window, 400, 220)
    sink.setFocus()
    qapp.processEvents()

    page = QColor(tokens.value("bg.page", theme))
    frame = page.darker(140).name().upper()
    channels = (page.red(), page.green(), page.blue())
    assert frame == "#" + "".join(f"{round(c * 100 / 140):02X}" for c in channels)
    image = window.grab().toImage()
    for edit in (on_card, on_page):
        top = edit.mapTo(window, QPoint(edit.width() // 2, 0))
        assert _pixel(image, top.x(), top.y()) == frame


# ---- The calendar popup -----------------------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
def test_a_calendar_popups_navigation_bar_is_the_inset_under_body_text(qapp, tokens, style, theme):
    """A date field's calendar fills its navigation bar with the palette's Highlight and
    writes the month and year in HighlightedText: under the solid selection, a teal band.
    The stylesheet makes the bar the inset surface, under body text."""
    from collections import Counter  # noqa: PLC0415

    from PyQt5.QtCore import QDate, QPoint  # noqa: PLC0415
    from PyQt5.QtWidgets import QCalendarWidget, QToolButton, QWidget  # noqa: PLC0415

    manager, widgets = style
    manager.apply("light")
    calendar = QCalendarWidget()
    calendar.setSelectedDate(QDate(2030, 1, 15))
    _show(qapp, widgets, calendar, 320, 240)
    manager.apply(theme)  # a theme applied after the calendar exists reaches it
    qapp.processEvents()

    bar = calendar.findChild(QWidget, "qt_calendar_navigationbar")
    image = calendar.grab().toImage()
    middle = bar.mapTo(calendar, QPoint(bar.width() // 2, 2))
    assert _pixel(image, middle.x(), middle.y()) == tokens.value("bg.inset", theme)
    for name in ("qt_calendar_monthbutton", "qt_calendar_yearbutton"):
        button = bar.findChild(QToolButton, name)
        corner = button.mapTo(calendar, QPoint(0, 0))
        drawn = Counter(
            _pixel(image, corner.x() + x, corner.y() + y)
            for x in range(button.width())
            for y in range(button.height())
        )
        assert tokens.value("text.primary", theme) in drawn, name
        assert tokens.value("text.on-accent", theme) not in drawn, name


@pytest.mark.parametrize("theme", THEMES)
def test_a_calendars_weekend_dates_take_the_themes_colour(qapp, tokens, style, theme):
    """Qt writes a calendar's weekend dates and weekday names in its own red, #FF0000: 4.0:1
    on the light card, 3.0:1 on the dark one. A date field makes its calendar popup on the
    first click, and the popup takes the focus as it opens: StyleManager tones a calendar
    then, before it paints, and again after every theme applied."""
    from collections import Counter  # noqa: PLC0415

    from PyQt5.QtCore import QDate, QDateTime, Qt  # noqa: PLC0415
    from PyQt5.QtTest import QTest  # noqa: PLC0415
    from PyQt5.QtWidgets import (  # noqa: PLC0415
        QAbstractItemView,
        QCalendarWidget,
        QDateTimeEdit,
        QStyle,
        QStyleOptionComboBox,
    )

    manager, widgets = style
    manager.apply(theme)

    def weekend(calendar):
        return {
            calendar.weekdayTextFormat(day).foreground().color().name().upper()
            for day in (Qt.Saturday, Qt.Sunday)
        }

    # A date field's popup, opened with a click on its arrow as an operator opens it
    edit = QDateTimeEdit(QDateTime(2030, 1, 15, 9, 0))
    edit.setCalendarPopup(True)
    _show(qapp, widgets, edit, 240, 30)
    edit.activateWindow()
    option = QStyleOptionComboBox()
    option.initFrom(edit)
    option.editable = True
    option.subControls = QStyle.SC_All
    arrow = edit.style().subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxArrow, edit)
    QTest.mouseClick(edit, Qt.LeftButton, Qt.NoModifier, arrow.center())
    qapp.processEvents()
    popup = edit.calendarWidget()
    assert popup.window().isVisible(), "the click opened the popup"
    assert weekend(popup) == {tokens.value("text.weekend", theme)}
    popup.window().hide()

    # A calendar on screen, and a theme applied after it exists
    calendar = QCalendarWidget()
    calendar.setSelectedDate(QDate(2030, 1, 15))
    _show(qapp, widgets, calendar, 320, 240)
    other = "dark" if theme == "light" else "light"
    manager.apply(other)
    qapp.processEvents()
    assert weekend(calendar) == weekend(popup) == {tokens.value("text.weekend", other)}
    image = calendar.findChild(QAbstractItemView).viewport().grab().toImage()
    drawn = Counter(
        _pixel(image, x, y) for x in range(image.width()) for y in range(image.height())
    )
    assert tokens.value("text.weekend", other) in drawn
    assert "#FF0000" not in drawn


# ---- The Help pane ----------------------------------------------------------------------


def test_the_help_pane_follows_the_theme(qapp, tokens, style):
    from PyQt5.QtCore import QPoint  # noqa: PLC0415
    from PyQt5.QtWidgets import QWidget  # noqa: PLC0415
    from ui.HelpTab import HelpTab  # noqa: PLC0415

    manager, widgets = style
    manager.apply("light")
    help_tab = _show(qapp, widgets, HelpTab(), 1000, 700)  # opens its first topic

    def page():
        image = help_tab.content_browser.viewport().grab().toImage()
        return _pixel(image, 6, 6)  # inside the page's padding

    assert help_tab._current_theme() == "light"
    assert page() == tokens.value("bg.surface", "light")

    # The selected topic is one solid block: its indent keeps the surface the tree stands
    # on, the sidebar's (the tree has no box of its own: the navigation column on the base
    # layer, as WinUI's NavigationView)
    tree = help_tab.topic_tree
    rect = tree.visualItemRect(tree.currentItem())
    sidebar = help_tab.findChild(QWidget, "HelpSidebar")
    image = sidebar.grab().toImage()

    def at(x, y):
        point = tree.viewport().mapTo(sidebar, QPoint(x, y))
        return _pixel(image, point.x(), point.y())

    assert at(rect.left() + 12, rect.center().y()) == tokens.value("bg.selected", "light")
    assert at(4, rect.center().y()) == tokens.value("bg.page", "light")

    # Another theme applied while the pane shows: the pane redraws itself
    manager.apply("dark")
    qapp.processEvents()
    assert help_tab._current_theme() == "dark"
    assert page() == tokens.value("bg.surface", "dark")
    html = help_tab.content_browser.toHtml().lower()
    assert tokens.value("text.primary", "dark").lower() in html
    assert tokens.value("text.primary", "light").lower() not in html

    # A search hit takes the theme's highlight, and keeps it across a theme change
    help_tab.search_bar.setText("schedule")
    help_tab.perform_search()
    hits = help_tab.content_browser.extraSelections()
    assert hits, "the open topic mentions 'schedule'"
    assert hits[0].format.background().color().name().upper() == tokens.value(
        "bg.highlight", "dark"
    )
    manager.apply("light")
    qapp.processEvents()
    hits = help_tab.content_browser.extraSelections()
    assert hits and hits[0].format.background().color().name().upper() == tokens.value(
        "bg.highlight", "light"
    )
    assert page() == tokens.value("bg.surface", "light")
