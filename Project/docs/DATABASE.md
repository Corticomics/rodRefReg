# RRR Database Reference

The runtime data store is a single SQLite file. On installed devices it lives
at `~/rrr/shared/data/rrr_database.db`; on a developer clone it falls back to
`Project/rrr_database.db` (both resolved through
[`utils.paths.database_path()`](../utils/paths.py)). `DatabaseHandler`
([`Project/models/database_handler.py`](../models/database_handler.py))
owns the whole schema and is the only entry point to it: the run-history
queries live in
[`Project/models/schedule_runs_repo.py`](../models/schedule_runs_repo.py)
behind it, and no other module issues SQL directly.

This document is the single source of truth for the schema, intended for
developers extending the app. **If you change the schema, update this file in
the same commit.**

---

## 1. Schema (ERD)

GitHub renders the diagram below natively. Key columns only — see §2 for the
full DDL.

```mermaid
erDiagram
    TRAINERS ||--o{ ANIMALS                       : owns
    TRAINERS ||--o{ SCHEDULES                     : creates
    TRAINERS ||--o{ LOGS                          : performs
    TRAINERS ||--o{ VALVE_CALIBRATION             : calibrates
    TRAINERS ||--o{ VALVE_CALIBRATION_HISTORY     : calibrates

    SCHEDULES ||--o{ SCHEDULE_ANIMALS             : "has rows"
    ANIMALS   ||--o{ SCHEDULE_ANIMALS             : "is in"
    RELAY_UNITS ||--o{ SCHEDULE_ANIMALS           : "assigned to"

    SCHEDULES ||--o{ SCHEDULE_DESIRED_OUTPUTS     : ""
    ANIMALS   ||--o{ SCHEDULE_DESIRED_OUTPUTS     : ""

    SCHEDULES ||--o{ SCHEDULE_INSTANT_DELIVERIES  : ""
    ANIMALS   ||--o{ SCHEDULE_INSTANT_DELIVERIES  : ""
    RELAY_UNITS ||--o{ SCHEDULE_INSTANT_DELIVERIES : ""

    SCHEDULES ||--o{ SCHEDULE_STAGGERED_WINDOWS   : ""
    ANIMALS   ||--o{ SCHEDULE_STAGGERED_WINDOWS   : ""

    SCHEDULES ||--o{ CYCLE_TRACKING               : ""
    ANIMALS   ||--o{ CYCLE_TRACKING               : ""

    SCHEDULES ||--o{ DISPENSING_HISTORY           : ""
    ANIMALS   ||--o{ DISPENSING_HISTORY           : ""
    RELAY_UNITS ||--o{ DISPENSING_HISTORY         : ""

    TRAINERS      ||--o{ SCHEDULE_RUNS            : "starts / stops"
    SCHEDULE_RUNS ||--|{ SCHEDULE_RUN_ANIMALS     : "one row per animal"

    TRAINERS {
        int  trainer_id    PK
        text trainer_name  UK
        text salt
        text password
        text role
    }
    ANIMALS {
        int  animal_id      PK
        text lab_animal_id  UK
        text name
        int  trainer_id     FK
        real last_weight
        text last_watering
        text sex
    }
    RELAY_UNITS {
        int  relay_unit_id  PK
        text relay_ids
    }
    SCHEDULES {
        int  schedule_id        PK
        text name
        real water_volume
        text start_time
        text end_time
        int  created_by         FK
        bool is_super_user
        text delivery_mode
        text dispensing_status
    }
    SCHEDULE_ANIMALS {
        int schedule_id    PK_FK
        int animal_id      PK_FK
        int relay_unit_id  FK
    }
    SCHEDULE_DESIRED_OUTPUTS {
        int  schedule_id         PK_FK
        int  animal_id           PK_FK
        real desired_output
        int  interval_minutes
        real volume_per_interval
    }
    SCHEDULE_INSTANT_DELIVERIES {
        int  delivery_id        PK
        int  schedule_id        FK
        int  animal_id          FK
        int  relay_unit_id      FK
        text delivery_datetime
        real water_volume
        bool completed
    }
    SCHEDULE_STAGGERED_WINDOWS {
        int  window_id        PK
        int  schedule_id      FK
        int  animal_id        FK
        text start_time
        text end_time
        real target_volume
        real delivered_volume
        text status
    }
    CYCLE_TRACKING {
        int  tracking_id      PK
        int  schedule_id      FK
        int  animal_id        FK
        int  cycle_index
        text start_time
        text end_time
        real target_volume
        real delivered_volume
        text status
        text completed_at
    }
    DISPENSING_HISTORY {
        int  history_id       PK
        int  schedule_id      FK
        int  animal_id        FK
        int  relay_unit_id    FK
        text timestamp
        real volume_dispensed
        text status
        int  cycle_index
    }
    SCHEDULE_RUNS {
        int  run_id         PK
        int  schedule_id
        text schedule_name
        text delivery_mode
        text started_at
        text ended_at
        text end_reason
        int  started_by     FK
        int  stopped_by     FK
        int  relays_confirmed_off
        int  worker_exited
        text app_version
    }
    SCHEDULE_RUN_ANIMALS {
        int  run_id         PK_FK
        int  animal_id      PK
        int  relay_unit_id
        real requested_ml
        real planned_ml
        real delivered_ml
        text outcome
    }
    LOGS {
        int  log_id         PK
        text timestamp
        text action
        int  super_user_id  FK
        text details
    }
    SYSTEM_SETTINGS {
        text setting_key    PK
        text setting_value
        text setting_type
        text updated_at
    }
    VALVE_CALIBRATION {
        int  calibration_id      PK
        int  cage_id             UK
        int  relay_id
        int  pulse_width_ms
        real volume_per_pulse_ml
        int  num_samples
        text calibration_date
        int  calibrated_by       FK
        int  inter_pulse_interval_ms
        text topology
    }
    VALVE_CALIBRATION_HISTORY {
        int  history_id          PK
        int  cage_id
        int  relay_id
        int  pulse_width_ms
        real volume_per_pulse_ml
        int  num_samples
        text calibration_date
        int  calibrated_by       FK
        int  inter_pulse_interval_ms
        text topology
    }
    CAGE_NAMES {
        int  cage_id     PK
        int  relay_id
        text name
        text description
        text created_at
        text updated_at
    }
```

