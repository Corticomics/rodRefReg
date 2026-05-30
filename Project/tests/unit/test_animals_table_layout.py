"""Regression test for the animals table column layout on refresh.

Bug: after adding an animal, ``AnimalsTab.populate_animal_table`` called
``resizeColumnsToContents()``, which collapses every column — including the
stretch column — to its content width. That left a wide band of empty
whitespace on the right of the table that only cleared on the next resize
event (in practice, restarting the app). The initial load looked fine only
because a resize event fired after the first show.

This test repopulates the table while it is shown and asserts the columns
still fill the viewport (the last column stretches), so a future reintroduction
of a content-resize in the refresh path fails CI immediately.

Skips when PyQt5 is unavailable (dev laptops without the system bindings); CI
installs ``python3-pyqt5`` so it always runs there.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


def _animal(lab_id: str, name: str):
    """A minimal duck-typed stand-in for the attributes the table reads."""
    return SimpleNamespace(
        lab_animal_id=lab_id,
        name=name,
        sex="male",
        initial_weight=30.0,
        last_weight=25.0,
        last_weighted=None,
        last_watering=None,
    )


def _make_tab(qapp):
    from ui.animals_tab import AnimalsTab  # noqa: PLC0415

    # Stub the collaborators: load_animals() (called in __init__) only needs
    # get_current_trainer() -> None and get_all_animals() -> []. No DB touched.
    login_system = SimpleNamespace(get_current_trainer=lambda: None)
    database_handler = SimpleNamespace(get_all_animals=lambda: [])
    return AnimalsTab(
        settings={},
        print_to_terminal=lambda *_: None,
        database_handler=database_handler,
        login_system=login_system,
    )


def test_columns_fill_viewport_after_repopulate(qapp):
    tab = _make_tab(qapp)
    tab.resize(1000, 600)
    tab.show()
    qapp.processEvents()

    table = tab.animals_table
    viewport_width = table.viewport().width()
    assert viewport_width > 500, "offscreen table did not lay out to a usable width"

    # Repopulate to mimic an "add animal" refresh of an already-shown tab, then
    # assert the layout WITHOUT spinning the event loop. The bug only persists
    # because no relayout/resize event fires after the refresh — pumping events
    # here would re-stretch the columns and mask the regression.
    tab.populate_animal_table([_animal("1", "Martin the Warrior"), _animal("2", "Cornflower")])

    total = sum(table.columnWidth(c) for c in range(table.columnCount()))
    # No trailing whitespace: the columns (last one stretched) fill the viewport.
    assert total >= viewport_width - 5, (
        f"columns sum to {total}px but viewport is {viewport_width}px — "
        "trailing whitespace regression (resizeColumnsToContents in refresh?)"
    )
    # The last column must be the one that stretched, well past its base width.
    assert table.columnWidth(table.columnCount() - 1) > 160
