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

import pytest

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
    worker.request_cancel.side_effect = lambda: order.append("cancel")
    signals = _make_signals()
    signals.stop_requested.emit.side_effect = lambda: order.append("stop_emit")

    stop_sequence.execute_stop_sequence(handler, worker, thread, signals)

    assert order, "nothing happened"
    assert order[0] == "relays_off", f"hardware not first: {order}"
    assert order.index("relays_off") < order.index("thread_wait")


def test_cooperative_cancel_fires_before_queued_stop_and_thread_wait():
    """Direct request_cancel() must precede the queued emit + thread wait.

    The worker thread is blocked in run_until_complete and cannot service
    the queued stop() slot, so the direct cancel from the GUI thread is
    what actually breaks the delivery loop. It must happen first.
    """
    order = []
    handler = MagicMock()
    worker = MagicMock()
    worker.request_cancel.side_effect = lambda: order.append("cancel")
    thread = MagicMock()
    thread.isRunning.return_value = True
    thread.wait.side_effect = lambda *_a: order.append("thread_wait") or True
    signals = _make_signals()
    signals.stop_requested.emit.side_effect = lambda: order.append("stop_emit")

    stop_sequence.execute_stop_sequence(handler, worker, thread, signals)

    assert order.index("cancel") < order.index("stop_emit")
    assert order.index("cancel") < order.index("thread_wait")


def test_worker_without_request_cancel_does_not_raise():
    """Older worker objects without request_cancel are tolerated."""
    handler = MagicMock()
    worker = MagicMock(spec=["isRunning"])  # no request_cancel attr
    stop_sequence.execute_stop_sequence(handler, worker, None, _make_signals())


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


# ---------------------------------------------------------------------------
# Relays the handler could not confirm off (v1.21.0)
# ---------------------------------------------------------------------------
#
# RelayHandler.set_all_relays returns False when a HAT was missing or did
# not take the command. Stop used to print "HARDWARE SAFE" regardless.


def test_force_hardware_safe_state_reports_relays_not_confirmed_off(capsys):
    handler = MagicMock()
    handler.set_all_relays.return_value = False
    assert stop_sequence.force_hardware_safe_state(handler) is False
    out = capsys.readouterr().out
    assert "not every relay HAT confirmed OFF" in out
    assert "HARDWARE SAFE" not in out


def test_an_unconfirmed_stop_is_reported_once_the_worker_is_down():
    """Replaces test_an_unconfirmed_stop_warns_after_teardown_and_returns_false:
    the sequence no longer shows the warning itself (on_unsafe is gone);
    RunStopSection shows one dialog from the result it returns, after the
    teardown by construction (test_stop_button.py)."""
    order = []
    handler = MagicMock()
    handler.set_all_relays.side_effect = lambda *_a: order.append("relays_off") or False
    thread = MagicMock()
    thread.isRunning.return_value = True
    thread.wait.side_effect = lambda *_a: order.append("thread_wait") or True

    result = stop_sequence.execute_stop_sequence(handler, MagicMock(), thread, _make_signals())

    assert result == stop_sequence.StopResult(relays_confirmed_off=False, worker_exited=True)
    assert result.safe is False
    assert order == ["relays_off", "thread_wait", "relays_off"], "off first, and again at the end"


def test_a_confirmed_stop_is_safe():
    """Replaces test_a_confirmed_stop_does_not_warn."""
    handler = MagicMock()
    handler.set_all_relays.return_value = True
    result = stop_sequence.execute_stop_sequence(handler, None, None, _make_signals())
    assert result == stop_sequence.StopResult(relays_confirmed_off=True, worker_exited=True)
    assert result.safe is True


def test_no_handler_is_not_an_unconfirmed_stop():
    result = stop_sequence.execute_stop_sequence(None, None, None, _make_signals())
    assert result.relays_confirmed_off is True
    assert result.safe is True


# ---------------------------------------------------------------------------
# Stop hardening (v2.0.0): cancel at once, off again at the end, StopResult
# ---------------------------------------------------------------------------


