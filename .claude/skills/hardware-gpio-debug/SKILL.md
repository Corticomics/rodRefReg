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
| [Project/gpio/gpio_handler.py](Project/gpio/gpio_handler.py) `RelayHandler` | Public façade. Owns the per-HAT `SM16relind` instances; routes trigger commands; tolerates missing hardware by falling back to `MockSM16relind`. |
| [Project/gpio/relay_worker.py](Project/gpio/relay_worker.py) `RelayWorker(QObject)` | Lives on a `QThread`. **Lazy-imports** the flow-sensor and solenoid drivers inside method bodies (line ~215) so GUI startup doesn't pull hardware modules. |
| [Project/gpio/mock_gpio_handler.py](Project/gpio/mock_gpio_handler.py) `MockSM16relind` | Drop-in stand-in when `sm_16relind` isn't installed or hardware is absent. Logs the call instead of clicking. |
| [Project/gpio/custom_SM16relind.py](Project/gpio/custom_SM16relind.py) | Project-local wrapper used for Pi 5 — upstream lib originally Pi-4-only. |
| [Project/drivers/i2c_coordinator.py](Project/drivers/i2c_coordinator.py) `I2CCoordinator` | Single mutex-guarded I²C handle shared by the relay HAT and flow sensor; prevents address-collision deadlocks. |

## The mock-vs-real seam

`RelayHandler.__init__` tries `from sm_16relind import SM16relind` and falls back
to `MockSM16relind` on `ImportError` or board-not-found errors. **Do not** add
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
