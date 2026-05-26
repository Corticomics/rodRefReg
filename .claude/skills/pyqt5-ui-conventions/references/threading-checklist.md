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
worker.finished.connect(thread.quit)
worker.finished.connect(worker.deleteLater)
thread.finished.connect(thread.deleteLater)
thread.start()
```

Reference: [Project/main.py](Project/main.py) `setup_program()` around the
`RelayWorker` construction (~L300-L395). [Project/gpio/relay_worker.py](Project/gpio/relay_worker.py)
`RelayWorker(QObject)`.

## 2. Every cross-thread signal uses `Qt.QueuedConnection`

Default `AutoConnection` will run a slot **synchronously on the emitter's
thread** if connection happens to be made within one thread, which causes
intermittent crashes. Always be explicit.

Real call sites:

```python
worker.volume_updated.connect(_on_volume_updated, Qt.QueuedConnection)   # main.py:L359
worker.finished.connect(_on_finished, Qt.QueuedConnection)               # main.py:L376
control_signals.stop_requested.connect(worker.stop, Qt.QueuedConnection) # main.py:L388
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
[Project/gpio/relay_worker.py:215](Project/gpio/relay_worker.py#L215):

```python
def _do_dispense(self, ...):
    from drivers.flow_sensor_factory import create_flow_sensor  # noqa: PLC0415
    from drivers.uart_flow_sensor import TeensyUnavailableError
    ...
```

## 5. Cleanup order: stop signal → wait → handler cleanup → quit

`RelayHandler.cleanup()` must run **before** `QApplication.quit()`. The
correct chain is:

1. Emit `stop_requested` to the worker.
2. `thread.quit()` and `thread.wait(timeout_ms)` to let the event loop drain.
3. Call `relay_handler.cleanup()` to release I²C resources.
4. `app.quit()`.

Reverse this order and you'll see `QObject::~QObject: Timers cannot be
stopped from another thread` warnings on shutdown.

## 6. No `QMessageBox.exec_()` from worker-connected slots without `QueuedConnection`

Modal dialogs must run on the main thread. If you connect a worker
signal to a slot that pops a dialog, that connection **must** be
`QueuedConnection`.
