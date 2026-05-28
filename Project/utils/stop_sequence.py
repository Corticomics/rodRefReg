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

  1. **Hardware safe FIRST.** Drop every relay (master + cages) before
     touching the worker thread at all. Even if teardown then hangs, the
     hardware is already safe.
  2. **Bounded waits only.** Never call ``thread.wait()`` without a
     timeout. A thread that refuses to die is abandoned, not awaited
     forever.

See docs/MAINTENANCE.md §1 (delivery/relay bug → always release).
"""

from __future__ import annotations

import time
import traceback

# How long to wait for a clean worker exit before escalating to
# terminate(), and how long to wait for terminate() to take. Both bounded
# — the GUI must never block indefinitely on Stop.
CLEAN_EXIT_TIMEOUT_MS = 3000
TERMINATE_TIMEOUT_MS = 1000


def force_hardware_safe_state(handler) -> bool:
    """Drop every relay (including the global master) immediately.

    Runs FIRST in the stop sequence, before any thread coordination.
    Idempotent. Logs but never raises — a failure here is the most
    important thing the operator could see, so it must not be swallowed
    into a generic stack unwind. Returns True on success, False on error
    (or when there is no handler).
    """
    if handler is None:
        return False
    try:
        handler.set_all_relays(0)
        print("[STOP] HARDWARE SAFE: all relays off (master + cages)")
        return True
    except Exception as exc:
        print(f"[STOP] CRITICAL: hardware safe-state call failed: {exc}")
        traceback.print_exc()
        return False


def bounded_worker_teardown(worker_obj, thread_obj, signals) -> None:
    """Signal the worker and wait briefly. Never block the GUI forever.

    A. Emit ``stop_requested`` (delivered to the worker via QueuedConnection).
    B. ``thread.wait(CLEAN_EXIT_TIMEOUT_MS)`` for a clean exit.
    C. On timeout: ``terminate()`` then ``wait(TERMINATE_TIMEOUT_MS)``.
    D. If that also times out: log and abandon. Hardware is already safe.

    The bounded waits in C/D are the whole point — the v1.8.0 deadlock
    was an unbounded ``wait()`` after a ``terminate()`` that never took.
    """
    if worker_obj is not None:
        # FIRST: poke the cooperative-cancel token directly from this
        # (GUI) thread. The worker thread is typically blocked inside
        # run_until_complete and cannot process the queued stop() slot,
        # so this direct call is what actually breaks the delivery loop.
        # Thread-safe (the strategy uses a threading.Event).
        if hasattr(worker_obj, "request_cancel"):
            try:
                worker_obj.request_cancel()
            except Exception as exc:
                print(f"[STOP] worker.request_cancel() failed: {exc}")

        # THEN: emit the queued stop() for full timer/sensor teardown,
        # which runs once the worker returns to its Qt event loop.
        try:
            signals.stop_requested.emit()
            print("[DEBUG] Worker stop() requested")
        except RuntimeError:
            print("[DEBUG] Worker already deleted")

    if thread_obj is None:
        return
    try:
        is_running = getattr(thread_obj, "isRunning", None)
        if not (callable(is_running) and is_running()):
            return
        # Instrumentation: measure how long the worker takes to exit so a
        # Pi-side log shows whether cooperative cancellation worked
        # (clean exit, small N) or fell through to terminate(). Lets us
        # verify the v1.8.3 fix from real timing instead of guessing.
        t0 = time.monotonic()
        if thread_obj.wait(CLEAN_EXIT_TIMEOUT_MS):
            dt_ms = int((time.monotonic() - t0) * 1000)
            print(f"[STOP] Worker exited cleanly in {dt_ms}ms (cooperative cancel)")
            return
        print(f"[STOP] Worker did not exit in {CLEAN_EXIT_TIMEOUT_MS}ms;"
              " calling terminate()")
        thread_obj.terminate()
        if thread_obj.wait(TERMINATE_TIMEOUT_MS):
            print("[STOP] Thread terminated (cooperative cancel did NOT exit in time)")
        else:
            # NEVER wait() with no arg here — that's the v1.8.0 deadlock.
            print("[STOP] terminate() did not take; abandoning thread"
                  " (hardware already safe)")
    except RuntimeError:
        print("[DEBUG] Thread already deleted")


def execute_stop_sequence(handler, worker_obj, thread_obj, signals,
                          dialog_factory=None) -> bool:
    """Run the stop sequence in the safety-critical order.

    Contract (locked by tests/unit/test_stop_sequence.py):
      1. ``handler.set_all_relays(0)`` is called BEFORE any thread wait
         or terminate.
      2. ``thread.wait`` is only ever called with a positive timeout.

    ``dialog_factory`` (optional) returns an object with a ``close()``
    method shown during teardown; it is always closed, even on error.
    """
    print("[DEBUG] Starting stop sequence")
    force_hardware_safe_state(handler)

    dialog = dialog_factory() if dialog_factory else None
    try:
        bounded_worker_teardown(worker_obj, thread_obj, signals)
    finally:
        if dialog is not None:
            try:
                dialog.close()
            except Exception:
                pass

    print("[DEBUG] Stop sequence completed successfully")
    return True
