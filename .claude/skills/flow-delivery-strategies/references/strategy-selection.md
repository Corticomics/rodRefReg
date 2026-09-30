# Strategy selection

How `StrategyFactory.create()` picks a strategy and what each mode
requires.

## The `hardware_mode` setting

A `system_settings` key (default `'solenoid'`):

| Value | Strategy | Notes |
|---|---|---|
| `'pump'` | `PumpStrategy` | legacy time-based; relay HAT only |
| `'solenoid'` | `SolenoidFlowStrategy` | canonical; relay HAT + solenoids; flow sensor optional |
| anything else | — | `StrategyFactory.create` raises `ValueError` (v1.21.0; it used to fall back to `pump`) ([`factory.py`](Project/strategies/factory.py)) |

The setting comes from `SystemController.settings['hardware_mode']`, read
from the `system_settings` table. Operators set it in Settings > Delivery >
Delivery Hardware Mode
([`Project/ui/SettingsTab.py`](Project/ui/SettingsTab.py)); the combo is
greyed out, and a change refused, while a schedule, priming session or
calibration runs, and a settings backup never changes it.
`SystemController.ensure_solenoid_defaults()`, run at every start
(main.py:168), sets it back to `'solenoid'`, so pump mode lasts only until
the next start.

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

- `solenoid_controller` — required. Built by
  `utils.topology.build_solenoid_controller` from `valve_topology`:
  `SolenoidController` (shared manifold: master valve on relay 16 plus one
  valve per cage) or `IndependentSolenoidController` (one syringe and valve
  per animal; no master, relay 16 reserved and never driven).
- `flow_sensor` — optional. `UARTFlowSensor` (Teensy bridge) is the only
  driver; `None` runs without flow verification (the production rig).
- `calibration_store` — optional. RelayWorker passes
  `utils.calibration.CalibrationStore()`; the per-cage rows come from
  `database_handler` (a `get_all_valve_calibrations()` snapshot at start,
  `get_valve_calibration(cage_id)` read-through).
- `settings` — required. Drives the continuous-vs-pulse sub-mode:
  `settings['use_pulse_delivery'] = True | False`.

Hardware footprint:

- Relay HAT (drives the per-cage valves, and the master on the shared manifold)
- Shared manifold (`valve_topology = shared_manifold`, default): one master
  valve (typically Parker Series 3, 12 V) on relay 16 feeding a manifold.
  Independent (`valve_topology = independent`): one syringe per animal, no
  master, no manifold; relay 16 stays reserved and unwired.
- One solenoid per cage
- Optional: SLF3S-0600F flow sensor behind a Teensy 4.1
  (`flow_sensor_type='uart'`), on the shared manifold mounted between the
  master and the manifold

## Sub-mode: continuous vs pulse (solenoid only)

`use_pulse_delivery=False` (continuous):

- Open the master (shared manifold only) and the cage valve.
- With a flow sensor: stream samples at ~50 Hz; integrate.
- Without one: hold the cage valve open for target ÷ `expected_flow_ml_min`
  (capped at `max_valve_open_s`), with no feedback.
- With a sensor, apply predictive cutoff (close ~closing_lag_ms before integral hits
  target).
- Verify post-close volume; warn if outside tolerance.
- Good for Lee Company LHD valves.

`use_pulse_delivery=True` (pulse, production):

- Replay the cage's calibrated pulse width and rest from `valve_calibration`.
- RelayWorker plans the dose in whole pulses (`_quantize_to_pulses`):
  the nearest whole number of pulses, or the next one up with
  `round_doses_up`.
- Fire the planned pulses at that width and rest.
- Stop at the first pulse that fails, including a valve command that did
  not switch (`[VALVE ERROR] cage N: …; delivery stopped after …`). Only
  pulses whose valve opened are credited; a pulse whose close got through
  late is credited with the time its valve stayed open.
- Optionally verify final integral against the flow sensor.
- Good for Parker Series 3 valves. Higher precision.

## Decision tree

```
Do you have solenoid valves?
├── No  → 'pump' mode (reset to 'solenoid' at the next start; see above)
└── Yes → 'solenoid' mode
         │
         ├── Plumbing? (Settings > Delivery > Valve Topology)
         │   ├── Reservoir → master valve (relay 16) → manifold → cage valves
         │   │   └── shared_manifold (default)
         │   └── One syringe + one valve per animal, no master
         │       └── independent (relay 16 stays reserved, unwired)
         │
         ├── Lee Company LHD valves?
         │   └── use_pulse_delivery = False (continuous; reset to True at every start)
         │
         └── Parker Series 3 valves?
             └── use_pulse_delivery = True (pulse) — production
                 │
                 └── Every cage calibrated under this topology?
                     ├── No  → calibrate first; Run refuses otherwise (see calibration-pipeline.md)
                     └── Yes → ready to deliver
```

## Why pump-mode is still around

Some lab rigs ship with only the relay HAT, so `PumpStrategy` is still
kept and tested. But `SystemController.ensure_solenoid_defaults()` sets
`hardware_mode` back to `'solenoid'` at every start (main.py:168), so pump
mode lasts only until the next start; a pump-only rig would need that
start-up default changed first. `SolenoidFlowStrategy` is what rigs run.
