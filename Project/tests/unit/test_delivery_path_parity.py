"""Both delivery paths share one pre-flight and one post-flight.

RelayWorker has two delivery entry points: ``_handle_delivery`` (the QTimer
slot used by staggered and instant deliveries) and ``execute_delivery`` (the
retry path). They were near-identical copies, so an accounting fix applied
to one silently missed the other — and the retry path had no test at all.

These tests pin the behaviour both paths must share: the cooperative-cancel
check, the cumulative over-delivery guard, the failed-retry compensation,
volume crediting, history logging, and retry scheduling. They are written
against both entry points deliberately: a future change that edits one and
not the other fails here.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")


def _make_worker(monkeypatch):
    """A RelayWorker with hardware, Qt signals and retry timers stubbed out."""
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415

    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415

    # Bypass RelayWorker.__init__ (it builds hardware) but still initialise
    # the QObject base, or signal emission raises.
    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)

    worker.mutex = QMutex()
    worker.delivered_volumes = {}
    worker.failed_deliveries = {}
    worker.schedule_id = 7
    worker.hardware_mode = 'solenoid'
    worker.database_handler = MagicMock()
    worker.strategy = MagicMock()

    # Record what the worker reports instead of wiring a Qt event loop.
    worker.emitted_progress = []
    worker.emitted_volumes = []
    worker.progress.connect(worker.emitted_progress.append)
    worker.volume_updated.connect(
        lambda animal_id, total: worker.emitted_volumes.append((animal_id, total))
    )

    class _Event:
        def __init__(self):
            self._set = False

        def set(self):
            self._set = True

        def is_set(self):
            return self._set

    worker._cancel_requested = _Event()
    worker.retries = []
    monkeypatch.setattr(
        type(worker), "schedule_retry", lambda self, data: self.retries.append(data), raising=False
    )
    return worker


def _delivery(volume=0.2, animal_id=1):
    return {
        'animal_id': animal_id,
        'relay_unit_id': 3,
        'water_volume': volume,
        'instant_time': datetime(2026, 9, 15, 8, 0, 0),
        'schedule_id': 7,
    }


def _run_primary(worker, data, success=True):
    """Drive _handle_delivery with the strategy forced to `success`."""

    async def _deliver(**_kwargs):
        return success

    worker.strategy.deliver = _deliver
    return worker._handle_delivery(data)


def _run_retry(worker, data, success=True):
    """Drive execute_delivery (the retry path) with the same forcing."""

    async def _deliver(**_kwargs):
        return success

    worker.strategy.deliver = _deliver
    return asyncio.run(worker.execute_delivery(data))


ENTRY_POINTS = [("primary", _run_primary), ("retry", _run_retry)]


@pytest.mark.parametrize("name,run", ENTRY_POINTS)
def test_cancel_short_circuits_before_hardware(monkeypatch, name, run):
    worker = _make_worker(monkeypatch)
    worker._cancel_requested.set()

    called = []

    async def _deliver(**_kwargs):
        called.append(1)
        return True

    worker.strategy.deliver = _deliver
    result = (
        worker._handle_delivery(_delivery())
        if name == "primary"
        else asyncio.run(worker.execute_delivery(_delivery()))
    )

    assert result is False
    assert not called, "a cancelled delivery must not reach the strategy"
    assert worker.database_handler.log_delivery.call_count == 0


@pytest.mark.parametrize("name,run", ENTRY_POINTS)
def test_success_credits_volume_and_logs_completed(monkeypatch, name, run):
    worker = _make_worker(monkeypatch)
    data = _delivery(volume=0.25)

    assert run(worker, data, success=True) is True
    assert worker.delivered_volumes[1] == pytest.approx(0.25)
    assert worker.failed_deliveries[1] == 0

    logged = worker.database_handler.log_delivery.call_args.args[0]
    assert logged['status'] == 'completed'
    assert logged['volume_delivered'] == pytest.approx(0.25)
    assert logged['schedule_id'] == 7
    assert worker.retries == []


@pytest.mark.parametrize("name,run", ENTRY_POINTS)
def test_failure_logs_zero_and_schedules_retry(monkeypatch, name, run):
    worker = _make_worker(monkeypatch)
    data = _delivery(volume=0.25)

    assert run(worker, data, success=False) is False
    assert worker.delivered_volumes.get(1, 0) == 0
    assert worker.failed_deliveries[1] == 1

    logged = worker.database_handler.log_delivery.call_args.args[0]
    assert logged['status'] == 'failed'
    assert logged['volume_delivered'] == 0
    assert len(worker.retries) == 1


@pytest.mark.parametrize("name,run", ENTRY_POINTS)
def test_window_guard_skips_once_target_is_met(monkeypatch, name, run):
    """An animal already at target must not receive more water."""
    worker = _make_worker(monkeypatch)
    worker.animal_windows = {1: {'target_volume': 1.0}}
    worker.delivered_volumes[1] = 1.0

    called = []

    async def _deliver(**_kwargs):
        called.append(1)
        return True

    worker.strategy.deliver = _deliver
    data = _delivery()
    result = (
        worker._handle_delivery(data)
        if name == "primary"
        else asyncio.run(worker.execute_delivery(data))
    )

    assert result is True, "guard reports success without dispensing"
    assert not called
    assert worker.delivered_volumes[1] == 1.0


@pytest.mark.parametrize("name,run", ENTRY_POINTS)
def test_retry_never_asks_for_more_than_is_outstanding(monkeypatch, name, run):
    """
    A retry requests the outstanding dose, never an inflated one.

    Earlier code grew the request by 5% per prior failure. A failure is not
    evidence the next delivery should be larger, and since a failed delivery
    may have dispensed part of its volume already, inflating the retry is
    how over-delivery compounded.
    """
    worker = _make_worker(monkeypatch)
    worker.animal_windows = {1: {'target_volume': 1.0}}
    worker.delivered_volumes[1] = 0.5
    worker.failed_deliveries[1] = 2  # prior failures must NOT inflate

    data = _delivery(volume=0.2)
    run(worker, data, success=True)
    assert data['water_volume'] == pytest.approx(0.2), "request must not be inflated"

    # And it is still capped by what the animal actually has coming.
    worker2 = _make_worker(monkeypatch)
    worker2.animal_windows = {1: {'target_volume': 1.0}}
    worker2.delivered_volumes[1] = 0.95
    worker2.failed_deliveries[1] = 4
    data2 = _delivery(volume=0.2)
    run(worker2, data2, success=True)
    assert data2['water_volume'] == pytest.approx(0.05), "capped at the outstanding 0.05 mL"


def test_completion_tolerance_scales_with_the_pulse(monkeypatch):
    """A window can only land within half a pulse; judge it on that scale."""
    worker = _make_worker(monkeypatch)
    worker.settings = {'relay_unit_assignments': {'1': 3}}

    # No calibration known -> the old fixed tolerance.
    worker.strategy._cal_snapshot = {}
    assert worker._completion_tolerance_ml(1) == pytest.approx(0.01)

    # Calibrated cage -> half a pulse.
    worker.strategy._cal_snapshot = {3: {25: {'volume_per_pulse_ml': 0.136}}}
    assert worker._completion_tolerance_ml(1) == pytest.approx(0.068)

    # A very fine pulse must not shrink the tolerance below the float guard.
    worker.strategy._cal_snapshot = {3: {25: {'volume_per_pulse_ml': 0.001}}}
    assert worker._completion_tolerance_ml(1) == pytest.approx(0.01)


def _result(**kw):
    from strategies.delivery_strategy import DeliveryResult  # noqa: PLC0415

    return DeliveryResult(**kw)


def _run_with_result(worker, data, result, path="primary"):
    async def _deliver(**_kwargs):
        return result

    worker.strategy.deliver = _deliver
    if path == "primary":
        return worker._handle_delivery(data)
    return asyncio.run(worker.execute_delivery(data))


@pytest.mark.parametrize("path", ["primary", "retry"])
def test_credits_actual_volume_not_requested(monkeypatch, path):
    """A pulse is whole: asking for 0.2 mL can dispense 0.357 mL."""
    worker = _make_worker(monkeypatch)
    data = _delivery(volume=0.2)
    result = _result(success=True, delivered_ml=0.357, pulses=1, volume_per_pulse_ml=0.357)

    assert _run_with_result(worker, data, result, path) is True
    assert worker.delivered_volumes[1] == pytest.approx(0.357)

    logged = worker.database_handler.log_delivery.call_args.args[0]
    assert logged['volume_actual_ml'] == pytest.approx(0.357)
    assert logged['volume_delivered'] == pytest.approx(0.2), "requested figure preserved"
    assert logged['pulses_fired'] == 1


@pytest.mark.parametrize("path", ["primary", "retry"])
def test_failed_result_is_never_mistaken_for_success(monkeypatch, path):
    """A DeliveryResult object is always truthy — .success must be consulted."""
    worker = _make_worker(monkeypatch)
    data = _delivery(volume=0.2)
    result = _result(success=False, delivered_ml=0.0)

    assert _run_with_result(worker, data, result, path) is False
    assert worker.failed_deliveries[1] == 1
    assert worker.delivered_volumes.get(1, 0) == 0
    assert len(worker.retries) == 1


@pytest.mark.parametrize("path", ["primary", "retry"])
def test_partial_delivery_is_credited_before_the_retry(monkeypatch, path):
    """
    Water already in the cage must be credited even though the delivery
    failed — otherwise the retry sends the whole dose a second time.
    """
    worker = _make_worker(monkeypatch)
    data = _delivery(volume=1.0)
    result = _result(success=False, delivered_ml=0.64, pulses=2, volume_per_pulse_ml=0.32)

    assert _run_with_result(worker, data, result, path) is False
    assert worker.delivered_volumes[1] == pytest.approx(0.64), "partial volume credited"
    assert worker.failed_deliveries[1] == 1

    logged = worker.database_handler.log_delivery.call_args.args[0]
    assert logged['status'] == 'partial'
    assert logged['volume_actual_ml'] == pytest.approx(0.64)
    assert len(worker.retries) == 1


def test_legacy_truthy_outcome_still_works(monkeypatch):
    """The pump branch returns relay_info/None, not a DeliveryResult."""
    worker = _make_worker(monkeypatch)
    normalised = worker._as_delivery_result({'relay': 1}, requested_ml=0.3)
    assert normalised.success is True
    assert normalised.delivered_ml == pytest.approx(0.3)

    failed = worker._as_delivery_result(None, requested_ml=0.3)
    assert failed.success is False
    assert failed.delivered_ml == 0.0


def test_both_paths_use_the_same_helpers():
    """Guard against the two paths drifting apart again."""
    import inspect  # noqa: PLC0415

    from gpio.relay_worker import RelayWorker  # noqa: PLC0415

    for method in (RelayWorker._handle_delivery, RelayWorker.execute_delivery):
        src = inspect.getsource(method)
        assert '_prepare_delivery' in src
        assert '_finalize_delivery' in src
