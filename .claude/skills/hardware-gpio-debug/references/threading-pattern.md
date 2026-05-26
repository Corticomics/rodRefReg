# Hardware threading pattern

PyQt5 + hardware = one thread for the UI, one thread for the relays. Crossing
that boundary without `Qt.QueuedConnection` causes random crashes that only
show up under real schedules.

## The pattern

`RelayWorker(QObject)` lives on a `QThread`. The main thread connects to its
signals/slots using `Qt.QueuedConnection`, which marshals the call onto the
worker's event loop.

Reference call sites in [Project/main.py](Project/main.py):

```python
# Volume updates flow UI ← worker thread
worker.volume_updated.connect(_on_volume_updated, Qt.QueuedConnection)  # ~L359
worker.finished.connect(_on_finished, Qt.QueuedConnection)              # ~L376

# Stop requests cross the other way
control_signals.stop_requested.connect(worker.stop, Qt.QueuedConnection) # ~L388
```

## Why it matters

- Without `QueuedConnection`, the slot runs **synchronously on the calling
  thread**. If the GUI emits and the slot then touches I²C, you've now
  blocked the event loop on a hardware call.
- Worse, if the slot touches Qt widget state from the worker thread, you
  get `QObject::startTimer: Timers cannot be started from another thread`
  or a silent crash.

## What "lazy import" means here

`RelayWorker._do_dispense` defers the flow-sensor and solenoid imports until
the method actually runs ([Project/gpio/relay_worker.py:215](Project/gpio/relay_worker.py#L215)).
Two reasons:

1. **Boot speed** — the GUI starts before hardware drivers initialize, so
   the splash appears instantly even when the Teensy is slow to enumerate.
2. **Test isolation** — `test_gui_smoke.py` can import the whole `ui`
   package without pulling `RPi.GPIO` / `sm_16relind` / `pyserial`.

Don't move these imports to the top of `relay_worker.py`. The cost is a
one-line import inside the hot path; the benefit is the smoke test stays
runnable on any machine.

## Cleanup order

`RelayHandler.cleanup()` must run **before** `QApplication.quit()`. The
pattern in [main.py](Project/main.py) chains: stop signal → worker exits
event loop → `thread.wait()` → handler cleanup → app quit. Reverse that
order and Qt complains about destroyed objects.
