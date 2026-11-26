"""A failing or stalled disk never delays a valve close.

The home test Pi's NVMe root disk has dropped out more than once (from
2026-10-29 on). While a disk is gone, a call that reads or writes it fails
or hangs. If the code between a valve's open and its close made such a call,
the valve would stay open while it waited, and the animal would get more
water than its dose.

In 2.1.1 nothing in that window touches the disk:

- the pulse's prints go through ``_say`` to ``print``, and after start-up
  ``sys.stdout`` and ``sys.stderr`` are main's ``StreamRedirector``, whose
  ``write`` only emits a Qt signal;
- the calibration-only valve window makes no logging call with ``exc_info``.
  Formatting a traceback reads the ``.py`` files through ``linecache``.

No test pinned that, and the logging planned for 2.3.0 adds file I/O to this
path. Here a 10-pulse calibration-only delivery runs through the real
SolenoidFlowStrategy on conftest's FakeRelayHandler, with the cage's
calibration saved first. While the delivery runs, the disk fails:

- every DatabaseHandler method raises
  ``sqlite3.OperationalError('disk I/O error')``;
- open (builtins and io), os.open, os.stat, os.lstat, os.listdir,
  os.scandir, os.mkdir, os.utime, os.rename, os.replace, os.remove and
  os.unlink raise ``OSError(EIO)``. sqlite3.connect raises
  ``sqlite3.OperationalError('disk I/O error')``: the sqlite3 module reports
  a failed disk as an OperationalError, never as an OSError. The os.path
  checks, pathlib's open, stat, touch, mkdir, rename, replace and unlink,
  and linecache all go through these calls (Python 3.11 and up: the Pi's
  and both CI jobs').

Each relay write and each disk call is recorded, with its time, in one list,
in the order they happened. The test asserts on that order: no disk call
comes between a relay's ON and its OFF. A stalled disk can only delay a close
from inside that window, so no call has to hang, and the result does not
depend on how fast a CI runner is. One loose timing bound is checked as well:
the median pulse's OFF comes within the pulse width + 50 ms of its ON. A
slow call added to the window would slow every pulse, but one pulse can be
late only because the machine stalled: on a Mac that was swapping, a 30 ms
pulse once stayed open 87 ms with no disk call in it. So the bound is not
put on every pulse. The garbage collector waits while the delivery runs, so
an object an earlier test left behind is not finalized, file cleanup and
all, inside a valve window. On the shared manifold the master is held open
through the whole pulse loop, so there no disk call may come anywhere in the
loop.

The faults are applied only around the delivery call, and only for the
thread that runs it and the threads it starts (asyncio.to_thread and
run_in_executor start theirs from it), so pytest's own file access is
untouched. During the delivery, sys.stdout and sys.stderr are main's
StreamRedirector, as after start-up, and a log handler formats every record
at every level, so a traceback logged inside the window would be formatted
there.

What this cannot see:

- a write, flush or fsync to a file that was opened before the delivery
  (the stream a logging.FileHandler keeps open): it makes none of the calls
  above. The file logging planned for 2.3.0 is to be tested in this file
  with a handler whose write blocks;
- the first import of a module inside the window: the import system reads
  the disk through posix and io.open_code, not through the calls above;
- a call on a thread that was already running when the delivery started (a
  log writer started at start-up): it keeps its disk, so the window waiting
  on such a thread is not seen.
"""

from __future__ import annotations

import asyncio
import builtins
import errno
import gc
import io
import linecache
import logging
import os
import sqlite3
import statistics
import sys
import threading
import time
from contextlib import contextmanager
from typing import NamedTuple

import pytest
from models.database_handler import DatabaseHandler
from strategies import solenoid_flow_strategy
from strategies.solenoid_flow_strategy import SolenoidFlowStrategy
from utils.topology import build_solenoid_controller

PULSES = 10
PULSE_MS = 30  # the production valve's pulse width (Parker 003-0257-900)
Q = 0.034164  # its volume per pulse at 30 ms, in mL, as calibrated on the Pi
# The settle after each pulse and the rest between pulses come after the
# close, outside the window this test is about. They are short only to keep
# the test quick.
SETTLE_MS = 20
REST_MS = 20
# The loose timing bound: the median pulse's OFF comes within this long of its ON.
OPEN_LIMIT_MS = PULSE_MS + 50

