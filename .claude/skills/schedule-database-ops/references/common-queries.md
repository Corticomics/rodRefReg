# Common queries

Recipes operators and developers actually need. All go through existing
`DatabaseHandler` methods — find one before writing a new one.

## "Show me all schedules I authored"

```python
schedules = db.get_schedules_by_trainer(trainer_id)
# returns list of Schedule objects with delivery_mode, status, animal IDs
# implementation: database_handler.py:688
```

## "What's the dispensing history for a specific animal?"

There's no direct method. The canonical pattern is to pull the animal,
then walk schedules:

```python
# Higher-level query — preferred path
for sched in db.get_all_schedules():
    progress = db.get_schedule_progress(sched.schedule_id)
    # progress is a dict keyed by animal_id with delivered_volume, status
```

`get_schedule_progress` is at [`database_handler.py:1588`](Project/models/database_handler.py#L1588).
If you genuinely need a flat `dispensing_history` query, add a method on
`DatabaseHandler` — don't run raw SQL from the UI.

## "What's running right now?"

```python
active = db.get_active_schedules()
# returns rows where dispensing_status = 'active'
# implementation: database_handler.py:1066
```

## "Get the instant deliveries of a schedule"

```python
rows = db.get_schedule_instant_deliveries(schedule_id)
# tuples: (animal_id, lab_animal_id, name, delivery_datetime,
#          water_volume, completed, relay_unit_id), ordered by time
# implementation: database_handler.py:1094
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
# implementation: database_handler.py:1998
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
# database_handler.py:782
```

## "Add a new schedule"

```python
schedule_id = db.add_schedule(schedule)
# staggered or instant: a Schedule with delivery_mode='instant' also writes
# its schedule_instant_deliveries rows.
# implementation: database_handler.py:417 (instant rows at :454);
# edit with db.update_instant_schedule(schedule) (:1338)
```

## Cage names for the UI dropdown

```python
opts = db.get_cages_for_dropdown(num_hats=1, master_relay=16)
# returns [{'cage_id': N, 'display_name': str}, ...]
# database_handler.py:2348
```

`master_relay` (relay 16 by default) is kept out of the dropdown on both
topologies: on the shared manifold it drives the master valve; on the
independent rig it is reserved and never driven, so both rigs number their
cages the same way.
