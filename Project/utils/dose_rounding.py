"""Whole-pulse dose rounding: one rule for every planned figure.

Water leaves a valve in whole pulses of the cage's calibrated volume (q). The
delivery planner (RelayWorker._quantize_to_pulses) rounds every ask with
whole_pulses(), and the bench tool's planner verdict
(tools/gravimetric_check.py) judges a fired pulse count by the same function.
Anything else that plans a dose in whole pulses must use it too, so a planned
figure is what a normal run delivers.

Qt-free, so the rule can be tested on its own.
"""

from __future__ import annotations

import math


def whole_pulses(volume_ml: float, q_ml: float, round_up: bool = False) -> int:
    """The number of pulses of ``q_ml`` that deliver ``volume_ml``.

    Nearest whole pulse by default, an exact half rounding up; the next whole
    pulse with ``round_up`` (the round_doses_up setting). Never negative.

    The epsilons absorb floating point. Under round-up, an exact multiple of q
    can land a hair above n (0.14 / 0.02 is 7.000000000000001) and must not buy
    a pulse. Under nearest, an exact half can land a hair below n + 0.5 (0.15 /
    0.1 is 1.4999999999999998) and must not lose its pulse: otherwise the same
    dose rounds one way as an instant delivery and the other way at the end of a
    staggered window, depending on how its chunks happened to add up.
    """
    if round_up:
        return max(0, math.ceil(volume_ml / q_ml - 1e-9))
    return max(0, int(volume_ml / q_ml + 0.5 + 1e-9))