CAGE = 1
CAGE_MAP = {cage: cage for cage in range(1, 16)}  # one HAT: cages 1-15 on relays 1-15
RELAY = CAGE_MAP[CAGE]

# The calls that open, look up or change a file, as (module, name). The
# os.path checks, pathlib's file calls and linecache all go through them.
DISK_CALLS = (
    (builtins, "open"),
    (io, "open"),
    (os, "open"),
    (os, "stat"),
    (os, "lstat"),
    (os, "listdir"),
    (os, "scandir"),
    (os, "mkdir"),
    (os, "utime"),
    (os, "rename"),
    (os, "replace"),
    (os, "remove"),
    (os, "unlink"),
    (sqlite3, "connect"),
)

_APP = os.path.dirname(os.path.dirname(os.path.abspath(solenoid_flow_strategy.__file__))) + os.sep
_HERE = os.path.abspath(__file__)
_EIO_TEXT = os.strerror(errno.EIO)


class Event(NamedTuple):
    """A relay write that switched, or a disk call."""

    kind: str  # "relay" or "disk"
    at: float  # time.monotonic()
    what: str  # "relay 1 ON", "os.stat('/x')"
    where: str = ""  # for a disk call: the app code it came from
    relays: tuple = ()  # for a relay write: the relays it switched
    state: int = 0  # and what it switched them to


# --- the recording ---------------------------------------------------------------


def _record_relay_writes(relays, monkeypatch):
    """Record each relay write that switched, with its time. Returns the event list."""
    events = []
    set_relays, set_all_relays = relays.set_relays, relays.set_all_relays

    def _switched(ids, state, name):
        on_off = "ON" if state else "OFF"
        events.append(Event("relay", time.monotonic(), f"{name} {on_off}", "", ids, int(state)))

    def recorded_set_relays(relay_ids, state):
        relay_ids = list(relay_ids)
        ids = tuple(int(relay) for relay in relay_ids)
        switched = set_relays(relay_ids, state)
        if switched:
            _switched(ids, state, f"relay {', '.join(map(str, ids))}")
        return switched

    def recorded_set_all_relays(state):
        switched = set_all_relays(state)
        if switched:
            _switched(("all",), state, "all relays")
        return switched

    monkeypatch.setattr(relays, "set_relays", recorded_set_relays)
    monkeypatch.setattr(relays, "set_all_relays", recorded_set_all_relays)
    return events


def _caller(frame) -> str:
    """Where a disk call came from: the innermost app frame, as 'file.py:line (function)'.

    It walks out of the standard library (when a traceback is formatted,
    linecache makes the os.stat) and out of this file's own helpers.
    """
    found = frame
    while found is not None:
        name = found.f_code.co_filename
        if name.startswith(_APP) and name != _HERE:
            break
        found = found.f_back
    found = found or frame
    code = found.f_code
    return f"{os.path.basename(code.co_filename)}:{found.f_lineno} ({code.co_name})"


def _eio():
    return OSError(errno.EIO, _EIO_TEXT)


def _sqlite_io_error():
    return sqlite3.OperationalError("disk I/O error")


def _failing(label, real, error, events, faulted):
    """A disk call that fails on the ``faulted`` threads and is recorded; any other
    thread gets ``real``."""

    def disk_call(*args, **kwargs):
        if threading.get_ident() not in faulted:
            return real(*args, **kwargs)
        arg = args[0] if args else None
        if isinstance(arg, (str, bytes, int, os.PathLike)):
            shown = f"{label}({arg!r})"
        else:
            shown = f"{label}()"
        events.append(Event("disk", time.monotonic(), shown, _caller(sys._getframe(1))))
        raise error()

    return disk_call


