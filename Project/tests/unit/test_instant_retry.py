"""An instant retry after a partial delivery sends only the rest of the dose.

An instant delivery has no window, so the whole-pulse planner rounds each
request on its own. When a delivery stopped part-way (a time or pulse limit
inside the strategy, a relay fault), the retry re-entered with the first
attempt's whole plan still in water_volume and fired all of it again: the
review measured 10 + 18 = 28 pulses for one 0.6 mL dose (+54 %). The
partial was credited to the animal's running total, but nothing on the
instant path read it. The retry now plans from the ask recorded before
rounding minus what this delivery already dispensed.
"""

from __future__ import annotations

import asyncio
import gc
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from strategies.delivery_strategy import DeliveryResult

pytest.importorskip("PyQt5")

Q = 0.032936  # mL per pulse, the needle rig


def _worker(monkeypatch, *, q=Q, round_up=False, pulses_per_attempt=()):
    """A RelayWorker whose strategy stops after the given pulse counts, then succeeds."""
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415

    # Each worker below sits in a reference cycle (worker -> strategy ->
    # _deliver -> worker), so the previous test's worker is freed only by
    # the cyclic collector, at an arbitrary moment. When that moment fell
    # inside the next test, the new worker's C++ object was gone too
    # ("wrapped C/C++ object of type RelayWorker has been deleted"), about
    # one full-suite run in three. Collecting first makes it deterministic.
    gc.collect()
    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.settings = {'valve_topology': 'shared_manifold', 'round_doses_up': round_up}
    worker.delivered_volumes, worker.failed_deliveries, worker.issued_targets = {}, {}, {}
    worker.schedule_id = 7
    worker.hardware_mode = 'solenoid'
    worker.mode = 'instant'
    worker.database_handler = MagicMock()
    worker.progress.connect(lambda _m: None)
    worker.volume_updated.connect(lambda *_a: None)

    class _Event:
        def is_set(self):
            return False

    worker._cancel_requested = _Event()
    worker.retries = []
    monkeypatch.setattr(
        type(worker), "schedule_retry", lambda self, data: self.retries.append(data), raising=False
    )

    stops = list(pulses_per_attempt)
    worker.fired = []  # pulses each attempt was asked for

    async def _deliver(relay_unit_id, target_volume_ml, triggers_hint=None):
        planned = round(target_volume_ml / q)
        worker.fired.append(planned)
        if stops:
            got = min(stops.pop(0), planned)
            return DeliveryResult(success=False, delivered_ml=got * q, pulses=got, volume_per_pulse_ml=q)
        return DeliveryResult(
            success=True, delivered_ml=planned * q, pulses=planned, volume_per_pulse_ml=q
        )

    strategy = MagicMock()
    strategy.pulse_volume_for = lambda cage_id: q
    strategy.deliver = _deliver
    worker.strategy = strategy
    return worker


def _instant(volume=0.6):
    return {
        'animal_id': 1,
        'relay_unit_id': 3,
        'water_volume': volume,
        'instant_time': datetime(2026, 9, 29, 8, 0, 0),
        'schedule_id': 7,
    }


def _rows(worker):
    return [c.args[0] for c in worker.database_handler.log_delivery.call_args_list]


@pytest.mark.parametrize("round_up,total", [(False, 18), (True, 19)])
def test_the_retry_sends_the_rest_not_the_whole_dose(monkeypatch, round_up, total):
    """0.6 mL is 18.22 pulses: 18 at nearest, 19 rounded up. Stopped after 10."""
    worker = _worker(monkeypatch, round_up=round_up, pulses_per_attempt=[10])
    data = _instant()
    worker._handle_delivery(data)
    assert worker.retries == [data]
    worker._handle_delivery(data)  # schedule_retry re-enters with the same dict

    assert worker.fired == [total, total - 10]
    assert sum(r['pulses_fired'] for r in _rows(worker)) == total
    assert [r['status'] for r in _rows(worker)] == ['partial', 'completed']
    assert worker.delivered_volumes[1] == pytest.approx(total * Q)


def test_the_real_retry_path_does_the_same(monkeypatch):
    """schedule_retry's timer runs execute_delivery, which shares the pre/post-flight."""
    worker = _worker(monkeypatch, pulses_per_attempt=[10])
    data = _instant()
    worker._handle_delivery(data)
    assert asyncio.run(worker.execute_delivery(data)) is True
    assert worker.fired == [18, 8]


def test_two_partials_then_the_rest(monkeypatch):
    worker = _worker(monkeypatch, pulses_per_attempt=[10, 5])
    data = _instant()
    for _ in range(3):
        worker._handle_delivery(data)
    assert worker.fired == [18, 8, 3]
    assert sum(r['pulses_fired'] for r in _rows(worker)) == 18


def test_a_nearly_complete_delivery_is_not_topped_past_the_dose(monkeypatch):
    """Stopped after all 18 pulses: the rest (7 uL) is under half a pulse."""
    worker = _worker(monkeypatch, pulses_per_attempt=[18])
    data = _instant()
    worker._handle_delivery(data)
    assert worker._handle_delivery(data) is True  # nothing more to deliver
    assert worker.fired == [18]
    assert len(_rows(worker)) == 1


def test_a_retry_after_no_water_at_all_sends_the_whole_dose(monkeypatch):
    worker = _worker(monkeypatch, pulses_per_attempt=[0])
    data = _instant()
    worker._handle_delivery(data)
    worker._handle_delivery(data)
    assert worker.fired == [18, 18]


def test_a_non_pulse_strategy_retry_asks_only_for_the_rest(monkeypatch):
    worker = _worker(monkeypatch)
    del worker.strategy.pulse_volume_for  # pump / continuous: no pulse quantum
    asked = []

    async def _deliver(relay_unit_id, target_volume_ml, triggers_hint=None):
        asked.append(target_volume_ml)
        if len(asked) == 1:
            return DeliveryResult(success=False, delivered_ml=0.25)
        return DeliveryResult(success=True, delivered_ml=target_volume_ml)

    worker.strategy.deliver = _deliver
    data = _instant()
    worker._handle_delivery(data)
    worker._handle_delivery(data)
    assert asked == [pytest.approx(0.6), pytest.approx(0.35)]
