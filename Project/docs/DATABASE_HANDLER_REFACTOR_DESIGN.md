# DatabaseHandler Refactor — Design Doc

**Status:** proposal (no code yet). Companion to
[DATABASE.md](DATABASE.md) / [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md)
(schema reference) and [DEVELOPMENT.md](DEVELOPMENT.md) (architecture).

This doc weighs how (and whether) to refactor
[`Project/models/database_handler.py`](../models/database_handler.py),
recommends a target, and lays out a low-risk migration plan with
acceptance criteria. It does **not** change code. Nothing here ships
until the recommendation is approved.

---

## 1. Current state (facts, not opinions)

Measured on `main` at the time of writing:

| Property | Value |
|---|---|
| File | `Project/models/database_handler.py` |
| Size | **2245 LOC**, one class (`DatabaseHandler`), **52 methods** |
| Tables | **15**: `animals`, `trainers`, `relay_units`, `schedules`, `schedule_animals`, `schedule_desired_outputs`, `schedule_instant_deliveries`, `schedule_staggered_windows`, `cycle_tracking`, `dispensing_history`, `logs`, `system_settings`, `valve_calibration`, `valve_calibration_history`, `cage_names` |
| Connection model | `connect()` opens a **new** `sqlite3.connect(self.db_path)` per call, used as `with self.connect() as conn:`. No pool, no WAL, no `PRAGMA foreign_keys=ON`. |
| Schema management | `create_tables()` runs on every `__init__` (idempotent `CREATE TABLE IF NOT EXISTS`). Schema changes are **ad-hoc** inline `ALTER TABLE … ADD COLUMN` wrapped in try/except (2 today: `dispensing_history`, `animals`). No `PRAGMA user_version`, no migration framework, no schema-version row. |
| Construction | `DatabaseHandler()` is instantiated **independently in ≥4 places** (`main.py`, `projects_controller.py`, `ui/schedule_drop_area.py`, `ui/splash_screen.py`). Not a singleton; not consistently dependency-injected. Each instance re-runs `create_tables()`. |
| Access discipline | **Good** — grep confirms **no** raw `sqlite3`/`import sqlite3` anywhere outside this file. The handler genuinely is the single DB access point already. |

### Method domains (the 52 methods cluster into ~7 concerns)

| Domain | Representative methods | ~count |
|---|---|---|
| Schema/lifecycle | `connect`, `create_tables` | 2 |
| Relay units | `add_relay_unit`, `get_all_relay_units`, `get_relay_units` | 3 |
| Animals | `add_animal`, `update_animal`, `remove_animal`, `get_all_animals`, `get_animals_by_trainer`, `get_animal_by_id`, `update_animal_watering` | 7 |
| Trainers / auth | `authenticate_trainer`, `get_trainer_by_id`, `add_trainer` | 3 |
| Schedules (core) | `add_schedule`, `get_schedule_details`, `update_schedule`, `remove_schedule`, `get_all_schedules`, `get_schedules_by_trainer`, `update_schedule_status`, `get_active_schedules` | 8 |
| Schedules (instant) | `add_schedule_instant`, `add_instant_schedule`, `get_pending_schedule_instants`, `mark_instant_completed`, `get_schedule_instant_deliveries` | 5 |
| Schedules (staggered + cycles) | `add_staggered_schedule`, `get_active_staggered_windows`, `create_staggered_delivery_window`, `update_staggered_window_progress`, `get_staggered_window_status`, `log_staggered_delivery`, `get_schedule_progress`, `track_cycle_progress`, `update_cycle_progress`, `get_schedule_staggered_windows`, `log_delivery` | 11 |
| System settings (type-tagged) | `get_system_settings`, `update_system_setting`, `delete_system_setting` | 3 |
| Valve calibration | `save_valve_calibration`, `get_valve_calibration`, `get_all_valve_calibrations`, `get_valve_calibration_history` | 4 |
| Cage names | `get_cage_name`, `get_all_cage_names`, `set_cage_name`, `delete_cage_name`, `initialize_default_cage_names`, `get_cages_for_dropdown` | 6 |
| Logs | `log_action` | 1 |