def _starting_faulted(start, faulted):
    """Thread.start, so that a thread a faulted thread starts is faulted too, from its
    first line to its last (asyncio.to_thread and run_in_executor start their
    workers this way)."""

    def faulted_start(thread, *args, **kwargs):
        if threading.get_ident() in faulted:
            run = thread.run

            def faulted_run():
                ident = threading.get_ident()
                faulted.add(ident)
                try:
                    run()
                finally:
                    faulted.discard(ident)

            thread.run = faulted_run
        return start(thread, *args, **kwargs)

    return faulted_start


@contextmanager
def _failing_disk(events):
    """While inside, the disk fails for this thread and for every thread it starts:
    each call is recorded in ``events``, then raises. A thread that was already
    running keeps its disk.

    linecache is emptied on the way in, so a traceback formatted inside has to ask
    the disk for its source lines (and is seen), whatever earlier tests left in the
    cache, and on the way out, so the entries cached while the disk failed go too.
    """
    faulted = {threading.get_ident()}
    start = threading.Thread.start
    linecache.clearcache()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(threading.Thread, "start", _starting_faulted(start, faulted))
        for module, name in DISK_CALLS:
            error = _sqlite_io_error if module is sqlite3 else _eio
            real = getattr(module, name)
            patch.setattr(
                module, name, _failing(f"{module.__name__}.{name}", real, error, events, faulted)
            )
        for name, member in list(vars(DatabaseHandler).items()):
            if name.startswith("__"):
                continue
            label = f"DatabaseHandler.{name}"
            if isinstance(member, (staticmethod, classmethod)):
                failing = _failing(label, member.__func__, _sqlite_io_error, events, faulted)
                patch.setattr(DatabaseHandler, name, type(member)(failing))
            elif callable(member):
                failing = _failing(label, member, _sqlite_io_error, events, faulted)
                patch.setattr(DatabaseHandler, name, failing)
        try:
            yield
        finally:
            faulted.clear()  # a patched call kept past the end gets the real disk
            linecache.clearcache()


@contextmanager
def _terminal_after_start_up(redirector):
    """sys.stdout and sys.stderr are main's StreamRedirector, as after start-up, and
    every log record is formatted onto it, so a traceback logged with exc_info is
    formatted while the delivery runs."""
    handler = logging.StreamHandler(redirector)
    root = logging.getLogger()
    level = root.level
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sys, "stdout", redirector)
        patch.setattr(sys, "stderr", redirector)
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            yield
        finally:
            root.removeHandler(handler)
            root.setLevel(level)


@contextmanager
def _collector_waiting():
    """The garbage collector waits until the delivery is over, so no object an earlier
    test left behind is finalized on the delivery thread: a finalizer that cleans up
    a file would make disk calls inside a valve window. And no full collection (up to
    50 ms in the suite, on a Mac) lands in the timing."""
    enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if enabled:
            gc.enable()


def _deliver_on_a_failing_disk(strategy, events, redirector, pulses=PULSES):
    """One delivery of ``pulses`` x Q while the disk fails. Disk calls go in ``events``."""
    with _terminal_after_start_up(redirector), _failing_disk(events), _collector_waiting():
        return asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=pulses * Q))


# --- what the record says ----------------------------------------------------------


def _disk_calls_while_a_valve_was_open(events):
    """Each disk call that came between a relay's ON and its OFF, with the relays on."""
    on = set()
    found = []
    for event in events:
        if event.kind == "relay":
            if event.relays == ("all",):
                on = {"all"} if event.state else set()
            elif event.state:
                on.update(event.relays)
            else:
                on.difference_update(event.relays)
        elif on:
            relays = ", ".join(str(relay) for relay in sorted(on, key=str))
            found.append(f"{event.what} from {event.where} with relay {relays} on")
    return found


def _open_times(events, relay):
    """How long ``relay`` stayed on each time it was switched on, in seconds."""
    times, since = [], None
    for event in events:
        if event.kind != "relay" or not (relay in event.relays or event.relays == ("all",)):
            continue
        if event.state and since is None:
            since = event.at
        elif not event.state and since is not None:
            times.append(event.at - since)
            since = None
    return times


# --- the rig -----------------------------------------------------------------------