**Three orphan tables** are intentionally not connected by FKs:

- **`system_settings`** — a key/value store; the canonical home for app
  preferences since Phase 2.5a (v1.5.0). See §6.
- **`cage_names`** — `relay_id` is stored as a plain `INTEGER`, *not* a FK to
  `relay_units`. The application assigns the relay-to-cage mapping by
  convention.
- **`valve_calibration_history`** — mirrors `valve_calibration` and is written
  to on every recalibration (audit trail). There is no FK between the two.

**Run history keeps copies, not links.** `schedule_runs.schedule_id`,
`schedule_run_animals.animal_id` and `schedule_run_animals.relay_unit_id`
name the schedule, animal and relay unit (the cage in solenoid mode) of a
past run but are deliberately not foreign keys: a run's record outlives the
schedule and the animal, so
deleting either leaves its runs in place, as it leaves `dispensing_history`
rows. The run copies the schedule's name and mode for that reason.

**Important caveat — FKs are declared but not enforced.** The database is
opened without `PRAGMA foreign_keys = ON`, so the FK declarations above are
*documentation*, not runtime constraints. Deleting a row referenced elsewhere
will succeed and leave dangling IDs. See §7.

---

## 2. Table reference (verbatim DDL)

All DDL lives inside
[`DatabaseHandler.create_tables()`](../models/database_handler.py)
and runs idempotently on every startup (`CREATE TABLE IF NOT EXISTS`
everywhere except `dispensing_history`, which is created only when
`PRAGMA table_info` finds it absent and otherwise upgraded column by column;
the inline migrations are listed in §4).

### Auth & users

```sql
CREATE TABLE IF NOT EXISTS trainers (
    trainer_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_name TEXT    UNIQUE NOT NULL,
    salt         TEXT    NOT NULL,
    password     TEXT    NOT NULL,           -- SHA-256(salt + plaintext)
    role         TEXT    DEFAULT 'normal'    -- 'normal' | 'super'
);
```

### Animals & cages

```sql
CREATE TABLE IF NOT EXISTS animals (
    animal_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_animal_id     TEXT    UNIQUE NOT NULL,
    name              TEXT    NOT NULL,
    initial_weight    REAL,
    last_weight       REAL,
    last_weighted     TEXT,
    last_watering     TEXT,
    last_water_volume REAL,
    trainer_id        INTEGER,
    sex               TEXT CHECK(sex IN ('male', 'female')) DEFAULT NULL,
    FOREIGN KEY(trainer_id) REFERENCES trainers(trainer_id)
);

CREATE TABLE IF NOT EXISTS cage_names (
    cage_id     INTEGER PRIMARY KEY,           -- application-assigned, not AUTOINCREMENT
    relay_id    INTEGER NOT NULL,              -- not a FK; see §1
    name        TEXT    NOT NULL DEFAULT '',
    description TEXT    DEFAULT '',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
```

### Hardware

