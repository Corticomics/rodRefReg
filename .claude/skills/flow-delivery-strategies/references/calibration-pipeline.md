# Calibration pipeline

Per-cage pulse-to-volume calibration for `SolenoidFlowStrategy` in pulse
mode. In solenoid pulse mode (the default), Run refuses a schedule that
waters a cage with no usable calibration measured under this device's valve
topology (Valve calibration needed; `utils/calibration_gate.py`); the
strategy's own fallback (about 0.026 mL/pulse) is only a defence in depth.

## What gets calibrated

For each cage valve (gravimetric; no flow sensor needed), the wizard records:

- `pulse_width_ms` — duration of a single pulse (10–500 ms)
- `inter_pulse_interval_ms` — the valve-closed rest between pulses
  (100–2000 ms); delivery replays it
- `volume_per_pulse_ml` — weighed volume ÷ pulses fired
- `stddev_ml` / `coefficient_of_variation_pct` — estimates (one weighing
  cannot measure the spread between pulses)
- `num_samples` — pulses fired (10–1000)
- `relay_id` — the relay the cage is wired to
- `topology` — the valve topology the device ran when it was measured
  (v1.21.0; NULL on older rows, read as `shared_manifold`)

These are persisted to the `valve_calibration` table (one row per cage,
unique on `cage_id`) and appended to `valve_calibration_history` (audit
trail).

Schema reference:
[`schedule-database-ops/references/schema.md`](../../schedule-database-ops/references/schema.md)
under "valve_calibration".

## The flow (UI side)

1. Operator opens the calibration wizard from **Settings → Calibration**
   (the Cages tab has no calibration entry point).
   Entry point: [`Project/ui/CalibrationWizard.py`](Project/ui/CalibrationWizard.py).
2. The operator opens it per cage (the row's **Calibrate** button, or
   **Calibrate All Uncalibrated**), works through the pre-flight checklist
   and sets the number of pulses, `pulse_width_ms` and the inter-pulse
   interval. Prime the line first in the priming tab (see below).
3. Wizard fires N pulses into a beaker.
4. The operator weighs the output and enters the measured volume
   (gravimetric; the production rig runs without a flow sensor).
5. Wizard computes mL/pulse and an estimated CV, shows a quality rating.
6. **Save & Finish** calls `DatabaseHandler.save_valve_calibration(...)`
   directly ([`Project/models/database_handler.py`](Project/models/database_handler.py)).
   [`Project/utils/pulse_calibration.py`](Project/utils/pulse_calibration.py)
   is not involved: it only holds the global default profile used for a
   cage with no row.

The write is atomic — both `valve_calibration` (upsert by `cage_id`) and
`valve_calibration_history` (insert) happen in one transaction.

## Priming the line

Before calibration starts, the line up to the cage valve must be full of
water — on the shared manifold from the master through the manifold, on
the independent rig the syringe line — otherwise the first few pulses
deliver air and ruin the mean.

[`Project/ui/PrimingControlWidget.py`](Project/ui/PrimingControlWidget.py)
(Settings > Priming):

- Shared manifold: open the master, then the cage valve (cages need the
  master open first).
- Independent: the master group is hidden; a cage valve is opened directly.
- Valves stay open until the operator closes them or presses CLOSE ALL
  RELAYS. There is no flow readout: watch the outlet for a steady stream
  with no bubbles.
- **Does not count against the schedule** — priming water goes to drain.
- After the valve topology is changed in Settings, Priming cannot open a
  valve until RRR is closed and reopened.

The widget is independent of any delivery strategy; it drives the relays
through the topology's valve controller
(`utils.topology.build_solenoid_controller`) and never opens the flow sensor.

## Reading calibration at delivery time

When a schedule starts, `SolenoidFlowStrategy` snapshots every row
(`get_all_valve_calibrations`) and, per cage, replays the row's pulse
width and rest (`_get_cage_calibration`); a cage missing from the snapshot
is read through with `get_valve_calibration(cage_id)`.

Before that, in solenoid pulse mode (the default), Run refuses the schedule
(`utils/calibration_gate.py`, called from
`RunStopSection._passes_calibration_gate`; there is no setting to turn it
off) when a cage it waters has no row, a missing, zero or invalid volume
per pulse or pulse width (Invalid in Settings > Calibration), or a row
measured under the other valve topology (Stale). The dialog (Valve
calibration needed) lists the cages; calibrate them in Settings >
Calibration. Run also refuses a schedule that waters a cage not on this
device. That cage cannot be calibrated: edit the schedule so its animals
are on cages shown in Settings > Calibration (the dialog is titled Cage not
on this device when that is the only problem).

What remains in the strategy is defence in depth only: a cage with no row
uses the global default from `utils/pulse_calibration.py` (about
0.026 mL/pulse at 20 ms, against about 0.034 mL on the production valve,
so roughly 30 % too much water), and a stale row is used with a warning to
recalibrate. Continuous and pump mode read no calibration, and the gate
does not apply to them.

## When to recalibrate

- After replacing a solenoid (mechanical wear → different bore characteristics)
- After major plumbing changes (line length, fittings)
- After changing the valve topology: every row measured under the other
  topology shows Stale in Settings > Calibration, and Run refuses a
  schedule that waters one of those cages
- When a weighed delivery disagrees with its calibration
  (`Project/tools/gravimetric_check.py weigh` records balance readings
  against ledger rows). The ledger alone cannot show drift: without a flow
  sensor `volume_actual_ml` is pulses fired × the calibrated volume, not a
  measurement
- Quarterly as a default cadence

The `valve_calibration_history` table preserves prior calibrations for
audit, so re-calibrating doesn't lose history.

## Don't do this

- Don't calibrate with the cage's lickspout connected — water spits into
  the cage and skews the measurement. Calibrate to a graduated vial.
- Don't save a calibration from a run that stopped with a valve error
  (`The cage N valve did not open …` / `did not close …`): the weighed
  water no longer matches the pulse count.
- Don't tweak `pulse_width_ms` mid-experiment. Operator-visible behavior
  must match the recorded calibration. If you need a different width,
  start a new calibration session for that cage and accept a new
  history row.
- Don't write `valve_calibration` rows by hand. Go through
  `DatabaseHandler.save_valve_calibration`, which also appends the history
  row in the same transaction. The standalone CLI that used to do this was
  removed in v1.21.0 (it could not start); the wizard is the only writer.
