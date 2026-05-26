---
name: schedule-database-ops
description: Safely query and migrate the RRR SQLite database (rrr_database.db) — animals, schedules (staggered + instant + cycle tracking), dispensing history, system settings, valve calibration, cage naming, and trainers/login. Use when adding columns or tables, writing migrations, debugging schedule-creation, querying watering history, validating schedule assignments, or recovering from a corrupted settings state. Enforces the project's DatabaseHandler-only access rule and the idempotent-migration pattern.
---

# Schedule & database operations

The RRR app persists everything to a single SQLite file. The database
location follows the `RRR_DATA` environment contract — on an installed
device it sits at `~/rrr/shared/data/rrr_database.db`; on a dev clone it
falls back to `Project/rrr_database.db`. Path resolution is in
[`Project/utils/paths.py`](Project/utils/paths.py) `database_path()`.

## The hard rule

**All database access goes through
[`Project/models/database_handler.py`](Project/models/database_handler.py)
`DatabaseHandler` (1989 LOC).** Never `import sqlite3` from UI, controller,
or strategy code. Reasons:

- `DatabaseHandler` owns connection lifecycle, schema versioning, FK
  pragma, and error handling.
- Tests inject a temp-dir-backed handler via the `database_handler` fixture
  in [`Project/tests/unit/conftest.py`](Project/tests/unit/conftest.py).
  A raw `sqlite3.connect` from a controller bypasses that and writes to
  the real DB during tests.

## Schema at a glance

14 tables, FK-linked:

```
trainers ──< schedules ─┬─< schedule_animals >─── animals
                        ├─< schedule_desired_outputs
                        ├─< schedule_instant_deliveries >─ relay_units
                        ├─< schedule_staggered_windows
                        ├─< cycle_tracking
                        └─< dispensing_history     (also FKs relay_units)

trainers ──< logs

system_settings   (k/v with type tag; standalone)
valve_calibration / valve_calibration_history    (per-cage, FKs trainers)
cage_names        (user-friendly names per cage_id)
```

Full column-level reference: [`references/schema.md`](references/schema.md).

## Two delivery modes, two tables

Schedules have a `delivery_mode` column:

- `staggered` (default) → uses `schedule_desired_outputs` (per-animal
  volume + interval) and `schedule_staggered_windows` (per-window
  progress) and `cycle_tracking` (per-cycle progress).
- `instant` → uses `schedule_instant_deliveries` (explicit
  `delivery_datetime` rows, marked `completed BOOLEAN`).

Both modes write to `dispensing_history` on every actual relay click —
that's the audit log a researcher would query later.

## Settings persistence (Phase 2.5a)

`system_settings` is the live store for everything that used to live in
the legacy `settings/settings.json`. It's a typed key-value table —
[`Project/controllers/system_controller.py`](Project/controllers/system_controller.py)
`SystemController` owns reads/writes via `_write_setting_to_db()` and
`_load_database_settings()`. Type tags: `bool` / `int` / `float` / `str`
/ `json` (lists and dicts go through JSON).

A one-time legacy-JSON migration runs on first load and writes a sentinel
row so it never runs twice. The pattern is tested in
[`Project/tests/unit/test_settings_persistence.py`](Project/tests/unit/test_settings_persistence.py).

## Idempotent schema (the contract)

`DatabaseHandler.create_tables` is called on **every** app startup. It
must therefore be safe to re-run:

- Every `CREATE TABLE` uses `IF NOT EXISTS`.
- Adding a column on an existing install uses the `PRAGMA table_info` →
  `ALTER TABLE ADD COLUMN` pattern (see the `sex` column on `animals`
  at [`database_handler.py:260-269`](Project/models/database_handler.py#L260-L269)).
- Never drop a column. SQLite's `ALTER TABLE DROP COLUMN` is partial; for
  RRR we mark columns deprecated in comments and leave them.

Recipes for safe migrations: [`references/migration-recipes.md`](references/migration-recipes.md).

## Common queries

The patterns operators actually need (history per animal, schedules per
trainer, today's deliveries, etc.) live in
[`references/common-queries.md`](references/common-queries.md). All of
them go through existing `DatabaseHandler` methods —
**don't add a new method for a one-off query**; assemble from existing
ones, or extend an existing method by a kwarg.

## Don't do this

- Don't open `sqlite3.connect(...)` outside `DatabaseHandler`.
- Don't store secrets (`slack_token`, `slack_channel_id`) in
  `system_settings`. Secrets live in `secrets.json` at `paths.secrets_path()`.
  See [`Project/utils/secrets.py`](Project/utils/secrets.py).
- Don't commit the `.db` file. `.gitignore` excludes `*.db` and
  `build-bundle.sh` strips it from release bundles — keep it that way.
- Don't write a destructive migration without a sentinel — if it runs
  twice, it must be a no-op.
- Don't `DROP TABLE` or `DELETE FROM <table>` without a `WHERE`. There's
  no migration framework here; once you've shipped a bad migration,
  recovery is manual.

## When testing

Use the `database_handler` fixture
([`conftest.py:36`](Project/tests/unit/conftest.py#L36)). It builds a
fresh handler against `RRR_DATA = <tmp_path>/data` via `monkeypatch.setenv`,
so every test gets a pristine SQLite file. The `system_controller` fixture
layers `SystemController` on top.
