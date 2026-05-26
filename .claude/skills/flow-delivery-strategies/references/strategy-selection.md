# Strategy selection

How `StrategyFactory.create()` picks a strategy and what each mode
requires.

## The `hardware_mode` setting

A `system_settings` key (default `'pump'`):

| Value | Strategy | Notes |
|---|---|---|
| `'pump'` | `PumpStrategy` | legacy time-based; relay HAT only |
| `'solenoid'` | `SolenoidFlowStrategy` | canonical; relay + solenoids + flow sensor |
| anything else | `PumpStrategy` | defensive fallback ([`factory.py`](Project/strategies/factory.py)) |

The setting comes from `SystemController.settings['hardware_mode']` which
in turn reads from the `system_settings` table (Phase 2.5a). Operators
set it from
[`Project/ui/SettingsTab.py`](Project/ui/SettingsTab.py) under the
"Hardware" subtab.

## Pump mode — what it needs

`StrategyFactory.create(hardware_mode='pump', ...)` requires:

- `pump_controller` — a `PumpController` instance. Owns the relay-clicking
  logic and trigger pulse generator.
- `volume_calculator` — a `VolumeCalculator` instance. Converts mL into
  pump trigger counts using `pump_volume_ul` (µL per click).

Hardware footprint: just the Sequent Microsystems 16-relay HAT. No flow
sensor, no master valve, no solenoids. Cheapest setup, lowest precision
(trigger counts are nominal — actual delivered volume drifts with tubing
wear).

## Solenoid mode — what it needs

`StrategyFactory.create(hardware_mode='solenoid', ...)` requires:

- `solenoid_controller` — owns master-valve and per-cage solenoid timing.
- `flow_sensor` — optional. `SLF3S0600FDriver` or `UARTFlowSensor`. May be
  `None` for calibration-only mode (the strategy still fires pulses; you
  just can't verify volume).
- `calibration_store` — optional. Provides the per-cage
  pulse-to-volume calibration. In practice this wraps
  `DatabaseHandler.get_valve_calibration(cage_id)`.
- `settings` — required. Drives the continuous-vs-pulse sub-mode:
  `settings['use_pulse_delivery'] = True | False`.

Hardware footprint:

- Relay HAT (drives the master valve + per-cage solenoid drivers)
- One global master valve (typically Parker Series 3, 12V)
- Per-cage solenoids
- SLF3S-0600F flow sensor (mounted between master and manifold)
- Teensy 4.1 (if `flow_sensor_type='uart'`) bridging the sensor over USB

## Sub-mode: continuous vs pulse (solenoid only)

`use_pulse_delivery=False` (continuous):

- Open master + cage solenoid.
- Stream samples from flow sensor at ~50 Hz; integrate.
- Apply predictive cutoff (close ~closing_lag_ms before integral hits
  target).
- Verify post-close volume; warn if outside tolerance.
- Good for Lee Company LHD valves.

`use_pulse_delivery=True` (pulse, recommended):

- Look up per-cage pulse profile from `valve_calibration`.
- Compute pulse count = `ceil(target_mL / volume_per_pulse_ml)`.
- Fire pulses with `pulse_width_ms` per pulse.
- Optionally verify final integral against the flow sensor.
- Good for Parker Series 3 valves. Higher precision.

## Decision tree

```
Do you have a flow sensor + solenoids?
├── No  → 'pump' mode
└── Yes → 'solenoid' mode
         │
         ├── Lee Company LHD valves?
         │   └── set use_pulse_delivery = False (continuous)
         │
         └── Parker Series 3 valves?
             └── set use_pulse_delivery = True (pulse) — recommended
                 │
                 └── Did you run per-cage calibration?
                     ├── No  → calibrate first (see calibration-pipeline.md)
                     └── Yes → ready to deliver
```

## Why pump-mode is still around

Some lab rigs ship with only the relay HAT. Phasing it out would force
those operators to buy solenoid hardware. The strategy is kept as a
first-class implementation, not a deprecated fallback — but
`SolenoidFlowStrategy` is what new rigs should use.
