# Changelog

Curated, operator-facing summary of each **published** RRR release (a
release = a git tag `v<x.y.z>` with a `.rrrupdate` bundle devices can
install via the in-app Updates tab), newest first. Most releases get one
line. A release that asks something of the operator starts with a
**Before you update** list. A version number that was set on `main` but
never tagged is folded into the next release's entry.

The release workflow publishes the tagged version's entry from this file,
verbatim, as the GitHub Release notes, and the in-app Updates tab shows
them. Versioning follows SemVer for RRR — see
[Project/docs/MAINTENANCE.md §2](Project/docs/MAINTENANCE.md#2-picking-the-version-number--semver-for-rrr).
Test-only / doc-only / tooling-only changes do not get a release and are
not listed here.

---

## 1.21.0 — valve topology, calibration gate, relay-failure reporting

This release also carries 1.18.1, 1.19.0 and 1.20.0, which were numbered
on `main` but never released.

**Before you update**

- **Calibrate every cage your schedules use.** In solenoid pulse mode (the
  default), Run refuses a schedule that waters a cage with no usable
  calibration measured under this device's valve topology (**Valve
  calibration needed**), and the dialog names those cages. Until now such a
  cage was dosed at a guessed ~0.026 mL per pulse, about 30 % too much
  water on the production valve. Before updating, open Settings >
  Calibration and calibrate every **Not Calibrated** row a schedule uses.
  After updating, look again before the next Run: this release also marks
  a calibration it cannot use as **Invalid**, and on a two-HAT device it
  lists cages 16–31 for the first time. Those cages could not be
  calibrated before, so allow about 10 minutes for each one a schedule
  uses.
- **A shared-manifold rig needs no other change.** Valve Topology defaults
  to *Shared manifold (master valve)*, calibrations made before this
  release count as shared-manifold ones, and a clean delivery drives the
  relays exactly as before.
- **Check the Slack token.** An older Settings bug blanked the stored Slack
  token whenever any setting changed. This release stops that, but it
  cannot bring back a token that is already gone. If notifications stopped,
  enter the token again in Settings > General > Slack Integration. It takes
  effect without a restart.

**What changes on the device**

- **Add (safety):** Run refuses a schedule while any cage it waters has
  - no calibration;
  - a missing, zero or invalid volume per pulse or pulse width;
  - a calibration measured under the other valve topology;
  - or is not a cage on this device (dialog **Cage not on this device**:
    edit the schedule).

  The dialog lists each cage and why. Calibrate those cages in Settings >
  Calibration, then press Run again. This applies in solenoid pulse mode
  (the default).
- **Fix (safety):** a relay command that does not reach its HAT is
  reported, and only water from a valve that actually opened is counted.
  - A delivery stops at the first valve command that did not switch, or
    at a pulse that failed for any other reason (`[VALVE ERROR] cage N:
    …; delivery stopped after …` in the Terminal tab). Only pulses whose
    valve opened are credited, and the retry asks only for the rest. The
    same line reports a dose refused or cut short by the pulse or time
    limit.
  - A close that does not reach its relay is retried twice at once, then
    after 20, 50 and 100 ms. A pulse whose close got through late is
    credited with the time its valve stayed open, at the valve's steady
    flow.
  - `[VALVE CRITICAL] … OPEN` has two wordings: *the valve may still be
    OPEN* for a valve seen to open whose close did not get through, and
    *the … valve's relay is not answering, so the valve cannot be confirmed
    closed; it may be OPEN* for a valve whose relay has not answered since
    the run started. A dead HAT therefore alarms. If a later close gets
    through, `[VALVE OK] … closed after all` clears the alarm.
  - Pump relays that do not switch off are retried once, then
    `[VALVE CRITICAL] relay unit N: …` says they may still be ON.
  - When the relays cannot be confirmed off, CLOSE ALL RELAYS shows
    **Emergency Stop Failed** and Stop shows **Relays Not Confirmed Off**.
    Both say to disconnect the valve power supply.
  - CLOSE ALL RELAYS (Settings > Priming) now also stops a running
    schedule. Before, the schedule carried on and opened its valves again
    at its next pulse. The stopped schedule does not resume: animals it
    had not finished watering get no more water from it, and Run starts
    it over (a staggered schedule gives every animal its whole dose
    again; an instant schedule skips the times that have passed).
  - CLOSE ALL RELAYS frees the hardware lock only when every relay is
    confirmed off and nothing is still running. After **Emergency Stop
    Failed** the hardware stays locked (Run and calibration unavailable)
    until a later press is confirmed or RRR is restarted.
  - The calibration wizard stops at a pulse whose valve did not open or
    close. Do not save a measurement from that run.
  - Esc in the calibration wizard stops the pulse run, as the window's X
    does. Before, Esc closed the window and the run carried on to its
    last pulse. A run that cannot be stopped (a relay command that does
    not return) keeps the hardware locked and shows **Calibration Did Not
    Stop**.
  - Priming keeps its session and the hardware lock while a cage valve
    may still be open after Close Master, until that valve is confirmed
    closed. While such a valve may be open, a failed Open Master does not
    free them either.
