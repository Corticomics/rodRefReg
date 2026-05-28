"""Tests for the safety-critical stop sequence (utils.stop_sequence).

Regression coverage for the v1.8.0 incident: an operator pressed Stop
mid-delivery, the GUI deadlocked on an unbounded ``thread.wait()`` after
a ``terminate()`` that never took, and the hardware failsafe (which ran
last) was never reached — leaving the master solenoid energized.

These tests are deliberately Qt-free and hardware-free: the module under
test takes all collaborators as injected mocks, so the ordering contract
can be asserted on any machine without PyQt5 or a relay HAT.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from utils import stop_sequence


def _make_signals():
    signals = MagicMock()
    signals.stop_requested = MagicMock()
    return signals


# ---------------------------------------------------------------------------
# The core safety invariant
# ---------------------------------------------------------------------------

def test_hardware_safe_runs_before_any_thread_interaction():
    """``set_all_relays(0)`` must fire before the thread is waited on.

    The whole incident was caused by the failsafe running *after* a
    blocking wait. A shared call-order recorder proves the ordering.
    """
    order = []
    handler = MagicMock()
    handler.set_all_relays.side_effect = lambda *_a: order.append("relays_off")

    thread = MagicMock()
    thread.isRunning.return_value = True
    thread.wait.side_effect = lambda *_a: order.append("thread_wait") or True

    worker = MagicMock()
    signals = _make_signals()
    signals.stop_requested.emit.side_effect = lambda: order.append("stop_emit")

    stop_sequence.execute_stop_sequence(handler, worker, thread, signals)

    assert order, "nothing happened"
    assert order[0] == "relays_off", f"hardware not first: {order}"
    assert order.index("relays_off") < order.index("thread_wait")


def test_thread_wait_is_always_bounded():
    """Every ``thread.wait`` call must carry a positive timeout.

    Guards against the exact v1.8.0 bug: ``thread.wait()`` with no arg
    blocks the GUI thread forever when ``terminate()`` doesn't take.
    """
    handler = MagicMock()
    thread = MagicMock()
    thread.isRunning.return_value = True
    # Clean-exit wait times out -> escalate to terminate, then wait again.
    thread.wait.return_value = False
    worker = MagicMock()

    stop_sequence.execute_stop_sequence(handler, worker, thread, _make_signals())

    assert thread.wait.call_count >= 1
    for call in thread.wait.call_args_list:
        args = call.args
        assert args, f"thread.wait() called with no timeout: {call}"
        assert args[0] > 0, f"thread.wait() called with non-positive timeout: {call}"


def test_terminate_called_when_clean_exit_times_out():
    handler = MagicMock()
    thread = MagicMock()
    thread.isRunning.return_value = True
    thread.wait.return_value = False  # never exits cleanly
    worker = MagicMock()

    stop_sequence.execute_stop_sequence(handler, worker, thread, _make_signals())

    thread.terminate.assert_called_once()


def test_clean_exit_skips_terminate():
    handler = MagicMock()
    thread = MagicMock()
    thread.isRunning.return_value = True
    thread.wait.return_value = True  # exits cleanly on first wait
    worker = MagicMock()

    stop_sequence.execute_stop_sequence(handler, worker, thread, _make_signals())

    thread.terminate.assert_not_called()


# ---------------------------------------------------------------------------
# Defensive scope: hardware safe even when nothing is running
# ---------------------------------------------------------------------------

def test_hardware_safe_called_even_with_no_worker_or_thread():
    """Pressing Stop with no active schedule still drops all relays."""
    handler = MagicMock()
    stop_sequence.execute_stop_sequence(handler, None, None, _make_signals())
    handler.set_all_relays.assert_called_once_with(0)


def test_no_handler_does_not_raise():
    # No relay handler wired yet (early startup); must not blow up.
    stop_sequence.execute_stop_sequence(None, None, None, _make_signals())


# ---------------------------------------------------------------------------
# force_hardware_safe_state isolation
# ---------------------------------------------------------------------------

def test_force_hardware_safe_state_returns_true_on_success():
    handler = MagicMock()
    assert stop_sequence.force_hardware_safe_state(handler) is True
    handler.set_all_relays.assert_called_once_with(0)


def test_force_hardware_safe_state_swallows_errors_returns_false():
    handler = MagicMock()
    handler.set_all_relays.side_effect = OSError("I2C bus error")
    assert stop_sequence.force_hardware_safe_state(handler) is False


def test_force_hardware_safe_state_none_handler_returns_false():
    assert stop_sequence.force_hardware_safe_state(None) is False


# ---------------------------------------------------------------------------
# Dialog lifecycle
# ---------------------------------------------------------------------------

def test_dialog_is_closed_after_teardown():
    handler = MagicMock()
    dialog = MagicMock()
    stop_sequence.execute_stop_sequence(
        handler, None, None, _make_signals(),
        dialog_factory=lambda: dialog,
    )
    dialog.close.assert_called_once()


def test_dialog_closed_even_if_teardown_raises():
    handler = MagicMock()
    dialog = MagicMock()
    thread = MagicMock()
    thread.isRunning.side_effect = RuntimeError("boom")  # forces an error path
    # RuntimeError is caught inside bounded_worker_teardown, but prove the
    # dialog still closes regardless by making emit raise instead.
    signals = _make_signals()
    signals.stop_requested.emit.side_effect = ValueError("unexpected")
    try:
        stop_sequence.execute_stop_sequence(
            handler, MagicMock(), thread, signals,
            dialog_factory=lambda: dialog,
        )
    except ValueError:
        pass
    dialog.close.assert_called_once()
