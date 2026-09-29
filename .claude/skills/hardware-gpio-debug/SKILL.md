---
name: hardware-gpio-debug
description: Diagnose RRR hardware path failures — Sequent Microsystems 16-relay HAT not detected, I²C errors (errno 121 / 5 / 110), Pi 4 vs Pi 5 GPIO differences, mock-vs-real seam in gpio/, and the lazy-init pattern used by RelayWorker. Use when the user reports "relays not clicking", "Hardware control will not work", "pump not firing", an I²C exception, or asks how to test the relay path before running a schedule.
---

# Hardware / GPIO debugging

The water-delivery hot path is:

```
Schedule → ScheduleController → DeliveryQueueController → RelayWorker (QThread)
       → RelayHandler → SM16relind (or MockSM16relind) → I²C bus
       → 16-channel relay HAT → pump or solenoid → animal
```

A failure anywhere on this chain manifests as "no water delivered." Diagnose
**top-down** — schedule UI, then controllers, then GPIO, then I²C, then board.

## First-pass triage (always do these)

```bash
# Is the bus alive and does the kernel see addresses 0x20–0x27?
i2cdetect -y 1                # Pi 4 + 5

# Sequent Microsystems CLI sanity (installed by scripts/install/40-hardware.sh)
16relind 0 board              # stack 0 board info
16relind 0 read 1             # read relay 1 (expect 0 or 1)
16relind 0 write 1 1; sleep 1; 16relind 0 write 1 0   # click test

# RRR's own selftest (used by the update applier; safe to run manually)
~/rrr/shared/venv/bin/python3 ~/rrr/current/Project/main.py --selftest
```

If `i2cdetect` shows no devices → bus or wiring (check 3.3 V, SDA/SCL, common
ground). If `16relind` works but RRR doesn't → it's a Python-layer problem.

## Key files and their responsibilities

| File | What it owns |
|---|---|
| [Project/gpio/gpio_handler.py](Project/gpio/gpio_handler.py) `RelayHandler` | Public façade. Owns the per-HAT `SM16relind` instances; routes trigger commands; If the `SM16relind` module is missing, or a HAT does not answer at start-up, it initialises no hats and every write becomes a silent no-op that still returns True (see the seam below). |
| [Project/gpio/relay_worker.py](Project/gpio/relay_worker.py) `RelayWorker(QObject)` | Lives on a `QThread`. **Lazy-imports** the flow-sensor and solenoid drivers inside method bodies (line ~215) so GUI startup doesn't pull hardware modules. |
| [Project/gpio/custom_SM16relind.py](Project/gpio/custom_SM16relind.py) | Project-local wrapper used for Pi 5 — upstream lib originally Pi-4-only. |
| [Project/drivers/i2c_coordinator.py](Project/drivers/i2c_coordinator.py) `I2CCoordinator` | Single mutex-guarded I²C handle shared by the relay HAT and flow sensor; prevents address-collision deadlocks. |

## The mock-vs-real seam

At import, `gpio/gpio_handler.py` tries `import SM16relind`, then
`import sm_16relind`. If both raise `ImportError` it prints `WARNING:
SM16relind module not found` and binds the name to an inline
`MockSM16relind` class, but `RelayHandler.__init__` looks up
`SM16relind.SM16relind`, which the mock class does not have, so no hat is
created (`Failed to initialize any relay hats`). The same empty-handler
state follows when the real module loads but the HAT does not answer at
start-up. In that state every `set_relays` call does nothing and still
returns True: the app runs, and deliveries are logged, with no valve moving.
Check the journal for those two lines before trusting a run. Unit tests use
`FakeRelayHandler` from `Project/tests/unit/conftest.py`. **Do not** add
new hardware imports at module top-level — they break boot on a dev Mac and
the headless smoke test. Follow the lazy-import pattern at
[Project/gpio/relay_worker.py:215](Project/gpio/relay_worker.py#L215):

```python
def _do_dispense(self, ...):
    from drivers.flow_sensor_factory import create_flow_sensor  # noqa: PLC0415
    from drivers.uart_flow_sensor import TeensyUnavailableError
    ...
```

## Common errors and what they mean

| Symptom | Likely cause | Where to look |
|---|---|---|
| `OSError: [Errno 121] Remote I/O error` | HAT not at expected I²C address; jumpers wrong | `i2cdetect`, check stack-level jumpers per the 16-RELAYS vendor manual |
| `OSError: [Errno 5] Input/output error` | Bus glitch, loose SDA/SCL, ground loop | Reseat HAT, re-crimp wires, check common ground |
| `OSError: [Errno 110] Connection timed out` | I²C clock conflict (often if `i2c-dev` was just modprobed) | `sudo modprobe i2c-dev` then retry; reboot if persistent |
| `ImportError: No module named 'sm_16relind'` | apt package not installed (or venv not seeing system packages) | Run `scripts/install/40-hardware.sh`; check venv uses `--system-site-packages` |
| GUI says "Hardware control will not work" | `RelayHandler` fell back to mock — likely on a dev machine, but **suspicious on a Pi** | grep startup logs for which branch was taken |

## Pi 4 vs Pi 5 differences

- Pi 5 changed the I²C bus number for the user-facing 40-pin header. Check
  `i2cdetect -y 1` first; if that's empty, try `-y 13` on Pi 5 with certain
  HATs. `scripts/install/40-hardware.sh` configures the right one.
- `custom_SM16relind.py` exists because the upstream lib hard-coded a `/dev/i2c-1`
  open that broke on Pi 5 in earlier firmware. Don't delete it.

## Threading rule (load-bearing)

Hardware calls happen on `RelayWorker`'s `QThread`. Never call `RelayHandler`
methods from a slot connected via the default `AutoConnection`; use
`Qt.QueuedConnection` to marshal the call onto the worker thread. The pattern
is at [Project/main.py:319, 359, 376, 388](Project/main.py#L319). Breaking
this rule manifests as intermittent crashes only seen under real schedules.

See [`references/i2c-cheatsheet.md`](references/i2c-cheatsheet.md) for the
full address map, [`references/diagnostic-commands.md`](references/diagnostic-commands.md)
for shell-level hardware probes, and
[`references/threading-pattern.md`](references/threading-pattern.md) for the
QThread/QueuedConnection pattern.

## Don't do this

- Don't add `RPi.GPIO` or `sm_16relind` to `requirements.txt` — they come
  from apt (see [requirements.txt:3-5](requirements.txt#L3-L5)).
- Don't bypass `RelayHandler` and call `SM16relind` directly from a
  controller or widget — the mock fallback only works through the handler.
- Don't change the mock surface to add behavior the real driver lacks; the
  mock is a *seam* not a *simulator*.