- **Fix (safety):** with the first HAT missing, relay commands are no
  longer shifted onto the next HAT, where they drove another animal's
  valve.
- **Fix (safety):** after Change Relay Hats, Priming (CLOSE ALL RELAYS
  included) uses the new HAT count and lists its cages. Before, it kept
  the relay handler it first built until RRR was restarted, so CLOSE ALL
  RELAYS did not switch a HAT added since and still reported every relay
  closed. Restoring a settings backup no longer changes the relay layout
  (the number of HATs, the master relay and the cage relays): change the
  number with Change Relay Hats.
- **Fix (safety):** starting RRR while it is already running (a second
  click on its icon, for example) brings the running window to the front,
  instead of opening a second RRR beside it that drives the same relays.
  Before, RRR stopped noticing such a start shortly after it opened.
- **Add:** a **Valve Topology** choice in Settings > Delivery > Solenoid
  Mode Settings.
  - *Shared manifold (master valve)*: the production rig, where relay 16
    opens a master valve around every delivery.
  - *Independent (one syringe and one valve per animal)*: relay 16 stays
    reserved, is never driven, and should be left unwired.

  The choice is greyed out while a schedule, priming or calibration runs.
  After a change, Priming cannot open a valve until RRR is closed and
  reopened. Every start prints `[TOPOLOGY] Valve topology: …`.
- **Add:** each calibration records the topology it was measured under.
  Settings > Calibration marks a calibration measured under the other
  valve topology **Stale**, and Run refuses it. After switching the
  topology, recalibrate every cage.
- **Add:** Settings > Calibration marks a stored calibration whose volume
  per pulse or pulse width is missing, zero or invalid **Invalid** (red),
  and highlights its Recalibrate button; Run refuses it too. The table's
  statuses are now [OK], Stale, Invalid and Not Calibrated. **Calibrate
  All Uncalibrated** also runs the Stale and Invalid rows, and the CSV
  report marks Invalid rows `Invalid`. A missing CV shows as a dash
  instead of breaking the table.
- **Change:** on an independent rig, Priming hides the master controls,
  and opening a cage valve primes that animal's line. The Cages tab, the
  schedule wizard and Help describe relay 16 as reserved and unused. The
  Priming banner and the calibration checklist name the animal's syringe
  instead of the reservoir.
- **Add:** *Round doses up to the next whole pulse* in Settings >
  Delivery > Pulse Mode, off by default. With it on, a dose lands at most
  one pulse over its target instead of within half a pulse either side
  (1.19.0).
- **Fix:** a staggered window no longer fires one extra pulse from a
  rounding leftover (1.18.1).
- **Fix:** an instant delivery retried after a partial delivery sends
  only the rest. Before, it fired the whole dose again: 28 pulses for one
  0.6 mL dose.
- **Fix (two-HAT devices):** cage 16 can be scheduled (the wizard refused
  it as the master relay). Settings > Calibration, Calibrate All
  Uncalibrated, the CSV export and the wizard cover all 31 cages and drive
  each cage's real relay. Calibrate All Uncalibrated runs the whole batch
  instead of stopping after the first cage. The Calibration table
  refreshes after Change Relay Hats.
- **Fix:** the Hardware Mode choice is greyed out and refused while
  anything drives the hardware. Restoring a settings backup no longer
  changes the hardware mode or the valve topology.
- **Fix:** an unknown hardware mode is refused instead of running the
  pump strategy.
- **Fix:** a Slack token saved in Settings is kept and used at once.
  Auto-save no longer blanks it, and no longer fails for the rest of the
  session after a token is typed.