```sql
CREATE TABLE IF NOT EXISTS relay_units (
    relay_unit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    relay_ids     TEXT    NOT NULL             -- comma-delimited integer list
);
```

### Scheduling

```sql
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL,
    water_volume      REAL    NOT NULL,
    start_time        TEXT    NOT NULL,
    end_time          TEXT    NOT NULL,
    created_by        INTEGER NOT NULL,
    is_super_user     BOOLEAN DEFAULT 0,
    delivery_mode     TEXT    DEFAULT 'staggered',  -- 'staggered' | 'instant'
    dispensing_status TEXT    DEFAULT 'pending',
    FOREIGN KEY(created_by) REFERENCES trainers(trainer_id)
);

CREATE TABLE IF NOT EXISTS schedule_animals (
    schedule_id   INTEGER NOT NULL,
    animal_id     INTEGER NOT NULL,
    relay_unit_id INTEGER,
    PRIMARY KEY (schedule_id, animal_id),
    FOREIGN KEY(schedule_id)   REFERENCES schedules(schedule_id),
    FOREIGN KEY(animal_id)     REFERENCES animals(animal_id),
    FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id)
);

CREATE TABLE IF NOT EXISTS schedule_desired_outputs (
    schedule_id         INTEGER NOT NULL,
    animal_id           INTEGER NOT NULL,
    desired_output      REAL    NOT NULL,
    interval_minutes    INTEGER DEFAULT 60,
    volume_per_interval REAL,
    PRIMARY KEY (schedule_id, animal_id),
    FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
    FOREIGN KEY(animal_id)   REFERENCES animals(animal_id)
);

CREATE TABLE IF NOT EXISTS schedule_instant_deliveries (
    delivery_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id       INTEGER NOT NULL,
    animal_id         INTEGER NOT NULL,
    delivery_datetime TEXT    NOT NULL,
    water_volume      REAL    NOT NULL,
    relay_unit_id     INTEGER,
    completed         BOOLEAN DEFAULT 0,
    FOREIGN KEY(schedule_id)   REFERENCES schedules(schedule_id),
    FOREIGN KEY(animal_id)     REFERENCES animals(animal_id),
    FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id)
);

CREATE TABLE IF NOT EXISTS schedule_staggered_windows (
    window_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id      INTEGER NOT NULL,
    animal_id        INTEGER NOT NULL,
    start_time       TEXT    NOT NULL,
    end_time         TEXT    NOT NULL,
    target_volume    REAL    NOT NULL,
    delivered_volume REAL    DEFAULT 0,
    status           TEXT    DEFAULT 'pending',
    FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
    FOREIGN KEY(animal_id)   REFERENCES animals(animal_id)
);

CREATE TABLE IF NOT EXISTS cycle_tracking (
    tracking_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id      INTEGER NOT NULL,
    animal_id        INTEGER NOT NULL,
    cycle_index      INTEGER NOT NULL,
    start_time       TEXT    NOT NULL,
    end_time         TEXT    NOT NULL,
    target_volume    REAL    NOT NULL,
    delivered_volume REAL    DEFAULT 0,
    status           TEXT    DEFAULT 'pending',
    completed_at     TEXT,
    FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
    FOREIGN KEY(animal_id)   REFERENCES animals(animal_id)
);
```

### Telemetry

