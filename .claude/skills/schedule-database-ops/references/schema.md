# Schema reference

Authoritative source: [`Project/models/database_handler.py`](Project/models/database_handler.py)
`create_tables` (line 26). This file is a fast lookup; if it disagrees with
`create_tables`, the code wins.

## trainers (L102)

| col | type | notes |
|---|---|---|
| `trainer_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `trainer_name` | TEXT UNIQUE NOT NULL | login identifier |
| `salt` | TEXT NOT NULL | per-user salt |
| `password` | TEXT NOT NULL | hash (not plaintext) |
| `role` | TEXT DEFAULT 'normal' | `'normal'` or `'super'` |

## animals (L113)

| col | type | notes |
|---|---|---|
| `animal_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `lab_animal_id` | TEXT UNIQUE NOT NULL | operator-facing ID |
| `name` | TEXT NOT NULL | |
| `initial_weight` | REAL | grams |
| `last_weight` | REAL | grams |
| `last_weighted` | TEXT | ISO datetime |
| `last_watering` | TEXT | ISO datetime |
| `last_water_volume` | REAL | mL |
| `trainer_id` | INTEGER → trainers | owner |
| `sex` | TEXT CHECK IN ('male','female') | added via ALTER on existing installs |

## relay_units (L130)

| col | type | notes |
|---|---|---|
| `relay_unit_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `relay_ids` | TEXT NOT NULL | JSON list of physical relay numbers |

## schedules (L138)

| col | type | notes |
|---|---|---|
| `schedule_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `name` | TEXT NOT NULL | |
| `water_volume` | REAL NOT NULL | mL — total per animal across schedule |
| `start_time` | TEXT NOT NULL | ISO datetime |
| `end_time` | TEXT NOT NULL | ISO datetime |
| `created_by` | INTEGER → trainers | author |
| `is_super_user` | BOOLEAN DEFAULT 0 | |
| `delivery_mode` | TEXT DEFAULT 'staggered' | `'staggered'` or `'instant'` |
| `dispensing_status` | TEXT DEFAULT 'pending' | `'pending'` / `'active'` / `'completed'` / `'failed'` |

## schedule_animals (L154)

Junction. PRIMARY KEY (schedule_id, animal_id).

| col | type | notes |
|---|---|---|
| `schedule_id` | INTEGER → schedules | |
| `animal_id` | INTEGER → animals | |
| `relay_unit_id` | INTEGER → relay_units | nullable; set at execution time |

## schedule_desired_outputs (L167, staggered mode)

Per-animal target. PRIMARY KEY (schedule_id, animal_id).

| col | type | notes |
|---|---|---|
| `desired_output` | REAL NOT NULL | mL total |
| `interval_minutes` | INTEGER DEFAULT 60 | between deliveries |
| `volume_per_interval` | REAL | computed = desired_output / N intervals |

## schedule_instant_deliveries (L181, instant mode)

| col | type | notes |
|---|---|---|
| `delivery_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `delivery_datetime` | TEXT NOT NULL | scheduled wallclock |
| `water_volume` | REAL NOT NULL | mL |
| `relay_unit_id` | INTEGER → relay_units | nullable |
| `completed` | BOOLEAN DEFAULT 0 | never set: no code has ever written it (`mark_instant_completed`, removed in v1.14.1, updated `schedule_time_instants`, a table that does not exist); attempts are in `dispensing_history` |

## schedule_staggered_windows (L209)

Per-window state for staggered mode.

| col | type | notes |
|---|---|---|
| `window_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `start_time` / `end_time` | TEXT | ISO |
| `target_volume` | REAL NOT NULL | mL |
| `delivered_volume` | REAL DEFAULT 0 | running total |
| `status` | TEXT DEFAULT 'pending' | `'pending'` / `'active'` / `'completed'` |

## cycle_tracking (L225)

Per-cycle progress within a staggered window.

| col | type | notes |
|---|---|---|
| `tracking_id` | INTEGER PRIMARY KEY | |
| `cycle_index` | INTEGER NOT NULL | 0-based |
| `target_volume` / `delivered_volume` | REAL | |
| `status` | TEXT DEFAULT 'pending' | |
| `completed_at` | TEXT | ISO when status flipped to completed |

## dispensing_history (L39)

Append-only audit log; one row per delivery attempt, failed ones included.
Written by `DatabaseHandler.log_delivery`. On an existing install the
columns after `status` are added by the `PRAGMA table_info` checks at L66-L98.