@pytest.fixture
def redirector(monkeypatch, isolated_data_dir):
    """main's StreamRedirector: what sys.stdout and sys.stderr are after start-up."""
    pytest.importorskip("PyQt5")
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # main installs its own on import
    import main  # noqa: PLC0415

    return main.StreamRedirector()


def _calibrate(db, topology):
    """The cage's calibration, saved as the wizard saves it, before the run."""
    assert db.save_valve_calibration(
        cage_id=CAGE,
        relay_id=RELAY,
        pulse_width_ms=PULSE_MS,
        volume_per_pulse_ml=Q,
        stddev_ml=0.0003,
        cv_pct=1.0,
        num_samples=250,
        inter_pulse_interval_ms=REST_MS,
        topology=topology,
    )


def _strategy(relays, db, topology):
    """The strategy as the worker builds it: the device's valve controller, no flow
    sensor (calibration-only, as the rigs run), and the database it takes the
    calibration snapshot from."""
    settings = {
        'valve_topology': topology,
        'pulse_settling_ms': SETTLE_MS,
        'max_pulses_per_delivery': 100,
        'max_pulse_delivery_time_s': 120.0,
    }
    return SolenoidFlowStrategy(
        solenoid_controller=build_solenoid_controller(relays, settings, CAGE_MAP),
        flow_sensor=None,
        calibration_store=None,
        settings=settings,
        database_handler=db,
    )


# --- the tests -----------------------------------------------------------------------


@pytest.mark.parametrize("topology", ["independent", "shared_manifold"])
def test_a_failing_or_stalled_disk_never_delays_a_valve_close(
    topology, database_handler, fake_relay_handler, redirector, monkeypatch
):
    """Ten pulses while the disk fails: no disk call while a valve is open, every
    pulse fired and credited at the cage's q, and every relay off at the end."""
    _calibrate(database_handler, topology)
    strategy = _strategy(fake_relay_handler, database_handler, topology)
    events = _record_relay_writes(fake_relay_handler, monkeypatch)

    result = _deliver_on_a_failing_disk(strategy, events, redirector)

    assert _disk_calls_while_a_valve_was_open(events) == []
    cage_writes = [event.state for event in events if RELAY in event.relays]
    fired = cage_writes.count(1)
    assert fired == PULSES, f"{PULSES} pulses fired"
    assert cage_writes[-1] == 0, "the last write to the cage relay is OFF"
    assert fake_relay_handler.energized() == set()
    assert result.success is True
    assert result.pulses == fired
    assert result.volume_per_pulse_ml == pytest.approx(Q), "the cage's own calibration"
    assert result.delivered_ml == pytest.approx(fired * Q), "pulses fired x q"
    # The loose bound only: the order above is what pins the property. It is put on
    # the median pulse, since one pulse can be late because the machine stalled.
    open_ms = [seconds * 1000 for seconds in _open_times(events, RELAY)]
    assert len(open_ms) == PULSES
    shown = ", ".join(f"{ms:.0f}" for ms in open_ms)
    assert statistics.median(open_ms) < OPEN_LIMIT_MS, f"{PULSE_MS} ms pulses open {shown} ms"


def _open_a_file():
    try:
        open(_HERE).close()
    except OSError:
        pass


def _open_a_file_on_a_thread():
    """The valve window waits for a disk call made on a thread of its own, as an
    ``await asyncio.to_thread(...)`` would."""
    thread = threading.Thread(target=_open_a_file)
    thread.start()
    thread.join()


def _log_a_traceback():
    try:
        raise RuntimeError("a fault while a valve is open")
    except RuntimeError:
        logging.getLogger(__name__).error("logged with its traceback", exc_info=True)


