"""Instant-delivery create + update round-trips (Qt-free).

Regression for the bug where instant schedules wrote to a non-existent
``schedule_time_instants`` table (and so delivered nothing): create now writes
``schedule_instant_deliveries`` — the table the runtime reads — and
``update_instant_schedule`` replaces those rows transactionally.
"""

from __future__ import annotations

from datetime import datetime

from models.database_handler import DatabaseHandler  # noqa: F401 (fixture import path)
from models.Schedule import Schedule


def _instant(name, deliveries, schedule_id=None) -> Schedule:
    """Build an instant Schedule. ``deliveries`` is ``[(animal_id, cage, vol, datetime)]``."""
    total = sum(v for _, _, v, _ in deliveries)
    times = [d for *_, d in deliveries]
    sched = Schedule(
        schedule_id=schedule_id,
        name=name,
        water_volume=total,
        start_time=min(times).isoformat(),
        end_time=max(times).isoformat(),
        created_by=1,
        is_super_user=0,
        delivery_mode="instant",
    )
    for animal_id, cage, vol, when in deliveries:
        sched.add_animal(animal_id, cage, vol)
        sched.add_instant_delivery(animal_id, when.isoformat(), vol, cage)
    return sched


def _rows(database_handler, schedule_id):
    """Read schedule_instant_deliveries directly (avoids the animals JOIN)."""
    with database_handler.connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT animal_id, delivery_datetime, water_volume, relay_unit_id
            FROM schedule_instant_deliveries
            WHERE schedule_id = ?
            ORDER BY animal_id
            """,
            (schedule_id,),
        )
        return cur.fetchall()


def test_add_schedule_writes_instant_delivery_rows(database_handler):
    d1 = datetime(2026, 6, 5, 9, 0, 0)
    d2 = datetime(2026, 6, 5, 10, 30, 0)
    sid = database_handler.add_schedule(_instant("inst", [(1, 1, 1.0, d1), (2, 2, 2.0, d2)]))
    assert sid is not None

    rows = _rows(database_handler, sid)
    assert rows == [
        (1, d1.isoformat(), 1.0, 1),
        (2, d2.isoformat(), 2.0, 2),
    ]


def _seed_animal(database_handler, animal_id, lab_id, name):
    with database_handler.connect() as conn:
        conn.execute(
            "INSERT INTO animals (animal_id, lab_animal_id, name) VALUES (?, ?, ?)",
            (animal_id, lab_id, name),
        )
        conn.commit()


def test_get_schedule_instant_deliveries_returns_joined_rows(database_handler):
    """The runtime read that run_stop_section / schedule_drop_area call to
    execute or drop an instant schedule.

    Regression for v1.14.1: this LIVE method was wrongly removed with the dead
    schedule_time_instants cluster, so pressing Run on an instant schedule raised
    'DatabaseHandler has no attribute get_schedule_instant_deliveries'. Restored
    in v1.14.2. (It JOINs animals, so animals must exist.)
    """
    _seed_animal(database_handler, 1, "A1", "Mouse A")
    _seed_animal(database_handler, 2, "A2", "Mouse B")
    d1 = datetime(2026, 6, 9, 9, 0, 0)
    d2 = datetime(2026, 6, 9, 10, 0, 0)
    sid = database_handler.add_schedule(_instant("inst", [(1, 1, 1.0, d1), (2, 2, 2.0, d2)]))

    rows = database_handler.get_schedule_instant_deliveries(sid)
    # (animal_id, lab_animal_id, name, delivery_datetime, water_volume, completed, relay_unit_id)
    assert len(rows) == 2
    assert rows[0][0] == 1 and rows[0][1] == "A1" and rows[0][3] == d1.isoformat()
    assert rows[0][4] == 1.0 and rows[0][6] == 1
    assert rows[1][0] == 2 and rows[1][1] == "A2" and rows[1][4] == 2.0


def test_loaded_instant_schedule_reports_its_animals(database_handler):
    """Regression: the card showed "0 animals" for instant schedules because
    get_all_schedules / get_schedules_by_trainer didn't populate .animals for
    instant mode (only instant_deliveries). The roster must now be filled."""
    d1 = datetime(2026, 6, 5, 9, 0, 0)
    d2 = datetime(2026, 6, 5, 10, 0, 0)
    sid = database_handler.add_schedule(_instant("inst", [(1, 1, 1.0, d1), (2, 2, 2.0, d2)]))

    loaded = next(s for s in database_handler.get_all_schedules() if s.schedule_id == sid)
    assert sorted(loaded.animals) == [1, 2]
    assert loaded.relay_unit_assignments == {"1": 1, "2": 2}

    by_trainer = next(
        s for s in database_handler.get_schedules_by_trainer(1) if s.schedule_id == sid
    )
    assert sorted(by_trainer.animals) == [1, 2]


def test_update_instant_schedule_replaces_rows(database_handler):
    d1 = datetime(2026, 6, 5, 9, 0, 0)
    sid = database_handler.add_schedule(_instant("inst", [(1, 1, 1.0, d1)]))

    # Edit: new delivery time, volume, and cage reassignment 1 -> 3.
    nd = datetime(2026, 6, 6, 14, 15, 0)
    updated = _instant("inst-edited", [(1, 3, 2.5, nd)], schedule_id=sid)
    assert database_handler.update_instant_schedule(updated) is True

    assert _rows(database_handler, sid) == [(1, nd.isoformat(), 2.5, 3)]

    # Parent row + animal/cage assignment also updated.
    details = database_handler.get_schedule_details(sid)[0]
    assert details["relay_unit_assignments"] == {"1": 3}
    with database_handler.connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, delivery_mode FROM schedules WHERE schedule_id = ?", (sid,))
        assert cur.fetchone() == ("inst-edited", "instant")
