# Stop, Partial Delivery and Run History — Design Doc

**Status:** approved 2026-10-09; to be implemented in v2.0.0 (PR train in §12).
Line references are to f36d5223 (v1.21.0) unless stated. Companion to
[PRIMING_FEATURE_DOCUMENTATION.md](PRIMING_FEATURE_DOCUMENTATION.md)
(CLOSE ALL RELAYS), [DATABASE.md](DATABASE.md) (schema) and
[MAINTENANCE.md](MAINTENANCE.md) (releases).

This doc records the v2.0.0 design: Stop becomes the only way to end a
running schedule, every run is recorded per animal, and the Animals tab
shows each animal's last run. It lands before the code, so the owner and
every code PR's reviewers see the contract and the version decision first.
A code PR that refines a contract here updates its section in the same PR;
the docs PR (PR 13) reconciles the rest and sets the Status line.

---

## 1. Why

The owner's request, with a minimal schema change, existing patterns
reused, and the delivery and Stop hot paths kept simple and cheap (§5):

- **CLOSE ALL RELAYS** is a priming and emergency control: not available
  while a schedule runs.
- **Stop** is fixed, and records the amounts scheduled and delivered.
- **The Animals tab** gains *Last schedule delivered amount*: 1:1 with the
  scheduled amount when a run completes, less when it is stopped early.
- **Incomplete runs are bright red** and show scheduled vs delivered.

---

## 2. Where v1.21.0 stands

| Fact | Ref |
|---|---|
| No run state is saved: nothing writes `schedules.dispensing_status`, and `update_schedule_status` updates a `status` column that does not exist and has no callers | `database_handler.py:update_schedule_status:1036` |
| A run lives only in memory: `RunStopSection.job_in_progress`, the SCHEDULE lock, `main.worker` / `main.thread` | `run_stop_section.py:run_program:264`, `main.py:run_program:216` |
| Every Run starts from zero (`delivered_volumes = {}`): run again after a Stop, a staggered schedule gives its whole dose again and an instant one skips the passed times | `main.py:run_program:325`, `relay_worker.py:115`, `run_instant_cycle:496-527` |
| Every ending emits the same `worker.finished`: a natural end, the circuit breaker, an error or Stop | `relay_worker.py:check_completion:1219`, `stop:1498` |
| Each attempt credits what it dispensed to `delivered_volumes` and writes one ledger row with `volume_actual_ml`. Credit is pulses × the cage's calibration (sensor-blended when fitted; triggers × volume in pump mode); nothing reads a relay back | `relay_worker.py:_finalize_delivery:997`, `database_handler.py:log_delivery:1733`, `gpio_handler.py:set_all_relays:196` |
| The ledger has no run id, its `timestamp` is the planned time, and re-runs share one `schedule_id` | `database_handler.py:create_tables:39` |
| Instant runs get no `relay_unit_assignments`, so their completion tolerance falls back to 0.01 mL | `main.py:241`, `relay_worker.py:_completion_tolerance_ml:1115-1161` |
| Stop: all-off, then the Stopping dialog (it pumps events), then cancel and teardown; only the first all-off decides "confirmed" | `stop_sequence.py:execute_stop_sequence:148-152` |
| `reset_ui` always releases SCHEDULE; unconfirmed relays give two dialogs (**Relays Not Confirmed Off**, then **Warning**), an abandoned worker none | `run_stop_section.py:reset_ui:711`, `_execute_stop:683-689`; `main.py:_warn_relays_not_confirmed_off:496` |
| The manifold prime opens the master with no cancel check; Run after an abandoned Stop drops a running QThread's only reference | `solenoid_flow_strategy.py:_deliver_pulse_mode:1125`; `main.py:run_program:302-312` |
| Since #177 CLOSE ALL RELAYS stops a running schedule, switches the relays off again, latches EMERGENCY when unconfirmed and builds a fresh handler. It is never greyed; a cage change re-enables Close Selected. The `[VALVE CRITICAL]` alarms say it "stops the schedule" | `PrimingControlWidget.py:_on_emergency_stop_clicked:685`, `:1004`; `SettingsTab.py:_stop_running_schedule:1661`; `solenoid_flow_strategy.py:_alarm_unclosed:720-722`, `gpio_handler.py:_switch_unit_off:361-364` |
| `job_in_progress` is set after `try_acquire(SCHEDULE)` | `run_stop_section.py:run_program:300, :311` |
| Stop needs a login, logout is allowed mid-run and Settings is hidden from guests: after a logout nothing can stop the run | `run_stop_section.py:update_button_states:233`; `gui.py:on_logout:642`, `_update_tab_access:761` |
| The Animals tab hard-codes 7 columns (`setColumnCount(7)`, two `range(7)`, `COLUMN_WIDTHS`), widens columns 5–6 above 800 px, and its filter calls `item.text()` on every cell. `setBackground()` on an item is not painted under the app QSS | `animals_tab.py:61, :77, :142, :213, :259, :443`; `app-light.qss:331` |

