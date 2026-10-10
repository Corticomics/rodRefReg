"""Schedule run history: the record behind the Animals tab's last-run column.

One schedule_runs row per run that started delivering and one
schedule_run_animals row per animal in it (models/schedule_runs_repo.py,
reached through DatabaseHandler). Pinned here: the tables appear on an
existing database without touching its rows and creating them again is a
no-op; a run opens, closes once and is never reopened; a run a crash left
open is closed as interrupted with its delivered amount unknown; the animal
readers return each animal's latest run - by run order, not by clock - in
the one query they already ran, still in animal_id order; and Run's reader
returns each animal's latest run of one schedule, whatever ran since.
"""

from __future__ import annotations

import sqlite3

import pytest

from models.animal import Animal
from models.database_handler import DatabaseHandler
from version import __version__

# Animal.last_run: what the Animals tab, the animal export and the Run warning
# read. How a run ended for the audit (end_reason, stopped_by, the Stop flags)
# stays in schedule_runs, which these tests read directly.
LAST_RUN_KEYS = {
    'run_id',
    'schedule_name',
    'delivery_mode',
    'started_at',
    'ended_at',
    'outcome',
    'relay_unit_id',
    'requested_ml',
    'planned_ml',
    'delivered_ml',
}

# A slice of a v1.21.0 database: trainers and animals as v1.21.0 created them,
# with one animal on record.
V1_21_DDL = """
    CREATE TABLE trainers (
        trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        trainer_name TEXT UNIQUE NOT NULL,
        salt TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'normal'
    );
    CREATE TABLE animals (
        animal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        lab_animal_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        initial_weight REAL,
        last_weight REAL,
        last_weighted TEXT,
        last_watering TEXT,
        last_water_volume REAL,
        trainer_id INTEGER,
        sex TEXT CHECK(sex IN ('male', 'female')) DEFAULT NULL
    );
    INSERT INTO animals (lab_animal_id, name, initial_weight, trainer_id, sex)
    VALUES ('M-001', 'Martin', 30.0, 1, 'male');
"""


def _plan(animal_id, requested=1.0, planned=0.991, cage=3):
    return {
        'animal_id': animal_id,
        'relay_unit_id': cage,
        'requested_ml': requested,
        'planned_ml': planned,
    }


def _animal(handler, lab_id, trainer_id=None):
    return handler.add_animal(Animal(lab_animal_id=lab_id, name=lab_id), trainer_id)


def _trainer(handler, name):
    assert handler.add_trainer(name, 'pw')
    [(trainer_id,)] = _rows(handler, "SELECT trainer_id FROM trainers WHERE trainer_name = ?", (name,))
    return trainer_id


def _rows(handler, sql, args=()):
    with handler.connect() as conn:
        return conn.execute(sql, args).fetchall()


def _start(handler, *animal_ids, schedule_id=7, name='AM water', mode='staggered'):
    run_id = handler.start_schedule_run(
        schedule_id, name, mode, None, [_plan(a) for a in animal_ids]
    )
    assert run_id is not None
    return run_id


def _record(handler, schedule_id, results, end_reason='stopped'):
    """One closed run: ``results`` is [(animal_id, delivered or None, outcome)], cage = id + 2."""
    run_id = handler.start_schedule_run(
        schedule_id, 'AM water', 'staggered', None, [_plan(a, cage=a + 2) for a, _, _ in results]
    )
    assert handler.finish_schedule_run(
        run_id, end_reason, {a: (delivered, outcome) for a, delivered, outcome in results}
    )
    return run_id


def _last_runs(handler):
    """Each animal's last run as the Animals tab reads it: {animal_id: dict or None}."""
    return {animal.animal_id: animal.last_run for animal in handler.get_all_animals()}


def _run_row(handler, run_id):
    """The schedule_runs row: how the run ended, which last_run does not carry."""
    with handler.connect() as conn:
        conn.row_factory = sqlite3.Row
        return dict(conn.execute("SELECT * FROM schedule_runs WHERE run_id = ?", (run_id,)).fetchone())


def _history(handler):
    """Every row of both history tables, to show that a call changed nothing."""
    return (
        _rows(handler, "SELECT * FROM schedule_runs ORDER BY run_id"),
        _rows(handler, "SELECT * FROM schedule_run_animals ORDER BY run_id, animal_id"),
    )