The schedule family alone (core + instant + staggered) is **24 methods** — nearly half the class.

---

## 2. The three pain axes

The user asked to weigh all three. Here is the honest assessment of each.

### Axis A — Maintenance velocity (navigability)

- **Real pain.** 2245 LOC in one class means every contributor scrolls
  the same file for any DB change; unrelated domains (auth, calibration,
  cage names, schedules) share one namespace.
- **Evidence in this very codebase:** the v1.8.5 whole-second datetime
  bug lived in `add_staggered_schedule` and was easy to miss precisely
  because it's buried in an 11-method staggered sub-area inside a
  52-method file.
- **Severity: medium.** It slows reading and raises the chance of
  "didn't see the related method" mistakes, but it isn't actively
  breaking anything.

### Axis B — Testability

- **Partial pain.** Methods call `self.connect()` internally (open their
  own connection to `self.db_path`). The unit suite already tests the
  handler (the conftest `database_handler` fixture + `RRR_DATA` temp-dir
  redirect), and the v1.8.5 regression test proves new behavior **can**
  be unit-tested today. So it is *not* untestable.
- **What's missing:** no exposed transaction boundary (can't compose
  multiple writes atomically from a caller), no seam to inject a fake
  connection for fast pure-logic tests, and no separation of "SQL
  plumbing" from "domain logic" (e.g., the type-tag (de)serialization in
  `system_settings`, the cage→relay generation logic).
- **Severity: low-medium.** Good enough to test; awkward to test
  *cheaply* or to test multi-statement atomicity.

### Axis C — Migration safety

- **The most real risk.** Schema evolution is ad-hoc `ALTER TABLE … ADD
  COLUMN` inside `create_tables`, guarded by bare try/except. There is:
  - no `PRAGMA user_version` / schema-version tracking,
  - no ordered, idempotent, testable migration sequence,
  - no down-migration or recovery story,
  - no guard against a half-applied ALTER on an interrupted upgrade.
- On a fleet that updates in-place (blue-green, in-app updater), a
  schema change that needs more than "add a nullable column" (a rename,
  a backfill, a constraint) currently has **no safe pattern** — which is
  exactly why MAINTENANCE.md classes DB-migration changes as MAJOR.
- **Severity: high** for any future schema change; **zero** while the
  schema is static.

---

## 3. Options considered

### Option 1 — Do nothing (status quo)
- **Pro:** zero risk, zero churn; the access-point discipline already
  holds (no raw sqlite3 elsewhere).
- **Con:** all three pains persist; the next non-trivial schema change
  is still scary.
- **When this is right:** if no schema change is on the horizon and the
  team's time is better spent on features.

### Option 2 — Split by domain into repository modules (no behavior change)
Carve the one class into domain repositories sharing a tiny connection
helper, e.g.:
```
models/db/
  connection.py        # connect(), PRAGMAs, the with-transaction helper
  schema.py            # create_tables() + the migration runner (Option 4)
  animals_repo.py      # add/update/remove/get animals
  trainers_repo.py     # auth + trainers
  schedules_repo.py    # core + instant + staggered + cycles (or split further)
  settings_repo.py     # type-tagged system_settings
  calibration_repo.py  # valve calibration + history
  cages_repo.py        # cage_names + dropdown
  relay_units_repo.py
```
`DatabaseHandler` becomes a thin **facade** that composes the repos and
keeps the existing public method names as delegating shims — so the ≥4
call sites and the UI keep working unchanged.
- **Pro:** directly fixes Axis A; enables per-domain tests (Axis B);
  pure mechanical move, behavior-preserving; the facade means **no caller
  changes** and the smoke/suite stay green.
- **Con:** large diff (moving 2245 LOC); risk of a copy/move slip.
- **Mitigation:** move one domain per PR behind the unchanged facade;
  the existing suite + a per-repo test gate each step.