---

## 3. Decisions

The owner's answers of 2026-10-09 to the approved plan's 13 questions,
verbatim, and the decisions D1–D12 the PRs implement:

| Q | Question | Answer | Decision |
|---|---|---|---|
| 1 | On completion, show the scheduled amount 1:1, the credited figure in the tooltip? | "yes or should we show the amount planned based on the calibration of each cage (use best practices here)" | **D1.** Three figures per animal per run (below); the cell shows delivered, the tooltip all three |
| 2 | Red when short by more than the worker's whole-pulse tolerance? | "yes" | **D2.** The per-animal outcome (below); raw delivered is never compared with scheduled |
| 3 | Red also when a run ends short without Stop, or after a crash? | "yes" | **D2.** `stopped`, `incomplete` and `interrupted` are red |
| 4 | Stop without a login, or block logout? | "logout blocked during run" | **D3.** Log Out greyed and refused during a run (§7) |
| 5 | Last schedule = the latest run that started delivering? | "yes" | **D4.** A re-run replaces it at its first delivery; the history keeps every run |
| 6 | No resume: Run starts over, after a warning? | "yes after a schedule is stopped nothing can be done to get the remaining volume besides creating a new schedule that delivers specifically that remaining volume" | **D5.** No resume; **Last Run Ended Early** asks, and gives the remainder for a new schedule (§9) |
| 7 | Instant run started late: plan what is due, or the whole schedule? | "whole schedule with a warning showing that and asking the user to confirm or cancel" | **D6.** The whole schedule; **Some Deliveries Passed** asks and says the run will show red (§9) |
| 8 | Last run per animal, or every run? | "history table on the database but on the animal table just the last run" | **D7.** Two history tables; no column on `animals`; ledger unchanged (§4) |
| 9 | Keep the run's end time? | "yes" | **D8.** "2 hours ago (YYYY-MM-DD HH:MM)" via `AnimalsTab.calculate_days_ago` (`animals_tab.py:156-177`) |
| 10 | How to show red; export it? | "use frontend best practice, and yes it should" | **D9.** A themed delegate with a status word (§8); the CSV export gains 7 columns |
| 11 | Interrupted: "?" and the delivery log? | "yes" | **D10.** "?" and the `gravimetric_check.py daily` command; no ledger watermark |
| 12 | Version, and order against palette B? | "follow SWE best practices and the maintenance and contributing docs of the project" | **D11.** 2.0.0 (MAJOR), one bump, no `-beta`; palette B is 2.1.0 (§12) |
| 13 | Close Selected also unavailable mid-run? | "yes" | **D12.** Greyed and refused, like CLOSE ALL RELAYS (§7) |

**D1.** **Scheduled** = `requested_ml`; for an instant schedule, the sum
of all its deliveries, past ones included. **Planned** = whole pulses × the
cage's mL per pulse under the rounding policy, per staggered window or per
instant delivery; = scheduled in pump and continuous modes. **Delivered** =
the credited Σ `volume_actual_ml` of the run's ledger rows. A completed run
delivers the plan 1:1 once the planner and the plan share one rounding
rule, an exact half rounding up (PR 6; today's `int(deficit / q + 0.5)`,
`relay_worker.py:888`, misses it in 76 of 6000 surveyed windows, all ties).

**D2.** `completed` when delivered is within RRR's own whole-pulse
tolerance, per mode (§5): staggered, the worker's completion test; instant
in pulse mode, ≥ min(planned − q/2, scheduled − that tolerance); instant in
pump or continuous mode, ≥ planned − 0.01. Otherwise `stopped`,
`incomplete` (short without Stop) or `interrupted` (RRR closed or crashed).
One pulse short of the plan is red, except under nearest rounding at an
exact half-pulse tie or below 0.02 mL per pulse.

---

## 4. Data (PR 5)

The **draft** DDL, reconciled with the merged code by the docs PR; it goes
at the end of `create_tables` (before its commit, `database_handler.py:334`).