```sql
CREATE TABLE dispensing_history (
    history_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id      INTEGER NOT NULL,
    animal_id        INTEGER NOT NULL,
    relay_unit_id    INTEGER NOT NULL,
    timestamp        TEXT    NOT NULL,
    volume_dispensed REAL    NOT NULL,
    status           TEXT    NOT NULL,
    cycle_index      INTEGER DEFAULT NULL,    -- added by inline migration
    -- volume_dispensed is the PLANNED volume: pulses planned x mL/pulse (0 on
    -- rows that did not complete). For an instant delivery that is the ask
    -- rounded per dose_rounding; a staggered chunk's plan also carries the
    -- window's running remainder. The ask itself is volume_requested_ml.
    -- v1.17.0: the volume credited to the animal, not a weighing. Pulse
    -- mode: the sum over the pulses whose valve opened (v1.21.0) of the
    -- calibrated mL/pulse, or of a sensor-corrected figure when a flow sensor
    -- is fitted; a pulse whose close reached its relay late is credited with
    -- the water that flowed while its valve stayed open, at the valve's
    -- steady flow. Continuous mode: the target when the
    -- delivery completed. Pump mode: the triggers that fired, at the pump's
    -- mL per trigger.
    -- NULL on older rows means "unknown", not zero.
    volume_actual_ml        REAL    DEFAULT NULL,
    pulses_fired            INTEGER DEFAULT NULL,
    volume_per_pulse_ml     REAL    DEFAULT NULL,
    -- v1.21.0: the context the delivery ran under, so the ledgers of two
    -- devices or two valve topologies can be compared without the app.
    topology                TEXT    DEFAULT NULL,   -- 'shared_manifold' | 'independent'
    calibration_id          INTEGER DEFAULT NULL,   -- valve_calibration row in force
    pulse_width_ms          INTEGER DEFAULT NULL,
    inter_pulse_interval_ms INTEGER DEFAULT NULL,
    duration_s              REAL    DEFAULT NULL,
    app_version             TEXT    DEFAULT NULL,
    volume_requested_ml     REAL    DEFAULT NULL,   -- the ask, before whole-pulse rounding
                                                    -- (sensor_failure rows: the undelivered part)
    dose_rounding           TEXT    DEFAULT NULL,   -- 'nearest' | 'up'; NULL = not recorded (older
                                                    -- rows, breaker rows) or not rounded to pulses
                                                    -- (pump, continuous)
    delivery_mode           TEXT    DEFAULT NULL,   -- 'instant' | 'staggered', kept on the row
                                                    -- because a schedule can be deleted
    FOREIGN KEY(schedule_id)   REFERENCES schedules(schedule_id),
    FOREIGN KEY(animal_id)     REFERENCES animals(animal_id),
    FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id)
);

CREATE TABLE IF NOT EXISTS logs (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT    NOT NULL,
    action        TEXT    NOT NULL,
    super_user_id INTEGER NOT NULL,
    details       TEXT,
    FOREIGN KEY(super_user_id) REFERENCES trainers(trainer_id)
);
```

### Run history (v2.0.0)

One record per run that started delivering, written through
`DatabaseHandler` (queries in
[`models/schedule_runs_repo.py`](../models/schedule_runs_repo.py)). The
record opens at the run's first due delivery (outcome `running`) and closes
once, when the run ends; a run that a crash or a power cut left open is
closed as `interrupted` at the next start. The Animals tab shows each
animal's latest run (the highest `run_id`); every run stays on record.
Design: [STOP_AND_PARTIAL_DELIVERY.md](STOP_AND_PARTIAL_DELIVERY.md) §4–§5.

```sql
CREATE TABLE IF NOT EXISTS schedule_runs (
    run_id               INTEGER PRIMARY KEY AUTOINCREMENT, -- start order, never reused
    schedule_id          INTEGER NOT NULL,   -- not a FK: the schedule can be deleted
    schedule_name        TEXT    NOT NULL,   -- copied at the start (rename, delete)
    delivery_mode        TEXT    NOT NULL,   -- 'staggered' | 'instant'
    started_at           TEXT    NOT NULL,   -- local ISO time of the first delivery
    ended_at             TEXT,               -- NULL while running; for 'interrupted',
                                             -- when the next start found it open
    end_reason           TEXT,               -- 'completed' | 'stopped' | 'ended_short'
                                             -- | 'interrupted'; NULL while running
    started_by           INTEGER,            -- trainer logged in at Run
    stopped_by           INTEGER,            -- trainer logged in at Stop (Stop only)
    relays_confirmed_off INTEGER,            -- Stop only: 1 / 0; NULL otherwise
    worker_exited        INTEGER,            -- Stop only: 1 / 0; NULL otherwise
    app_version          TEXT,               -- RRR version that ran it
    FOREIGN KEY(started_by) REFERENCES trainers(trainer_id),
    FOREIGN KEY(stopped_by) REFERENCES trainers(trainer_id)
);

CREATE TABLE IF NOT EXISTS schedule_run_animals (
    run_id        INTEGER NOT NULL,
    animal_id     INTEGER NOT NULL,          -- not a FK: the animal can be deleted
    relay_unit_id INTEGER,                   -- relay unit (the cage in solenoid mode)
    requested_ml  REAL    NOT NULL,          -- scheduled: what the schedule asks
    planned_ml    REAL    NOT NULL,          -- whole pulses x the cage's mL/pulse
                                             -- (= requested_ml outside pulse mode)
    delivered_ml  REAL,                      -- credited: the sum of the run's
                                             -- dispensing_history volume_actual_ml;
                                             -- NULL while running or when unknown
    outcome       TEXT    NOT NULL,          -- 'running' | 'completed' | 'stopped'
                                             -- | 'incomplete' | 'interrupted'
    PRIMARY KEY (run_id, animal_id),
    FOREIGN KEY(run_id) REFERENCES schedule_runs(run_id)
);

-- Each animal's latest run, MAX(run_id) per animal, in one index probe.
CREATE INDEX IF NOT EXISTS idx_schedule_run_animals_animal_run
    ON schedule_run_animals (animal_id, run_id);
```

