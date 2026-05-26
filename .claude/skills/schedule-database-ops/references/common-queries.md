# Common queries

Recipes operators and developers actually need. All go through existing
`DatabaseHandler` methods — find one before writing a new one.

## "Show me all schedules I authored"

```python
schedules = db.get_schedules_by_trainer(trainer_id)
# returns list of Schedule objects with delivery_mode, status, animal IDs
# implementation: database_handler.py:631
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

`get_schedule_progress` is at [`database_handler.py:1320`](Project/models/database_handler.py#L1320).
If you genuinely need a flat `dispensing_history` query, add a method on
`DatabaseHandler` — don't run raw SQL from the UI.

## "What's running right now?"

```python
active = db.get_active_schedules()
# returns rows where dispensing_status = 'active'
# implementation: database_handler.py:960
```

## "Get all pending instant deliveries"

```python
pending = db.get_pending_schedule_instants(schedule_id=None)
# schedule_id=None returns across all schedules
# rows have delivery_id, animal_id, delivery_datetime, water_volume,
# relay_unit_id, completed (always 0 here)
# implementation: database_handler.py:1005
```

After firing, mark complete:

```python
db.mark_instant_completed(instant_id, volume_dispensed)
# database_handler.py:1036
```

## "What's the calibration for cage 7?"

```python
cal = db.get_valve_calibration(cage_id=7)
# returns dict with pulse_width_ms, volume_per_pulse_ml, stddev, etc.
# or None if cage was never calibrated.
# implementation: database_handler.py:1618
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
# returns dict {trainer_id, trainer_name, role} on success, None on failure
# database_handler.py:704
```

## "Add a new schedule"

```python
schedule_id = db.add_schedule(schedule)        # staggered (default)
# or for instant mode:
schedule_id = db.add_instant_schedule(schedule_name, created_by,
                                       is_super_user, deliveries)
# implementations: database_handler.py:349 and :1071
```

## Cage names for the UI dropdown

```python
opts = db.get_cages_for_dropdown(num_hats=1, master_relay=16)
# returns [{'cage_id': N, 'display_name': str}, ...]
# database_handler.py:1932
```

`master_relay` excludes the master valve from the dropdown so operators
can't accidentally assign animals to it.
