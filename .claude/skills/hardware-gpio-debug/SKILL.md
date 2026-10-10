---
name: hardware-gpio-debug
description: Diagnose RRR hardware path failures — Sequent Microsystems 16-relay HAT not detected, I²C errors (errno 121 / 5 / 110), Pi 4 vs Pi 5 GPIO differences, what happens when the relay library or a HAT is missing (writes are refused, deliveries stop with [VALVE ERROR]), and the lazy-init pattern used by RelayWorker. Use when the user reports "relays not clicking", "Hardware control will not work", "pump not firing", an I²C exception, or asks how to test the relay path before running a schedule.
---

# Hardware / GPIO debugging

The water-delivery hot path is:

```
Run (RunStopSection) → main.run_program → RelayWorker (QThread)
       → StrategyFactory → SolenoidFlowStrategy / PumpStrategy
       → SolenoidController (or IndependentSolenoidController) / PumpController
       → RelayHandler → SM16relind (one per HAT stack) → I²C bus
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

# RRR's own selftest (used by the update applier; safe to run manually).
# It only imports the core modules and opens the database: it does not touch the relay HATs.
~/rrr/shared/venv/bin/python3 ~/rrr/current/Project/main.py --selftest
```

If `i2cdetect` shows no devices → bus or wiring (check 3.3 V, SDA/SCL, common
ground). If `16relind` works but RRR doesn't → it's a Python-layer problem.

## Key files and their responsibilities

| File | What it owns |
|---|---|
| [Project/gpio/gpio_handler.py](Project/gpio/gpio_handler.py) `RelayHandler` | Public façade. Keeps one `SM16relind` slot per configured stack (relay 17 is stack 1, relay 1). A HAT that did not answer when the handler was built leaves its slot empty. `set_relays` / `set_all_relays` return False when a relay did not switch (missing HAT, relay id below 1, vendor error), and callers stop and report it. The schedule path's handler is built at start-up and rebuilt only by Change Relay Hats. After fixing a HAT, close and reopen RRR, as the `[VALVE ERROR]` line says. |
| [Project/gpio/relay_worker.py](Project/gpio/relay_worker.py) `RelayWorker(QObject)` | Lives on a `QThread`. **Lazy-imports** the flow-sensor driver inside `_initialize_hardware` (line ~256) so GUI start-up doesn't pull serial/sensor modules; the valve controller comes from `utils.topology.build_solenoid_controller`, imported at the top of the module. |
| [Project/gpio/custom_SM16relind.py](Project/gpio/custom_SM16relind.py) | Project-local wrapper with multi-bus support. Used only when the environment sets `RRR_USE_CUSTOM_SM16=1`; by default RRR imports the vendor `SM16relind` / `sm_16relind` module. |
| [Project/drivers/i2c_coordinator.py](Project/drivers/i2c_coordinator.py) `I2CCoordinator` | Gates relay writes by device type. `RelayHandler._run_coordinated` calls `sync_exclusive_access('relay', …)`, which claims the bus under an `RLock`, runs the write outside the lock, then waits 10 ms before releasing. A second `'relay'` caller is let straight in, so two relay writes are not serialised against each other. If the coordinator itself fails, the write runs directly. The flow sensor no longer shares the bus: it sits behind the Teensy on USB serial. |

## Running without the relay library or a HAT

At import, `gpio/gpio_handler.py` tries `import SM16relind`, then
`import sm_16relind` (the project's `custom_SM16relind` comes first only
when `RRR_USE_CUSTOM_SM16=1`). If both raise `ImportError` it prints
`WARNING: SM16relind module not found. Hardware control will not work.`
and binds the name to an inline `MockSM16relind` stub. `RelayHandler`
looks up `SM16relind.SM16relind`, which the stub does not have, so every
stack fails with `Failed to initialize hat stack=N: SM16relind class not
found in module`, then `Failed to initialize any relay hats`. A HAT that
does not answer at start-up leaves its stack's slot empty the same way
(`Failed to initialize hat stack=N: <error>`).

Nothing is faked from there on. A write to a relay with no HAT prints
`Relay N not switched: no initialised relay HAT for it` and returns False.
In solenoid pulse mode (the default) the delivery stops with
`[VALVE ERROR] cage N: …; delivery stopped`; in any mode its ledger row is
`partial` (some water got through) or `failed`. A cage
or master valve whose close did not get through, or whose relay has not
answered since the run started, raises `[VALVE CRITICAL] … OPEN`. A Stop
whose all-off command a HAT did not confirm, or whose delivery worker did
not stop, shows one dialog (**Relays Not Confirmed Off** or **Delivery
Worker Did Not Stop**) and hands the operation lock to `EMERGENCY` until a
confirmed CLOSE ALL RELAYS or a restart; with a HAT missing since start-up,
every Stop does. The Priming panel's **CLOSE ALL RELAYS** button (which
also stops a running schedule) shows **Emergency Stop Failed** and keeps
the operation lock held: by the open priming session (which hands it to
`EMERGENCY` when it ends), or else by the `EMERGENCY` holder, until a later
press is confirmed or RRR is restarted. That later press builds a fresh
`RelayHandler`, so a HAT reseated since the first press is found.
The schedule path sets up its HATs when RRR starts (and again only on
Change Relay Hats): after fixing one, close and reopen RRR.