### Option 3 — Repository + dependency injection (callers take a handle)
Option 2 plus: stop constructing `DatabaseHandler()` in 4 places; create
one instance at startup and inject it everywhere.
- **Pro:** fixes Axis B more fully (single instance, injectable fakes);
  removes redundant `create_tables()` runs.
- **Con:** touches every construction site + the GUI wiring — bigger
  blast radius, more review.
- **Note:** can be layered **after** Option 2 as a separate phase.

### Option 4 — Add a real migration runner (orthogonal to 2/3)
Introduce `PRAGMA user_version`-based ordered migrations:
```
migrations = [
    (1, _migrate_0_to_1),   # baseline = current schema
    (2, _migrate_1_to_2),   # each: idempotent, single transaction
    ...
]
```
`create_tables()` becomes "ensure baseline, then run pending migrations
in a transaction, bump user_version." Enable `PRAGMA foreign_keys=ON`
and consider WAL while here.
- **Pro:** fixes Axis C — the highest-severity risk; makes future schema
  changes routine (and downgrades some future MAJORs to MINORs).
- **Con:** must capture the *current* live schema as the baseline
  exactly, or an existing device's DB gets mis-migrated. **Highest
  correctness bar of any option.**
- **Mitigation:** baseline migration is a no-op `CREATE TABLE IF NOT
  EXISTS` matching today's schema byte-for-byte; test against a copy of a
  real device DB before shipping; ship behind a PATCH with on-Pi
  verification.

---

## 4. Recommendation

**Phased, lowest-risk-first. Do NOT do a big-bang rewrite.**

1. **Phase R0 — guardrail tests first (no refactor).** Before moving any
   code, add characterization tests around the schedule family and
   settings type-tagging (the highest-traffic, highest-risk areas) so the
   later moves have a safety net beyond the smoke test. *No structural
   change.* MINOR-or-no-bump (test-only).
2. **Phase R1 — Option 4 (migration runner).** Fix the highest-severity
   axis (C) first, in isolation, while the code is still one file so the
   change is easy to reason about. `user_version` baseline = current
   schema; `foreign_keys=ON`; one no-op baseline migration; verified
   against a copied device DB. **PATCH**, on-Pi verified.
3. **Phase R2 — Option 2 (domain split behind a facade).** One domain per
   PR; `DatabaseHandler` stays as a delegating facade so no caller
   changes. Each PR: move + per-repo test + suite green. Spread over
   several small PRs. **No bump** (internal refactor, behavior-preserving)
   per MAINTENANCE.md §1 unless a PR also changes behavior.
4. **Phase R3 — Option 3 (DI), optional/last.** Only if R2 leaves enough
   benefit on the table to justify touching every construction site.

Rationale: tackle the **highest-severity** axis (migration safety) first
while the file is still simple; do the **largest-diff** work (domain
split) second behind a facade so it can never break a caller; defer the
**broadest-blast-radius** work (DI) to last and make it optional.

---

## 5. Acceptance criteria (per phase)

- **R0:** new characterization tests pass and meaningfully cover schedule
  create/read + settings round-trip; suite green on Pi (148-style full
  run).
- **R1:** a fresh DB initializes to `user_version = N`; an *existing*
  device DB (copy) migrates without data loss and ends at `user_version
  = N`; `foreign_keys` on; suite green; **on-Pi: create + run + stop a
  schedule, confirm no schema errors in the debug log.**
- **R2 (each domain PR):** the moved methods keep identical signatures
  and behavior; `DatabaseHandler` public API unchanged (facade delegates);
  suite + smoke green; `git grep` confirms no caller imported the moved
  internals directly.
- **R3:** exactly one `DatabaseHandler` instance at runtime; all call
  sites receive it by injection; suite + Pi smoke green.

