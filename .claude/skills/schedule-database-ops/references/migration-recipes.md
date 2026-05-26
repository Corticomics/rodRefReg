# Migration recipes

The RRR project has **no migration framework**. Schema changes go in
`DatabaseHandler.create_tables`, which runs on every app startup. The
recipes below are the patterns proven safe across upgrade paths.

## Recipe 1 — Add a new table

Append to `create_tables` with `IF NOT EXISTS`. Safe to re-run; safe on
older installs that lack the table.

```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS my_new_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ...
    )
''')
```

## Recipe 2 — Add a column to an existing table

SQLite can't conditionally `ADD COLUMN`, so probe with `PRAGMA table_info`
first. Reference implementation: the `sex` column added to `animals` at
[`database_handler.py:260-269`](Project/models/database_handler.py#L260-L269).

```python
cursor.execute("PRAGMA table_info(animals)")
columns = [col[1] for col in cursor.fetchall()]

if 'sex' not in columns:
    cursor.execute('''
        ALTER TABLE animals
        ADD COLUMN sex TEXT CHECK(sex IN ('male', 'female')) DEFAULT NULL
    ''')
```

Rules:

- New columns **must** be nullable or have a `DEFAULT` — otherwise the
  migration fails on rows that already exist.
- Don't combine "create table if not exists" + "add column" for the same
  column; only the `PRAGMA` path handles both new and existing installs
  correctly.

## Recipe 3 — One-time data migration with a sentinel

For data fixups that should run exactly once across the lifetime of a
device — e.g. the legacy `settings.json` → `system_settings` migration in
[`Project/controllers/system_controller.py`](Project/controllers/system_controller.py).

```python
SENTINEL_KEY = '_migrated_legacy_settings_v1'

# Read sentinel
already_done = db.get_system_settings().get(SENTINEL_KEY) == 'true'
if already_done:
    return

# Do the migration (idempotently if possible)
migrate_legacy(...)

# Write sentinel
db.update_system_setting(SENTINEL_KEY, 'true', 'bool')
```

Tested in
[`Project/tests/unit/test_settings_persistence.py::test_migration_writes_sentinel_even_with_no_legacy_file`](Project/tests/unit/test_settings_persistence.py).

The sentinel uses a leading underscore so it sorts above operator-visible
keys when someone browses `system_settings` by hand.

## Recipe 4 — Backfill computed values

When you add a column whose value should be derived from existing rows
(e.g. `volume_per_interval = desired_output / N`), backfill in the same
startup pass right after the `ALTER TABLE`:

```python
if 'volume_per_interval' not in columns:
    cursor.execute('ALTER TABLE schedule_desired_outputs ADD COLUMN volume_per_interval REAL')
    cursor.execute('''
        UPDATE schedule_desired_outputs
        SET volume_per_interval = desired_output * 1.0 / NULLIF(...interval_count..., 0)
        WHERE volume_per_interval IS NULL
    ''')
```

Use `NULLIF(x, 0)` to avoid divide-by-zero, and `WHERE col IS NULL` so
the backfill is idempotent.

## What NOT to do

- **Never `DROP TABLE`** in `create_tables`. Once a table has shipped,
  it's permanent. Rename the table conceptually; leave the row format.
- **Never `DROP COLUMN`** without a sentinel. SQLite supports
  `ALTER TABLE … DROP COLUMN` only since 3.35; the Pi may run older
  versions, and there's no safe rollback.
- **Never write a migration without a test.** Add a case to
  `test_settings_persistence.py` (or a sibling) that asserts the new
  column/table exists and the backfill produced the right values.
- **Never change column types in place.** If you must change a type,
  create a new column, backfill, and stop reading the old one — but leave
  the old column in the schema as deprecated. SQLite's column-rename
  path is fragile.

## Testing a migration

The `database_handler` fixture in
[`Project/tests/unit/conftest.py`](Project/tests/unit/conftest.py) builds
a fresh handler against a tmp directory, so every test runs the migration
on a clean DB. To test the "existing install" path, write a pre-migration
state first:

```python
def test_my_migration_adds_column(database_handler):
    # Force a pre-migration state by manually executing a CREATE TABLE
    # that lacks the new column, then re-instantiate DatabaseHandler to
    # trigger create_tables again.
    ...
```

In practice you'll only need this for non-trivial migrations; for a
plain `ADD COLUMN` the default fixture is enough.