| col | type | notes |
|---|---|---|
| `history_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `schedule_id` | INTEGER NOT NULL → schedules | |
| `animal_id` | INTEGER NOT NULL → animals | |
| `relay_unit_id` | INTEGER NOT NULL → relay_units | |
| `timestamp` | TEXT NOT NULL | ISO |
| `volume_dispensed` | REAL NOT NULL | mL; the PLANNED volume (for a pulse delivery, whole pulses × mL/pulse) on a `completed` row, else 0 |
| `status` | TEXT NOT NULL | `'completed'`, `'partial'` (some pulses got through before a failure), `'failed'`, or `'sensor_failure'` (the part of a staggered window's dose never delivered) |
| `cycle_index` | INTEGER | nullable; not written by current code |
| `volume_actual_ml` | REAL | mL the hardware reports it actually dispensed, the figure to trust (v1.17.0; NULL = unknown) |
| `pulses_fired` | INTEGER | pulses the valve actually fired (v1.17.0) |
| `volume_per_pulse_ml` | REAL | the calibration in force (v1.17.0) |
| `volume_requested_ml` | REAL | the dose asked for, before whole-pulse rounding; on a `sensor_failure` row, the undelivered remainder (v1.21.0) |
| `dose_rounding` | TEXT | `'nearest'` or `'up'` (v1.21.0) |
| `topology` | TEXT | valve topology the run used (v1.21.0) |
| `delivery_mode` | TEXT | schedule mode, `'instant'` or `'staggered'`; kept because the schedule can be deleted (v1.21.0) |
| `app_version` | TEXT | RRR version that wrote the row (v1.21.0) |
| `calibration_id` | INTEGER | the `valve_calibration` row used (v1.21.0) |
| `pulse_width_ms` / `inter_pulse_interval_ms` | INTEGER | timing the delivery ran with (v1.21.0) |
| `duration_s` | REAL | how long the delivery took (v1.21.0) |

The v1.21.0 context columns are NULL on older rows ("not recorded"). The
`sensor_failure` row carries only `topology`, `delivery_mode` and
`app_version` of that context.

## logs (L197)

| col | type | notes |
|---|---|---|
| `log_id` | INTEGER PK AUTOINCREMENT | |
| `timestamp` / `action` / `details` | TEXT | |
| `super_user_id` | INTEGER → trainers | |

## system_settings (L243) — Phase 2.5a typed K/V

| col | type | notes |
|---|---|---|
| `setting_key` | TEXT PRIMARY KEY | |
| `setting_value` | TEXT NOT NULL | stringified value |
| `setting_type` | TEXT NOT NULL | `'bool'` / `'int'` / `'float'` / `'str'` / `'json'` |
| `updated_at` | TEXT NOT NULL | ISO |

## valve_calibration (L253) and valve_calibration_history (L273)

Per-cage pulse-to-volume calibration. The non-`_history` table holds the
current calibration; every save also appends to history.

| col | type | notes |
|---|---|---|
| `calibration_id` | INTEGER PRIMARY KEY AUTOINCREMENT | `history_id` in the history table |
| `cage_id` | INTEGER UNIQUE | live table; not unique in history |
| `relay_id` | INTEGER | physical relay |
| `pulse_width_ms` | INTEGER | pulse duration |
| `volume_per_pulse_ml` | REAL | empirical |
| `stddev_ml` / `coefficient_of_variation_pct` | REAL | quality metrics |
| `num_samples` | INTEGER | calibration trial count |
| `calibration_date` | TEXT | ISO |
| `calibrated_by` | INTEGER → trainers | |
| `notes` | TEXT | |
| `inter_pulse_interval_ms` | INTEGER | rest between pulses the calibration used (v1.16.0; NULL = legacy timing) |
| `topology` | TEXT | valve topology measured under (v1.21.0; NULL = before it was recorded, read as `shared_manifold`) |

## cage_names (L296)

| col | type | notes |
|---|---|---|
| `cage_id` | INTEGER PRIMARY KEY | |
| `relay_id` | INTEGER NOT NULL | physical |
| `name` | TEXT NOT NULL DEFAULT '' | operator-friendly |
| `description` | TEXT DEFAULT '' | |
| `created_at` / `updated_at` | TEXT NOT NULL | ISO |