`outcome` is decided per animal when the run ends, by the run's recorder in
`main.py`, not here: `completed` when the animal got its amount within
RRR's own whole-pulse tolerance, by the per-mode rule in
[STOP_AND_PARTIAL_DELIVERY.md](STOP_AND_PARTIAL_DELIVERY.md) §5; otherwise
`stopped` (the operator pressed Stop), `incomplete` (the run ended short
without a Stop) or `interrupted` (RRR closed or lost power during the run;
what was delivered is in `dispensing_history`, e.g.
`tools/gravimetric_check.py daily`). `end_reason` is `completed` when every
animal completed, else `stopped` or `ended_short`; only the start-up check
sets `interrupted`. Python checks both value sets (`RUN_OUTCOMES`,
`RUN_END_REASONS`), not a `CHECK` constraint, so a later release can add a
value without rebuilding the table.

### App configuration

```sql
CREATE TABLE IF NOT EXISTS system_settings (
    setting_key   TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,            -- serialised; see §6
    setting_type  TEXT NOT NULL,            -- 'bool' | 'int' | 'float' | 'json' | 'str'
    updated_at    TEXT NOT NULL
);
```

### Calibration

```sql
CREATE TABLE IF NOT EXISTS valve_calibration (
    calibration_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cage_id                     INTEGER NOT NULL UNIQUE,
    relay_id                    INTEGER NOT NULL,
    pulse_width_ms              INTEGER NOT NULL,
    volume_per_pulse_ml         REAL    NOT NULL,
    stddev_ml                   REAL,
    coefficient_of_variation_pct REAL,
    num_samples                 INTEGER NOT NULL,
    calibration_date            TEXT    NOT NULL,
    calibrated_by               INTEGER,
    notes                       TEXT,
    inter_pulse_interval_ms     INTEGER,            -- v1.16.0; NULL = legacy 100 ms rest
    topology                    TEXT DEFAULT NULL,  -- v1.21.0; 'shared_manifold' | 'independent'
                                                    -- NULL = measured before it was recorded
                                                    --        (the shared manifold)
    FOREIGN KEY(calibrated_by) REFERENCES trainers(trainer_id)
);

CREATE TABLE IF NOT EXISTS valve_calibration_history (
    history_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cage_id                     INTEGER NOT NULL,   -- intentionally NOT UNIQUE
    relay_id                    INTEGER NOT NULL,
    pulse_width_ms              INTEGER NOT NULL,
    volume_per_pulse_ml         REAL    NOT NULL,
    stddev_ml                   REAL,
    coefficient_of_variation_pct REAL,
    num_samples                 INTEGER NOT NULL,
    calibration_date            TEXT    NOT NULL,
    calibrated_by               INTEGER,
    notes                       TEXT,
    inter_pulse_interval_ms     INTEGER,            -- v1.16.0; NULL = legacy 100 ms rest
    topology                    TEXT DEFAULT NULL,  -- v1.21.0; 'shared_manifold' | 'independent'
                                                    -- NULL = measured before it was recorded
                                                    --        (the shared manifold)
    FOREIGN KEY(calibrated_by) REFERENCES trainers(trainer_id)
);
```

---

## 3. Connection model

```python
def __init__(self, db_path=None):
    self.db_path = db_path or paths.database_path()
    self._schedule_runs = ScheduleRunsRepo(self.connect)  # run history (§5)
    self.create_tables()

def connect(self):
    return sqlite3.connect(self.db_path)
```

- **One connection per call.** Every public method opens a new `sqlite3`
  connection inside a `with self.connect() as conn:` block and lets the context
  manager commit/rollback. There is no `self.conn`, no pool. The run-history
  repo is handed `connect` and works the same way.
- **No pragmas set.** Journal mode is the SQLite default (DELETE, *not* WAL);
  `PRAGMA foreign_keys` is OFF; `PRAGMA synchronous` is the default.
- **Thread-safety story:** the per-call pattern is safe because each thread
  gets its own connection. Concurrent *writes* serialise on the database file
  lock (no WAL). For the RRR's workload — one GUI thread + one delivery
  worker — this is fine; do not assume it scales beyond that.

If you ever need to add a method, **do not** add `self.conn = ...` to
`__init__`; keep the per-call pattern.

---

## 4. Inline migrations

Schema changes are not run from a migration framework — they are inline
`PRAGMA table_info(...)` + `ALTER TABLE ... ADD COLUMN ...` sequences inside
`create_tables()`. All run idempotently on every startup, and every added
column is nullable so an older release can still read the rows (no `SELECT *`
in the handler; every `INSERT` names its columns).