```sql
CREATE TABLE IF NOT EXISTS schedule_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT, schedule_id INTEGER NOT NULL,
    schedule_name TEXT NOT NULL, delivery_mode TEXT NOT NULL,      -- 'instant' | 'staggered'
    started_at TEXT NOT NULL, ended_at TEXT, end_reason TEXT,
    started_by INTEGER, stopped_by INTEGER,
    relays_confirmed_off INTEGER, worker_exited INTEGER, app_version TEXT,
    FOREIGN KEY(started_by) REFERENCES trainers(trainer_id),
    FOREIGN KEY(stopped_by) REFERENCES trainers(trainer_id));
CREATE TABLE IF NOT EXISTS schedule_run_animals (
    run_id INTEGER NOT NULL, animal_id INTEGER NOT NULL, relay_unit_id INTEGER,
    requested_ml REAL NOT NULL, planned_ml REAL NOT NULL, delivered_ml REAL,
    outcome TEXT NOT NULL, PRIMARY KEY (run_id, animal_id),
    FOREIGN KEY(run_id) REFERENCES schedule_runs(run_id));
CREATE INDEX IF NOT EXISTS idx_schedule_run_animals_animal_run
    ON schedule_run_animals (animal_id, run_id);
```

- **Values.** `outcome` ∈ {running, completed, stopped, incomplete,
  interrupted}; `end_reason` ∈ {completed, stopped, ended_short,
  interrupted}; Python validates both. No CHECK: a new value would need a
  table rebuild, a one-way migration.
- **Copies, not links:** no foreign key to `schedules`, `animals` or
  `relay_units`, which the history outlives. The declared ones are inert:
  no Project code enables `PRAGMA foreign_keys`, and a migration runner
  that does must re-check deleting a trainer who owns runs. Latest = the
  highest `run_id`, so a clock jump cannot reorder runs.
- **Revert-safe.** Additive, idempotent DDL that older releases never read:
  no `sqlite_master` scan, and the two `SELECT s.*` / `w.*` read other
  tables (`database_handler.py:1072, :1527`). The `animals` columns, the
  ledger and `log_delivery` are unchanged.

**Where the code lives:** `Project/models/schedule_runs_repo.py`
(`RUN_OUTCOMES`, `RUN_END_REASONS`, `LAST_RUN_COLUMNS`, `LAST_RUN_JOIN`,
`last_run_from_row`, `ScheduleRunsRepo(connect)`), behind the facade
below; nothing else leaves `database_handler.py`. CLAUDE.md's R2 trigger 1
fired at its borderline (about 186 code lines); the owner approved the
module (§14, item 14), and PR 5 logs it in
[DATABASE_HANDLER_REFACTOR_DESIGN.md](DATABASE_HANDLER_REFACTOR_DESIGN.md) §11.

| `DatabaseHandler` method | Contract |
|---|---|
| `start_schedule_run(schedule_id, schedule_name, delivery_mode, started_by, animals) -> int \| None` | `animals` = `[{'animal_id', 'relay_unit_id', 'requested_ml', 'planned_ml'}]`; one transaction; None, with nothing written, on an empty list or a DB error |
| `finish_schedule_run(run_id, end_reason, results, stopped_by=None, relays_confirmed_off=None, worker_exited=None) -> bool` | `results = {animal_id: (delivered_ml or None, outcome)}`; True only when this call closed the run; False when it is already closed or unknown, or the DB refused (a lock held over about 5 s); a missing animal is closed `incomplete` with NULL; an unknown value raises ValueError before any write |
| `mark_interrupted_schedule_runs() -> int` | `running` → `interrupted`, `delivered_ml` NULL, `ended_at` = now |
| `get_latest_runs_of_schedule(schedule_id, animal_ids) -> {int: dict}` | each animal's latest run **of this schedule**: the `last_run` keys plus `lab_animal_id`; `{}` on an empty input or a DB error |

**Read path.** `get_all_animals` / `get_animals_by_trainer` gain a LEFT
JOIN on each animal's MAX(`run_id`), still one SELECT. `Animal.last_run`
(dict or None) carries only what the UI reads: `run_id`, `schedule_name`,
`delivery_mode`, `started_at`, `ended_at`, `outcome`, `relay_unit_id`,
`requested_ml`, `planned_ml`, `delivered_ml`; no join on `trainers`.

---

## 5. Recording a run (PR 7)

```
Run click   job_in_progress = True → try_acquire(SCHEDULE) → singleShot(prepare, token)
            ↳ CLOSE ALL RELAYS, Close Selected, Log Out: greyed and refused from here
prepare     token current? → refusals → at most ONE question (§9)
            → calibration gate → main.run_program() → True (thread started) / False
first due   worker thread, _handle_delivery → _open_run_record():
delivery    run_plan built → start_schedule_run() → rows 'running'
end         natural, circuit breaker, error: worker.finished (queued, bound to w)
            → _on_run_finished(w) → _record_run_end(w)   (skipped if stop_reason == 'operator')
            Stop: main.stop_program(): w = worker; w.stop_reason = 'operator';
            execute_stop_sequence() → StopResult → _record_run_end(w, result) + one logs row
close       _record_run_end (GUI thread, once per worker, never raises)
            → finish_schedule_run() → deferred Animals-tab reload
next start  main.setup() / _create_gui_from_components(): mark_interrupted_schedule_runs()
            before the GUI is built (never in create_tables)
```