- **Fix (installer):** `install.sh --dry-run` runs to the end; a warning
  printed before its first section used to stop it. It also no longer
  leaves an empty `vendor/` folder in the checkout. The install's final
  check scans for the relay HAT (it skipped the scan for a normal user)
  and warns when the HAT is jumpered to a stack level other than 0, which
  RRR cannot use. `scripts/runtime/diagnose.sh` finds the installed Python
  environment and lists the relay HATs with their stack levels.
- **Change:** the Updates tab shows a release's notes formatted (headings,
  bold, lists), from the top and in the tab's full height, instead of as
  raw Markdown in a small box. The notes are the release's entry in this
  file.
- **Change:** each delivery record (`dispensing_history`) also stores the
  dose asked for, the rounding policy, the schedule mode, the valve
  topology, the calibration used, the pulse timing, the duration and the
  app version. The new columns are added automatically at the first start;
  older rows leave them empty.

**If something goes wrong**

- A HAT that was not found when RRR started stays missing until RRR is
  restarted. Fix the HAT or its I²C cable, then close and reopen RRR.
- **Emergency Stop Failed**, **Relays Not Confirmed Off** or `[VALVE
  CRITICAL]`: disconnect the valve power supply first, then check the
  relay HAT and its I²C connection.
- Rolling back on an independent rig: set Valve Topology back to *Shared
  manifold* before **Revert to previous version**. Releases before 1.21.0
  ignore the setting and drive relay 16 on every delivery.

**Developer notes**

- The release workflow publishes this file's entry for the tagged version
  as the GitHub Release notes, which the Updates tab shows. The test suite
  fails while `Project/version.py` names a version with no entry.
- `utils/topology.py` is the single decision point: `build_solenoid_controller`,
  `cage_map_from`, `calibration_is_stale`, `reserved_relay_reason`.
  `IndependentSolenoidController` has `has_master = False` and makes no
  relay writes for master operations. Master and cage relay ids below 1 are
  refused. (The `valve_topology` setting, `build_solenoid_controller` and
  `IndependentSolenoidController` were 1.20.0; the other helpers and the
  Settings control came with 1.21.0.)
- `utils/calibration_gate.py` (Qt-free) holds the Run gate, called from
  `RunStopSection._passes_calibration_gate`. The strategy's ~0.026 mL/pulse
  fallback and its use of stale rows stay only as a defence in depth.
- `RelayHandler.set_relays` / `set_all_relays` return False when a relay
  did not switch, and HATs are held one slot per stack. The pulse loop
  raises `ValveCommandError`. `FakeRelayHandler` reports a lost write as
  False. `test_topology_trace.py` pins the relay-write trace of both
  topologies.
- On a machine without the vendor relay library (a dev Mac), no HAT
  initialises, so schedule runs there now fail their deliveries instead of
  reporting success.
- Pump mode credits the triggers that fired, at pump volume ÷ calibration
  factor. This also changes a successful pump run's credit when the factor
  is not 1.0.
- `StrategyFactory.create` accepts only `solenoid` and `pump` and raises on
  anything else; `RelayWorker` resolves a missing mode to `solenoid`.
- `main.py` no longer builds a second, hidden `SettingsTab`, so
  `gui.settings_tab` is the visible one.
- `valve_calibration` and `valve_calibration_history` gain `topology`.
  `dispensing_history` gains `topology`, `calibration_id`,
  `pulse_width_ms`, `inter_pulse_interval_ms`, `duration_s`, `app_version`,
  `volume_requested_ml`, `dose_rounding` and `delivery_mode`. All are
  nullable and added by the PRAGMA-guarded migrations.
- Bench tools:
  - `tools/set_valve_topology.py`: CLI, run with the app closed; it also
    detects an app started from the desktop icon.
  - `tools/gravimetric_check.py` and `tools/topology_compare.py`: grade
    against `volume_requested_ml`.
  - The criteria are in `Project/docs/TOPOLOGY_VALIDATION.md`.
- Removed: `tools/valve_calibration_tool.py` (it could not start),
  `PulseCalibrator`, and the unused `gpio/mock_gpio_handler.py`.
- CI also runs the unit suite on Debian Bookworm with Python 3.11.
- `scripts/install/test_install.sh` recognises a dry run that reached its
  end; it looked for a message the installer stopped printing in May 2026,
  so it failed every run. It checks that the dry run leaves the release
  tree, the venv, `vendor/`, `dist/` and the udev rule as it found them, so
  it also passes on a Pi where RRR is installed.

## 1.18.0 — whole-pulse doses

