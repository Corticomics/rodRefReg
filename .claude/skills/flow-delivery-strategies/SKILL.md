---
name: flow-delivery-strategies
description: Understand and modify how RRR turns "deliver N mL to animal X" into actual valve/pump actions. Two strategies live behind the DeliveryStrategy Protocol — SolenoidFlowStrategy (canonical; per-cage valves on a shared manifold or one syringe per animal; Teensy-bridged flow sensor optional) and PumpStrategy (legacy time-based). Selection happens in StrategyFactory by hardware_mode. Use when wiring a new dispensing path, choosing between continuous and pulse mode, debugging "delivered 0 mL", working with the SLF3S-0600F or Teensy UART bridge, or running the per-cage pulse calibration pipeline.
---

# Flow / delivery strategies

The RRR architecture isolates "how do we actually move water" behind a
single Protocol. The scheduling layer only knows "deliver N mL to relay
unit K" — it doesn't care whether that means firing a pump for 800 ms or
holding a solenoid open until the flow sensor integrates to N.

## The Protocol

[`Project/strategies/delivery_strategy.py`](Project/strategies/delivery_strategy.py)
defines:

```python
@runtime_checkable
class DeliveryStrategy(Protocol):
    async def deliver(self, relay_unit_id: int,
                      target_volume_ml: float,
                      triggers_hint: Optional[int] = None) -> DeliveryResult: ...

    async def clean(self, relay_unit_id: int, to_waste: bool = True) -> None: ...
```

Check `result.success`, never `if result:` (a dataclass is always truthy);
`result.delivered_ml` is the strategy's estimate of what left the valve
(pulses fired × the calibrated volume, or the sensor-corrected figure where
a flow sensor is fitted), reported on failure too.

Two concrete implementations:

| Strategy | File | When |
|---|---|---|
| `SolenoidFlowStrategy` | [`Project/strategies/solenoid_flow_strategy.py`](Project/strategies/solenoid_flow_strategy.py) | canonical — one solenoid per cage, plus a master valve on relay 16 on the shared manifold (none on the independent topology); flow sensor optional |
| `PumpStrategy` | [`Project/strategies/pump_strategy.py`](Project/strategies/pump_strategy.py) | legacy — peristaltic pump fired for N triggers per `volume_calculator` |

## The factory

[`Project/strategies/factory.py`](Project/strategies/factory.py)
`StrategyFactory.create()` picks the strategy from `hardware_mode`
(a `system_settings` key):

```python
mode = hardware_mode.strip().lower() if isinstance(hardware_mode, str) else ""
if mode == "pump":
    return PumpStrategy(pump_controller, volume_calculator)
if mode == "solenoid":
    return SolenoidFlowStrategy(...)
raise ValueError(f"Unknown hardware_mode {hardware_mode!r}: ...")
```

An unknown value is refused with `ValueError` (v1.21.0); it used to fall
back to `pump`, which on a valve rig would pulse the valves with pump
trigger timing. `RelayWorker._resolve_hardware_mode` treats a missing value
as `solenoid`. Selection rules
and what each mode requires: [`references/strategy-selection.md`](references/strategy-selection.md).

## SolenoidFlowStrategy has two sub-modes

Auto-selected from `settings['use_pulse_delivery']`.
`SystemController.ensure_solenoid_defaults()` runs at every start
(main.py:168) and sets it back to True, so continuous mode lasts only until
the next start.

- **Continuous mode** (Lee Company LHD valves, legacy) — open the
  solenoid, integrate the flow sensor, close when the integral hits
  target with a predictive cutoff. Without a sensor it holds the valve
  open for a time worked out from `expected_flow_ml_min` instead.
- **Pulse mode** (Parker Series 3 valves, production) — fire timed pulses
  (10–500 ms wide) at the cage's calibrated width and rest. Doses are
  planned in whole pulses of the cage's calibrated volume (about 0.034 mL
  on the production valve), so a window lands within half a pulse of its
  target (an exact half rounds up), or within one pulse above it with
  `round_doses_up`. The rounding is `utils/dose_rounding.whole_pulses`,
  the one rule for every planned figure: the planner
  (`RelayWorker._quantize_to_pulses`) and `tools/gravimetric_check.py`'s
  planner verdict call it, and so must anything new that plans a dose in
  pulses.

Per-cage pulse profiles live in the `valve_calibration` table, written by
the calibration wizard through `DatabaseHandler.save_valve_calibration`;
each row records the valve topology it was measured under (v1.21.0); one
saved before v1.21.0 counts as shared manifold. In solenoid pulse mode (the
default), Run refuses a schedule that waters a cage with no usable
calibration measured under this device's valve topology (Valve calibration
needed): no row, a missing, zero or invalid volume per pulse or pulse width
(Invalid in Settings > Calibration), or a row from the other topology
(Stale). It also refuses a schedule that waters a cage not on this device;
there is nothing to calibrate there, so the schedule has to be edited (the
dialog is titled Cage not on this device when that is the only problem)
(`utils/calibration_gate.py`, `RunStopSection._passes_calibration_gate`).
[`Project/utils/pulse_calibration.py`](Project/utils/pulse_calibration.py)
holds only the global default profile (`CalibrationStore`, a JSON file with
hardcoded fallbacks, about 0.026 mL/pulse at 20 ms). The strategy still
falls back to it for a cage with no row, and still uses a stale row with a
warning, but only as a defence in depth behind the Run check.

