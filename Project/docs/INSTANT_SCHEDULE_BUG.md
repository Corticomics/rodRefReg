# Instant-delivery schedules: storage inconsistency (tracked)

**Status:** open. Discovered while refactoring the edit-schedule flow (v1.11.0).
This is a **separate concern** from edit-schedule and is intentionally *not*
fixed in that PR (one concern per PR — see [CLAUDE.md](../../CLAUDE.md)).

## Symptom

Instant-delivery schedules created through the wizard appear to save but
**deliver nothing** when run, because the rows the runtime reads are never
written.

## Root cause

Two different tables are used for "instant" deliveries, and the write path and
the read path disagree:

| Path | Code | Table |
|---|---|---|
| Wizard create (intended) | `ScheduleCreationWizard._create_schedule` instant branch → `add_schedule(schedule)` | `schedule_instant_deliveries` — but `schedule.instant_deliveries` is **empty** (the wizard called `add_animal`, never `add_instant_delivery`), so **no rows** are written |
| Wizard create (actual) | same method → `add_schedule_instant()` per animal | **`schedule_time_instants`** — a table that is **never created** in the schema (`DatabaseHandler.__init__`), so the INSERT raises and is swallowed |
| Runtime read | `run_stop_section.py` / `schedule_drop_area.py` → `get_schedule_instant_deliveries()` | **`schedule_instant_deliveries`** |

Net effect: nothing is written to `schedule_instant_deliveries`, so the runtime
finds zero deliveries. Staggered schedules are unaffected (separate, coherent
tables: `schedule_animals` / `schedule_desired_outputs` /
`schedule_staggered_windows`).

Key references:
- `add_schedule_instant` →
  [database_handler.py](../models/database_handler.py) (`INSERT INTO schedule_time_instants`)
- `get_schedule_instant_deliveries` reads `schedule_instant_deliveries`
- Wizard instant create branch →
  [schedule_wizard.py](../ui/schedule_wizard.py) `_create_schedule`

## Why edit-schedule (v1.11.0) sidesteps it

The rebuilt `ScheduleEditDialog` fully supports **staggered** editing. For
**instant** schedules it shows a short "editing instant schedules isn't
available yet" notice instead of a half-working form, so no edit can land on the
broken storage.

## Planned fix (phased)

- **Phase A — unify instant storage (own PR, MINOR).** Make the wizard write
  real rows to `schedule_instant_deliveries` (populate the schedule via
  `add_instant_delivery`, or call `add_schedule_instant` against the correct
  table). Drop or migrate the orphaned `schedule_time_instants` path. Requires a
  Pi delivery test (instant schedule actually dispenses).
- **Phase B — enable instant editing.** Once storage is coherent, extend the
  edit dialog's instant branch to load/save real instant deliveries and
  re-enable Save (reuse the same `Step3ConfigureParameters` instant mode).

## Test gaps to add with the fix

- A Qt-free DB test that an instant schedule created end-to-end has rows in
  `schedule_instant_deliveries` and that `get_schedule_instant_deliveries`
  returns them.