- **1.18.0** — Change: a staggered window fires whole pulses against its
  running shortfall (asked minus delivered). A chunk no longer rounds up to
  a whole pulse each time, which ends the measured over-delivery on
  staggered doses; a slot whose shortfall is under half a pulse is skipped
  and a later slot picks it up. An instant dose also rounds to the nearest
  whole pulse instead of up (a 0.6 mL dose at 0.1415 mL per pulse: 4
  pulses, 0.57 mL, where 1.17.0 fired 5, 0.71 mL).

## 1.17.0 — honest delivery accounting

- **1.17.0** — Change: the ledger records what actually left the valve
  (`volume_actual_ml`, `pulses_fired`, `volume_per_pulse_ml`, added
  automatically), and a delivery cut short is credited and logged as
  `partial` instead of zero. A retry asks only for the outstanding dose
  instead of +5 % per failure. Completion is judged within half a pulse
  instead of 0.01 mL.

## 1.16.x — calibration timing profile

- **1.16.1** — Fix: the calibration wizard accepts 10–1000 pulses (it
  accepted only 100–500).
- **1.16.0** — Feature: a calibration stores the rest between pulses,
  set in the wizard (**Inter-Pulse Interval**). Deliveries replay the
  pulse width and rest each cage was calibrated at; older calibrations
  keep the legacy 100 ms rest. A delivery whose estimated duration would
  exceed `max_pulse_delivery_time_s` (fixed at 120 s) is refused before
  any water moves, with the reason in the Terminal tab; before, the limit
  cut the dose off mid-way and the retry sent the whole dose again.
  Shorten the rest or split the dose. The calibration
  wizard runs its pulses off the GUI thread: the window no longer
  freezes, the progress bar is live, X cancels a run mid-way, and the
  master valve is closed on every exit (a mid-run error used to leave it
  open). (Tagged first as the pre-release 1.16.0-beta.)

## 1.15.x — hardware operation lock

- **1.15.1** — Change: controls locked by another hardware operation are
  greyed out.
- **1.15.0** — Feature (safety): schedule runs, priming and calibration
  share one hardware lock, and each refuses to start while another holds
  it (a "Hardware busy" message says which). CLOSE ALL RELAYS in Settings
  → Priming clears the lock.

## 1.13.0 – 1.14.2 — instant schedules

- **1.14.2** — Fix: pressing Run on an instant schedule (or dropping one
  into the run area) failed in 1.14.1 with a missing-method error; the
  method, removed by mistake in 1.14.1, is restored.
- **1.14.1** — Change: removed dead instant-delivery and legacy
  controller code.
- **1.14.0** — Change: instant deliveries run through the same delivery
  path as staggered ones. On solenoid hardware an instant dose now uses
  the cage's valve calibration and pulse width (and the flow sensor, when
  one is connected); before, it went through the legacy pump path (a
  generic trigger count with the stagger interval between triggers) and
  ignored them.
- **1.13.1** — Fix: instant schedule cards show the right animal count.
- **1.13.0** — Fix: instant schedules can be created, run and edited.

## 1.10.0 – 1.12.0 — schedule editing, guests, UI polish

- **1.12.0** — Add: an **Edit Schedule** button in the Schedules hub's
  select mode.
- **1.11.1** — Fix: edit-schedule follow-ups. The dialog opens large
  enough to show the whole form, the Quick Apply start/end/volume row is
  pre-filled and its edits now apply on save (before, they were ignored
  unless Apply to All was clicked), and the Schedules hub log lists the
  exact edits made.
- **1.11.0** — Change: the edit-schedule dialog is rebuilt on the wizard's
  step 3 and saves its edits. Card labels no longer show grey boxes.
- **1.10.1** — Fix: drop-down lists show every item; Help opens on its
  first topic.
- **1.10.0** — Change: Settings is hidden from guests and Help is now open
  to them (it was disabled when logged out). The schedule wizard validates
  the delivery window before saving (a name, at least one animal, volume
  above zero, end after start, and a window long enough for the summed
  per-cage pulse time) and defaults the staggered window to 1 hour instead
  of 12, as does the edit dialog. The solenoid strategy's fallback now
  defaults to pulse mode (already enforced in production, so no delivery
  change).

## 1.9.x — legacy flow sensor removed, lint gate, UI polish

- **1.9.3** — Fix: calibration buttons fit their row. Tidier wizard
  header; Help's "Creating Schedules" rewritten for the wizard.
- **1.9.2** — Fix: calibration buttons centred; the animals table fills
  its width after a refresh; login prompt and Schedules empty state
  tidied.
