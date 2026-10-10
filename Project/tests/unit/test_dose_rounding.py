"""Whole-pulse rounding, one rule for every planned figure (Qt-free).

RelayWorker._quantize_to_pulses rounds every ask with whole_pulses(), and
tools/gravimetric_check.py judges a fired pulse count by the same function.
An exact half pulse must round the same way whichever path reaches it: until
2.0.0, 0.15 mL at 0.1 mL/pulse (1.4999999999999998 in floating point) rounded
down as one instant dose, while a staggered window could land either side of
a tie depending on how its chunks added up.
"""

from __future__ import annotations

import pytest

from utils.dose_rounding import whole_pulses

NEEDLE_Q = 0.032936  # Parker valve with the needle, as calibrated on the Pi


@pytest.mark.parametrize("dose,expected", [(0.3, 9), (0.5, 15), (0.6, 18), (0.7, 21), (1.0, 30)])
def test_nearest_rounding_of_the_lab_doses(dose, expected):
    assert whole_pulses(dose, NEEDLE_Q) == expected


@pytest.mark.parametrize("dose,expected", [(0.3, 10), (0.5, 16), (0.6, 19), (0.7, 22), (1.0, 31)])
def test_round_up_buys_the_next_whole_pulse(dose, expected):
    assert whole_pulses(dose, NEEDLE_Q, round_up=True) == expected


def test_round_up_does_not_buy_a_pulse_for_an_exact_multiple():
    assert 0.14 / 0.02 > 7  # 7.000000000000001 in floating point
    assert whole_pulses(0.14, 0.02, round_up=True) == 7


@pytest.mark.parametrize(
    "dose,q,expected", [(0.15, 0.1, 2), (0.1, 0.04, 3), (1.17, 0.02, 59), (1.18, 0.04, 30)]
)
def test_an_exact_half_pulse_rounds_up(dose, q, expected):
    assert whole_pulses(dose, q) == expected


@pytest.mark.parametrize("deficit", [0.0, -0.01, -0.5])
def test_no_deficit_fires_nothing(deficit):
    assert whole_pulses(deficit, NEEDLE_Q) == 0
    assert whole_pulses(deficit, NEEDLE_Q, round_up=True) == 0