- **Opens at the first due delivery,** the only first-dispatch path being
  `_handle_delivery` (`relay_worker.py:1759`): a run stopped before
  anything was due leaves the previous record. A failed write prints a
  Terminal line, and the deliveries go on. `run_plan` = `{animal_id:
  {relay_unit_id, requested_ml, planned_ml, q_ml, complete_ml}}` covers
  every instant delivery, past ones included, or each staggered animal
  with a target above 0 (`relay_worker.py:590-599`).
- **Closes once per worker** (`run_end_recorded`). An operator Stop is
  recorded by `stop_program` with its StopResult, since the queued
  `finished` can run inside Stop's event pump (`main.py:536`).
  Reconciliation stays out of `create_tables`, which `--selftest`
  (`main.py:139`) and `tools/set_valve_topology.py` run while RRR may be up.
- **Hot-path cost:** one attribute check per delivery, and one INSERT
  transaction at a run's first dispatch on the worker thread, as the ledger
  writes are [SD-card cost NEEDS CONFIRMATION]. Stop adds one UPDATE and
  one `logs` INSERT after the relays are off, Run one indexed read (§9).
  The pulse loop gains only S6's two cancel checks; `log_delivery` is
  unchanged.

**The outcome rule** (D2), per animal; `complete_ml` is fixed at the first
dispatch. An animal below its threshold is `stopped` (operator Stop) or
`incomplete`.

| Run | `completed` iff delivered ≥ | Basis |
|---|---|---|
| Staggered, any mode | scheduled − `_completion_tolerance_ml`: max(0.01, q/2) under nearest, 1e-6 under round-up, 0.01 without a quantum | the worker's own completion test (`relay_worker.py:_completion_tolerance_ml:1115-1161`, used at `:1358`) |
| Instant, pulse mode | min(planned − q/2, scheduled − tol), tol as for staggered with a quantum | D2, or the worker's tolerance of the ask: a retry re-plans the ask minus what was dispensed (`relay_worker.py:_quantize_to_pulses:873-880`) |
| Instant, pump or continuous | planned − 0.01 (planned = scheduled) | D2's non-pulse case |

- The comparison has a 1e-9 slack. `end_reason` is `completed`, `stopped`
  or `ended_short`; only reconciliation sets `interrupted`.
- **One pulse short is red,** except where RRR's own completion test counts
  the animal done, under nearest: at an exact half-pulse tie (PR 6 rounds
  the plan up, so one pulse less is scheduled − q/2), or below 0.02 mL per
  pulse (the 0.01 mL floor exceeds half a pulse). The production 0.034164
  mL per pulse meets neither. Off-grid credits the worker accepts (late
  close, sensor blend) are never red: none in 1092 + 1040 probe deliveries.

**Audit row.** One `logs` row per operator Stop, through
`log_action(trainer_id or 0, 'schedule_stopped', details)`
(`database_handler.py:1015`); none for a Stop during "Starting…":

```
AM water (schedule 12, run 41) stopped by alice: animal 3 0.410 of 0.410 mL planned; animal 5 0.410 of 0.991 mL planned. Relays confirmed off: yes; worker exited: yes
```

---

## 6. Stop (PR 2)

Stop becomes the only way to end a run, so it takes over CLOSE ALL
RELAYS' safety duties.

| | Change | Fixes |
|---|---|---|
| S1 | Cancel the worker right after the first all-off, before the dialog pumps events | a pulse starting after the all-off |
| S2 | All relays off again after the teardown (when a worker or thread existed); that last command decides "confirmed off" | `cleanup()`'s later all-off is only printed (`main.py:462`) |
| S3 | The latch: when `not result.safe`, SCHEDULE passes to EMERGENCY in one step (`OperationLock.hold_until_safe`), before `reset_ui` and any dialog. Run, Change Relay Hats, priming, calibration and topology changes stay refused until a confirmed CLOSE ALL RELAYS or a restart | `reset_ui` releasing the lock regardless |
| S4 | One dialog: **Relays Not Confirmed Off** or **Delivery Worker Did Not Stop** | two dialogs, or none |
| S5 | Run refuses beside a live worker thread, keeps its reference and latches (**Delivery Worker Did Not Stop**); another failed start says **Schedule not started**; `main.cleanup` keeps a running thread | dropping a running QThread |
| S6 | A cancel check before the manifold prime and before the master hold | a Stop reopening the master (`solenoid_flow_strategy.py:1125, :1208-1210`) |
| S8 | A Stop during "Starting…" cancels the queued start (a run token) | a start that launches after the Stop, which nothing could end once CLOSE ALL no longer stops schedules |