---

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Migration baseline doesn't match a real device's schema → corruption | Baseline = idempotent `CREATE IF NOT EXISTS` identical to today; test against a **copy of the live Pi DB**; never run against the real DB until verified |
| Big move PR drops/duplicates a method | One domain per PR; facade keeps API stable; per-domain tests; `ruff` (now CI-gated) catches unused/redef; review diff method-by-method |
| Hidden second writer to the DB | Already verified none exists (no raw sqlite3 outside the handler) — re-grep before R2 |
| Behavior drift during "mechanical" move | The full Pi suite (148 items incl. GUI construction) + on-device schedule run after each phase |
| Animal-safety regression via the delivery/schedule path | Schedule/delivery methods are exercised by the worker; gate R1/R2 behind an on-Pi run-and-stop before tagging |

---

## 7. Estimate

- R0: 1 PR (tests). 
- R1: 1 PR (migration runner) + 1 on-Pi verification cycle.
- R2: ~6–8 small PRs (one per domain repo) behind the facade.
- R3 (optional): 1–2 PRs.

Total: a multi-PR initiative, not a single change. Each PR is independently
reviewable, revertible, and (where it touches shipped code) tagged + Pi-
verified per MAINTENANCE.md.

---

## 8. Decision record (answers to §-open-questions, 2026-05-29)

The three blocking questions were answered:

1. **Schema change planned?** No. The schema is satisfactory; a change
   would only be considered if it were clearly better/more efficient
   *without* adding much debt.
2. **Device DB snapshot?** There is **no production fleet at all** — full
   freedom. A fresh Pi can be flashed and run sample operations to
   generate fake data if ever needed.
3. **R3 (DI):** analyze effort/files/bugs/debt and give a reasoned
   recommendation (done in §10).

### What these answers change

- **Axis C (migration safety) collapses from HIGH to ~zero, today.** Its
  whole severity rested on "an in-place fleet update could corrupt a real
  device DB." With **no fleet and no planned schema change**, there is
  nothing to migrate and nothing to corrupt. A migration runner built now
  would be **unexercised infrastructure** — code that never runs in anger
  is itself a form of tech debt, and the user explicitly wants to avoid
  that. → **R1 is no longer "do first"; it is deferred until a schema
  change is actually wanted.**
- **Axis A (navigability) is now the only *present* concern**, and even it
  is a maintainability investment, not an active bug — the file works, is
  tested, and has clean single-point access.
- **Axis B (testability)** is the one with a cheap, concrete win: DI is
  already ~90% wired (see §10), so finishing it is small and real.

---

## 9. Revised recommendation (given §8)

Priorities flipped from §4. Honest, given a static schema and no fleet:

1. **R1 (migration runner): DROP for now.** No fleet + static schema = no
   value; shipping an unused `user_version` framework is speculative
   infra/debt. Re-open *only* if a concrete schema change is greenlit
   (at which point R1 becomes its prerequisite and is worth doing
   properly, tested against fake data from a flashed Pi per §8.2).
2. **R3 (finish dependency injection): RECOMMENDED — best value/effort.**
   It's small (≈4 files, the backbone already exists), removes a real
   smell (4 redundant `DatabaseHandler()` instances, each re-running
   `create_tables()`), and improves testability. Full analysis in §10.
3. **R2 (domain split behind facade): DEFER (do not do now).** It is the
   largest diff (~6–8 PRs moving 2245 LOC) for the weakest *present*
   justification — navigability — with no fleet pressure forcing it. The
   risk/churn-to-benefit ratio only turns favorable when someone is about
   to do heavy work inside one domain. Recommendation: split **lazily** —
   when a domain next needs substantial change, extract *that* domain
   then, behind the facade. Avoid a big-bang reorganization of working,
   tested code purely for tidiness.

**Net recommendation:** do **R3 only**, as a small standalone improvement;
keep `database_handler.py` otherwise as-is; revisit R1/R2 when a real
driver (a schema change, or heavy work in one domain) appears. This
maximizes value while honoring "don't add much tech debt" and the
project's own rule against landing code paths that aren't yet exercised.

---

## 10. R3 — Dependency-injection feasibility (the §-Q3 deep-dive)

### How hard: LOW. The backbone already exists.

