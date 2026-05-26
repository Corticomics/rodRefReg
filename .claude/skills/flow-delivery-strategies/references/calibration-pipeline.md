# Calibration pipeline

Per-cage pulse-to-volume calibration for `SolenoidFlowStrategy` in pulse
mode. Without this, the strategy can't translate "deliver 0.2 mL" into a
pulse count.

## What gets calibrated

For each cage that has a solenoid + flow sensor, we measure:

- `pulse_width_ms` — duration of a single pulse (operator-chosen, usually
  10-500 ms)
- `volume_per_pulse_ml` — empirical mean volume delivered per pulse at
  that width
- `stddev_ml` — variability across pulses
- `coefficient_of_variation_pct` — `stddev / mean * 100`
- `num_samples` — pulses fired during calibration (typically 50-100)

These are persisted to the `valve_calibration` table (one row per cage,
unique on `cage_id`) and appended to `valve_calibration_history` (audit
trail).

Schema reference:
[`schedule-database-ops/references/schema.md`](../../schedule-database-ops/references/schema.md)
under "valve_calibration".

## The flow (UI side)

1. Operator opens the calibration wizard from the Settings tab or from
   the Cages visualization.
   Entry point: [`Project/ui/CalibrationWizard.py`](Project/ui/CalibrationWizard.py).
2. Selects a cage, sets `pulse_width_ms` and `num_samples`.
3. Wizard primes the line (see priming below).
4. Wizard fires N pulses, integrating volume per pulse from the flow
   sensor between pulses.
5. Wizard computes mean / stddev / CV, shows the operator a preview.
6. On accept, writes via
   [`Project/utils/pulse_calibration.py`](Project/utils/pulse_calibration.py)
   → `DatabaseHandler.save_valve_calibration(...)`
   ([`database_handler.py:1558`](Project/models/database_handler.py#L1558)).

The write is atomic — both `valve_calibration` (upsert by `cage_id`) and
`valve_calibration_history` (insert) happen in one transaction.

## Priming the line

Before calibration starts, the line between the master valve and the
cage solenoid must be full of water — otherwise the first few pulses
deliver air and ruin the mean.

[`Project/ui/PrimingControlWidget.py`](Project/ui/PrimingControlWidget.py)
exposes a "prime" action that:

- Opens the master valve + the selected cage solenoid.
- Holds them open until the operator stops.
- Reports flow rate live (helps operator know when air is purged).
- **Does not count against the schedule** — priming volume is wasted
  to drain, not delivered to the animal.

The widget is independent of any delivery strategy; it talks directly to
the relay handler + flow sensor.

## Reading calibration at delivery time

`SolenoidFlowStrategy` in pulse mode reads via the calibration store:

```python
cal = db.get_valve_calibration(cage_id)
if cal is None:
    raise NoCalibrationError(...)
pulse_count = math.ceil(target_volume_ml / cal['volume_per_pulse_ml'])
```

If `cal` is `None` (cage was never calibrated), pulse mode has no way to
make a defensible decision. Either:

- Fall back to continuous mode for that cage (current behavior, with a
  warning in the log), OR
- Refuse to deliver (planned, gated on a setting)

Continuous mode doesn't need calibration — it integrates the flow sensor
in real time.

## When to recalibrate

- After replacing a solenoid (mechanical wear → different bore characteristics)
- After major plumbing changes (line length, fittings)
- When CV creeps above ~5% in routine deliveries (the audit log in
  `dispensing_history` is the signal here — compare commanded vs
  delivered volume per cage over time)
- Quarterly as a default cadence

The `valve_calibration_history` table preserves prior calibrations for
audit, so re-calibrating doesn't lose history.

## Don't do this

- Don't calibrate with the cage's lickspout connected — water spits into
  the cage and skews the measurement. Calibrate to a graduated vial.
- Don't trust calibration that ran with the flow sensor uncalibrated.
  The SLF3S-0600F ships factory-calibrated, but if the line has air or
  the sensor was bumped during installation, the integration is bogus.
- Don't tweak `pulse_width_ms` mid-experiment. Operator-visible behavior
  must match the recorded calibration. If you need a different width,
  start a new calibration session for that cage and accept a new
  history row.
- Don't bypass `pulse_calibration.py` and write directly to the table.
  The util enforces a basic sanity check (CV < threshold, num_samples
  > 0) before committing.