- `execute_stop_sequence(handler, worker_obj, thread_obj, signals,
  dialog_factory=None)` returns `StopResult(relays_confirmed_off,
  worker_exited)` with `.safe`; `on_unsafe` goes. `main.run_program`
  returns whether the thread started; `main.stop_program` never raises. A
  Stop that fails before the sequence runs leaves the job and Stop live.
- S7 of the approved plan (Stop without a login) is dropped for D3. No
  valve stays open after Stop returns, but one may still open briefly (the
  hold, or one pulse of at most 30 ms) before the worker's next check
  [NEEDS CONFIRMATION on a rig].

---

## 7. Who can end a run (PRs 3, 4)

CLOSE ALL RELAYS, Close Selected and Log Out are unavailable exactly while
a schedule job is in progress: from the Run click ("Starting…"), through a
staggered run waiting for its window, to the end of the run or of Stop.

| State | `job_in_progress` | Lock | CLOSE ALL RELAYS / Close Selected | Log Out |
|---|---|---|---|---|
| Idle | False | none | enabled | enabled |
| Priming | False | PRIMING | enabled | enabled |
| Calibration | False | CALIBRATION | behind the modal wizard (as today) | as today |
| Run click → end of the run or of Stop | True | SCHEDULE | **greyed + refused** | **greyed + refused** |
| After an unsafe Stop | False | EMERGENCY | enabled: a fresh handler; clears the latch only when every relay is confirmed off | enabled |
| Stale SCHEDULE hold | False | SCHEDULE | enabled (force-release failsafe) | enabled |

- **Two layers** (`operation_lock.py:19-23`): greyed with the tooltip "A
  schedule is running: press Stop to end it", and refused first thing in
  each handler (**Schedule running**). The predicate,
  `RunStopSection.job_in_progress`, replaces `PrimingControlWidget`'s
  `stop_schedule` (as `schedule_running`) and reaches `UserTab`
  (`gui.py:182`); PR 3 sets it **before** `try_acquire(SCHEDULE)`. Stop
  needs a login (`run_stop_section.py:233`), hence D3.
- **CLOSE ALL RELAYS no longer stops a schedule;** its all-off, fresh
  handler, latch and failsafe stay, and Close Master is unchanged. The
  `[VALVE CRITICAL]` alarms end "Check the rig; the Stop button switches
  every relay off and stops the schedule." A cage change keeps Close
  Selected greyed; `QPushButton[variant="danger"]:disabled` keeps a greyed
  CLOSE ALL RELAYS from painting red.

---

## 8. Animals tab and export (PRs 8, 9)

The last column, **Last schedule delivered amount**, shows `last_run`
(D4), volumes to three decimals:

| Outcome | Cell | Red |
|---|---|---|
| none | `—` | no |
| running | `Running · {planned} mL planned` | no |
| completed | `{delivered} mL` | no |
| stopped | `Stopped · {delivered} / {planned} mL` | yes |
| incomplete | `Incomplete · {delivered} / {planned} mL` | yes |
| interrupted | `Interrupted · ? / {planned} mL` | yes |
| a newer release's value, after a revert | `{Outcome} · {delivered} / {planned} mL` | yes |

- **Tooltip:** the schedule, when the run ended ("2 hours ago (YYYY-MM-DD
  HH:MM)"; an interrupted run by its start), and `Scheduled:`, `Planned:`,
  `Delivered:` lines. A red staggered cell gives the remainder (scheduled −
  delivered) for a new schedule; a red instant cell points to the delivery
  log first (§14, item 8). An unknown amount shows "?" and the command to
  type on the Pi (D10): `cd ~/rrr/current/Project &&
  ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py daily --since
  <YYYY-MM-DD> --cage <n>`.
- **Drawing (D9).** A `QStyledItemDelegate` fills the cell with `alertFill`
  and draws `alertText`, `pyqtProperty(QColor)` values from the QSS
  (`QWidget#AnimalsTab { qproperty-alertFill: #DC2626; qproperty-alertText:
  #FFFFFF; }`, both themes; 4.83:1, WCAG AA). A status word, never colour
  alone; the text stays in the item for the filter and selection.
- **Layout and refresh.** `len(COLUMN_WIDTHS)` replaces the 7s, and the
  columns 5–6 widening goes. The tab reloads after a run and when
  selected, keeping filter and selection. The words live in the Qt-free
  `utils/last_run_text.py`, shared with the export and D5.
- **Export Animals to CSV** gains `Last Schedule`, `Last Schedule Result`,
  `Last Schedule Scheduled (mL)`, `Last Schedule Planned (mL)`,
  `Last Schedule Delivered (mL)`, `Last Schedule Started` and
  `Last Schedule Ended`. Delivered is empty when unknown (never 0), and
  Ended is empty for an interrupted run.

---

