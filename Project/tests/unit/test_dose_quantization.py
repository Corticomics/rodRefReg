"""Staggered chunks fire whole pulses against a carried within-window deficit.

The pulse loop rounds UP, so before this change every chunk delivered at
least one whole pulse however small its target: a 1 mL dose split into five
0.2 mL chunks on a 0.357 mL/pulse cage fired 5 pulses = 1.784 mL (+78%),
matching the bench weighings (1.774 g) to 0.6%.

The quantizer instead tracks the cumulative volume asked of each animal in
the window and fires round(deficit / q) pulses per slot — zero being a
legal answer — so the window closes within half a pulse of its target, the
theoretical floor for whole-pulse dispensing. Nothing crosses the window
boundary (daily targets change through the week), and a failed or partial
delivery is absorbed by later slots because the deficit is computed from
actually-delivered volume.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt5")

BENCH_Q = 0.3569  # measured: original valve, 100 ms x 75, CV 0.80%
PARKER2_Q = 0.0622  # measured: Parker valve, 50 ms x 150, CV 0.9%


def _make_worker(monkeypatch, q):
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415
    from strategies.delivery_strategy import DeliveryResult  # noqa: PLC0415

    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.delivered_volumes = {}
    worker.failed_deliveries = {}
    worker.issued_targets = {}
    worker.schedule_id = 7
    worker.hardware_mode = 'solenoid'
    worker.database_handler = MagicMock()

    class _Event:
        def is_set(self):
            return False

    worker._cancel_requested = _Event()
    worker.retries = []
    monkeypatch.setattr(
        type(worker), "schedule_retry", lambda self, data: self.retries.append(data), raising=False
    )
    worker.progress.connect(lambda _msg: None)
    worker.volume_updated.connect(lambda *_a: None)

    strategy = MagicMock()
    strategy.pulse_volume_for = lambda cage_id: q
    worker.fired = []  # volumes the "hardware" was asked for

    async def _deliver(relay_unit_id, target_volume_ml, triggers_hint=None):
        # The worker requests exactly n*q, so the real pulse loop fires
        # exactly n pulses; the stub reports that volume as dispensed.
        worker.fired.append(target_volume_ml)
        return DeliveryResult(
            success=True, delivered_ml=target_volume_ml, pulses=round(target_volume_ml / q)
        )

    strategy.deliver = _deliver
    worker.strategy = strategy
    return worker


def _chunk(volume, animal_id=1):
    return {
        'animal_id': animal_id,
        'relay_unit_id': 3,
        'water_volume': volume,
        'instant_time': datetime(2026, 9, 17, 8, 0, 0),
        'schedule_id': 7,
    }


def _run_window(worker, target, chunks):
    worker.animal_windows = {1: {'target_volume': target}}
    per = target / chunks
    for _ in range(chunks):
        worker._handle_delivery(_chunk(per))
    return worker.delivered_volumes.get(1, 0.0)


def test_bench_scenario_lands_within_half_a_pulse(monkeypatch):
    """The measured +78% case: 1 mL in five 0.2 mL chunks at q=0.357."""
    worker = _make_worker(monkeypatch, BENCH_Q)
    total = _run_window(worker, target=1.0, chunks=5)

    assert total == pytest.approx(3 * BENCH_Q)  # 1.071 mL, +7.1%
    assert abs(total - 1.0) <= BENCH_Q / 2, "within half a pulse of target"
    # Before the quantizer this was 5 pulses = 1.784 mL.
    assert total < 1.2


@pytest.mark.parametrize(
    "dose", [0.4, 0.6, 0.7]
)  # the lab's real mouse doses, which change through the week
def test_mouse_doses_on_the_parker_valve(monkeypatch, dose):
    worker = _make_worker(monkeypatch, PARKER2_Q)
    total = _run_window(worker, target=dose, chunks=5)
    assert abs(total - dose) <= PARKER2_Q / 2, (
        f"{dose} mL window closed at {total:.3f}, off by more than half a pulse"
    )


def test_sub_pulse_chunks_skip_and_carry(monkeypatch):
    """Chunks smaller than half a pulse fire nothing until carry accrues."""
    worker = _make_worker(monkeypatch, BENCH_Q)
    total = _run_window(worker, target=0.5, chunks=5)  # 0.1 mL chunks

    # Slot arithmetic: deficits 0.1/0.2/... -> pulses 0,1,0,0,0.
    assert worker.fired == [pytest.approx(BENCH_Q)]
    assert total == pytest.approx(BENCH_Q)
    assert abs(total - 0.5) <= BENCH_Q / 2


def test_partial_failure_is_absorbed_by_later_slots(monkeypatch):
    """A slot that under-delivers grows the deficit; the window recovers."""
    from strategies.delivery_strategy import DeliveryResult  # noqa: PLC0415

    worker = _make_worker(monkeypatch, PARKER2_Q)
    q = PARKER2_Q
    calls = {'n': 0}

    async def _flaky(relay_unit_id, target_volume_ml, triggers_hint=None):
        calls['n'] += 1
        if calls['n'] == 2:  # second slot dies after a single pulse
            return DeliveryResult(success=False, delivered_ml=q, pulses=1)
        worker.fired.append(target_volume_ml)
        return DeliveryResult(success=True, delivered_ml=target_volume_ml)

    worker.strategy.deliver = _flaky
    total = _run_window(worker, target=0.6, chunks=5)

    assert abs(total - 0.6) <= q / 2, f"window closed at {total:.3f} despite the failure"


def test_instant_one_shot_rounds_to_nearest(monkeypatch):
    """No window: an instant dose gets nearest rounding, not round-up."""
    worker = _make_worker(monkeypatch, 0.1415)  # Parker 1, 100 ms
    worker._handle_delivery(_chunk(1.0))

    # round(1.0 / 0.1415) = 7 pulses = 0.9905 mL, not ceil's 8 = 1.132.
    assert worker.delivered_volumes[1] == pytest.approx(7 * 0.1415)


def test_non_pulse_strategies_are_untouched(monkeypatch):
    """Pump/legacy strategies have no quantum; requests pass through as-is."""
    worker = _make_worker(monkeypatch, BENCH_Q)
    del worker.strategy.pulse_volume_for
    worker._handle_delivery(_chunk(0.2))
    assert worker.fired == [pytest.approx(0.2)]


def test_retry_does_not_double_count_toward_the_window(monkeypatch):
    """A retried chunk was already counted; re-entry must not inflate issued."""
    worker = _make_worker(monkeypatch, PARKER2_Q)
    worker.animal_windows = {1: {'target_volume': 0.6}}
    data = _chunk(0.12)

    worker._handle_delivery(data)
    issued_after_first = worker.issued_targets[1]
    worker._handle_delivery(data)  # same dict re-enters, as schedule_retry does
    assert worker.issued_targets[1] == pytest.approx(issued_after_first)


# Parker valve with the upstream needle, as calibrated on the Pi.
NEEDLE_Q = 0.032936


def _sliver(worker, target):
    """What the cycle loop does after the planned chunks: re-request the
    rounding leftover, cycle_volume = min(target - delivered, per_cycle)."""
    remaining = target - worker.delivered_volumes.get(1, 0.0)
    if remaining > 0:
        worker._handle_delivery(_chunk(remaining))


def test_post_plan_sliver_chunk_does_not_buy_an_extra_pulse(monkeypatch):
    """
    Bench, 1.0 mL windows: 30 or 31 pulses depending on window timing.
    Nearest rounding of 1.0 / 0.032936 = 30.36 is 30. The 31st came from the
    cycle loop's leftover chunk being counted toward the window a second
    time; capping the cumulative ask at the target removes it.
    """
    worker = _make_worker(monkeypatch, NEEDLE_Q)
    total = _run_window(worker, target=1.0, chunks=5)  # 5 x 0.2 -> 30 pulses
    assert round(total / NEEDLE_Q) == 30

    _sliver(worker, 1.0)  # a 6th cycle fires with the 0.012 mL leftover
    _sliver(worker, 1.0)  # ...and, in a long window, a 7th
    assert round(worker.delivered_volumes[1] / NEEDLE_Q) == 30, "no 31st pulse"
    assert worker.issued_targets[1] == pytest.approx(1.0), "ask capped at the target"


def test_slivers_after_a_failure_still_converge_without_overshoot(monkeypatch):
    """Repeated leftover chunks may fill a real deficit, never exceed the dose."""
    from strategies.delivery_strategy import DeliveryResult  # noqa: PLC0415

    worker = _make_worker(monkeypatch, NEEDLE_Q)
    calls = {'n': 0}

    async def _flaky(relay_unit_id, target_volume_ml, triggers_hint=None):
        calls['n'] += 1
        if calls['n'] == 3:  # third chunk dies after one pulse
            return DeliveryResult(success=False, delivered_ml=NEEDLE_Q, pulses=1)
        worker.fired.append(target_volume_ml)
        return DeliveryResult(success=True, delivered_ml=target_volume_ml)

    worker.strategy.deliver = _flaky
    _run_window(worker, target=1.0, chunks=5)
    for _ in range(4):  # the loop keeps re-requesting the leftover
        _sliver(worker, 1.0)

    total = worker.delivered_volumes[1]
    assert abs(total - 1.0) <= NEEDLE_Q / 2, f"window closed at {total:.3f}"
    assert total <= 1.0 + NEEDLE_Q / 2, "never more than half a pulse over"


def test_completion_tolerance_follows_the_fallback_quantum(monkeypatch):
    """An uncalibrated cage plans at the empirical default; judge it on that."""
    worker = _make_worker(monkeypatch, 0.026)  # pulse_volume_for -> fallback q
    worker.settings = {'relay_unit_assignments': {'1': 3}}
    worker.strategy._cal_snapshot = {}  # no stored calibration for cage 3
    assert worker._completion_tolerance_ml(1) == pytest.approx(0.013)
