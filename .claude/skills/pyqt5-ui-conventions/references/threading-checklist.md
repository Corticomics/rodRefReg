# Threading checklist

Before merging any code that spawns a `QThread` or moves a `QObject` worker
off the main thread, confirm every item below.

## 1. Worker is a `QObject` moved to a `QThread`

Not a `QThread` subclass. The Qt-recommended pattern (and what RRR uses) is:

```python
worker = MyWorker(...)              # QObject subclass
thread = QThread()
worker.moveToThread(thread)
thread.started.connect(worker.run)
worker.finished.connect(thread.quit, Qt.DirectConnection)  # quit() is thread-safe; see main.py:355-365
worker.finished.connect(worker.deleteLater)
thread.finished.connect(thread.deleteLater)
thread.start()
```

Reference: [Project/main.py](Project/main.py) `run_program()` around the
`RelayWorker` construction (~L339-L454). [Project/gpio/relay_worker.py](Project/gpio/relay_worker.py)
`RelayWorker(QObject)`.

## 2. Every cross-thread signal uses `Qt.QueuedConnection`

Default `AutoConnection` will run a slot **synchronously on the emitter's
thread** if connection happens to be made within one thread, which causes
intermittent crashes. Always be explicit.

Real call sites:

```python
worker.finished.connect(partial(_on_run_finished, worker), Qt.QueuedConnection)  # main.py:L370
worker.volume_updated.connect(_on_volume_updated, Qt.QueuedConnection)   # main.py:L423
worker.finished.connect(_on_finished, Qt.QueuedConnection)               # main.py:L440
control_signals.stop_requested.connect(worker.stop, Qt.QueuedConnection) # main.py:L453
```

A handler that needs the worker that finished is bound to it with
`functools.partial`, as `_on_run_finished` is, and connected before
`cleanup`, which sets the global `worker` to None. It can run after
`deleteLater` has deleted the worker's Qt side: read only attributes the
worker's `__init__` set. Those still read, but a missing one raises
`RuntimeError`, not `AttributeError`, so a `getattr` default does not help.

## 3. No widget touch from the worker thread

Slots that read or mutate widgets must run on the GUI (main) thread. Verify
by reading the slot body — does it call `setText`, `addItem`, `show`,
`hide`, `setEnabled`? If yes, the signal that triggers it must use
`QueuedConnection`.

## 4. Hardware imports are lazy

Don't top-level-import `RPi.GPIO`, `sm_16relind`, or `pyserial` from a UI
module. Import inside the method body so `test_gui_smoke.py` can construct
the widget without hardware deps. Pattern from
[Project/gpio/relay_worker.py:285](Project/gpio/relay_worker.py#L285) (`RelayWorker._initialize_hardware`):

```python
def _initialize_hardware(self):
    ...
    from drivers.flow_sensor_factory import create_flow_sensor
    from drivers.uart_flow_sensor import TeensyUnavailableError
    ...
```

## 5. Stop order: hardware off → cancel → signal → bounded wait → off again

Stop goes through `utils.stop_sequence.execute_stop_sequence`:

1. `relay_handler.set_all_relays(0)` first, before touching the worker
   thread.
2. Call `worker.request_cancel()` directly and at once, before the Stopping
   dialog opens: that dialog pumps the GUI event loop. The call is
   thread-safe; the worker is usually blocked in a delivery and cannot run a
   queued slot.
3. Open the dialog, emit `stop_requested` to the worker (QueuedConnection),
   then `thread.wait(3000)`; on timeout `terminate()` and `wait(1000)`; then
   abandon. Never an unbounded `wait()`.
4. With a worker or a thread to tear down, `set_all_relays(0)` again: a pulse
   begun before the cancel may have switched a relay on. This last command
   gives `relays_confirmed_off`.

It returns `StopResult(relays_confirmed_off, worker_exited)`. When that is
not `.safe`, `RunStopSection._execute_stop` calls
`OperationLock.hold_until_safe(SCHEDULE)` before `reset_ui` and before any
dialog (a dialog's event loop can run the worker's queued `main.cleanup`,
whose `reset_ui` releases SCHEDULE), then shows one dialog: **Relays Not
Confirmed Off** (disconnect the valve power supply, then check the relay HAT
and its I²C connection) or **Delivery Worker Did Not Stop**. Run, priming and
calibration stay unavailable until a confirmed CLOSE ALL RELAYS or a restart.

`main.cleanup()` switches the relays off again when the worker finishes. It
keeps a worker thread that is still running after its wait (dropping the
last reference to a running `QThread` can abort the app), and
`main.run_program` refuses to start beside one.

## 6. No `QMessageBox.exec_()` from worker-connected slots without `QueuedConnection`

Modal dialogs must run on the main thread. If you connect a worker
signal to a slot that pops a dialog, that connection **must** be
`QueuedConnection`.
