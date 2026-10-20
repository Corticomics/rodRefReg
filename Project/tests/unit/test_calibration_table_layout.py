"""The Calibration table reads in full on the lab's screen (v2.1.0).

On the lab Pi (1920 x 1080) the table sits in the main window's right column,
about 700 px wide, and its fixed column widths cut the data off: "Not ...",
"0....", "1....", "2026-1...", and the Recalibrate buttons' first letter. Only
the cage name may now stretch and elide (its tooltip has it in full); every
other column is as wide as its widest text or its header.

Pinned in the real main window at 1920 x 1080, offscreen, in both themes,
with every kind of row. A text fits when Qt's own measure of it, the font's
advance plus the cell's padding (the cell's size hint, or the header
section's), is no wider than its column, so this holds whatever font the
device draws with. On origin/main's layout the cell and button checks fail.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# The QApplication this module uses, kept for the rest of the session. When a
# QApplication is destroyed, PyQt5 deletes every QObject without a parent.
_QAPP = []

# cage: (width, rest, mL/pulse, CV %, topology); every other cage uncalibrated.
SEED = {
    1: (30, 1000, 0.034164, 0.82, 'shared_manifold'),
    2: (20, 500, 0.026012, 2.41, 'shared_manifold'),
    3: (50, 1000, 0.041377, 4.62, 'shared_manifold'),
    4: (30, 1000, 0.035020, 1.10, 'independent'),  # Stale
    5: (20, None, 0.025871, 6.30, 'shared_manifold'),  # saved before rests were stored
    6: (30, 1000, 0.0, 1.00, 'shared_manifold'),  # Invalid
    7: (25, 800, 0.031250, 12.34, 'shared_manifold'),  # the widest CV
}


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415
    from utils import updater  # noqa: PLC0415

    monkeypatch.setattr(updater, "_busy_check", lambda: False)
    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, kind, staticmethod(lambda *a, **k: QMessageBox.Ok))


@pytest.fixture(params=["light", "dark"])
def calibration_table(request, qapp, monkeypatch, system_controller, database_handler):
    """Settings > Calibration in the real main window at 1920 x 1080, in the
    theme RRR applies (StyleManager), with an operator logged in."""
    from models.login_system import LoginSystem  # noqa: PLC0415
    from PyQt5.QtCore import QCoreApplication, QEvent  # noqa: PLC0415
    from ui.gui import RodentRefreshmentGUI  # noqa: PLC0415
    from ui.style.theme import StyleManager  # noqa: PLC0415

    old_sheet, old_font = qapp.styleSheet(), qapp.font()
    StyleManager(qapp).apply(request.param)
    for cage, (width, rest, volume, cv, topology) in SEED.items():
        assert database_handler.save_valve_calibration(
            cage_id=cage,
            relay_id=cage,
            pulse_width_ms=width,
            volume_per_pulse_ml=volume,
            stddev_ml=volume * cv / 100,
            cv_pct=cv,
            num_samples=250,
            inter_pulse_interval_ms=rest,
            topology=topology,
        )
    database_handler.set_cage_name(2, 2, "Left rack, top shelf, by the window")

    monkeypatch.setattr(RodentRefreshmentGUI, "showMaximized", lambda self: None)
    login = LoginSystem(database_handler)
    gui = RodentRefreshmentGUI(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        system_controller=system_controller,
        database_handler=database_handler,
        login_system=login,
        relay_handler=MagicMock(),
        notification_handler=MagicMock(),
    )
    assert login.create_user("zes", "pw") is True
    gui.user_tab.username_input.setText("zes")
    gui.user_tab.password_input.setText("pw")
    gui.user_tab.handle_login()
    gui.resize(1920, 1080)
    gui.show()
    tab = gui.settings_tab
    gui.main_tab_widget.setCurrentWidget(tab)
    tab.tab_widget.setCurrentWidget(tab.calibration_tab)
    _settle(qapp)

    yield tab
    gui.hide()  # not close(): closeEvent asks "Quit RRR?" in a modal box
    gui.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.setStyleSheet(old_sheet)
    qapp.setFont(old_font)


def _settle(qapp):
    for _ in range(10):
        qapp.processEvents()


def _cut_texts(table):
    """Every header and data cell whose text does not fit its column. The
    cage column is left out of the cells: it stretches and elides by design."""
    from PyQt5.QtCore import QRect, Qt  # noqa: PLC0415
    from PyQt5.QtWidgets import QStyle, QStyleOptionHeader  # noqa: PLC0415

    header = table.horizontalHeader()
    style = table.style()
    grid = 1 if table.showGrid() else 0
    font = table.fontMetrics()
    options = table.viewOptions()
    # The margin Qt keeps each side of a cell's text, inside its padding, and
    # elides the text against.
    text_margin = style.pixelMetric(QStyle.PM_FocusFrameHMargin, None, table) + 1
    cut = []
    for column in range(table.columnCount()):
        label = table.horizontalHeaderItem(column).text()
        width = table.columnWidth(column)
        # The header draws its label in the theme's section font; its size
        # hint is that label's advance plus the section's padding and margins.
        if header.sectionSizeHint(column) > header.sectionSize(column):
            cut.append(('header', label, header.sectionSizeHint(column), width))
        if header.textElideMode() != Qt.ElideNone:
            # The header also elides, measuring in its own font.
            section = QStyleOptionHeader()
            section.initFrom(header)
            section.rect = QRect(header.sectionViewportPosition(column), 0, width, header.height())
            room = style.subElementRect(QStyle.SE_HeaderLabel, section, header).width()
            room -= 2 * style.pixelMetric(QStyle.PM_HeaderMargin, None, header)
            if header.fontMetrics().horizontalAdvance(label) > room:
                cut.append(('header (elided)', label, room, width))
        if label == "Cage":
            continue
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is None or not item.text():
                continue
            index = table.model().index(row, column)
            need = table.itemDelegate().sizeHint(options, index).width()
            # Qt's size for the cell: the text's advance, its margins and the
            # cell's padding.
            assert need >= font.horizontalAdvance(item.text()) + 2 * text_margin, item.text()
            if need > width - grid:
                cut.append((label, item.text(), need, width - grid))
    return cut


def test_every_header_and_data_cell_reads_in_full_at_1920x1080(qapp, calibration_table):
    table = calibration_table.calibration_table

    assert 600 < table.width() < 800, "the right column of the Pi's 1920 x 1080 window"
    assert _cut_texts(table) == []
    assert table.horizontalScrollBar().maximum() == 0, "nothing scrolls sideways"
    shown = {table.item(row, 1).text() for row in range(table.rowCount())}
    assert shown == {"[OK]", "Stale", "Invalid", "Not Calibrated"}, "every kind of row"


def test_the_table_still_reads_in_full_after_a_refresh(
    qapp, calibration_table, database_handler
):
    """The columns follow their content: a wider text after a recalibration
    widens its column, as soon as the table refreshes."""
    tab = calibration_table
    assert database_handler.save_valve_calibration(
        cage_id=9,
        relay_id=9,
        pulse_width_ms=500,
        volume_per_pulse_ml=0.051300,
        stddev_ml=0.06,
        cv_pct=123.45,
        num_samples=250,
        inter_pulse_interval_ms=2000,
        topology='shared_manifold',
    )
    tab.refresh_calibration_table()
    _settle(qapp)

    table = tab.calibration_table
    assert table.item(8, tab.CAL_COL_CV).text() == "123.45%"
    assert table.item(8, tab.CAL_COL_PROFILE).text() == "500 / 2000 ms"
    assert _cut_texts(table) == []
    assert table.horizontalScrollBar().maximum() == 0


def test_the_action_buttons_keep_their_width_centred_in_their_cells(qapp, calibration_table):
    table = calibration_table.calibration_table
    action = table.columnCount() - 1
    assert table.horizontalHeaderItem(action).text() == "Action"
    left = table.columnViewportPosition(action)
    for row in range(table.rowCount()):
        button = table.cellWidget(row, action)
        box = button.geometry()
        top = table.rowViewportPosition(row)
        above = box.top() - top
        below = top + table.rowHeight(row) - (box.top() + box.height())
        before = box.left() - left
        after = left + table.columnWidth(action) - (box.left() + box.width())
        assert box.width() >= button.sizeHint().width(), f"{button.text()} cut off (row {row})"
        assert above >= 0 and below >= 0, f"row {row} runs into the next row"
        assert abs(above - below) <= 1, f"row {row}: {above} px above, {below} below"
        assert abs(before - after) <= 1, f"row {row}: {before} px left, {after} right"


def test_only_the_cage_name_elides_and_its_tooltip_has_it(qapp, calibration_table):
    table = calibration_table.calibration_table
    name = table.item(1, 0)
    assert name.text() == "2: Left rack, top shelf, by the window"
    assert name.toolTip() == "Cage 2 - Relay 2\nLeft rack, top shelf, by the window"
    assert table.item(0, 0).toolTip() == "Cage 1 - Relay 1", "a default name adds nothing"