`main.py:162` already creates the canonical `database_handler` and
injects it into `SystemController`, `LoginSystem`, the GUI, and the whole
UI tree (`SettingsTab`, `animals_tab`, `projects_section`,
`cages_visualization_tab`, `run_stop_section`, `UserTab`,
`schedule_wizard`, …). The UI is ~90% DI'd already. Only a few sites
self-construct.

### Construction sites (the complete inventory)

| Site | Self-constructs? | Verdict |
|---|---|---|
| `main.py:162` `database_handler = DatabaseHandler()` | — | **The canonical instance.** Keep. |
| `controllers/projects_controller.py:7` | Yes | **Fix** → accept `database_handler` param; caller `main.py:187` already has it. |
| `ui/schedule_drop_area.py:30` | Yes | **Fix** → accept param; caller `run_stop_section.py:121` already holds `self.database_handler` (run_stop_section.py:51). |
| `ui/splash_screen.py:54` | Yes | **Defer** — splash worker is disabled (`USE_SPLASH_SCREEN=False`); handle under Phase 5.2. |
| `main.py:140` `DatabaseHandler().connect().close()` | Yes (throwaway) | **Keep** — `--selftest` health probe; a standalone instance is correct here. |
| `tools/valve_calibration_tool.py:344` | Yes (`args.db_path`) | **Keep** — standalone CLI, intentionally independent of the app. |

So the *live-app* DI work is exactly **two** objects:
`ProjectsController` and `ScheduleDropArea`.

### Files that would change (R3, minimal scope)

1. `controllers/projects_controller.py` — `__init__(self, database_handler)`; store it instead of constructing.
2. `Project/main.py` — `ProjectsController(database_handler)` at line 187.
3. `ui/schedule_drop_area.py` — `__init__(self, database_handler, …)`; drop the self-construct.
4. `ui/run_stop_section.py` — pass `self.database_handler` when creating `ScheduleDropArea` (line 121).

Four files. Optionally a 5th cleanup: tighten the `database_handler=None`
default params (`SettingsTab`, `run_stop_section`, `UserTab`) to required,
to stop masking missing wiring — but that touches more call sites and is
a separate, optional tidy.

### Possible bugs & mitigations

| Risk | Mitigation |
|---|---|
| Construction-order: an injected site runs before `main.py:162` creates the handle | Both targets are created *after* line 162 (controller at 187; ScheduleDropArea inside the GUI build, later still). Verified by reading the call order. |
| `ScheduleDropArea` created somewhere without a handle in scope | Its only construction is `run_stop_section.py:121`, which already holds `self.database_handler`. `git grep "ScheduleDropArea("` to re-confirm at fix time. |
| `ProjectsController()` called elsewhere without args after signature change | Only one caller (`main.py:187`). `git grep "ProjectsController("` to confirm; the smoke/suite catch a missed one as a `TypeError` at construction. |
| Behavior drift (the injected handle differs from a self-made one) | They point at the same DB file; functionally identical. Full Pi suite (148 items, constructs the GUI tree) + on-Pi launch confirm. |

### Technical debt this removes / leaves

- **Removes:** 2 redundant `DatabaseHandler()` instances (each currently
  re-runs `create_tables()` on startup — wasteful, and a latent footgun
  if `create_tables` ever stops being perfectly idempotent).
- **Removes:** a hidden coupling where `ProjectsController`/`ScheduleDropArea`
  silently opened their own DB rather than sharing the app's.
- **Leaves (optional follow-up):** the `database_handler=None` default
  params — a smell that allows un-injected construction. Tightening them
  is a clean but separable second step.

### Effort & risk verdict

≈**1 small PR**, 4 files, no schema/behavior change, no version bump
(internal refactor). Risk **low** — single caller each, backbone exists,
covered by the smoke + full Pi suite. This is the rare refactor that is
almost pure upside: it finishes a pattern the codebase already committed
to, rather than imposing a new one.

**Recommendation: do R3 as a single standalone PR; skip R1 and R2 until a
concrete driver appears.**

---