def _plan_of_the_select(handler, monkeypatch, read):
    """The query plan of the one SELECT that ``read(handler)`` runs, one step per item."""
    statements = []

    class Cursor(sqlite3.Cursor):
        def execute(self, sql, parameters=()):
            statements.append((sql, parameters))
            return super().execute(sql, parameters)

    class Connection(sqlite3.Connection):
        def cursor(self, factory=Cursor):
            return super().cursor(factory)

    def connect():
        return sqlite3.connect(handler.db_path, factory=Connection)

    # The handler's readers call its connect; the repo kept the one it was given.
    monkeypatch.setattr(handler, 'connect', connect)
    monkeypatch.setattr(handler._schedule_runs, '_connect', connect)
    read(handler)
    [(sql, parameters)] = [s for s in statements if s[0].lstrip().startswith('SELECT')]
    with sqlite3.connect(handler.db_path) as conn:
        return [str(row[-1]) for row in conn.execute('EXPLAIN QUERY PLAN ' + sql, parameters)]


# --- schema -----------------------------------------------------------------


def test_an_existing_database_gains_the_tables_and_keeps_its_rows(tmp_path):
    db_path = tmp_path / "v1_21.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(V1_21_DDL)

    handler = DatabaseHandler(db_path=str(db_path))
    # The names the read-only sqlite_master check of the manual QA lists.
    names = _rows(handler, "SELECT name FROM sqlite_master WHERE name LIKE '%schedule_run%'")
    assert sorted(name for (name,) in names) == [
        'idx_schedule_run_animals_animal_run',
        'schedule_run_animals',
        'schedule_runs',
        'sqlite_autoindex_schedule_run_animals_1',
    ]

    [martin] = handler.get_all_animals()
    assert martin.lab_animal_id == 'M-001' and martin.last_run is None

    run_id = _start(handler, martin.animal_id)
    DatabaseHandler(db_path=str(db_path))  # creating the tables again is a no-op
    assert handler.get_all_animals()[0].last_run['run_id'] == run_id


# --- writing a run ----------------------------------------------------------


def test_a_run_opens_running_with_nothing_delivered_yet(database_handler):
    alice = _trainer(database_handler, 'alice')
    a1, a2 = _animal(database_handler, 'A1'), _animal(database_handler, 'A2')
    run_id = database_handler.start_schedule_run(
        7, 'AM water', 'instant', alice, [_plan(a1), _plan(str(a2), requested=0.5, planned=0.513)]
    )

    runs = _last_runs(database_handler)
    first = runs[a1]
    assert set(first) == LAST_RUN_KEYS, "last_run carries what the UI reads, no audit field"
    assert first['run_id'] == run_id and first['outcome'] == 'running'
    assert first['schedule_name'] == 'AM water' and first['delivery_mode'] == 'instant'
    assert first['relay_unit_id'] == 3
    assert first['requested_ml'] == 1.0 and first['planned_ml'] == 0.991
    assert first['delivered_ml'] is None and first['ended_at'] is None
    assert first['started_at']
    assert runs[a2]['planned_ml'] == 0.513  # a str animal id is stored as its int
    run = _run_row(database_handler, run_id)
    assert run['schedule_id'] == 7 and run['started_by'] == alice
    assert run['end_reason'] is None and run['stopped_by'] is None
    assert run['app_version'] == __version__


def test_a_run_with_no_animals_records_nothing(database_handler):
    assert database_handler.start_schedule_run(7, 'AM water', 'staggered', None, []) is None
    assert _rows(database_handler, "SELECT COUNT(*) FROM schedule_runs") == [(0,)]


def test_a_failed_start_writes_neither_table(database_handler):
    a1 = _animal(database_handler, 'A1')
    # The same animal twice violates the primary key: the whole start rolls back.
    run_id = database_handler.start_schedule_run(
        7, 'AM water', 'staggered', None, [_plan(a1), _plan(a1)]
    )
    assert run_id is None
    assert _rows(database_handler, "SELECT COUNT(*) FROM schedule_runs") == [(0,)]
    assert _rows(database_handler, "SELECT COUNT(*) FROM schedule_run_animals") == [(0,)]


