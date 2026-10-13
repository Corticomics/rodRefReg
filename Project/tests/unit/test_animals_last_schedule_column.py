"""The Animals tab's "Last schedule delivered amount" column, on screen.

The cell's words come from utils.last_run_text (test_last_run_text.py). Here:
the tab puts them in an eighth column, read-only, and flags the red ones for
a delegate that fills the whole cell in the tab's alertFill / alertText,
which both theme stylesheets set with AA contrast, and frames it when it is
selected. The table keeps the
operator's filter and selected animal when it reloads, and the Animals tab
reloads whenever it is selected, so a run that opened while another tab was
on screen shows. Rendered offscreen; pixels are compared with the tab's own
colours, not with hex literals.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"

# The Animals tab's width on the Pi's 1920 x 1080 monitor (test_animals_table_layout.py).
PI_TAB_WIDTH = 1114

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
def theme_qss(qapp):
    """Apply a theme stylesheet to the app; the old one comes back after the test."""
    old = qapp.styleSheet()

    def _apply(qss_name):
        qapp.setStyleSheet((STYLE_DIR / qss_name).read_text(encoding="utf-8"))
        qapp.processEvents()

    yield _apply
    qapp.setStyleSheet(old)
    qapp.processEvents()


@pytest.fixture
def make_tab(qapp):
    """An AnimalsTab shown at the Pi's width, over a stand-in database that
    returns the list it was given, as the list is when the tab reloads."""
    from ui.animals_tab import AnimalsTab  # noqa: PLC0415

    tabs = []

    def _make(animals):
        tab = AnimalsTab(
            settings={},
            print_to_terminal=lambda *_: None,
            database_handler=SimpleNamespace(get_all_animals=lambda: list(animals)),
            login_system=SimpleNamespace(get_current_trainer=lambda: None),
        )
        tab.resize(PI_TAB_WIDTH, 600)
        tab.show()
        qapp.processEvents()
        tabs.append(tab)
        return tab

    yield _make
    for tab in tabs:
        tab.close()


def _run(outcome, delivered=0.991, **fields):
    run = {
        'run_id': 1,
        'schedule_name': "AM water",
        'delivery_mode': 'staggered',
        'started_at': "2026-10-09T07:00:00",
        'ended_at': "2026-10-09T07:30:00",
        'outcome': outcome,
        'relay_unit_id': 5,
        'requested_ml': 1.0,
        'planned_ml': 0.991,
        'delivered_ml': delivered,
    }
    run.update(fields)
    return run


def _animal(animal_id, name, run):
    return SimpleNamespace(
        animal_id=animal_id,
        lab_animal_id=f"M-{animal_id:03d}",
        name=name,
        sex="female",
        initial_weight=30.0,
        last_weight=25.0,
        last_weighted=None,
        last_watering=None,
        last_run=run,
    )


OUTCOMES = [
    (1, "Never", None),
    (2, "Done", _run('completed')),
    (3, "Halted", _run('stopped', delivered=0.4)),
    (4, "Short", _run('incomplete', delivered=0.8)),
    (5, "Crashed", _run('interrupted', delivered=None)),
    (6, "Busy", _run('running', delivered=None, ended_at=None)),
]


def _shown(tab):
    """The names of the rows the filter shows."""
    table = tab.animals_table
    return [table.item(r, 1).text() for r in range(table.rowCount()) if not table.isRowHidden(r)]


def test_each_outcome_has_its_text_tooltip_and_red_flag_in_the_table(make_tab):
    from PyQt5.QtCore import Qt  # noqa: PLC0415

    from ui.animals_tab import LAST_RUN_ALERT_ROLE  # noqa: PLC0415
    from utils.last_run_text import last_run_cell  # noqa: PLC0415

    tab = make_tab([_animal(*row) for row in OUTCOMES])
    table = tab.animals_table
    column = tab.LAST_RUN_COLUMN
    assert column == table.columnCount() - 1 == 7
    assert table.horizontalHeaderItem(column).toolTip() == (
        "Water each animal received in its last schedule run. "
        "Red: the run ended before the animal got its full amount."
    )
    expected = {
        "Never": ("—", False),
        "Done": ("0.991 mL", False),
        "Halted": ("Stopped · 0.400 / 0.991 mL", True),
        "Short": ("Incomplete · 0.800 / 0.991 mL", True),
        "Crashed": ("Interrupted · ? / 0.991 mL", True),
        "Busy": ("Running · 0.991 mL planned", False),
    }
    for row, (_animal_id, name, run) in enumerate(OUTCOMES):
        item = table.item(row, column)
        assert table.item(row, 1).text() == name
        assert (item.text(), bool(item.data(LAST_RUN_ALERT_ROLE))) == expected[name], name
        assert item.toolTip() == last_run_cell(run, tab._when)[1], name
        assert not item.flags() & Qt.ItemIsEditable, name


def test_a_red_cell_is_filled_to_its_edges_under_the_theme(make_tab, theme_qss):
    """The stylesheet pads every item (12 px by 16 px), and a cell widget sits
    inside that padding: a red QLabel would fill only a band of the cell. The
    delegate fills it to its edges; a completed cell is painted as usual."""
    theme_qss("app-light.qss")
    tab = make_tab([_animal(*OUTCOMES[1]), _animal(*OUTCOMES[2])])
    table = tab.animals_table
    column = tab.LAST_RUN_COLUMN
    image = table.viewport().grab().toImage()
    left = table.columnViewportPosition(column)
    right = left + table.columnWidth(column) - 4

    def colour(x, row, dy):
        return image.pixelColor(x, table.rowViewportPosition(row) + dy).name()

    fill = tab.alertFill.name()
    bottom = table.rowHeight(1) - 4
    for x, dy in ((left + 3, 3), (left + 3, bottom), (right, 3), (right, bottom)):
        assert colour(x, 1, dy) == fill, f"the stopped cell at ({x}, {dy})"
    assert colour(left + 3, 0, table.rowHeight(0) // 2) != fill, "the completed cell"


def test_the_filter_finds_the_status_word(make_tab):
    tab = make_tab([_animal(*row) for row in OUTCOMES])
    tab.filter_input.setText("stopped")
    assert _shown(tab) == ["Halted"]
    tab.filter_input.setText("Interrupted")
    assert _shown(tab) == ["Crashed"]
    tab.filter_input.setText("running")
    assert _shown(tab) == ["Busy"]
    tab.filter_input.setText("Short")
    assert _shown(tab) == ["Short"]
    tab.filter_input.setText("")
    assert len(_shown(tab)) == len(OUTCOMES)


def test_a_reload_keeps_the_filter(make_tab):
    """The table reloads on its own when a run ends and when the tab is
    selected: the operator's filter stays, and a new animal that does not
    match it stays hidden."""
    animals = [_animal(*row) for row in OUTCOMES]
    tab = make_tab(animals)
    tab.filter_input.setText("Sho")
    assert _shown(tab) == ["Short"]
    animals.append(_animal(7, "Newcomer", None))
    tab.load_animals()
    assert tab.animals_table.rowCount() == len(OUTCOMES) + 1
    assert _shown(tab) == ["Short"]


def test_a_reload_keeps_the_selected_animal(make_tab):
    """Edit and Remove act on the current row. A reload can move the animal to
    another row; it stays current there. When the filter hides it, no row is
    current, so Edit and Remove ask for a selection: they never act on
    another animal."""
    animals = [_animal(*row) for row in OUTCOMES]
    tab = make_tab(animals)
    table = tab.animals_table
    table.setCurrentCell(3, 1)
    assert table.item(3, 1).text() == "Short"

    del animals[0]  # an animal above it is removed: Short moves up a row
    tab.load_animals()
    assert table.currentRow() == 2
    assert table.item(2, 1).text() == "Short"
    assert table.item(2, 1).isSelected()

    tab.filter_input.setText("Halted")
    tab.load_animals()
    assert table.currentRow() == -1


def test_clicking_a_red_cell_selects_its_row_and_shows_it(make_tab, theme_qss):
    """Edit and Remove act on the current row: the painted cell must not
    swallow the click. The table selects single cells, and the red cell
    paints its own fill, so its selection is a frame in the text colour."""
    from PyQt5.QtCore import Qt  # noqa: PLC0415
    from PyQt5.QtTest import QTest  # noqa: PLC0415

    theme_qss("app-light.qss")
    tab = make_tab([_animal(*OUTCOMES[1]), _animal(*OUTCOMES[2])])
    table = tab.animals_table
    cell = table.visualItemRect(table.item(1, tab.LAST_RUN_COLUMN))

    def colour(dx):
        image = table.viewport().grab().toImage()
        return image.pixelColor(cell.left() + dx, cell.center().y()).name()

    assert colour(3) == tab.alertFill.name(), "no frame before the click"
    QTest.mouseClick(table.viewport(), Qt.LeftButton, Qt.NoModifier, cell.center())
    assert table.currentRow() == 1
    assert colour(3) == tab.alertText.name(), "the frame"
    assert colour(10) == tab.alertFill.name(), "still red inside the frame"


def test_tooltip_times_say_how_long_ago_and_when(make_tab):
    tab = make_tab([])
    now = datetime.now()
    past = now - timedelta(hours=2, minutes=5)
    assert tab._when(past.isoformat()) == f"2 hours ago ({past:%Y-%m-%d %H:%M})"
    day_before = now - timedelta(hours=30)
    assert tab._when(day_before.isoformat()) == f"yesterday ({day_before:%Y-%m-%d %H:%M})"
    ahead = now + timedelta(minutes=5)  # the clock went back since (the Pi has no RTC)
    assert tab._when(ahead.isoformat()) == f"at {ahead:%Y-%m-%d %H:%M}"
    # A time with a UTC offset cannot be compared with the local clock.
    assert tab._when("2026-10-09T07:00:00+00:00") == "at 2026-10-09 07:00"
    assert tab._when(None) == "at an unknown time"
    assert tab._when("not a time") == "at an unknown time"


def _luminance(hex_colour):
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _alert_colours(qss_name):
    text = (STYLE_DIR / qss_name).read_text(encoding="utf-8")
    rule = re.search(r"QWidget#AnimalsTab\s*\{([^}]*)\}", text)
    assert rule, f"{qss_name} has no QWidget#AnimalsTab rule"
    fill = re.search(r"qproperty-alertFill:\s*(#[0-9A-Fa-f]{6})", rule.group(1))
    ink = re.search(r"qproperty-alertText:\s*(#[0-9A-Fa-f]{6})", rule.group(1))
    assert fill and ink, f"{qss_name} must set qproperty-alertFill and qproperty-alertText"
    return fill.group(1), ink.group(1)


@pytest.mark.parametrize("qss_name", ["app-light.qss", "app-dark.qss"])
def test_both_themes_set_red_cell_colours_with_aa_contrast(qss_name):
    """WCAG 2.x AA for normal text: 4.5:1. Holds for any palette that sets the rule."""
    fill, ink = _alert_colours(qss_name)
    lighter, darker = sorted((_luminance(fill), _luminance(ink)), reverse=True)
    assert (lighter + 0.05) / (darker + 0.05) >= 4.5, f"{qss_name}: {ink} on {fill}"


def test_a_theme_switch_sets_the_red_cell_colours(make_tab, theme_qss):
    """The stylesheets reach the tab by its name, through qproperty-*: each
    switch replaces whatever colours the tab held (sentinels here, as the
    Python defaults equal both themes' values)."""
    from PyQt5.QtGui import QColor  # noqa: PLC0415

    tab = make_tab([_animal(*OUTCOMES[2])])
    for qss_name in ("app-dark.qss", "app-light.qss"):
        tab.setProperty("alertFill", QColor("#010203"))
        tab.setProperty("alertText", QColor("#040506"))
        theme_qss(qss_name)
        fill, ink = _alert_colours(qss_name)
        assert tab.alertFill.name().upper() == fill.upper(), qss_name
        assert tab.alertText.name().upper() == ink.upper(), qss_name


def test_selecting_the_animals_tab_reloads_it(qapp, database_handler, system_controller):
    """A run's record opens at its first delivery, on the worker thread, and
    nothing reloads the tab then. Selecting the Animals tab does: it shows the
    run as Running, and the next selection shows how it ended."""
    from models.animal import Animal  # noqa: PLC0415
    from models.login_system import LoginSystem  # noqa: PLC0415
    from ui.projects_section import ProjectsSection  # noqa: PLC0415

    section = ProjectsSection(
        settings={},
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
        login_system=LoginSystem(database_handler),
        system_controller=system_controller,
    )
    table = section.animals_tab.animals_table
    assert section.tab_widget.currentIndex() == section.schedules_tab_index
    assert table.rowCount() == 0

    animal_id = database_handler.add_animal(Animal(lab_animal_id="M-011", name="Basil"), None)
    run_id = database_handler.start_schedule_run(
        12,
        "AM water",
        'staggered',
        None,
        [{'animal_id': animal_id, 'relay_unit_id': 3, 'requested_ml': 1.0, 'planned_ml': 0.991}],
    )

    def cell():
        return table.item(0, section.animals_tab.LAST_RUN_COLUMN).text()

    section.tab_widget.setCurrentIndex(section.animals_tab_index)
    assert table.rowCount() == 1, "selecting the tab reloads it"
    assert cell() == "Running · 0.991 mL planned"

    assert database_handler.finish_schedule_run(run_id, 'stopped', {animal_id: (0.4, 'stopped')})
    section.tab_widget.setCurrentIndex(section.wizard_tab_index)
    assert cell() == "Running · 0.991 mL planned", "another tab does not reload it"
    section.tab_widget.setCurrentIndex(section.animals_tab_index)
    assert cell() == "Stopped · 0.400 / 0.991 mL"