@pytest.mark.parametrize(
    "touch",
    [_open_a_file, _open_a_file_on_a_thread, _log_a_traceback],
    ids=["open", "open-on-a-thread", "exc_info-log"],
)
def test_a_disk_call_while_a_valve_is_open_is_caught(
    touch, database_handler, fake_relay_handler, redirector, monkeypatch
):
    """The test above cannot pass by missing what it looks for: the same delivery with
    a disk call made while each valve is open is caught, whether the delivery thread
    makes it or waits for a thread it started to make it, and so is a traceback
    logged then, through the os.stat that linecache makes."""
    _calibrate(database_handler, "independent")
    strategy = _strategy(fake_relay_handler, database_handler, "independent")
    events = _record_relay_writes(fake_relay_handler, monkeypatch)
    write = fake_relay_handler.set_relays

    def set_relays(relay_ids, state):
        switched = write(relay_ids, state)
        if state:
            touch()  # the valve is open now
        return switched

    monkeypatch.setattr(fake_relay_handler, "set_relays", set_relays)

    result = _deliver_on_a_failing_disk(strategy, events, redirector, pulses=2)

    found = _disk_calls_while_a_valve_was_open(events)
    assert found, "a disk call while a valve was open went unnoticed"
    assert all(line.endswith(f"with relay {RELAY} on") for line in found), found
    assert result.pulses == 2, "the disk call itself stopped nothing"


def _error_of(call):
    """What ``call`` raised: (its type's name, its errno or else its text)."""
    try:
        call()
    except Exception as error:
        return type(error).__name__, getattr(error, "errno", None) or str(error)
    return None


def test_the_disk_fails_inside_only_and_only_for_the_delivery(database_handler, tmp_path):
    """Inside the fault, every patched call fails and is recorded, on this thread and
    on a thread it starts; a thread that was already running keeps its disk; after
    it, the real calls are back. So the tests above cannot pass because a call
    slipped past the fault, and pytest and any other thread keep their disk."""
    probe = tmp_path / "probe.txt"
    probe.write_text("x")
    moved = tmp_path / "moved.txt"
    events, seen = [], {}
    told, done = threading.Event(), threading.Event()

    def read_when_told():
        told.wait(timeout=10)
        with open(probe) as f:
            seen["running"] = f.read()
        done.set()

    def open_on_a_started_thread():
        seen["started"] = _error_of(lambda: open(probe))

    running = threading.Thread(target=read_when_told)
    running.start()  # before the fault: a thread that was already running
    calls = {  # one call to each, in DISK_CALLS order
        "builtins.open": lambda: open(probe),
        "io.open": lambda: io.open(probe),
        "os.open": lambda: os.open(probe, os.O_RDONLY),
        "os.stat": lambda: os.stat(probe),
        "os.lstat": lambda: os.lstat(probe),
        "os.listdir": lambda: os.listdir(tmp_path),
        "os.scandir": lambda: os.scandir(tmp_path),
        "os.mkdir": lambda: os.mkdir(tmp_path / "new"),
        "os.utime": lambda: os.utime(probe),
        "os.rename": lambda: os.rename(probe, moved),
        "os.replace": lambda: os.replace(probe, moved),
        "os.remove": lambda: os.remove(probe),
        "os.unlink": lambda: os.unlink(probe),
        "sqlite3.connect": lambda: sqlite3.connect(str(tmp_path / "probe.db")),
    }
    assert list(calls) == [f"{module.__name__}.{name}" for module, name in DISK_CALLS]

    with _failing_disk(events):
        errors = [_error_of(call) for call in calls.values()]
        errors.append(_error_of(database_handler.get_all_valve_calibrations))
        started = threading.Thread(target=open_on_a_started_thread)
        started.start()
        started.join(timeout=10)
        told.set()
        done.wait(timeout=10)
    running.join(timeout=10)

    sqlite_error = ("OperationalError", "disk I/O error")
    assert errors == [("OSError", errno.EIO)] * (len(calls) - 1) + [sqlite_error] * 2
    assert [event.what.split("(")[0] for event in events] == [
        *calls,
        "DatabaseHandler.get_all_valve_calibrations",
        "builtins.open",  # from the thread started inside
    ]
    assert seen == {
        "started": ("OSError", errno.EIO),
        "running": "x",
    }, "a thread started inside is faulted; one already running is not"
    left = sorted(os.listdir(tmp_path))
    assert left == ["data", "probe.txt"], "no faulted call reached the disk"
    with open(probe) as f:
        assert f.read() == "x", "after it, open is the real one again"
    assert os.stat(probe).st_size == 1
    assert database_handler.get_all_valve_calibrations() == {}
