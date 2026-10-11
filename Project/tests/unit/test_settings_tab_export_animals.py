"""Export Animals to CSV adds each animal's last schedule run.

Settings > General > Data Import/Export > Export Animals to CSV
(SettingsTab.export_animals) writes seven more columns after Last Watering:
the schedule, how its run ended for the animal, the scheduled, planned and
delivered amounts as numbers (mL, three decimals, so a spreadsheet can add
them up), and when the run started and ended. They follow the Animals tab:
the result is the word its cell starts with (utils.last_run_text.outcome_word;
Completed for a completed run, whose cell shows only the amount); an amount
that was not recorded is empty, never 0, and one recorded as 0 is 0.000; an
interrupted run has no end, because its stored end is when the next start
found it open. An animal that
never ran has the seven cells empty. The runs are recorded through the
DatabaseHandler facade, as RRR records them.
"""

from __future__ import annotations

import csv
import os
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")
pytest.importorskip("pandas")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

COLUMNS_BEFORE = [
    'Lab Animal ID',
    'Name',
    'Sex',
    'Initial Weight (g)',
    'Last Weight (g)',
    'Last Weighted',
    'Last Watering',
]
LAST_SCHEDULE_COLUMNS = [
    'Last Schedule',
    'Last Schedule Result',
    'Last Schedule Scheduled (mL)',
    'Last Schedule Planned (mL)',
    'Last Schedule Delivered (mL)',
    'Last Schedule Started',
    'Last Schedule Ended',
]


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def dialogs(qapp, monkeypatch):
    """Every message box, recorded as (kind, title) instead of shown: offscreen,
    a modal box nobody closes would hang the run."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    shown = []

    def _box(kind):
        return staticmethod(
            lambda *a, **k: shown.append((kind, a[1] if len(a) > 1 else None)) or QMessageBox.Ok
        )

    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, kind, _box(kind))
    return shown


@pytest.fixture(autouse=True)
def _reset_lock(qapp):
    # SettingsTab subscribes to the OperationLock singleton; other test
    # modules leave it as a QObject whose C++ side is gone.
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield
    ol._singleton = None


@pytest.fixture
def clock(monkeypatch):
    """Set the time the run history stamps on what it records next."""
    import models.schedule_runs_repo as schedule_runs_repo  # noqa: PLC0415

    def _set(timestamp):
        monkeypatch.setattr(schedule_runs_repo, "_now", lambda: timestamp)

    return _set


def _add_animal(database_handler, lab_id, name, **fields):
    from models.animal import Animal  # noqa: PLC0415

    animal_id = database_handler.add_animal(
        Animal(lab_animal_id=lab_id, name=name, **fields), trainer_id=None
    )
    assert animal_id is not None
    return animal_id


def _plan(animal_id, cage, requested_ml=1.0, planned_ml=0.991):
    """One animal of a run, as the delivery worker plans it at the first delivery."""
    return {
        'animal_id': animal_id,
        'relay_unit_id': cage,
        'requested_ml': requested_ml,
        'planned_ml': planned_ml,
    }


def _export(system_controller, database_handler, tmp_path, monkeypatch):
    """Press Export Animals to CSV, save as CSV, and read the file back as
    rows, the header first."""
    from PyQt5.QtWidgets import QFileDialog  # noqa: PLC0415

    from ui.SettingsTab import SettingsTab  # noqa: PLC0415

    out = tmp_path / "animals.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **k: (str(out), "CSV Files (*.csv)")),
    )
    tab = SettingsTab(
        system_controller,
        login_system=SimpleNamespace(is_logged_in=lambda: True, get_current_trainer=lambda: None),
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
    )
    tab.export_animals()
    # The file starts with a BOM, for Excel on a Mac.
    return list(csv.reader(out.read_text(encoding="utf-8-sig").splitlines()))


def test_the_export_adds_each_animals_last_schedule(
    qapp, database_handler, system_controller, tmp_path, monkeypatch, dialogs, clock
):
    """One animal for each way its last run can stand, and one that never ran:
    each row ends with what the Animals tab shows of that run."""
    weighed = {
        'sex': "female",
        'initial_weight': 30.0,
        'last_weight': 25.0,
        'last_weighted': "2026-10-08T09:00:00",
    }
    stopped = _add_animal(database_handler, "M-011", "Basil", **weighed)
    completed = _add_animal(
        database_handler, "M-012", "Clover", last_watering="2026-10-09T07:20:00"
    )
    not_recorded = _add_animal(database_handler, "M-013", "Dill")
    interrupted = _add_animal(database_handler, "M-014", "Fennel")
    running = _add_animal(database_handler, "M-015", "Ginger")
    _add_animal(database_handler, "M-016", "Juniper")  # never ran
    not_reached = _add_animal(database_handler, "M-017", "Lovage")

    # "AM water", staggered: Stop was pressed after one animal had its full
    # amount. The close gave no figure for a third, so its amount is not known.
    # Stop came before a fourth's turn: it got nothing, and the close records
    # 0 for it, as main._record_run_end does.
    clock("2026-10-09T07:00:00")
    am_water = database_handler.start_schedule_run(
        12,
        "AM water",
        'staggered',
        None,
        [_plan(stopped, 3), _plan(completed, 4), _plan(not_recorded, 7), _plan(not_reached, 8)],
    )
    clock("2026-10-09T07:30:12")
    assert database_handler.finish_schedule_run(
        am_water,
        'stopped',
        {
            stopped: (0.4, 'stopped'),
            completed: (0.991, 'completed'),
            not_reached: (0.0, 'stopped'),
        },
    )
    # "PM water", instant: RRR closed during it, and the next start found it open.
    clock("2026-10-09T08:00:00")
    database_handler.start_schedule_run(
        13, "PM water", 'instant', None, [_plan(interrupted, 5, 0.3, 0.307)]
    )
    clock("2026-10-09T09:05:00")
    assert database_handler.mark_interrupted_schedule_runs() == 1
    # "Evening" is delivering.
    clock("2026-10-09T09:10:00")
    database_handler.start_schedule_run(
        14, "Evening", 'staggered', None, [_plan(running, 6, 0.5, 0.513)]
    )

    header, *rows = _export(system_controller, database_handler, tmp_path, monkeypatch)

    assert [kind for kind, _title in dialogs if kind == "critical"] == [], "the export failed"
    assert ("information", "Success") in dialogs
    assert header == COLUMNS_BEFORE + LAST_SCHEDULE_COLUMNS
    row = {cells[0]: cells for cells in rows}
    assert list(row) == ["M-011", "M-012", "M-013", "M-014", "M-015", "M-016", "M-017"]
    # The first seven columns are as before.
    assert row["M-011"][:7] == [
        "M-011",
        "Basil",
        "female",
        "30.0",
        "25.0",
        "2026-10-08 09:00:00",
        "",
    ]
    assert row["M-012"][:7] == ["M-012", "Clover", "", "", "", "", "2026-10-09 07:20:00"]

    assert row["M-011"][7:] == [
        "AM water",
        "Stopped",
        "1.000",
        "0.991",
        "0.400",
        "2026-10-09 07:00:00",
        "2026-10-09 07:30:12",
    ]
    assert row["M-012"][7:] == [
        "AM water",
        "Completed",
        "1.000",
        "0.991",
        "0.991",
        "2026-10-09 07:00:00",
        "2026-10-09 07:30:12",
    ]
    # An amount that was not recorded is empty, never 0.
    assert row["M-013"][7:] == [
        "AM water",
        "Incomplete",
        "1.000",
        "0.991",
        "",
        "2026-10-09 07:00:00",
        "2026-10-09 07:30:12",
    ]
    # One recorded as 0 is 0.000, never empty: the animal got nothing, which
    # the file must not confuse with an amount nobody knows.
    assert row["M-017"][7:] == [
        "AM water",
        "Stopped",
        "1.000",
        "0.991",
        "0.000",
        "2026-10-09 07:00:00",
        "2026-10-09 07:30:12",
    ]
    # The interrupted run has a stored end, the time the next start found it
    # open, which is not when it stopped: the export leaves it empty.
    stored = {
        animal.lab_animal_id: animal.last_run for animal in database_handler.get_all_animals()
    }
    assert stored["M-014"]['ended_at'] == "2026-10-09T09:05:00"
    assert row["M-014"][7:] == [
        "PM water",
        "Interrupted",
        "0.300",
        "0.307",
        "",
        "2026-10-09 08:00:00",
        "",
    ]
    assert row["M-015"][7:] == [
        "Evening",
        "Running",
        "0.500",
        "0.513",
        "",
        "2026-10-09 09:10:00",
        "",
    ]
    assert row["M-016"][7:] == [""] * 7, "an animal that never ran"


def test_before_any_run_the_last_schedule_columns_are_there_and_empty(
    qapp, database_handler, system_controller, tmp_path, monkeypatch, dialogs
):
    """Right after the update, before a run is recorded: the seven columns are
    in the file and empty, not "None", "nan" or 0."""
    _add_animal(database_handler, "M-021", "Hyssop")

    header, *rows = _export(system_controller, database_handler, tmp_path, monkeypatch)

    assert [kind for kind, _title in dialogs if kind == "critical"] == [], "the export failed"
    assert header == COLUMNS_BEFORE + LAST_SCHEDULE_COLUMNS
    assert rows == [["M-021", "Hyssop"] + [""] * 12]
