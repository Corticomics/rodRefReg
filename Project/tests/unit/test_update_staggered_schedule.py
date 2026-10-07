"""Regression tests for editing (updating) an existing staggered schedule.

These guard the bugs that made the old edit-schedule dialog non-functional:

1. Per-animal volume edits wrote a column named ``desired_water_output``; the
   real column is ``desired_output`` — so edits raised OperationalError, were
   swallowed, and never saved.
2. The edit path never touched ``schedule_staggered_windows`` (the table the
   delivery engine reads) nor cage reassignment in ``schedule_animals`` — so a
   "saved" edit did not reach the runtime.

``update_staggered_schedule`` replaces all child rows transactionally; this test
asserts volumes, cage assignments, bounds, and the staggered windows all
persist. Qt-free: DatabaseHandler imports no PyQt5, so it runs everywhere.
"""

from __future__ import annotations

from datetime import datetime

from models.database_handler import DatabaseHandler  # noqa: F401 (fixture import path)
from models.Schedule import Schedule


def _staggered(name, start_iso, end_iso, animals, schedule_id=None) -> Schedule:
    """Build a staggered Schedule. ``animals`` is ``[(animal_id, cage_id, volume)]``."""
    total = sum(v for _, _, v in animals)
    sched = Schedule(
        schedule_id=schedule_id,
        name=name,
        water_volume=total,
        start_time=start_iso,
        end_time=end_iso,
        created_by=1,
        is_super_user=0,
        delivery_mode="staggered",
    )
    for animal_id, cage_id, volume in animals:
        sched.add_animal(animal_id=animal_id, relay_unit_id=cage_id, desired_volume=volume)
    return sched


def _windows(database_handler, schedule_id):
    with database_handler.connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT animal_id, start_time, end_time, target_volume
            FROM schedule_staggered_windows
            WHERE schedule_id = ?
            ORDER BY animal_id
            """,
            (schedule_id,),
        )
        return cur.fetchall()


def _schedule_name(database_handler, schedule_id):
    with database_handler.connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM schedules WHERE schedule_id = ?", (schedule_id,))
        row = cur.fetchone()
        return row[0] if row else None


def test_update_persists_volumes_cages_times_and_windows(database_handler):
    start = datetime(2026, 6, 1, 9, 0, 0)
    end = datetime(2026, 6, 1, 10, 0, 0)
    sid = database_handler.add_staggered_schedule(
        _staggered("orig", start.isoformat(), end.isoformat(), [(1, 1, 1.0), (2, 2, 2.0)])
    )
    assert sid is not None

    # Edit: rename, reassign cages (1→3, 2→4), change volumes, shift the window.
    new_start = datetime(2026, 6, 2, 14, 0, 0)
    new_end = datetime(2026, 6, 2, 15, 30, 0)
    updated = _staggered(
        "edited",
        new_start.isoformat(),
        new_end.isoformat(),
        [(1, 3, 1.5), (2, 4, 2.5)],
        schedule_id=sid,
    )
    assert database_handler.update_staggered_schedule(updated) is True

    details = database_handler.get_schedule_details(sid)[0]

    # Per-animal volumes persisted (regression for the desired_output column bug)
    assert details["desired_water_outputs"] == {"1": 1.5, "2": 2.5}
    # Cage reassignment persisted
    assert details["relay_unit_assignments"] == {"1": 3, "2": 4}
    # Bounds + total volume persisted
    assert details["water_volume"] == 4.0
    assert details["start_time"] == new_start.isoformat()
    assert details["end_time"] == new_end.isoformat()
    assert _schedule_name(database_handler, sid) == "edited"

    # The runtime windows were replaced, not left stale.
    windows = _windows(database_handler, sid)
    assert len(windows) == 2
    for animal_id, w_start, w_end, target in windows:
        assert w_start == new_start.isoformat()
        assert w_end == new_end.isoformat()
        assert target == (1.5 if animal_id == 1 else 2.5)


def test_update_can_drop_an_animal(database_handler):
    start = datetime(2026, 6, 1, 9, 0, 0)
    end = datetime(2026, 6, 1, 10, 0, 0)
    sid = database_handler.add_staggered_schedule(
        _staggered("orig", start.isoformat(), end.isoformat(), [(1, 1, 1.0), (2, 2, 2.0)])
    )

    # Edit down to a single animal — child rows for the removed animal must go.
    updated = _staggered(
        "one-animal", start.isoformat(), end.isoformat(), [(1, 1, 1.0)], schedule_id=sid
    )
    assert database_handler.update_staggered_schedule(updated) is True

    details = database_handler.get_schedule_details(sid)[0]
    assert details["animal_ids"] == [1]
    assert details["desired_water_outputs"] == {"1": 1.0}
    assert len(_windows(database_handler, sid)) == 1
