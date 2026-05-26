# Schema reference

Authoritative source: [`Project/models/database_handler.py`](Project/models/database_handler.py)
`create_tables` (line 24). This file is a fast lookup; if it disagrees with
`create_tables`, the code wins.

## trainers (L60)

| col | type | notes |
|---|---|---|
| `trainer_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `trainer_name` | TEXT UNIQUE NOT NULL | login identifier |
| `salt` | TEXT NOT NULL | per-user salt |
| `password` | TEXT NOT NULL | hash (not plaintext) |
| `role` | TEXT DEFAULT 'normal' | `'normal'` or `'super'` |

## animals (L71)

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

## relay_units (L88)

| col | type | notes |
|---|---|---|
| `relay_unit_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `relay_ids` | TEXT NOT NULL | JSON list of physical relay numbers |

## schedules (L96)

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

## schedule_animals (L112)

Junction. PRIMARY KEY (schedule_id, animal_id).

| col | type | notes |
|---|---|---|
| `schedule_id` | INTEGER → schedules | |
| `animal_id` | INTEGER → animals | |
| `relay_unit_id` | INTEGER → relay_units | nullable; set at execution time |

## schedule_desired_outputs (L125, staggered mode)

Per-animal target. PRIMARY KEY (schedule_id, animal_id).

| col | type | notes |
|---|---|---|
| `desired_output` | REAL NOT NULL | mL total |
| `interval_minutes` | INTEGER DEFAULT 60 | between deliveries |
| `volume_per_interval` | REAL | computed = desired_output / N intervals |

## schedule_instant_deliveries (L139, instant mode)

| col | type | notes |
|---|---|---|
| `delivery_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `delivery_datetime` | TEXT NOT NULL | scheduled wallclock |
| `water_volume` | REAL NOT NULL | mL |
| `relay_unit_id` | INTEGER → relay_units | nullable |
| `completed` | BOOLEAN DEFAULT 0 | flipped by `mark_instant_completed` |

## schedule_staggered_windows (L167)

Per-window state for staggered mode.

| col | type | notes |
|---|---|---|
| `window_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `start_time` / `end_time` | TEXT | ISO |
| `target_volume` | REAL NOT NULL | mL |
| `delivered_volume` | REAL DEFAULT 0 | running total |
| `status` | TEXT DEFAULT 'pending' | `'pending'` / `'active'` / `'completed'` |

## cycle_tracking (L183)

Per-cycle progress within a staggered window.

| col | type | notes |
|---|---|---|
| `tracking_id` | INTEGER PRIMARY KEY | |
| `cycle_index` | INTEGER NOT NULL | 0-based |
| `target_volume` / `delivered_volume` | REAL | |
| `status` | TEXT DEFAULT 'pending' | |
| `completed_at` | TEXT | ISO when status flipped to completed |

## dispensing_history (L37)

Append-only audit log; one row per relay click that actually delivered.

| col | type | notes |
|---|---|---|
| `history_id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `timestamp` | TEXT NOT NULL | ISO |
| `volume_dispensed` | REAL NOT NULL | mL |
| `status` | TEXT NOT NULL | typically `'completed'` or error code |
| `cycle_index` | INTEGER | nullable; populated for staggered cycles |

## logs (L155)

| col | type | notes |
|---|---|---|
| `log_id` | INTEGER PK AUTOINCREMENT | |
| `timestamp` / `action` / `details` | TEXT | |
| `super_user_id` | INTEGER → trainers | |

## system_settings (L201) — Phase 2.5a typed K/V

| col | type | notes |
|---|---|---|
| `setting_key` | TEXT PRIMARY KEY | |
| `setting_value` | TEXT NOT NULL | stringified value |
| `setting_type` | TEXT NOT NULL | `'bool'` / `'int'` / `'float'` / `'str'` / `'json'` |
| `updated_at` | TEXT NOT NULL | ISO |

## valve_calibration (L211) and valve_calibration_history (L229)

Per-cage pulse-to-volume calibration. The non-`_history` table holds the
current calibration; every save also appends to history.

| col | type | notes |
|---|---|---|
| `cage_id` | INTEGER UNIQUE | live table; not unique in history |
| `relay_id` | INTEGER | physical relay |
| `pulse_width_ms` | INTEGER | pulse duration |
| `volume_per_pulse_ml` | REAL | empirical |
| `stddev_ml` / `coefficient_of_variation_pct` | REAL | quality metrics |
| `num_samples` | INTEGER | calibration trial count |
| `calibration_date` | TEXT | ISO |
| `calibrated_by` | INTEGER → trainers | |
| `notes` | TEXT | |

## cage_names (L250)

| col | type | notes |
|---|---|---|
| `cage_id` | INTEGER PRIMARY KEY | |
| `relay_id` | INTEGER NOT NULL | physical |
| `name` | TEXT NOT NULL DEFAULT '' | operator-friendly |
| `description` | TEXT DEFAULT '' | |
| `created_at` / `updated_at` | TEXT NOT NULL | ISO |