| Migration | What it does | Since |
|---|---|---|
| `dispensing_history.cycle_index` | If the table pre-dates the column, add it with `DEFAULT NULL`. | pre-v1.5 |
| `animals.sex` | Add a nullable `sex TEXT CHECK(sex IN ('male','female'))` if absent. | pre-v1.5 |
| `valve_calibration.inter_pulse_interval_ms`, `valve_calibration_history.inter_pulse_interval_ms` | The valve-closed rest the calibration was measured at; NULL = legacy 100 ms cadence. | v1.16.0 |
| `valve_calibration.topology`, `valve_calibration_history.topology` | The valve topology the calibration was measured under; NULL = measured before it was recorded, which reads as the shared manifold. A calibration from the other topology is reported as Stale in Settings → Calibration, and Run refuses a pulse-mode schedule that waters that cage (`utils/calibration_gate.py`); the delivery strategy still reads such a row only as a defence in depth. | v1.21.0 |
| `dispensing_history.volume_actual_ml`, `.pulses_fired`, `.volume_per_pulse_ml` | The volume credited to the animal (pulse mode: the calibrated or sensor-corrected volume of each pulse whose valve opened; continuous mode: the target when the delivery completed; pump mode: the triggers that fired), with the pulses fired and the mL/pulse they were fired at. Not a weighing; NULL = unknown. | v1.17.0 |
| `dispensing_history.topology`, `.calibration_id`, `.pulse_width_ms`, `.inter_pulse_interval_ms`, `.duration_s`, `.app_version`, `.volume_requested_ml`, `.dose_rounding`, `.delivery_mode` | The context the delivery ran under (valve topology, calibration row, timing profile, wall-clock duration, app version, schedule mode), and the volume asked for before whole-pulse rounding with the rounding policy applied. | v1.21.0 |

A new table needs no migration step: `CREATE TABLE IF NOT EXISTS` adds it
to an existing database, and a release that predates it never reads it.
`schedule_runs`, `schedule_run_animals` and `idx_schedule_run_animals_animal_run`
(v2.0.0) arrive that way.

When you need another migration, add it to `create_tables()` in the same
style; *do not* introduce a parallel framework — see [`docs/UPDATE_SYSTEM.md`
§14.5 F4](UPDATE_SYSTEM.md) for the reasoning.

---

## 5. `DatabaseHandler` — method reference

All methods are synchronous (with one broken exception flagged in §7).

### Trainers

| Method | Purpose |
|---|---|
| `authenticate_trainer(name, password)` | SHA-256 hash check; returns `{trainer_id, role}` or `None`. |
| `add_trainer(name, password)` | Insert a new trainer with a fresh salt. |
| `get_trainer_by_id(trainer_id)` | Lookup by PK. |

### Animals & cages

| Method | Purpose |
|---|---|
| `add_animal(animal, trainer_id)` | Insert; returns new `animal_id`. |
| `update_animal(animal)` | Full-row update by `animal_id`. |
| `remove_animal(lab_animal_id)` | Delete by external ID. |
| `get_all_animals()` / `get_animals_by_trainer(trainer_id)` / `get_animals(trainer_id, role)` | List variants, ordered by `animal_id`. Each `Animal` carries its latest schedule run as `last_run` (a dict, see Schedule run history below, or `None`), read in the same query. |
| `get_animal_by_id(animal_id)` | Single fetch (no `sex`, no `last_run`). |
| `update_animal_watering(animal_id, volume, timestamp)` | **Broken** — declared `async`, awaits a non-existent `execute`. See §7. |
| `get_cage_name` / `get_all_cage_names` / `set_cage_name` / `delete_cage_name` / `initialize_default_cage_names` / `get_cages_for_dropdown` | CRUD + helpers for `cage_names`. |

### Relay hardware

| Method | Purpose |
|---|---|
| `add_relay_unit(relay_unit)` | Insert one unit (relay IDs serialised as CSV). |
| `get_all_relay_units()` / `get_relay_units()` | Hydrate `RelayUnit` objects. |

### Schedules & their satellites