- **1.9.1** — Fix: the Delivery hardware-mode help text and the drop-down
  menu.
- **1.9.0** — Change: removed the legacy direct-I²C flow-sensor driver.
  The Teensy UART bridge is the only flow sensor, and a device still set
  to `i2c` falls back to calibration-only mode. The code is now formatted
  and linted with ruff. CONTRIBUTING.md and this changelog added;
  ProjectsController and ScheduleDropArea now take the shared
  DatabaseHandler (one DB handle instead of three).

## 1.8.x — stop-sequence safety + multi-HAT

- **1.8.7** — Fix: the Stop button now ends a running schedule *cleanly*
  in well under a second instead of being force-terminated after a 3 s
  hang. (Root cause: the worker-thread quit signal was queued behind the
  blocked UI thread; switched to a direct connection.)
- **1.8.6** — Fix: a crash in the stop cleanup path (`UnboundLocalError`)
  that prevented the delivery worker from shutting down on Stop.
- **1.8.5** — Fix: creating a staggered schedule failed when the start/end
  time landed on a whole second (no microseconds). Schedule creation now
  parses ISO datetimes robustly.
- **1.8.4** — Internal: temporary timing instrumentation for the Stop
  investigation (removed in 1.8.6).
- **1.8.3** — Fix: Stop now reliably cancels an in-flight delivery instead
  of letting the next chunk start (cancellation token reset moved to
  schedule start; worker cycle loops honor cancellation).
- **1.8.2** — Add: cooperative cancellation in the delivery strategies so
  Stop interrupts a pour promptly.
- **1.8.1** — Fix (safety): on Stop, all relays — including the master
  solenoid — are dropped *first*, before any thread teardown, so the
  hardware can never be left energized if shutdown stalls.
- **1.8.0** — Feature: the Cages tab now paginates by HAT (one tab per
  relay HAT) so multi-HAT setups are fully visible and editable.

## 1.7.x — cleanup, multi-HAT plumbing, update-flow fixes

- **1.7.7** — Fix: changing the relay-HAT count now regenerates the
  cage→relay map (a 2-HAT setup yields 31 cages, not a stale 15).
- **1.7.6** — Fix: the Cages tab now refreshes correctly after a HAT-count
  change (the system controller is wired through to it).
- **1.7.5** — Fix: "Change Relay Hats" updates the Cages tab immediately,
  without an app restart.
- **1.7.4** — Change: simplified the update notifier to the single GitHub
  release-check path; removed the unused legacy local-changelog dialog.
- **1.7.3** — Change: removed a stale ~1.9 MB doc archive from the release
  bundle (smaller, faster updates).
- **1.7.2** — Fix (safety): quitting RRR is now blocked while a delivery
  schedule is running — Stop the schedule first.
- **1.7.1** — Fix: applying an in-app update now reliably loads the new
  version on restart (was occasionally relaunching the old release).
- **1.7.0** — Change: removed unused legacy UI modules (public-surface
  cleanup; no operator-visible behavior change).

## 1.6.x — dead-code cleanup + offline resilience

- **1.6.4** — Change: removed unused/dead code across the app (Tier-0
  cleanup); fixed a latent crash in the "Change Relay Hats" path.
- **1.6.1** — Improve: clearer Slack-status indicator and update-failure
  dialogs (offline-resilience Phase 3).
- **1.6.0** — Add: fail-closed update verification + a network helper so a
  flaky connection can never install an unverifiable bundle (Phase 2).

## 1.5.x — settings persistence + offline groundwork

- **1.5.3** — Add: offline-resilience test harness (Phase 1).
- **1.5.2** — Maintenance release.
- **1.5.1** — Change: Slack credentials moved to a mode-0600 `secrets.json`
  separate from the settings DB (Phase 2.5b).
- **1.5.0** — Change: type-aware settings persistence in SQLite with a
  one-time migration from the legacy `settings.json` (Phase 2.5a).

## 1.0.0 – 1.4.2 — the in-app update system

- **1.4.x** — Update-apply engine, blue-green activation, recovery fixes
  (Phase 2c).
- **1.3.0** — Blue-green release layout under `~/rrr` + data migration
  (Phase 2b).
- **1.2.0** — Centralized data paths via a `paths` module (Phase 2a).
- **1.1.0** — In-app update check + notification banner (Phase 1).
- **1.0.0** — First versioned release; baseline for the update system
  (Phase 0).
