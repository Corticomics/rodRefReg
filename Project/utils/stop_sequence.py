"""Safety-critical stop-sequence ordering for the Stop button.

Deliberately **Qt-free** so the ordering contract can be unit-tested with
plain mocks and no PyQt5 / hardware present. main.py supplies the real
worker / thread / relay-handler globals and a Qt dialog factory; this
module owns *only* the order of operations and the bounded-wait policy.

Why this module exists (the v1.8.0 incident):

An operator pressed Stop mid-delivery. The old ``stop_program`` emitted
the worker-stop signal, then called ``thread.wait()`` with no timeout
after ``terminate()``. The worker was inside an async C-extension call
(asyncio + libserial), so ``terminate()`` never took, ``wait()`` blocked
the GUI thread forever, and the hardware-failsafe line — which ran *last*
— was never reached. The global master solenoid stayed energized with
the cage valves closed: trapped line pressure, an unsafe state.

The fix this module encodes:

  1. **Hardware safe FIRST.** Drop every relay (cage valves, and the master where
     the rig has one) before
     touching the worker thread at all. Even if teardown then hangs, the
     hardware is already safe.
  2. **Cancel at once.** The worker's cooperative cancel follows the all-off
     immediately, before the Stopping dialog pumps events, so a delivery
     cannot start another pulse while that dialog opens.
  3. **Bounded waits only.** Never call ``thread.wait()`` without a
     timeout. A thread that refuses to die is abandoned, not awaited
     forever.
  4. **Off again at the end.** A pulse the worker began before it saw the
     cancel may have switched a relay on after the first all-off, so every
     relay is switched off once more after the teardown, and that command
     decides whether the relays count as confirmed off.

See docs/MAINTENANCE.md §1 (delivery/relay bug → always release).
"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass

# How long to wait for a clean worker exit before escalating to
# terminate(), and how long to wait for terminate() to take. Both bounded
# — the GUI must never block indefinitely on Stop.
CLEAN_EXIT_TIMEOUT_MS = 3000
TERMINATE_TIMEOUT_MS = 1000


@dataclass(frozen=True)
class StopResult:
    """What a stop achieved.

    ``relays_confirmed_off``: the last all-off command was taken by every
    relay HAT (True when there is no relay handler at all: nothing to switch).
    ``worker_exited``: the worker thread is gone (it exited, was terminated,
    or there was none); False when it was abandoned still running.
    """

    relays_confirmed_off: bool
    worker_exited: bool

    @property
    def safe(self) -> bool:
        """Every relay confirmed off and no worker left that could open one."""
        return self.relays_confirmed_off and self.worker_exited


def force_hardware_safe_state(handler) -> bool:
    """Drop every relay on every HAT (cage valves, and the master where the rig
    has one) immediately.

    Runs FIRST in the stop sequence, before any thread coordination.
    Idempotent. Logs but never raises — a failure here is the most
    important thing the operator could see, so it must not be swallowed
    into a generic stack unwind. Returns True on success, False on error
    (or when there is no handler).
    """
    if handler is None:
        return False
    try:
        all_off = handler.set_all_relays(0)
    except Exception as exc:
        print(f"[STOP] CRITICAL: hardware safe-state call failed: {exc}")
        traceback.print_exc()
        return False
    if all_off is False:
        # RelayHandler says a HAT was missing or did not take the command:
        # its relays, and the valves on them, are in an unknown state.
        print(
            "[STOP] CRITICAL: not every relay HAT confirmed OFF; a valve may still be "
            "open. Disconnect the valve power supply."
        )
        return False
    print("[STOP] HARDWARE SAFE: all relays off on every relay HAT")
    return True


def request_worker_cancel(worker_obj) -> None:
    """Poke the worker's cooperative-cancel token directly from this (GUI)
    thread. Never raises.

    The worker thread is typically blocked inside run_until_complete and
    cannot process the queued stop() slot, so this direct call is what
    actually breaks the delivery loop. Thread-safe (the strategy uses a
    threading.Event).
    """
    if worker_obj is None or not hasattr(worker_obj, "request_cancel"):
        return
    try:
        worker_obj.request_cancel()
    except Exception as exc:
        print(f"[STOP] worker.request_cancel() failed: {exc}")


def bounded_worker_teardown(worker_obj, thread_obj, signals) -> bool:
    """Signal the worker and wait briefly. Never block the GUI forever.

    A. Emit ``stop_requested`` (delivered to the worker via QueuedConnection).
    B. ``thread.wait(CLEAN_EXIT_TIMEOUT_MS)`` for a clean exit.
    C. On timeout: ``terminate()`` then ``wait(TERMINATE_TIMEOUT_MS)``.
    D. If that also times out: log and abandon. Hardware is already safe.

    The bounded waits in C/D are the whole point — the v1.8.0 deadlock
    was an unbounded ``wait()`` after a ``terminate()`` that never took.

    Returns True once the worker thread is gone (it exited, was terminated,
    was already deleted, or there was none), False if it was abandoned.
    """
    if worker_obj is not None:
        # Emit the queued stop() for full timer/sensor teardown, which runs
        # once the worker returns to its Qt event loop. (The cooperative
        # cancel was already requested; see execute_stop_sequence.)
        try:
            signals.stop_requested.emit()
            print("[DEBUG] Worker stop() requested")
        except RuntimeError:
            print("[DEBUG] Worker already deleted")

    if thread_obj is None:
        return True
    try:
        is_running = getattr(thread_obj, "isRunning", None)
        if not (callable(is_running) and is_running()):
            return True
        # Instrumentation: measure how long the worker takes to exit so a
        # Pi-side log shows whether cooperative cancellation worked
        # (clean exit, small N) or fell through to terminate(). Lets us
        # verify the v1.8.3 fix from real timing instead of guessing.
        t0 = time.monotonic()
        if thread_obj.wait(CLEAN_EXIT_TIMEOUT_MS):
            dt_ms = int((time.monotonic() - t0) * 1000)
            print(f"[STOP] Worker exited cleanly in {dt_ms}ms (cooperative cancel)")
            return True
        print(f"[STOP] Worker did not exit in {CLEAN_EXIT_TIMEOUT_MS}ms;" " calling terminate()")
        thread_obj.terminate()
        if thread_obj.wait(TERMINATE_TIMEOUT_MS):
            print("[STOP] Thread terminated (cooperative cancel did NOT exit in time)")
            return True
        # NEVER wait() with no arg here — that's the v1.8.0 deadlock.
        print("[STOP] terminate() did not take; abandoning thread" " (hardware already safe)")
        return False
    except RuntimeError:
        # The QThread is deleted (deleteLater) only after it has finished.
        print("[DEBUG] Thread already deleted")
        return True


def execute_stop_sequence(
    handler, worker_obj, thread_obj, signals, dialog_factory=None
) -> StopResult:
    """Run the stop sequence in the safety-critical order.

    Contract (locked by tests/unit/test_stop_sequence.py):
      1. ``handler.set_all_relays(0)`` is called BEFORE any thread wait
         or terminate.
      2. ``worker.request_cancel()`` follows it at once, before
         ``dialog_factory`` (whose dialog pumps the GUI event loop).
      3. ``thread.wait`` is only ever called with a positive timeout.
      4. With a worker or a thread to tear down, every relay is switched
         off once more afterwards, and that command decides
         ``relays_confirmed_off``.

    ``dialog_factory`` (optional) returns an object with a ``close()``
    method shown during teardown; it is always closed, even on error.

    Returns a :class:`StopResult`. The caller tells the operator when the
    stop is not :attr:`StopResult.safe`, and keeps the hardware locked.
    """
    print("[DEBUG] Starting stop sequence")
    relays_off = force_hardware_safe_state(handler)
    request_worker_cancel(worker_obj)

    dialog = dialog_factory() if dialog_factory else None
    worker_exited = False
    try:
        worker_exited = bounded_worker_teardown(worker_obj, thread_obj, signals)
    finally:
        # With no worker and no thread, nothing could have switched a relay
        # on since the first all-off.
        if worker_obj is not None or thread_obj is not None:
            relays_off = force_hardware_safe_state(handler)
        if dialog is not None:
            try:
                dialog.close()
            except Exception:
                pass

    result = StopResult(
        relays_confirmed_off=relays_off or handler is None,
        worker_exited=worker_exited,
    )
    if not result.relays_confirmed_off:
        print("[DEBUG] Stop sequence completed; relays NOT confirmed off")
    elif not result.worker_exited:
        print("[DEBUG] Stop sequence completed; the worker thread is still running")
    else:
        print("[DEBUG] Stop sequence completed successfully")
    return result
