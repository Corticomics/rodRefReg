"""Regression test for staggered-schedule datetime parsing.

Bug (found on the Pi, v1.8.4): add_staggered_schedule parsed
schedule.start_time / end_time with
    datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")
The %f token REQUIRES fractional seconds, but datetime.isoformat()
OMITS them when microseconds == 0. So a start time that happened to
land on a whole second (e.g. '2026-05-28T18:00:14') made schedule
creation raise ValueError and silently return None — the wizard's
Finish "did nothing". Times with nonzero microseconds worked, which
is why it looked intermittent.

Fix: parse with datetime.fromisoformat (the inverse of isoformat),
which accepts both with- and without-microsecond ISO strings.

Qt-free: DatabaseHandler imports no PyQt5, so this runs everywhere.
"""

from __future__ import annotations

from datetime import datetime

from models.database_handler import DatabaseHandler
from models.Schedule import Schedule


def _staggered_schedule(start_iso: str, end_iso: str) -> Schedule:
    sched = Schedule(
        schedule_id=None,
        name="regression",
        water_volume=1.0,
        start_time=start_iso,
        end_time=end_iso,
        created_by=1,
        is_super_user=0,
        delivery_mode="staggered",
    )
    sched.add_animal(animal_id=1, relay_unit_id=1, desired_volume=1.0)
    return sched


def test_whole_second_start_time_creates_schedule(database_handler):
    """A start time on a whole second (no microseconds) must succeed.

    This is the exact shape that failed: isoformat() of a datetime whose
    microsecond is 0 yields 'YYYY-MM-DDTHH:MM:SS' with no '.ffffff'.
    """
    start = datetime(2026, 5, 28, 18, 0, 14)         # microsecond == 0
    end = datetime(2026, 5, 28, 18, 3, 14)
    assert start.isoformat() == "2026-05-28T18:00:14"  # no fractional part

    schedule_id = database_handler.add_staggered_schedule(
        _staggered_schedule(start.isoformat(), end.isoformat())
    )
    assert schedule_id is not None


def test_microsecond_start_time_still_works(database_handler):
    """The previously-working case (nonzero microseconds) must still work."""
    start = datetime(2026, 5, 28, 18, 0, 14, 549000)   # has microseconds
    end = datetime(2026, 5, 28, 18, 3, 14, 549000)
    assert "." in start.isoformat()                    # fractional part present

    schedule_id = database_handler.add_staggered_schedule(
        _staggered_schedule(start.isoformat(), end.isoformat())
    )
    assert schedule_id is not None