Unit tests use `FakeRelayHandler` from `Project/tests/unit/conftest.py`.
**Do not** add new hardware imports at module top-level — they break boot
on a dev Mac and the headless smoke test. Follow the lazy-import pattern in
`RelayWorker._initialize_hardware`
([Project/gpio/relay_worker.py:256](Project/gpio/relay_worker.py#L256)):

```python
def _initialize_hardware(self):
    ...
    from drivers.flow_sensor_factory import create_flow_sensor
    from drivers.uart_flow_sensor import TeensyUnavailableError
    ...
```

## Common errors and what they mean

| Symptom | Likely cause | Where to look |
|---|---|---|
| `OSError: [Errno 121] Remote I/O error` | HAT not at expected I²C address; jumpers wrong | `i2cdetect`, check stack-level jumpers per the 16-RELAYS vendor manual |
| `OSError: [Errno 5] Input/output error` | Bus glitch, loose SDA/SCL, ground loop | Reseat HAT, re-crimp wires, check common ground |
| `OSError: [Errno 110] Connection timed out` | I²C clock conflict (often if `i2c-dev` was just modprobed) | `sudo modprobe i2c-dev` then retry; reboot if persistent |
| Journal shows `WARNING: SM16relind module not found. Hardware control will not work.`, then `Failed to initialize hat stack=0: SM16relind class not found in module` and `Failed to initialize any relay hats` | apt package not installed, or the venv does not see system packages (the ImportError is caught, so there is no traceback) | Run `scripts/install/40-hardware.sh`; check the venv uses `--system-site-packages` |
| Terminal tab shows `Relay N not switched: no initialised relay HAT for it` or `[VALVE ERROR] cage N: …; delivery stopped` | No HAT answered for that relay when RRR started, or an I²C write failed | `i2cdetect -y 1`; fix the HAT, then close and reopen RRR (the schedule path sets its HATs up at start-up) |
| `[VALVE CRITICAL] … OPEN`, **Relays Not Confirmed Off** or **Emergency Stop Failed** | A close or the all-off command did not reach a HAT, or a valve's relay has not answered since the run started | Disconnect the valve power supply, then check the relay HAT and its I²C connection; Settings > Priming > **CLOSE ALL RELAYS** switches every relay off again and stops a running schedule |

## Pi 4 vs Pi 5 differences

- Pi 5 changed the I²C bus number for the user-facing 40-pin header. Check
  `i2cdetect -y 1` first; if that's empty, try `-y 13` on Pi 5 with certain
  HATs. `scripts/install/40-hardware.sh` configures the right one.
- `custom_SM16relind.py` exists because the upstream lib hard-coded a `/dev/i2c-1`
  open that broke on Pi 5 in earlier firmware. Don't delete it.

## Threading rule (load-bearing)

Schedule deliveries drive the relays from `RelayWorker`'s `QThread`. Some
hardware calls deliberately run elsewhere: Stop (`utils.stop_sequence`)
first calls `set_all_relays(0)`, then `worker.request_cancel()`, directly on
the GUI thread, and `set_all_relays(0)` again after the worker's teardown;
`main.cleanup()` switches the relays off again on the GUI thread; the
Priming panel drives its own `RelayHandler` from its buttons, on the GUI
thread; and Calibration pulses on its own `_CalibrationPulseWorker` thread.
Signals between the worker and the GUI use
`Qt.QueuedConnection`; don't move the Stop calls behind a queued signal. The
pattern is at
[Project/main.py:412, 429, 442](Project/main.py#L412). One connection is
deliberately `Qt.DirectConnection`: `worker.finished → thread.quit`
(main.py:348-358). `QThread.quit` is thread-safe, and a queued quit would
wait behind Stop's `thread.wait()` on the GUI thread. Breaking these rules
manifests as intermittent crashes or a hung Stop, seen only under real
schedules.

See [`references/i2c-cheatsheet.md`](references/i2c-cheatsheet.md) for the
full address map, [`references/diagnostic-commands.md`](references/diagnostic-commands.md)
for shell-level hardware probes, and
[`references/threading-pattern.md`](references/threading-pattern.md) for the
QThread/QueuedConnection pattern.

## Don't do this

- Don't add `RPi.GPIO` or `sm_16relind` to `requirements.txt` — they come
  from apt (see [requirements.txt:3-5](requirements.txt#L3-L5)).
- Don't bypass `RelayHandler` and call `SM16relind` directly from a
  controller or widget: the handler routes relays by stack and refuses (returns
  False for) a write to a missing HAT or a relay id below 1.
- Don't ignore a False from `set_relays` / `set_all_relays`: a relay did
  not switch. End the delivery, credit only the water that actually flowed,
  and say so (`[VALVE ERROR]` / `[VALVE CRITICAL]`).
- Don't make the inline `MockSM16relind` stub drive anything; for tests use
  `FakeRelayHandler` in `Project/tests/unit/conftest.py`.
