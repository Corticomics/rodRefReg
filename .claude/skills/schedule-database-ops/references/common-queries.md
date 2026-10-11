# Common queries

Recipes operators and developers actually need. All go through existing
`DatabaseHandler` methods — find one before writing a new one.

## "Show me all schedules I authored"

```python
schedules = db.get_schedules_by_trainer(trainer_id)
# returns list of Schedule objects with delivery_mode, status, animal IDs
# implementation: database_handler.py:742
```

## "What did each animal get in its last schedule run?"

```python
for animal in db.get_all_animals():          # or get_animals_by_trainer(id)
    run = animal.last_run                     # None: the animal never ran
    # run['requested_ml'], run['planned_ml'], run['delivered_ml'] (None while
    # running or after a crash), run['outcome'], run['schedule_name'], ...
# Each animal's latest run of one schedule (what Run reads before it starts
# that schedule over): the same dict plus 'lab_animal_id'.
latest = db.get_latest_runs_of_schedule(schedule_id, [3, 5])  # {animal_id: dict}
# implementation: models/schedule_runs_repo.py (through DatabaseHandler)
```

How a run ended for the audit (`end_reason`, `started_by`, `stopped_by`,
`relays_confirmed_off`, `worker_exited`, `app_version`) is not in that
dict: it stays on the `schedule_runs` row. Every run stays in
`schedule_runs` / `schedule_run_animals`. For the
per-attempt ledger (`dispensing_history`), the bench tool
`tools/gravimetric_check.py daily` sums `volume_actual_ml` per animal and
day. `get_schedule_progress` is unused: it sums only the planned volume of
`completed` rows. If you genuinely need a flat `dispensing_history` query,
add a method on `DatabaseHandler` — don't run raw SQL from the UI.

## "What's running right now?"

Nothing in the database says so: `get_active_schedules()` (unused) looks
for `dispensing_status = 'active'`, which nothing sets. In the app,
`RunStopSection.job_in_progress` is true from Run to the end of the run or
Stop. The run history shows a run that has started delivering as
`outcome = 'running'` until it ends.

## "Get the instant deliveries of a schedule"

```python
rows = db.get_schedule_instant_deliveries(schedule_id)
# tuples: (animal_id, lab_animal_id, name, delivery_datetime,
#          water_volume, completed, relay_unit_id), ordered by time
# implementation: database_handler.py:1149
```

Nothing sets `completed`: RelayWorker skips deliveries whose time has
passed and records each attempt in `dispensing_history` (`completed` /
`partial` / `failed`). An instant retry after a partial delivery sends
only the rest (v1.21.0).

## "What's the calibration for cage 7?"

```python
cal = db.get_valve_calibration(cage_id=7)
# dict with pulse_width_ms, volume_per_pulse_ml, inter_pulse_interval_ms,
# topology, stddev_ml, etc., or None if the cage was never calibrated.
# implementation: database_handler.py:2053
# Is it usable on this device? utils.calibration_gate.calibration_problems([7],
#   db.get_all_valve_calibrations(), settings) -> [] when it is, or when the
#   gate does not apply (pump or continuous mode)
#   (utils.topology.calibration_is_stale for the topology check alone).
```

## "Read a system setting"

Always through `SystemController`, never directly. The controller handles
type tagging and merges secrets from `secrets.json`:

```python
num_hats = system_controller.settings.get('num_hats', 1)  # in-memory cache
# To force a fresh read from DB:
system_controller.load_settings()
```

## "Write a system setting"

```python
system_controller.save_settings({'num_hats': 4, 'theme': 'dark'})
# Only managed keys get persisted; unknown keys are dropped silently.
# Managed-key list is the union of:
#   - _create_default_settings() keys
#   - _SECRET_KEYS (routed to secrets.json instead of DB)
```

The persist path is in
[`Project/controllers/system_controller.py`](Project/controllers/system_controller.py)
`save_settings()` (L37) → `_save_database_settings()` → `_write_setting_to_db()`.

## "Authenticate a user"

```python
trainer = db.authenticate_trainer(username, password)
# returns dict {trainer_id, role} on success, None on failure
# database_handler.py:836
```

## "Add a new schedule"

```python
schedule_id = db.add_schedule(schedule)
# staggered or instant: a Schedule with delivery_mode='instant' also writes
# its schedule_instant_deliveries rows.
# implementation: database_handler.py:471 (instant rows at :508);
# edit with db.update_instant_schedule(schedule) (:1393)
```

## Cage names for the UI dropdown

```python
opts = db.get_cages_for_dropdown(num_hats=1, master_relay=16)
# returns [{'cage_id': N, 'display_name': str}, ...]
# implementation: DatabaseHandler.get_cages_for_dropdown (near the end of database_handler.py)
```

`master_relay` (relay 16 by default) is kept out of the dropdown on both
topologies: on the shared manifold it drives the master valve; on the
independent rig it is reserved and never driven, so both rigs number their
cages the same way.