def test_an_operator_stop_closes_the_run_with_each_animals_amount(database_handler):
    alice = _trainer(database_handler, 'alice')
    a1, a2 = _animal(database_handler, 'A1'), _animal(database_handler, 'A2')
    run_id = _start(database_handler, a1, a2)

    closed = database_handler.finish_schedule_run(
        run_id,
        'stopped',
        {a1: (0.991, 'completed'), a2: (0.410, 'stopped')},
        stopped_by=alice,
        relays_confirmed_off=True,
        worker_exited=False,
    )

    assert closed is True
    runs = _last_runs(database_handler)
    assert runs[a1]['outcome'] == 'completed' and runs[a1]['delivered_ml'] == 0.991
    assert runs[a2]['outcome'] == 'stopped' and runs[a2]['delivered_ml'] == 0.410
    run = _run_row(database_handler, run_id)
    assert run['end_reason'] == 'stopped' and run['ended_at']
    assert runs[a2]['ended_at'] == run['ended_at']
    assert run['stopped_by'] == alice
    assert run['relays_confirmed_off'] == 1 and run['worker_exited'] == 0


def test_a_natural_end_leaves_the_stop_fields_empty(database_handler):
    a1 = _animal(database_handler, 'A1')
    run_id = _start(database_handler, a1)

    assert database_handler.finish_schedule_run(run_id, 'completed', {a1: (0.991, 'completed')})

    run = _run_row(database_handler, run_id)
    assert run['end_reason'] == 'completed' and run['stopped_by'] is None
    assert run['relays_confirmed_off'] is None and run['worker_exited'] is None


def test_a_run_closes_only_once(database_handler):
    a1 = _animal(database_handler, 'A1')
    run_id = _start(database_handler, a1)
    assert database_handler.finish_schedule_run(run_id, 'stopped', {a1: (0.4, 'stopped')})
    first = _history(database_handler)

    # A second close (a late end hook) must not overwrite the first.
    again = database_handler.finish_schedule_run(run_id, 'completed', {a1: (0.9, 'completed')})
    assert again is False
    assert _history(database_handler) == first
    unknown = database_handler.finish_schedule_run(999, 'completed', {a1: (0.9, 'completed')})
    assert unknown is False
    assert _history(database_handler) == first


@pytest.mark.parametrize(
    'end_reason, outcome',
    [('cancelled', 'stopped'), ('stopped', 'running'), ('stopped', 'paused')],
)
def test_unknown_values_are_refused_before_anything_is_written(
    database_handler, end_reason, outcome
):
    a1 = _animal(database_handler, 'A1')
    run_id = _start(database_handler, a1)
    before = _history(database_handler)
    with pytest.raises(ValueError):
        database_handler.finish_schedule_run(run_id, end_reason, {a1: (0.4, outcome)})
    assert _last_runs(database_handler)[a1]['outcome'] == 'running'
    assert _history(database_handler) == before


def test_an_animal_left_out_of_the_results_is_not_left_running(database_handler):
    a1, a2 = _animal(database_handler, 'A1'), _animal(database_handler, 'A2')
    run_id = _start(database_handler, a1, a2)

    assert database_handler.finish_schedule_run(run_id, 'ended_short', {a1: (0.991, 'completed')})

    left_out = _last_runs(database_handler)[a2]
    assert left_out['outcome'] == 'incomplete' and left_out['delivered_ml'] is None


def test_a_close_the_database_refuses_leaves_the_run_open(database_handler, monkeypatch, capsys):
    # An abandoned worker can hold the write lock when Stop closes the run:
    # sqlite3 waits (about 5 s; 0.05 s here), then the close is refused.
    a1 = _animal(database_handler, 'A1')
    run_id = _start(database_handler, a1)
    path = database_handler.db_path
    monkeypatch.setattr(
        database_handler._schedule_runs, '_connect', lambda: sqlite3.connect(path, timeout=0.05)
    )
    holder = sqlite3.connect(path)
    holder.execute("BEGIN IMMEDIATE")
    try:
        refused = database_handler.finish_schedule_run(run_id, 'stopped', {a1: (0.4, 'stopped')})
    finally:
        holder.rollback()
        holder.close()

    assert refused is False
    assert f"Database error closing run {run_id}: database is locked" in capsys.readouterr().out
    assert _last_runs(database_handler)[a1]['outcome'] == 'running'
    assert _run_row(database_handler, run_id)['ended_at'] is None
    # Still open, so the next start closes it as interrupted.
    assert database_handler.mark_interrupted_schedule_runs() == 1
    assert _last_runs(database_handler)[a1]['outcome'] == 'interrupted'


# --- crash recovery ---------------------------------------------------------


