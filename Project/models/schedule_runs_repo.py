"""Schedule run history: one record per run that started delivering.

``schedule_runs`` holds one row per run, ``schedule_run_animals`` one row per
animal in it. A run opens at its first due delivery (outcome ``'running'``)
and closes once, when it ends; a run that a crash or a power cut left open
is closed as ``'interrupted'`` at the next start.

The amounts come from the delivery worker, not from here: ``requested_ml`` is
what the schedule asks of the animal, ``planned_ml`` the whole-pulse plan at
the cage's calibration, ``delivered_ml`` the volume credited to the animal
(the sum of the run's ``dispensing_history.volume_actual_ml``). Rows are never
deleted: like the ledger, they outlive the schedule and the animal.

The first domain kept out of ``database_handler.py`` under the R2 plan
(CLAUDE.md; docs/DATABASE_HANDLER_REFACTOR_DESIGN.md §11 logs it): the code
is new, so nothing moved. ``DatabaseHandler`` keeps the public methods and
delegates here; ``DatabaseHandler.create_tables`` keeps the DDL with the rest
of the schema.
"""

import sqlite3
import traceback
from datetime import datetime

from version import __version__

RUN_OUTCOMES = ('running', 'completed', 'stopped', 'incomplete', 'interrupted')
RUN_END_REASONS = ('completed', 'stopped', 'ended_short', 'interrupted')

# The last-run fields, Animal.last_run: what the Animals tab, the animal
# export and the Run warning read of a run, as the SQL that reads each one
# and its key in the dict. One list, so the SELECT and the keys cannot drift
# apart. How a run ended for the audit (end_reason, started_by, stopped_by,
# relays_confirmed_off, worker_exited, app_version) stays in schedule_runs.
_LAST_RUN_FIELDS = (
    ('r.run_id', 'run_id'),
    ('r.schedule_name', 'schedule_name'),
    ('r.delivery_mode', 'delivery_mode'),
    ('r.started_at', 'started_at'),
    ('r.ended_at', 'ended_at'),
    ('ra.outcome', 'outcome'),
    ('ra.relay_unit_id', 'relay_unit_id'),
    ('ra.requested_ml', 'requested_ml'),
    ('ra.planned_ml', 'planned_ml'),
    ('ra.delivered_ml', 'delivered_ml'),
)
LAST_RUN_COLUMNS = ', '.join(sql for sql, _ in _LAST_RUN_FIELDS)

# Each animal's latest run, joined onto a query over ``animals a``. run_id
# orders runs by start and is never reused, so "latest" does not depend on the
# clock (the Pi has no RTC). The MAX() subquery is one probe of
# idx_schedule_run_animals_animal_run per animal.
LAST_RUN_JOIN = '''
    LEFT JOIN schedule_run_animals ra
           ON ra.animal_id = a.animal_id
          AND ra.run_id = (SELECT MAX(run_id) FROM schedule_run_animals
                           WHERE animal_id = a.animal_id)
    LEFT JOIN schedule_runs r ON r.run_id = ra.run_id
'''


def last_run_from_row(values):
    """The LAST_RUN_COLUMNS part of a row as a dict, or None if the animal never ran."""
    run = dict(zip((key for _, key in _LAST_RUN_FIELDS), values))
    return None if run['run_id'] is None else run


def _now():
    return datetime.now().isoformat(timespec='seconds')