## 9. Run warnings (PRs 10, 11)

Run asks at most one question, after the **Expired Schedule** refusal: the
window note and a last-run paragraph go inside it, never into a second
dialog. Each question is plain text with Cancel as the default and Esc
button; every Cancel goes through `_reset_run_button`. The words live in
Qt-free `utils/run_warnings.py`.

| Mode | Times passed? | Last run of this schedule | Question |
|---|---|---|---|
| Staggered | start passed | none, or no water went out | **Schedule Start Time Passed** (unchanged) |
| Staggered | either | ended early (any animal) | **Last Run Ended Early**, with the window note when the start has passed |
| Staggered | either | completed (no animal ended early) | the completed-run question (PR 11 words it), with the window note when the start has passed |
| Instant | some passed | any | **Some Deliveries Passed**, with a last-run paragraph when the last run ended early or completed |
| Instant | none passed | ended early or completed | **Last Run Ended Early**, or the completed-run question |

Any other case asks nothing. An instant schedule whose last run completed
has all its delivery times behind it, so **Expired Schedule** refuses it
first (`run_stop_section.py:492-500`). Only an edit that moves its times
brings it to the instant rows: the edited schedule keeps its `schedule_id`,
and so its run history (`schedules_hub.py:288, :298`).

**Some Deliveries Passed** (D6; **Start Run** / Cancel) replaces today's
Yes/No question (`run_stop_section.py:502-516`). RRR creates one delivery
per animal (`schedule_wizard.py:336-341`; the editor refuses more,
`schedules_hub.py:136-145`):

```
2 of 4 deliveries of "PM water" have already passed. This run skips them:
• M-011, cage 3: 08:00 passed, nothing from this run (0.250 mL scheduled)
• M-012, cage 4: 11:00 passed, nothing from this run (0.300 mL scheduled)

This run delivers 0.600 of the 1.150 mL scheduled. For the animals above, the Animals tab will show this run in red as incomplete.

Start the 2 deliveries still ahead?
```