def test_runs_left_open_are_closed_as_interrupted_at_the_next_start(database_handler):
    a1, a2 = _animal(database_handler, 'A1'), _animal(database_handler, 'A2')
    finished = _start(database_handler, a1)
    database_handler.finish_schedule_run(finished, 'completed', {a1: (0.991, 'completed')})
    open_run = _start(database_handler, a2, schedule_id=8)

    assert database_handler.mark_interrupted_schedule_runs() == 1

    runs = _last_runs(database_handler)
    assert runs[a2]['run_id'] == open_run
    assert runs[a2]['outcome'] == 'interrupted' and runs[a2]['delivered_ml'] is None
    assert runs[a2]['ended_at']
    assert _run_row(database_handler, open_run)['end_reason'] == 'interrupted'
    assert runs[a1]['outcome'] == 'completed'
    assert _run_row(database_handler, finished)['end_reason'] == 'completed'
    assert database_handler.mark_interrupted_schedule_runs() == 0
    # An interrupted run is closed: a late end record cannot rewrite it.
    late = database_handler.finish_schedule_run(open_run, 'completed', {a2: (1.0, 'completed')})
    assert late is False


def test_creating_the_tables_does_not_close_a_live_run(database_handler):
    # --selftest and the bench tools build a handler while RRR may be running.
    a1 = _animal(database_handler, 'A1')
    run_id = _start(database_handler, a1)
    DatabaseHandler(db_path=database_handler.db_path)
    assert _last_runs(database_handler)[a1]['outcome'] == 'running'
    assert _run_row(database_handler, run_id)['ended_at'] is None


# --- reading the latest run -------------------------------------------------


def test_the_readers_return_each_animals_latest_run_by_run_order(database_handler):
    a1, a2, never = (_animal(database_handler, n) for n in ('A1', 'A2', 'NEVER'))
    first = _start(database_handler, a1, a2, schedule_id=7)
    database_handler.finish_schedule_run(
        first, 'stopped', {a1: (0.4, 'stopped'), a2: (0.4, 'stopped')}
    )
    second = _start(database_handler, a1, schedule_id=8, name='PM water')
    # The Pi has no RTC: a clock that jumped back must not reorder runs.
    with database_handler.connect() as conn:
        conn.execute(
            "UPDATE schedule_runs SET started_at = '2000-01-01T00:00:00' WHERE run_id = ?",
            (second,),
        )

    animals = {a.animal_id: a for a in database_handler.get_all_animals()}

    assert list(animals) == sorted(animals), "rows keep the animal_id order"
    assert animals[a1].last_run['run_id'] == second
    assert animals[a1].last_run['schedule_name'] == 'PM water'
    assert animals[a2].last_run['run_id'] == first
    assert animals[a2].last_run['outcome'] == 'stopped'
    assert animals[never].last_run is None


def test_animals_come_back_in_id_order_with_or_without_a_run(database_handler, monkeypatch):
    # The schedule wizard and the animal export read these lists too.
    with database_handler.connect() as conn:
        conn.executemany(
            "INSERT INTO animals (animal_id, lab_animal_id, name, trainer_id) VALUES (?, ?, ?, ?)",
            [(30, 'C', 'C', 1), (10, 'A', 'A', 1), (40, 'D', 'D', 2), (20, 'B', 'B', 1)],
        )
    _start(database_handler, 30, 10)
    path = database_handler.db_path

    def connect_unordered_reversed():
        # SQLite then returns a SELECT without ORDER BY in reverse: only the
        # readers' ORDER BY keeps the animal_id order.
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA reverse_unordered_selects = ON")
        return conn

    monkeypatch.setattr(database_handler, 'connect', connect_unordered_reversed)
    everyone = database_handler.get_all_animals()
    mine = database_handler.get_animals_by_trainer(1)

    assert [a.animal_id for a in everyone] == [10, 20, 30, 40]
    assert [a.last_run is not None for a in everyone] == [True, False, True, False]
    assert [a.animal_id for a in mine] == [10, 20, 30]


def test_a_deleted_schedule_keeps_its_runs(database_handler):
    a1 = _animal(database_handler, 'A1')
    run_id = _start(database_handler, a1, schedule_id=7, name='AM water')
    database_handler.finish_schedule_run(run_id, 'stopped', {a1: (0.4, 'stopped')})

    database_handler.remove_schedule(7)

    [animal] = database_handler.get_all_animals()
    assert animal.last_run['schedule_name'] == 'AM water'
    assert animal.last_run['delivered_ml'] == 0.4


