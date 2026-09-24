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


# Parker valve with the fine outlet needle: recalibrated at 32.936 uL/pulse,
# and weighed doses came up ~16 uL short of the app's plan at every size.
NEEDLE_Q = 0.032936
RETENTION_ML = 0.016


def _with_offset(worker, offset):
    worker.strategy.dose_offset_for = lambda cage_id: offset
    return worker


@pytest.mark.parametrize(
    "dose,expected_pulses", [(0.3, 10), (0.5, 16), (0.6, 19), (0.7, 22), (1.0, 31)]
)
def test_retention_offset_adds_the_missing_water(monkeypatch, dose, expected_pulses):
    """
    Bench: 9/15/18/21/30 pulses left each dose ~16 uL short. Planning the
    allowance in before rounding lifts every one of them by one pulse.
    """
    worker = _with_offset(_make_worker(monkeypatch, NEEDLE_Q), RETENTION_ML)
    worker._handle_delivery(_chunk(dose))  # instant one-shot
    assert round(worker.delivered_volumes[1] / NEEDLE_Q) == expected_pulses

    # What reaches the bowl (valve output minus the retained volume) is
    # within half a pulse of target.
    reaches_bowl = worker.delivered_volumes[1] - RETENTION_ML
    assert abs(reaches_bowl - dose) <= NEEDLE_Q / 2


def test_retention_offset_is_applied_per_delivery_in_a_window(monkeypatch):
    """Each chunk is its own delivery event, so each earns its own allowance."""
    worker = _with_offset(_make_worker(monkeypatch, NEEDLE_Q), RETENTION_ML)
    total = _run_window(worker, target=0.6, chunks=3)
    planned_for = 0.6 + 3 * RETENTION_ML
    assert abs(total - planned_for) <= NEEDLE_Q / 2


def test_retention_offset_is_capped_at_one_pulse(monkeypatch):
    """A misconfigured offset cannot add more than a single pulse per delivery."""
    worker = _with_offset(_make_worker(monkeypatch, NEEDLE_Q), 0.5)  # absurd value
    worker._handle_delivery(_chunk(0.3))
    pulses = round(worker.delivered_volumes[1] / NEEDLE_Q)
    assert pulses == round((0.3 + NEEDLE_Q) / NEEDLE_Q + 0.5) - 1 or pulses == 10


def test_retention_offset_ignored_when_absent_or_invalid(monkeypatch):
    worker = _make_worker(monkeypatch, NEEDLE_Q)  # MagicMock strategy: no real getter
    worker._handle_delivery(_chunk(0.3))
    assert round(worker.delivered_volumes[1] / NEEDLE_Q) == 9

    worker2 = _with_offset(_make_worker(monkeypatch, NEEDLE_Q), -0.01)  # negative -> ignored
    worker2._handle_delivery(_chunk(0.3))
    assert round(worker2.delivered_volumes[1] / NEEDLE_Q) == 9
