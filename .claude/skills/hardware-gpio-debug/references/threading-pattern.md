# Hardware threading pattern

PyQt5 + hardware: schedule deliveries drive the relays from the `RelayWorker`
thread; Stop (hardware safe first), `main.cleanup()` and the Priming panel
call `RelayHandler` on the GUI thread by design, and Calibration pulses on its
own worker thread. Crossing the worker/GUI boundary without
`Qt.QueuedConnection` causes random crashes that only show up under real
schedules.

## The pattern

`RelayWorker(QObject)` lives on a `QThread`. The main thread connects to its
signals/slots using `Qt.QueuedConnection`, which marshals the call onto the
worker's event loop.

Reference call sites in [Project/main.py](Project/main.py):

```python
# The one deliberate DirectConnection: QThread.quit is thread-safe, and a
# queued quit would wait behind Stop's thread.wait() on the GUI thread
worker.finished.connect(thread.quit, Qt.DirectConnection)               # ~L365 (see the comment there)

# The run's record closes on the GUI thread: bound to THIS worker, since
# cleanup() sets the global to None, and connected before cleanup
worker.finished.connect(partial(_on_run_finished, worker), Qt.QueuedConnection)  # ~L370

# Volume updates flow UI ← worker thread
worker.volume_updated.connect(_on_volume_updated, Qt.QueuedConnection)  # ~L423
worker.finished.connect(_on_finished, Qt.QueuedConnection)              # ~L440

# Stop requests cross the other way
control_signals.stop_requested.connect(worker.stop, Qt.QueuedConnection) # ~L453
```

The bound hook runs after `worker.deleteLater` has deleted the worker's Qt
side. It reads only attributes `RelayWorker.__init__` sets: those still
read, but a missing one raises `RuntimeError`, not `AttributeError`, so a
`getattr` default does not help. An operator Stop is recorded by
`stop_program` instead, once the stop sequence has its result: the queued
hook can run inside that sequence's event pump, and leaves the record to it.

## Why it matters

- Without `QueuedConnection`, the slot runs **synchronously on the calling
  thread**. If the GUI emits and the slot then touches I²C, you've now
  blocked the event loop on a hardware call.
- Worse, if the slot touches Qt widget state from the worker thread, you
  get `QObject::startTimer: Timers cannot be started from another thread`
  or a silent crash.

## What "lazy import" means here

`RelayWorker._initialize_hardware` defers the flow-sensor imports until
the method actually runs ([Project/gpio/relay_worker.py:285](Project/gpio/relay_worker.py#L285)).
Two reasons:

1. **Boot speed** — the GUI starts before hardware drivers initialize, so
   the splash appears instantly even when the Teensy is slow to enumerate.
2. **Test isolation** — `test_gui_smoke.py` can import the whole `ui`
   package without pulling `RPi.GPIO` / `sm_16relind` / `pyserial`.

Don't move these imports to the top of `relay_worker.py`. The cost is a
one-line import inside the hot path; the benefit is the smoke test stays
runnable on any machine.

## Stop and cleanup order

There is no `RelayHandler.cleanup()`. Stop runs
`utils.stop_sequence.execute_stop_sequence` (main.py `stop_program`),
**hardware safe first**: `set_all_relays(0)` before touching the worker
thread. Then `worker.request_cancel()` is called directly and at once, before
the Stopping dialog pumps events (thread-safe; it breaks the delivery loop
the worker is blocked in), `stop_requested` is emitted over
`QueuedConnection`, and the thread gets bounded `wait()` calls (3 s, then
`terminate()` and 1 s, then it is abandoned). With a worker or a thread to
tear down, `set_all_relays(0)` runs again after the teardown, and that last
command decides whether the relays count as confirmed off. The sequence
returns `StopResult(relays_confirmed_off, worker_exited)`. When it is not
safe, the Run/Stop section hands the schedule's hold on the operation lock to
`EMERGENCY` before any dialog, then the operator sees one dialog: **Relays
Not Confirmed Off** (disconnect the valve power supply, then check the relay
HAT and its I²C connection) or **Delivery Worker Did Not Stop**. Run,
priming and calibration stay unavailable until a confirmed CLOSE ALL RELAYS
or a restart. When the worker finishes, `main.cleanup()` switches all relays
off again and prints `[CLEANUP] CRITICAL: relays NOT confirmed off` if that
fails; a worker thread still running after its wait is kept, not dropped,
and Run refuses to start beside it. Never add an unbounded `thread.wait()`:
that was the v1.8.0 incident.
