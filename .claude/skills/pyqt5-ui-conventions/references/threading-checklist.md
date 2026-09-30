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
worker.finished.connect(thread.quit, Qt.DirectConnection)  # quit() is thread-safe; see main.py:335-345
worker.finished.connect(worker.deleteLater)
thread.finished.connect(thread.deleteLater)
thread.start()
```

Reference: [Project/main.py](Project/main.py) `run_program()` around the
`RelayWorker` construction (~L320-L430). [Project/gpio/relay_worker.py](Project/gpio/relay_worker.py)
`RelayWorker(QObject)`.

## 2. Every cross-thread signal uses `Qt.QueuedConnection`

Default `AutoConnection` will run a slot **synchronously on the emitter's
thread** if connection happens to be made within one thread, which causes
intermittent crashes. Always be explicit.

Real call sites:

```python
worker.volume_updated.connect(_on_volume_updated, Qt.QueuedConnection)   # main.py:L399
worker.finished.connect(_on_finished, Qt.QueuedConnection)               # main.py:L416
control_signals.stop_requested.connect(worker.stop, Qt.QueuedConnection) # main.py:L429
```

## 3. No widget touch from the worker thread

Slots that read or mutate widgets must run on the GUI (main) thread. Verify
by reading the slot body — does it call `setText`, `addItem`, `show`,
`hide`, `setEnabled`? If yes, the signal that triggers it must use
`QueuedConnection`.

## 4. Hardware imports are lazy

Don't top-level-import `RPi.GPIO`, `sm_16relind`, or `pyserial` from a UI
module. Import inside the method body so `test_gui_smoke.py` can construct
the widget without hardware deps. Pattern from
[Project/gpio/relay_worker.py:256](Project/gpio/relay_worker.py#L256) (`RelayWorker._initialize_hardware`):

```python
def _initialize_hardware(self):
    ...
    from drivers.flow_sensor_factory import create_flow_sensor
    from drivers.uart_flow_sensor import TeensyUnavailableError
    ...
```

## 5. Stop order: hardware off → cancel → signal → bounded wait

Stop goes through `utils.stop_sequence.execute_stop_sequence`:

1. `relay_handler.set_all_relays(0)` first. If it returns False, a HAT did
   not confirm OFF: tell the operator to disconnect the valve power
   (**Relays Not Confirmed Off**, shown once the teardown ends).
2. Call `worker.request_cancel()` directly (thread-safe; the worker is
   usually blocked in a delivery and cannot run a queued slot), then emit
   `stop_requested` to the worker (QueuedConnection).
3. `thread.wait(3000)`; on timeout `terminate()` and `wait(1000)`; then
   abandon. Never an unbounded `wait()`.

`main.cleanup()` switches the relays off again when the worker finishes.

## 6. No `QMessageBox.exec_()` from worker-connected slots without `QueuedConnection`

Modal dialogs must run on the main thread. If you connect a worker
signal to a slot that pops a dialog, that connection **must** be
`QueuedConnection`.