class ScheduleRunsRepo:
    """Reads and writes ``schedule_runs`` and ``schedule_run_animals``.

    ``connect`` returns a new sqlite3 connection per call
    (``DatabaseHandler.connect``), the pattern every handler method follows.
    """

    def __init__(self, connect):
        self._connect = connect

    def start_schedule_run(self, schedule_id, schedule_name, delivery_mode, started_by, animals):
        """Open the record of a run that has started delivering.

        ``animals`` holds one dict per animal in the run, with ``animal_id``,
        ``relay_unit_id``, ``requested_ml`` and ``planned_ml``. Returns the new
        run_id, or None when there is no animal or the write failed; nothing
        is written then.
        """
        if not animals:
            return None
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO schedule_runs
                    (schedule_id, schedule_name, delivery_mode, started_at,
                     started_by, app_version)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''',
                    (schedule_id, schedule_name, delivery_mode, _now(), started_by, __version__),
                )
                run_id = cursor.lastrowid
                cursor.executemany(
                    '''
                    INSERT INTO schedule_run_animals
                    (run_id, animal_id, relay_unit_id, requested_ml, planned_ml, outcome)
                    VALUES (?, ?, ?, ?, ?, 'running')
                ''',
                    [
                        (
                            run_id,
                            int(animal['animal_id']),
                            animal.get('relay_unit_id'),
                            animal['requested_ml'],
                            animal['planned_ml'],
                        )
                        for animal in animals
                    ],
                )
                conn.commit()
                return run_id
        except sqlite3.Error as e:
            print(f"Database error opening a run of schedule {schedule_id}: {e}")
            traceback.print_exc()
            return None

    def finish_schedule_run(
        self,
        run_id,
        end_reason,
        results,
        stopped_by=None,
        relays_confirmed_off=None,
        worker_exited=None,
    ):
        """Close a run record: how the run ended and what each animal got.

        ``results`` maps animal_id to ``(delivered_ml or None, outcome)``.
        ``stopped_by``, ``relays_confirmed_off`` and ``worker_exited`` describe
        an operator Stop and stay None otherwise. A run closes once: True only
        when this call closed it. False, with nothing changed, when the run is
        already closed or unknown, or when the database refused the write (a
        lock held for more than about 5 s); the run then stays open until the
        next start marks it interrupted. An animal of the run missing from
        ``results`` is closed 'incomplete' with an unknown amount, so a closed
        run never shows as running. An unknown end_reason or outcome raises
        ValueError before anything is written.
        """
        if end_reason not in RUN_END_REASONS:
            raise ValueError(f"unknown end_reason {end_reason!r}")
        rows = []
        for animal_id, (delivered_ml, outcome) in results.items():
            if outcome not in RUN_OUTCOMES or outcome == 'running':
                raise ValueError(f"unknown outcome {outcome!r}")
            rows.append((delivered_ml, outcome, run_id, int(animal_id)))
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    UPDATE schedule_runs
                    SET ended_at = ?, end_reason = ?, stopped_by = ?,
                        relays_confirmed_off = ?, worker_exited = ?
                    WHERE run_id = ? AND ended_at IS NULL
                ''',
                    (_now(), end_reason, stopped_by, relays_confirmed_off, worker_exited, run_id),
                )
                if cursor.rowcount == 0:
                    return False  # already closed, or no such run
                cursor.executemany(
                    '''
                    UPDATE schedule_run_animals SET delivered_ml = ?, outcome = ?
                    WHERE run_id = ? AND animal_id = ?
                ''',
                    rows,
                )
                cursor.execute(
                    '''
                    UPDATE schedule_run_animals SET outcome = 'incomplete'
                    WHERE run_id = ? AND outcome = 'running'
                ''',
                    (run_id,),
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Database error closing run {run_id}: {e}")
            traceback.print_exc()
            return False

    def mark_interrupted_schedule_runs(self):
        """Close every run that a crash or a power cut left open, as 'interrupted'.

        For RRR's start-up, before any run can begin; never from create_tables:
        --selftest and the bench tools build a handler while RRR may be
        running a schedule. delivered_ml stays NULL (unknown; the delivery log
        has what was credited). ended_at is the time this start found the run
        open. Returns the number of runs closed.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    UPDATE schedule_run_animals SET outcome = 'interrupted'
                    WHERE outcome = 'running' AND run_id IN
                        (SELECT run_id FROM schedule_runs WHERE ended_at IS NULL)
                '''
                )
                cursor.execute(
                    '''
                    UPDATE schedule_runs SET ended_at = ?, end_reason = 'interrupted'
                    WHERE ended_at IS NULL
                ''',
                    (_now(),),
                )
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            print(f"Database error closing interrupted runs: {e}")
            traceback.print_exc()
            return 0

    def get_latest_runs_of_schedule(self, schedule_id, animal_ids):
        """Each animal's latest run of this schedule, as ``{animal_id: dict}``.

        The dict is Animal.last_run's plus ``lab_animal_id`` (None once the
        animal is deleted). Run reads it before it starts this schedule over,
        to say what each animal got in the schedule's last run
        (docs/STOP_AND_PARTIAL_DELIVERY.md §9): a later run of another
        schedule, such as one made for the missing water, does not hide that
        run. Animals without a run of this schedule are left out; {} when the
        database cannot be read (the warning is advisory, so Run goes on
        without it).
        """
        ids = sorted({int(animal_id) for animal_id in animal_ids})
        if not ids:
            return {}
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f'''
                    SELECT ra.animal_id, a.lab_animal_id, {LAST_RUN_COLUMNS}
                    FROM schedule_run_animals ra
                    JOIN schedule_runs r ON r.run_id = ra.run_id
                    LEFT JOIN animals a ON a.animal_id = ra.animal_id
                    WHERE r.schedule_id = ?
                      AND ra.animal_id IN ({', '.join('?' * len(ids))})
                      AND ra.run_id = (SELECT MAX(sra.run_id)
                                       FROM schedule_run_animals sra
                                       JOIN schedule_runs sr ON sr.run_id = sra.run_id
                                       WHERE sra.animal_id = ra.animal_id
                                         AND sr.schedule_id = r.schedule_id)
                ''',
                    [schedule_id, *ids],
                )
                return {
                    row[0]: dict(last_run_from_row(row[2:]), lab_animal_id=row[1])
                    for row in cursor.fetchall()
                }
        except sqlite3.Error as e:
            print(f"Database error reading the last runs of schedule {schedule_id}: {e}")
            traceback.print_exc()
            return {}