def _recorder(order, *, thread_exits=(True,), relays=(True,)):
    """Mocks that log every step; ``thread_exits`` are the wait() results,
    ``relays`` the set_all_relays results, in call order."""
    exits, offs = list(thread_exits), list(relays)
    handler = MagicMock()
    handler.set_all_relays.side_effect = lambda *_a: order.append("relays_off") or offs.pop(0)
    worker = MagicMock()
    worker.request_cancel.side_effect = lambda: order.append("cancel")
    thread = MagicMock()
    thread.isRunning.return_value = True
    thread.wait.side_effect = lambda *_a: order.append("thread_wait") or exits.pop(0)
    thread.terminate.side_effect = lambda: order.append("terminate")
    signals = _make_signals()
    signals.stop_requested.emit.side_effect = lambda: order.append("stop_emit")
    dialog = MagicMock()
    dialog.close.side_effect = lambda: order.append("dialog_close")

    def factory():
        order.append("dialog")  # the real one pumps the GUI event loop
        return dialog

    return handler, worker, thread, signals, factory


def test_the_worker_is_cancelled_before_the_stopping_dialog_opens():
    """The dialog's processEvents() must not run while the worker can still
    start a pulse: the cancel follows the all-off at once."""
    order = []
    handler, worker, thread, signals, factory = _recorder(order, relays=(True, True))

    stop_sequence.execute_stop_sequence(handler, worker, thread, signals, dialog_factory=factory)

    assert order[:3] == ["relays_off", "cancel", "dialog"]


def test_the_relays_are_switched_off_again_once_the_worker_is_down():
    order = []
    handler, worker, thread, signals, factory = _recorder(order, relays=(True, True))

    result = stop_sequence.execute_stop_sequence(
        handler, worker, thread, signals, dialog_factory=factory
    )

    assert order == [
        "relays_off",
        "cancel",
        "dialog",
        "stop_emit",
        "thread_wait",
        "relays_off",
        "dialog_close",
    ]
    assert result.safe is True


def test_the_relays_are_switched_off_again_after_a_thread_with_no_worker():
    """main.cleanup drops the worker but keeps a thread that is still
    running, and the delivery in it can still switch a relay on."""
    order = []
    handler, _, thread, signals, _ = _recorder(order, relays=(True, True))

    stop_sequence.execute_stop_sequence(handler, None, thread, signals)

    assert order == ["relays_off", "thread_wait", "relays_off"]


def test_the_all_off_after_the_teardown_decides():
    order = []
    handler, worker, thread, signals, _ = _recorder(order, relays=(True, False))
    assert stop_sequence.execute_stop_sequence(
        handler, worker, thread, signals
    ).relays_confirmed_off is False, "a HAT stopped answering during the stop"

    order = []
    handler, worker, thread, signals, _ = _recorder(order, relays=(False, True))
    assert stop_sequence.execute_stop_sequence(
        handler, worker, thread, signals
    ).relays_confirmed_off is True, "every HAT took the last command"


def test_an_abandoned_worker_is_reported():
    order = []
    handler, worker, thread, signals, _ = _recorder(
        order, thread_exits=(False, False), relays=(True, True)
    )

    result = stop_sequence.execute_stop_sequence(handler, worker, thread, signals)

    assert result == stop_sequence.StopResult(relays_confirmed_off=True, worker_exited=False)
    assert order[-1] == "relays_off", "switched off again even beside a live worker"


def test_a_terminated_worker_has_exited():
    order = []
    handler, worker, thread, signals, _ = _recorder(
        order, thread_exits=(False, True), relays=(True, True)
    )
    result = stop_sequence.execute_stop_sequence(handler, worker, thread, signals)
    assert "terminate" in order
    assert result.worker_exited is True


def test_a_deleted_or_finished_thread_has_exited():
    handler = MagicMock()
    gone = MagicMock()
    gone.isRunning.side_effect = RuntimeError("wrapped C/C++ object has been deleted")
    assert stop_sequence.execute_stop_sequence(
        handler, MagicMock(), gone, _make_signals()
    ).worker_exited is True
    finished = MagicMock()
    finished.isRunning.return_value = False
    assert stop_sequence.execute_stop_sequence(
        handler, MagicMock(), finished, _make_signals()
    ).worker_exited is True
    finished.wait.assert_not_called()


def test_the_relays_are_switched_off_again_even_when_the_teardown_raises():
    """The error must still reach main.stop_program, which turns it into an
    unsafe StopResult, so Stop keeps the hardware locked."""
    order = []
    handler, worker, thread, signals, _ = _recorder(order, relays=(True, True))
    signals.stop_requested.emit.side_effect = ValueError("unexpected")
    with pytest.raises(ValueError, match="unexpected"):
        stop_sequence.execute_stop_sequence(handler, worker, thread, signals)
    assert order == ["relays_off", "cancel", "relays_off"]