## Flow sensor — one driver, one seam

| Driver | Class | Path |
|---|---|---|
| Teensy UART bridge (the only shipped type) | `UARTFlowSensor` | [`Project/drivers/uart_flow_sensor.py`](Project/drivers/uart_flow_sensor.py) |

Picked by
[`Project/drivers/flow_sensor_factory.py`](Project/drivers/flow_sensor_factory.py)
`create_flow_sensor(settings)` from `flow_sensor_type`; `'uart'` is the
only value it accepts (anything else raises `ValueError`). The direct-I²C
driver was deleted in v1.9.0; a future sensor gets its own driver and
branch (CLAUDE.md, "Flow sensor — extension point").

Why we moved off direct-I²C: the SLF3S-0600F sometimes wedges the I²C
bus, and Bookworm's smbus2 has been less reliable on the Pi 5 than the
Pi 4. The Teensy bridge isolates the sensor on its own I²C bus and
streams samples over USB-serial at `/dev/teensy_flow` (the udev rule is
in [`scripts/install/40-hardware.sh`](scripts/install/40-hardware.sh)).

## Calibration pipeline

Per-cage pulse-to-volume calibration:

1. Operator opens the calibration wizard from the UI:
   [`Project/ui/CalibrationWizard.py`](Project/ui/CalibrationWizard.py).
2. The wizard fires N pulses at the chosen width and interval into a
   beaker (on the shared manifold it opens the master first; on the
   independent topology it pulses the cage valve only). A pulse whose valve
   did not open or close stops the run with an error; save nothing from
   that run. The operator weighs the output and enters it (gravimetric; the
   production rig runs without a flow sensor).
3. **Save & Finish** calls `DatabaseHandler.save_valve_calibration`, which
   upserts the cage's `valve_calibration` row (its relay, timing profile
   and the device's valve topology) and appends to
   `valve_calibration_history`.
4. At schedule start `SolenoidFlowStrategy` snapshots every row
   (`get_all_valve_calibrations`), reading through to
   `get_valve_calibration(cage_id)` for a cage missing from the snapshot.

Priming the line (filling tubing without metering volume) is its own
flow:
[`Project/ui/PrimingControlWidget.py`](Project/ui/PrimingControlWidget.py)
has Open Master / Close Master buttons (shared manifold only) and a cage
selector with Open Selected / Close Selected. A valve stays open until the
operator closes it or presses CLOSE ALL RELAYS (which frees the operation
lock only when every relay is confirmed off and no delivery worker is
alive). CLOSE ALL RELAYS and Close Selected are greyed out and refused while
a schedule runs: Stop ends a schedule (a stopped schedule does not resume,
Run starts it over). On the independent topology
the master group is hidden and a cage valve is primed directly. A valve
topology change in Settings restarts RRR (`utils.updater.restart_app`), since
the panel is built for the topology RRR started with; where RRR cannot restart
itself, Priming cannot open a valve until RRR is closed and reopened. No flow
integration; it doesn't count against the schedule.

Full procedure: [`references/calibration-pipeline.md`](references/calibration-pipeline.md).

## Don't do this

- Don't add a third strategy by editing `RelayWorker` directly. The
  point of the Protocol is that `RelayWorker` doesn't import strategies
  — `StrategyFactory` does, and the worker holds an opaque reference.
- Don't import `RPi.GPIO` or `smbus2` at the top of a strategy module.
  Hardware imports are lazy ([threading-checklist](../pyqt5-ui-conventions/references/threading-checklist.md#4-hardware-imports-are-lazy)) — top-level imports kill `test_gui_smoke.py`.
- Don't write to `valve_calibration` from a strategy. Calibration writes
  are wizard-driven; strategies read.
- Don't assume the flow sensor is always present in pulse mode either
  — the `SolenoidFlowStrategy` constructor accepts `flow_sensor=None`
  for calibration-only mode (you fire pulses without verifying volume).
  Treat `None` defensively in any new code that reads flow.

## Where to start when "delivered 0 mL"

1. Read the Terminal tab for `[VALVE ERROR] cage N: <reason>; delivery
   stopped` or `Relay N not switched`. The reason is usually a relay write
   that did not reach its HAT (a HAT missing at start-up needs RRR
   restarted): read [`hardware-gpio-debug`](../hardware-gpio-debug/SKILL.md).
   It can also be the pulse or time limit (`max_pulses_per_delivery`,
   `max_pulse_delivery_time_s`).
2. Check the flow sensor path:
   `python3 -c "from drivers.flow_sensor_factory import create_flow_sensor; ..."`
3. If solenoid mode with pulse delivery: Run already refuses a cage with no
   usable calibration or one measured under the other topology
   (`utils/calibration_gate.py`). The `[CAL RESOLVE] cage=N using …` lines
   show which calibration a delivery used; a cage with no row falls back to
   about 0.026 mL/pulse. The ledger row's `status` (`completed` /
   `partial` / `failed`) and `volume_actual_ml` show what was credited.
4. Check `delivery_mode` on the schedule itself — staggered vs instant
   uses different code paths in `RelayWorker`.