| Method | Purpose |
|---|---|
| `add_schedule(schedule)` | Generic insert; also writes `schedule_animals` and (for instant mode) `schedule_instant_deliveries`. |
| `add_staggered_schedule(schedule)` | Staggered-mode insert with `schedule_desired_outputs` + `schedule_staggered_windows`. |
| `update_staggered_schedule(schedule)` / `update_instant_schedule(schedule)` | Transactional edit: update the `schedules` row + replace all child rows. |
| `update_schedule_status(...)` | **Broken and unused** — writes `schedules.status`, a column that does not exist, so every call raises `sqlite3.OperationalError`; nothing calls it. A run's outcome is in the run history (§2). |
| `remove_schedule(schedule_id)` | Deletes from `schedules` + `schedule_animals` only (no cascade — see §7). |
| `get_schedule_details(schedule_id)` / `get_all_schedules()` / `get_schedules_by_trainer(trainer_id)` | Hydrated reads. |
| `get_active_schedules()` | Currently in-window schedules with `dispensing_status='active'`. Unused: nothing sets `dispensing_status`. |
| `get_schedule_progress(schedule_id)` | Join of schedule + animals + desired_outputs + dispensing totals. Unused; it sums the planned volume of `completed` rows only. What each animal got in a run is in the run history. |
| `get_schedule_instant_deliveries(schedule_id)` | Instant-mode rows. |
| `get_active_staggered_windows()` / `get_staggered_window_status(window_id)` / `get_schedule_staggered_windows(schedule_id)` | Staggered-mode reads. |
| `create_staggered_delivery_window(...)` / `update_staggered_window_progress(...)` | Window lifecycle. |

### Telemetry

| Method | Purpose |
|---|---|
| `log_action(super_user_id, action, details)` | Append to `logs`. |
| `log_delivery(delivery_data)` / `log_staggered_delivery(...)` | Append to `dispensing_history`; also bump `animals.last_watering` on success. |
| `track_cycle_progress(...)` / `update_cycle_progress(...)` | Lifecycle on `cycle_tracking`. |

### Schedule run history

Queries in [`models/schedule_runs_repo.py`](../models/schedule_runs_repo.py)
(`ScheduleRunsRepo`); `DatabaseHandler` keeps these methods and delegates.

| Method | Purpose |
|---|---|
| `start_schedule_run(schedule_id, schedule_name, delivery_mode, started_by, animals)` | Open a run at its first due delivery: one `schedule_runs` row and one `running` row per animal, in one transaction. `animals`: dicts with `animal_id`, `relay_unit_id`, `requested_ml`, `planned_ml`. Returns the `run_id`, or `None` (nothing written) when `animals` is empty or the write fails. |
| `finish_schedule_run(run_id, end_reason, results, stopped_by=None, relays_confirmed_off=None, worker_exited=None)` | Close a run once. `results`: `{animal_id: (delivered_ml or None, outcome)}`. Returns `True` only when this call closed the run (it was still open, `ended_at IS NULL`). Returns `False`, with nothing changed, when the run is already closed or unknown, or when the database refused the write (a lock held for more than about 5 s: the run then shows as running until the next start marks it `interrupted`). An animal of the run missing from `results` is closed `incomplete` with `delivered_ml` NULL. An unknown `end_reason` or `outcome` raises `ValueError` before any write. |
| `mark_interrupted_schedule_runs()` | At start-up, before the GUI is built; never in `create_tables`, which `--selftest` and the bench tools run beside a live RRR. Closes every open run as `interrupted`, its animals too; `delivered_ml` stays NULL, and `ended_at` is the time of that start. Returns the number of runs closed. |
| `get_latest_runs_of_schedule(schedule_id, animal_ids)` | Each animal's latest run **of this schedule** (the highest `run_id` among that schedule's runs) as `{animal_id: dict}`: the `Animal.last_run` dict plus `lab_animal_id`. Run reads it, one indexed read, before it starts the schedule over. Animals without a run of that schedule are left out; `{}` for no ids or a database error. |

**`Animal.last_run`**, the dict the animal readers attach, holds what the
Animals tab, the animal export and the Run warning read: `run_id`,
`schedule_name`, `delivery_mode`, `started_at`, `ended_at` (NULL while
running; for an `interrupted` run, the time of the start that closed it),
`outcome`, `relay_unit_id`, `requested_ml`, `planned_ml` and `delivered_ml`
(a float, or `None` while running or when unknown). How the run ended for
the audit (`end_reason`, `started_by`, `stopped_by`, `relays_confirmed_off`,
`worker_exited`, `app_version`) stays in `schedule_runs`; the readers do not
join `trainers`.

### Settings

| Method | Purpose |
|---|---|
| `get_system_settings()` | Read all `system_settings` rows; decode by `setting_type` (`int`/`float`/`bool`/`json`/`str`). |
| `update_system_setting(key, value, setting_type)` | Upsert one row with `datetime('now')`. |

### Calibration

