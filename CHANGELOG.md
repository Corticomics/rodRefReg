# Changelog

Curated, operator-facing summary of each **published** RRR release (a
release = a git tag `v<x.y.z>` with a `.rrrupdate` bundle devices can
install via the in-app Updates tab), newest first. Most releases get one
line. A release that asks something of the operator starts with a
**Before you update** list. A version number that was set on `main` but
never tagged is folded into the next release's entry.

This is the human-readable companion to the auto-generated GitHub release
notes. Versioning follows SemVer for RRR — see
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
  water on the production valve. Open Settings > Calibration and calibrate
  every **Not Calibrated** or **Invalid** row a schedule uses. On a two-HAT
  device the table now lists all 31 cages.
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
    valve opened are credited, and the retry asks only for the rest.
  - A close that does not reach its relay is retried twice at once, then
    after 20, 50 and 100 ms. A pulse whose close got through late is
    credited with the time its valve stayed open, at the valve's steady
    flow.
  - `[VALVE CRITICAL] … OPEN` has two wordings: *the valve may still be
    OPEN* for a valve seen to open whose close did not get through, and
    *the … valve's relay is not answering, so the valve cannot be confirmed
    closed; it may be OPEN* for a valve whose relay has not answered since
    the run started. A
    dead HAT therefore alarms. If a later close gets through,
    `[VALVE OK] … closed after all` clears the alarm.
  - Pump relays that do not switch off are retried once, then
    `[VALVE CRITICAL] relay unit N: …` says they may still be ON.
  - When the relays cannot be confirmed off, CLOSE ALL RELAYS shows
    **Emergency Stop Failed** and Stop shows **Relays Not Confirmed Off**.
    Both say to disconnect the valve power supply.
  - The calibration wizard stops at a pulse whose valve did not open or
    close. Do not save a measurement from that run.
  - Priming keeps its session and the hardware lock while a cage valve
    may still be open after Close Master, until that valve is confirmed
    closed. A failed Open Master no longer frees them.
- **Fix (safety):** with the first HAT missing, relay commands are no
  longer shifted onto the next HAT, where they drove another animal's
  valve.
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
  Settings > Calibration marks a calibration from the other topology
  **Stale**, and Run refuses it. After switching the topology, recalibrate
  every cage.
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

- `utils/topology.py` is the single decision point: `build_solenoid_controller`,
  `cage_map_from`, `calibration_is_stale`, `reserved_relay_reason`.
  `IndependentSolenoidController` has `has_master = False` and makes no
  relay writes for master operations. Master and cage relay ids below 1 are
  refused.
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
