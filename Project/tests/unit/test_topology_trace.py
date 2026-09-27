"""Golden relay-write trace of the shared-manifold delivery path.

Production hardware today: one master valve on relay 16 upstream of a
manifold, one valve per cage on relays 1-15. A delivery is a fixed relay
choreography — prime the manifold through the master, hold the master open,
pulse the cage, close everything — and the exact sequence of relay writes
and valve-closed waits IS the behaviour the animal-facing rig depends on.

This test pins that sequence for the production profile (Parker valve at
30 ms / 1000 ms, 32.936 uL per pulse) over a stateful fake relay handler and
the REAL SolenoidController + SolenoidFlowStrategy. It exists so that the
work to support a second, master-less topology can be checked for one
property above all others: the shared-manifold trace must not change by a
single write or a single wait. Any diff in this list is a behaviour change
on the production device and needs its own justification.
"""

from __future__ import annotations

import asyncio

from drivers.solenoid_controller import SolenoidController
from strategies.solenoid_flow_strategy import SolenoidFlowStrategy

NEEDLE_Q = 0.032936  # mL per pulse, Parker 003-0257-900 at 30 ms with the upstream needle
PULSE_WIDTH_MS = 30
INTERVAL_MS = 1000
SETTLING_MS = 100
MASTER = 16
CAGE = 1
CAGE_MAP = {cage: cage for cage in range(1, 16)}  # the production 1-HAT map
SETTINGS = {
    'use_pulse_delivery': True,
    'pulse_width_ms': PULSE_WIDTH_MS,
    'pulse_settling_ms': SETTLING_MS,
    'max_pulses_per_delivery': 100,
    'max_pulse_delivery_time_s': 120.0,
}


class _StubDB:
    def __init__(self, calibrations):
        self._calibrations = calibrations

    def get_all_valve_calibrations(self):
        return dict(self._calibrations)

    def get_valve_calibration(self, cage_id):
        return self._calibrations.get(cage_id)


def _shared_strategy(fake, monkeypatch):
    """The production object graph over the fake: real controller, real strategy."""
    valves = SolenoidController(fake, MASTER, CAGE_MAP)
    db = _StubDB(
        {
            CAGE: {
                'calibration_id': 1,
                'pulse_width_ms': PULSE_WIDTH_MS,
                'volume_per_pulse_ml': NEEDLE_Q,
                'inter_pulse_interval_ms': INTERVAL_MS,
            }
        }
    )
    strategy = SolenoidFlowStrategy(
        solenoid_controller=valves,
        flow_sensor=None,  # production runs calibration-only
        calibration_store=None,
        settings=dict(SETTINGS),
        database_handler=db,
    )

    # Record the waits instead of sleeping them: the trace is about order and
    # duration, and a real 30 ms / 1000 ms profile would take ~10 s per dose.
    sleeps = []

    async def _record_sleep(seconds):
        sleeps.append(round(float(seconds), 3))

    monkeypatch.setattr(asyncio, 'sleep', _record_sleep)

    rests = []

    async def _record_rest(interval_ms):
        rests.append(int(interval_ms))
        return False  # not cancelled

    monkeypatch.setattr(strategy, '_rest_between_pulses', _record_rest)
    return strategy, sleeps, rests


def test_shared_manifold_trace_for_a_nine_pulse_dose(fake_relay_handler, monkeypatch):
    """0.3 mL at the needle calibration plans 9 pulses; this is every relay write."""
    strategy, sleeps, rests = _shared_strategy(fake_relay_handler, monkeypatch)

    result = asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=9 * NEEDLE_Q))

    assert result.success is True
    assert result.pulses == 9
    assert abs(result.delivered_ml - 9 * NEEDLE_Q) < 1e-9
    assert result.volume_per_pulse_ml == NEEDLE_Q

    prime = [((MASTER,), 1), ((MASTER,), 0)]
    hold = [((MASTER,), 1)]
    pulses = [((CAGE,), 1), ((CAGE,), 0)] * 9
    close = [((CAGE,), 0), ((MASTER,), 0)]
    assert fake_relay_handler.trace == prime + hold + pulses + close

    # Waits, in order: prime, post-prime settle, manifold stabilize, then
    # per pulse the open time and the valve-closed settling.
    assert sleeps == [0.2, 0.05, 0.3] + [PULSE_WIDTH_MS / 1000, SETTLING_MS / 1000] * 9
    # The calibrated rest runs between pulses, not after the last one.
    assert rests == [INTERVAL_MS] * 8

    assert fake_relay_handler.energized() == set(), "every relay closed at the end"
    assert fake_relay_handler.dropped == []


def test_shared_manifold_trace_touches_only_the_master_and_the_cage(
    fake_relay_handler, monkeypatch
):
    strategy, _sleeps, _rests = _shared_strategy(fake_relay_handler, monkeypatch)
    asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=3 * NEEDLE_Q))

    touched = {relay for ids, _state in fake_relay_handler.trace for relay in ids}
    assert touched == {MASTER, CAGE}


def test_refused_delivery_leaves_the_master_closed_without_pulsing(
    fake_relay_handler, monkeypatch
):
    """
    A dose that fails the pre-flight guard has primed, but never pulsed.

    The guard returns before the delivery's try/finally, so the only writes
    are the prime's own open and close: the master is left closed by the
    prime step itself and no cage relay is ever driven.
    """
    strategy, _sleeps, _rests = _shared_strategy(fake_relay_handler, monkeypatch)
    strategy._settings['max_pulses_per_delivery'] = 5

    result = asyncio.run(strategy.deliver(relay_unit_id=CAGE, target_volume_ml=9 * NEEDLE_Q))

    assert result.success is False
    assert result.pulses == 0
    assert fake_relay_handler.trace == [((MASTER,), 1), ((MASTER,), 0)]
    assert fake_relay_handler.energized() == set()


def test_fake_relay_handler_models_a_silently_lost_write(fake_relay_handler):
    """The HAT path swallows vendor errors and reports True; so does the fake."""
    fake_relay_handler.fail_on(nth=2)
    assert fake_relay_handler.set_relays([16], 1) is True
    assert fake_relay_handler.set_relays([1], 1) is True  # dropped
    assert fake_relay_handler.set_relays([1], 0) is True

    assert fake_relay_handler.trace == [((16,), 1), ((1,), 0)]
    assert fake_relay_handler.dropped == [((1,), 1)]
    assert fake_relay_handler.energized() == {16}

    fake_relay_handler.set_all_relays(0)
    assert fake_relay_handler.energized() == set()
