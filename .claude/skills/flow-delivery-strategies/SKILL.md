---
name: flow-delivery-strategies
description: Understand and modify how RRR turns "deliver N mL to animal X" into actual valve/pump actions. Two strategies live behind the DeliveryStrategy Protocol — SolenoidFlowStrategy (canonical, Teensy-bridged flow sensor) and PumpStrategy (legacy time-based). Selection happens in StrategyFactory by hardware_mode. Use when wiring a new dispensing path, choosing between continuous and pulse mode, debugging "delivered 0 mL", working with the SLF3S-0600F or Teensy UART bridge, or running the per-cage pulse calibration pipeline.
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
                      triggers_hint: Optional[int] = None) -> bool: ...

    async def clean(self, relay_unit_id: int, to_waste: bool = True) -> None: ...
```

Two concrete implementations:

| Strategy | File | When |
|---|---|---|
| `SolenoidFlowStrategy` | [`Project/strategies/solenoid_flow_strategy.py`](Project/strategies/solenoid_flow_strategy.py) | canonical — global master valve + per-cage solenoids + flow sensor |
| `PumpStrategy` | [`Project/strategies/pump_strategy.py`](Project/strategies/pump_strategy.py) | legacy — peristaltic pump fired for N triggers per `volume_calculator` |

## The factory

[`Project/strategies/factory.py`](Project/strategies/factory.py)
`StrategyFactory.create()` picks the strategy from `hardware_mode`
(a `system_settings` key):

```python
mode = (hardware_mode or "pump").strip().lower()
if mode == "pump":
    return PumpStrategy(pump_controller, volume_calculator)
if mode == "solenoid":
    return SolenoidFlowStrategy(...)
```

Unknown values fall back to `pump` (defensive default). Selection rules
and what each mode requires: [`references/strategy-selection.md`](references/strategy-selection.md).

## SolenoidFlowStrategy has two sub-modes

Auto-selected from `settings['use_pulse_delivery']`:

- **Continuous mode** (Lee Company LHD valves, legacy) — open the
  solenoid, integrate the flow sensor, close when the integral hits
  target with a predictive cutoff.
- **Pulse mode** (Parker Series 3 valves, recommended) — fire timed
  micro-pulses (10-500 ms each) using empirical per-valve
  pulse-to-volume calibration. Precision: ~±0.003 mL.

The pulse profile lives in
[`Project/utils/pulse_calibration.py`](Project/utils/pulse_calibration.py)
and is filled per cage by the calibration wizard.

## Flow sensors — two drivers, one shape

| Driver | Class | Path |
|---|---|---|
| Direct I²C (legacy) | `SLF3S0600FDriver` | [`Project/drivers/flow_sensor.py:17`](Project/drivers/flow_sensor.py#L17) |
| Teensy UART bridge (canonical) | `UARTFlowSensor` | [`Project/drivers/uart_flow_sensor.py`](Project/drivers/uart_flow_sensor.py) |

Picked by
[`Project/drivers/flow_sensor_factory.py`](Project/drivers/flow_sensor_factory.py)
`create_flow_sensor(settings)` based on `flow_sensor_type` (`'i2c'` or
`'uart'`).

Why we moved off direct-I²C: the SLF3S-0600F sometimes wedges the I²C
bus, and Bookworm's smbus2 has been less reliable on the Pi 5 than the
Pi 4. The Teensy bridge isolates the sensor on its own I²C bus and
streams samples over USB-serial at `/dev/teensy_flow` (the udev rule is
in [`scripts/install/40-hardware.sh`](scripts/install/40-hardware.sh)).

## Calibration pipeline

Per-cage pulse-to-volume calibration:

1. Operator opens the calibration wizard from the UI:
   [`Project/ui/CalibrationWizard.py`](Project/ui/CalibrationWizard.py).
2. The wizard runs N fixed pulses, records the integrated volume per
   pulse via the flow sensor.
3. `pulse_calibration.py` writes the empirical
   `pulse_width_ms`/`volume_per_pulse_ml` pair to the
   `valve_calibration` table (also appended to `valve_calibration_history`).
4. Future deliveries through `SolenoidFlowStrategy` read the calibration
   per cage via `DatabaseHandler.get_valve_calibration(cage_id)`.

Priming the line (filling tubing without metering volume) is its own
flow:
[`Project/ui/PrimingControlWidget.py`](Project/ui/PrimingControlWidget.py)
exposes a "prime" action that opens the cage solenoid until the operator
hits stop. No flow integration; it doesn't count against the schedule.

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

1. Read [`hardware-gpio-debug`](../hardware-gpio-debug/SKILL.md) first
   — relay HAT not detected is the most common cause.
2. Check the flow sensor path:
   `python3 -c "from drivers.flow_sensor_factory import create_flow_sensor; ..."`
3. If solenoid mode with pulse delivery: confirm the cage has a row in
   `valve_calibration`. Without calibration, the strategy can't translate
   target volume into pulse count.
4. Check `delivery_mode` on the schedule itself — staggered vs instant
   uses different code paths in `RelayWorker`.