def test_a_deleted_animals_runs_stay_on_record(database_handler):
    a1 = _animal(database_handler, 'A1')
    _start(database_handler, a1)

    database_handler.remove_animal('A1')

    assert database_handler.get_all_animals() == []
    assert _rows(database_handler, "SELECT COUNT(*) FROM schedule_run_animals") == [(1,)]
    # The schedule still lists the animal (remove_animal leaves schedule_animals),
    # so Run's reader still returns its run, without a lab ID.
    assert database_handler.get_latest_runs_of_schedule(7, [a1])[a1]['lab_animal_id'] is None


def test_the_trainer_filter_still_applies(database_handler):
    mine, theirs = _animal(database_handler, 'MINE', 1), _animal(database_handler, 'THEIRS', 2)
    _start(database_handler, mine, theirs)

    [animal] = database_handler.get_animals_by_trainer(1)
    assert animal.animal_id == mine and animal.last_run['outcome'] == 'running'
    assert {a.animal_id for a in database_handler.get_animals(1, 'super')} == {mine, theirs}


def test_the_last_run_of_a_schedule_is_its_newest_run_whatever_ran_since(database_handler):
    a, b = _animal(database_handler, 'M-11'), _animal(database_handler, 'M-12')
    _record(database_handler, 7, [(a, 0.2, 'stopped'), (b, 0.2, 'stopped')])
    newest = _record(database_handler, 7, [(a, 0.41, 'stopped')])
    other = _record(database_handler, 8, [(a, 0.581, 'completed')], end_reason='completed')

    latest = database_handler.get_latest_runs_of_schedule(7, [str(a), b, 999])

    assert set(latest) == {a, b}, "ids match as numbers; an animal without a run is left out"
    assert set(latest[a]) == LAST_RUN_KEYS | {'lab_animal_id'}
    assert latest[a]['run_id'] == newest and latest[a]['delivered_ml'] == 0.41
    assert latest[a]['lab_animal_id'] == 'M-11' and latest[a]['relay_unit_id'] == a + 2
    assert latest[b]['delivered_ml'] == 0.2, "b was not in the newest run"
    # The Animals tab shows the animal's newest run of any schedule.
    assert _last_runs(database_handler)[a]['run_id'] == other


def test_reading_the_last_runs_never_raises(database_handler, monkeypatch, capsys):
    a1 = _animal(database_handler, 'A1')
    _start(database_handler, a1, schedule_id=7)
    assert set(database_handler.get_latest_runs_of_schedule(7, [a1])) == {a1}
    calls = []

    def broken():
        calls.append('connect')
        raise sqlite3.OperationalError("database is locked")

    # The repo keeps the connect it was given: patching the handler's would not reach it.
    monkeypatch.setattr(database_handler._schedule_runs, '_connect', broken)

    assert database_handler.get_latest_runs_of_schedule(7, []) == {}
    assert calls == [], "no ids, no query"
    assert database_handler.get_latest_runs_of_schedule(7, [a1]) == {}
    assert calls == ['connect']
    out = capsys.readouterr().out
    assert "Database error reading the last runs of schedule 7: database is locked" in out


@pytest.mark.parametrize(
    'read',
    [
        lambda handler: handler.get_all_animals(),
        lambda handler: handler.get_animals_by_trainer(1),
        lambda handler: handler.get_latest_runs_of_schedule(7, [1, 2]),
    ],
    ids=['all animals', 'one trainer', 'last runs of a schedule'],
)
def test_the_latest_run_is_read_through_the_index(database_handler, monkeypatch, read):
    # One index probe per animal, not a scan of every run: on each Animals tab
    # load, and when Run reads the schedule's last run.
    a1, a2 = _animal(database_handler, 'A1', 1), _animal(database_handler, 'A2', 1)
    _start(database_handler, a1, a2)

    steps = _plan_of_the_select(database_handler, monkeypatch, read)

    assert any('idx_schedule_run_animals_animal_run' in step for step in steps)
    scans = [step for step in steps if step.startswith('SCAN')]
    assert scans in ([], ['SCAN a']), "only the animals table may be scanned"
    assert not any('TEMP B-TREE' in step for step in steps), "ORDER BY a.animal_id needs no sort"


def test_an_animal_built_without_a_run_has_none():
    # Positional construction (animals_tab.add_animal) is unchanged.
    animal = Animal(None, 'A1', 'Name', 30.0, None, None, None, 'male')
    assert animal.last_run is None and animal.sex == 'male'