**Last Run Ended Early** (D5; **Start Over** / Cancel) appears when an
animal's latest run **of this schedule** is `stopped`, `incomplete`,
`interrupted` or a leftover `running`, and some water went out (delivered
above 0, or unknown). It lists every animal that got water, completed ones
too, since Start Over doses them again ("M-011, cage 3: 0.410 of the
planned 0.991 mL, stopped at 10:32; remaining 0.590 of the 1.000 mL
scheduled"), and says to create a new schedule for the remaining amount.

- **Instant schedules:** re-running skips the passed times
  (`relay_worker.py:496-527`), so their lines carry no remainder and add
  "Passed deliveries are skipped, never repeated."
- **A completed last run** gets the completed-run question (the owner's
  choice on refinement 7; PR 11 words it), placed as the table shows: Run
  would otherwise give every animal its full amount again unasked.
- **One indexed read** (`get_latest_runs_of_schedule`) per Run; if it
  fails, a Terminal line is printed and the question skipped.

---

## 10. Edge cases

| Case | Behaviour |
|---|---|
| Stop pressed repeatedly | `stop_program` returns without a job; `RelayWorker.stop` is idempotent; one record close per worker |
| Stop before the first delivery | No record; one "before its first delivery" audit row |
| Crash or power loss | `running` until the next start marks it `interrupted`; that start's HAT set-up switches every relay off (`gpio_handler.py:_initialize_hats:162, :181`) [whether a HAT holds its outputs through a power loss NEEDS CONFIRMATION] |
| Relays not confirmed off | Outcome from the credited volume; `relays_confirmed_off` = 0; Stop latches. A valve stuck open cannot be measured |
| An abandoned worker holds the DB lock | The finish returns False after about 5 s; the tab shows **Running** until the next start marks the run `interrupted` (errs red) |
| Schedule edited or deleted | The run keeps its copied name and figures |
| Instant animal whose only delivery had passed (Q5 × Q7) | In the run with delivered 0, `incomplete`, red, even if an earlier run watered it; **Some Deliveries Passed** says so first |
| Revert to 1.21.x | Tables ignored; CLOSE ALL RELAYS as in 1.21.x; runs there are not recorded |
| Two RRR versions at once | The other would mark a live run `interrupted`; the single-instance guard is per version (`main.py:791`), and updates are refused during a run |

---

## 11. Limitations

- **Delivered is credited, not weighed;** nothing reads a relay back. A
  pulse cut by Stop is credited whole (at most one pulse over) [NEEDS
  CONFIRMATION physically]; a terminated worker never credits its attempt
  in flight, so delivered is then a lower bound.
- **Continuous and pump modes** cannot be cancelled mid-delivery; every
  start resets to solenoid pulse mode, so they stay documented, not fixed.
- **The Execution Monitor is unchanged:** "Incomplete" below 95 %
  (`ScheduleProgressTracker.py:464`), and an instant animal's target is the
  all-animal total (`run_stop_section.py:784`).

---

## 12. Delivery plan

**Version: 2.0.0 (MAJOR),** by
[MAINTENANCE.md §2](MAINTENANCE.md#2-picking-the-version-number--semver-for-rrr) (D11):

- **Data: MINOR** (two auto-created tables that older releases ignore;
  MAINTENANCE.md:83, :101). **Behaviour: MAJOR.** Operators **must** end a
  run with Stop, though 1.21.0's notes and alarms say CLOSE ALL RELAYS does
  (CHANGELOG.md:83-88), and **must** stop or wait before logging out: two
  "Operators must…" lines (MAINTENANCE.md:118-121, :127). The set-up-step
  exception (:128-132) does not apply; ties go higher (:133-135).
- **Stop and ask (MAINTENANCE.md:105-108):** it cannot be designed
  backwards-compatible. The owner's request (CLOSE ALL RELAYS and Close
  Selected unavailable during a run) and Q4 (logout blocked) *are* the
  incompatible changes; the data side is revert-safe (§4).
- **No cost, no `-beta`:** the updater compares integer tuples
  (`updater.py:31-49`); `/releases/latest` excludes pre-releases
  (`updater.py:27`), and TOPOLOGY_VALIDATION.md:12 forbids `-beta` on rigs.

**The train,** in merge order; release-bound subjects end "(v2.0.0)":

| Order | PR | Branch | Version |
|---|---|---|---|
| any, best before 2 | 0 Installer re-exec after the pull | `fix/installer-reexec-after-pull` | none; untagged |
| 1 | 1 This record; the MAINTENANCE §3a one-bump sentence | `docs/stop-partial-delivery-design` | none (§3c) |
| 2 | 2 Stop hardening, S1–S6 + S8 (§6) | `fix/stop-takes-over-close-all` | **sets 2.0.0**, opens `## 2.0.0` |
| 3 | 3 CLOSE ALL RELAYS / Close Selected unavailable mid-run (§7) | `feat/close-all-priming-only` | adds lines |
| 4 | 4 Log Out blocked mid-run (§7) | `feat/block-logout-during-run` | adds lines |
| 5 | 5 Run-history tables, facade, `Animal.last_run` (§4) | `feat/schedule-run-history` | adds lines |
| 6 | 6 One whole-pulse rounding (D1) | `fix/round-half-pulse-ties` | adds lines |
| 7 | 7 Record each run, reconciliation, audit row (§5) | `feat/record-schedule-runs` | adds lines |
| 8 | 8 Animals-tab column, red cell, Help (§8) | `feat/animals-last-schedule-column` | adds lines |
| 9 | 9 CSV export columns (§8) | `feat/export-last-schedule` | adds lines |
| 10 | 10 Some Deliveries Passed (§9) | `feat/warn-instant-passed-deliveries` | adds lines |
| 11 | 11 Last Run Ended Early and the completed-run question (§9) | `feat/run-warns-stopped-schedule` | adds lines |
| 12 | 12 Headless integration test | `chore/stop-partial-delivery-integration-test` | none (test-only) |
| 13 | 13 Operator docs, smoke test, release notes | `docs/v2-0-0-operator-docs` | finalises the entry |
| T | Tag `v2.0.0` on the validated SHA, at the owner's go | — | — |
| later | Palette B | its own series | **2.1.0**, merged after the tag |

- **PR 3 never merges before PR 2** (the latch and the second all-off). A
  partial train is never tagged; the smallest safe release is PRs 1–4.
- **One bump per release:** only PR 2 edits `version.py`; the other PRs add
  their lines under `## 2.0.0`, as v1.21.0's train did. PR 1 writes this
  into MAINTENANCE §3a. A code fix found while validating the merged
  candidate follows §3b (2.0.1, folding 2.0.0 into its entry, tag
  `v2.0.1`); doc-only and test-only fixes do not bump.
- **No v1.21.1 tag:** PR 0 is tooling-only (CONTRIBUTING.md:106-107):
  `install.sh` and `bootstrap.sh` are not shipped (:111-113), and the
  in-app update never runs the bundle's `scripts/install`. It ships
  untagged, with a line in the 2.0.0 entry.
- **Palette B is v2.1.0,** merged after the 2.0.0 tag (from PR 2 on, `main`
  says 2.0.0), carrying the QSS rules of §7 and §8.
- **Before the tag,** on the final SHA with CI green (`ubuntu-24.04`,
  #190): MAINTENANCE §5 on the home Pi as PR 13 extends it; a wet check
  weighing a stopped staggered run against the cell and
  `gravimetric_check.py daily` (§14, item 17); every rig that ran the
  candidate goes back to v1.21.0 before the tag and updates in-app after.
- **Rollback:** **Revert to previous version** keeps the database and is
  refused during a run (`updater.py:revert:393-414`); the launcher reverts
  after two failed starts. Older releases ignore the tables; back on 2.0.x
  an open run becomes `interrupted`. A bad published release gets the next
  PATCH (MAINTENANCE §6.3).

---

## 13. Out of scope

Item (d) (a full dose logged `partial`); the Execution Monitor's targets
and 95 % rule; the continuous and pump Stop gaps; a stalled staggered run;
the dead `update_schedule_status` / `get_schedule_progress`; a real resume
(Q6). Backlog: the `.xlsx` export's openpyxl dependency; MAINTENANCE §2's
beta-channel wording; `gui.closeEvent` after an abandoned worker; a click
guard for Change Relay Hats; two simultaneous "Stopping" dialogs; a
session-scoped `qapp` fixture; D5/D6 counts one short when a delivery
comes due during a question; the Run questions after the refusals; the
I²C coordinator's sleep under its lock; a sensor-mode cancel check after
the sensor restart; a note in Emergency Controls during a run; Help's
stale "Access and Modes" guest sentence; editable Animals cells; the dark
zebra rows (palette B).

---

## 14. Refinements acknowledged

Where the design departs from a literal answer or the approved plan. The
owner acknowledged every item on 2026-10-09; the choices made are shown.

| # | Refinement | Reason |
|---|---|---|
| 1 | The outcome rule is per mode (§5), not planned − q/2 alone | Credits land off the pulse grid (a late close: 14.30 of 15 pulses, which the worker calls done). The literal rule made 30 of 390 sensor-blended windows and 91 (nearest) / 84 (round-up) of 462 retried instant deliveries red. The one-pulse exception is Q2's "worker's whole-pulse tolerance" |
| 2 | PR 6 changes dosing at exact half-pulse ties: one pulse more, at most q | 74 of 6000 surveyed windows change, only at few-digit calibrations; production meets none. Older ledger rows at ties re-grade as `mismatch`. **Accepted** |
| 3 | A delegate, not the approved plan's QLabel cell widget | A cell widget paints a band inside the padding and `setForeground` turns teal when selected; a delegate fills the cell and follows the theme |
| 4 | 2.0.0 MAJOR, not "next MINOR" | MAINTENANCE §2 (§12). **Chosen:** 2.0.0, then palette B as 2.1.0 |
| 5 | No v1.21.1 tag | The app would be identical to 1.21.0. **Chosen:** PR 0 ships untagged |
| 6 | D3 trade-off | A staggered run waiting days keeps its user logged in (a second operator works in that session), and CLOSE ALL RELAYS, Close Selected and Log Out grey, until someone presses Stop |
| 7 | D5 extensions: interrupted and leftover `running` runs warn; completed animals are listed | Start Over doses them again. **Chosen:** Run also warns before re-running a schedule whose last run completed (PR 11) |
| 8 | Instant advice differs from D5's "delivers the full amount again" | Re-running skips passed times, so the operator checks the delivery log before a remainder schedule (no double water); the Q5 × Q7 case follows (§10) |
| 9 | The D5 reader is `get_latest_runs_of_schedule`; `get_latest_schedule_runs` is not added | Nothing would call it |
| 10 | S8 uses a run token, not a `job_in_progress` re-check | The queued start ran inside Stop's event pump while the flag was still True |
| 11 | One bump per release; a validation fix follows §3b | 102c136a (#149) set 1.21.0, and the 39 PRs merged after it did not bump. Unlike #187 and #189 (kept at 1.21.0), a validation fix bumps to 2.0.1, so every candidate on a device has its own number |
| 12 | Unknown means unknown | "?" and the log command for any unrecorded amount. An interrupted run's `ended_at` is the restart time, so the tooltip dates it by `started_at` and the export's Ended is empty |
| 13 | No audit row for a Stop during "Starting…" | No worker existed, and nothing ran |
| 14 | CLAUDE.md R2 trigger 1, at its borderline | **Chosen:** the module `models/schedule_runs_repo.py`, minimal, behind the facade (§4). R1 is not paired: `CREATE TABLE IF NOT EXISTS` migrates nothing |
| 15 | Reload on tab change and after a run, no new signal | A tab on screen at the first delivery shows **Running** at the next tab change |
| 16 | The latch keys on `StopResult.worker_exited`, not `updater.is_busy()` | Both read the same QThread and agree in every reachable case |
| 17 | Wet validation | An untagged candidate goes on a rig with an animal, or in TOPOLOGY_VALIDATION, only with the owner's OK. **Chosen:** OK; such rigs return to v1.21.0 before the tag |