| Method | Purpose |
|---|---|
| `save_valve_calibration(..., inter_pulse_interval_ms=None, topology=None)` | Dual-write: append to `valve_calibration_history`, then `INSERT OR REPLACE` into `valve_calibration`. The row is replaced, so callers always pass the interval and the topology. |
| `get_valve_calibration(cage_id)` / `get_all_valve_calibrations(*, raise_errors=False)` | Current calibrations, including `calibration_id`, `inter_pulse_interval_ms` and `topology`. A database error returns `None` / `{}`; `raise_errors=True` raises it instead, so the Run calibration gate can tell "nothing calibrated" from "could not read". |
| `get_valve_calibration_history(cage_id, limit=10)` | Audit trail, newest first. |

### Cross-cutting

| Method | Purpose |
|---|---|
| `__init__(db_path=None)` | Resolve `db_path` via `paths.database_path()`; hand `connect` to the run-history repo; run `create_tables()`. |
| `connect()` | Return a fresh `sqlite3.Connection`. |
| `create_tables()` | DDL bootstrap + inline migrations; idempotent. |

---

## 6. Settings persistence (Phase 2.5, v1.5.0+)

Every persisted *preference* lives in `system_settings`. **Slack credentials
do NOT** — since Phase 2.5b (v1.5.1) they live in a dedicated mode-0600
`secrets.json` next to the database; see
[`Project/utils/secrets.py`](../utils/secrets.py) and
[`SystemController._ensure_secrets_migrated()`](../controllers/system_controller.py).

`setting_type` records how to decode `setting_value`:

| `setting_type` | Storage | Decode on read |
|---|---|---|
| `int` | `str(value)` | `int(float(value))` |
| `float` | `str(value)` | `float(value)` |
| `bool` | `str(value)` ("True"/"False") | `value.lower() == 'true'` |
| `str` | `value` | `value` |
| `json` | `json.dumps(value, default=str)` | `json.loads(value)` |

The type tag is inferred at write time by
[`SystemController._write_setting_to_db`](../controllers/system_controller.py)
based on Python type — `list`/`dict` round-trip through `json`.

The set of keys persisted to the DB is the single source of truth
[`SystemController._get_persisted_keys()`](../controllers/system_controller.py).
Anything else passed to `save_settings()` stays in `self.settings` in-memory
only — useful for runtime objects (e.g. `relay_unit_manager`) you do not want
to serialise.

A first-launch migration on v1.5.0+ copies any existing legacy
`settings.json` into the DB and writes a `_migrated_from_json_v1` sentinel
row that prevents re-running. The legacy file is left intact (copy-not-move).
See [`docs/UPDATE_SYSTEM.md` §13.8 / §14](UPDATE_SYSTEM.md) for the full plan.

Test coverage:
[`test_settings_persistence.py`](../tests/unit/test_settings_persistence.py)
— 20 cases for round-trip, migration, save semantics, and the previously silent `theme` drop.
[`test_secrets.py`](../tests/unit/test_secrets.py) — 12 cases for the secrets store
plus the v1.5.0 → v1.5.1 and pre-v1.5.0 → v1.5.1 migration paths.

---

## 7. Known issues / accepted technical debt

- **FK enforcement is off.** `PRAGMA foreign_keys` is never set, so the FK
  declarations are documentation only. `remove_schedule(...)` does no cascade
  and will leave dangling rows in the satellite tables. Switching enforcement
  on would require auditing every delete path first.
- **No WAL.** Concurrent writes serialise on the file lock. Acceptable for the
  GUI-thread + single-worker pattern; revisit if you ever add a third writer.
- **`update_animal_watering` is broken.** It is declared `async` and
  `await self.execute(...)` — but `DatabaseHandler` has no `execute` method and
  no event loop wraps it. The intended behaviour is covered by `log_delivery`
  (which updates `animals.last_watering` on `status='completed'`).
- **`update_schedule_status` is broken and unused.** It writes
  `schedules.status`, which does not exist, so every call raises
  `sqlite3.OperationalError`; `schedules.dispensing_status` is never
  written either. Run outcomes live in the run history.
- **Run history is never deleted.** `remove_animal` and `remove_schedule`
  leave `schedule_runs` / `schedule_run_animals` rows in place on purpose
  (the record of the water each animal was given), as they leave
  `dispensing_history` rows. A lab ID added again gets a new `animal_id`,
  so it does not inherit the old animal's runs.
- **`cage_names.relay_id`** is not a FK to `relay_units`; the mapping is
  application-convention.
- **No formal schema-version table.** The inline `ALTER TABLE` migrations
  listed in §4 live in `create_tables()`. Adding another? Same pattern; do
  not bolt on a framework (see [`docs/UPDATE_SYSTEM.md` §14.5 F4](UPDATE_SYSTEM.md)).
  (The dead `schedule_time_instants` method cluster that referenced a
  non-existent table was removed in v1.14.1; instant deliveries live solely in
  `schedule_instant_deliveries`.)
