"""Tests for the schedule-wizard delivery-window safety estimate (QA item #14).

A staggered schedule's window must physically fit the sequential per-cage
delivery time; estimate_min_window_seconds() is the lower bound the wizard
enforces before saving. Pure arithmetic — only needs the module imported.

Skips when PyQt5 is unavailable (schedule_wizard imports it at module load);
CI installs python3-pyqt5 so it runs there.
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("PyQt5")

from ui.schedule_wizard import (  # noqa: E402
    _ML_PER_PULSE,
    _PULSE_CYCLE_S,
    estimate_min_window_seconds,
)


def test_empty_or_zero_volume_needs_no_time():
    assert estimate_min_window_seconds({}) == 0.0
    assert estimate_min_window_seconds({1: {"volume": 0}}) == 0.0
    assert estimate_min_window_seconds({1: {"volume": -5}}) == 0.0


def test_ten_animals_one_ml_need_a_few_minutes():
    cfgs = {i: {"volume": 1.0} for i in range(10)}
    need = estimate_min_window_seconds(cfgs)
    # ceil(1 / 0.026) = 39 pulses per cage; sequential across 10 cages.
    per_cage = 1.0 + 39 * _PULSE_CYCLE_S + 0.5
    assert need == pytest.approx(per_cage * 10, rel=1e-6)
    # Sanity: clearly more than three minutes, so a 1-minute window is rejected.
    assert need > 180


def test_more_volume_needs_more_time():
    small = estimate_min_window_seconds({1: {"volume": 0.5}})
    large = estimate_min_window_seconds({1: {"volume": 5.0}})
    assert large > small > 0


def test_pulse_count_uses_ceiling():
    # Just over one pulse worth of volume still rounds up to two pulses.
    cfgs = {1: {"volume": _ML_PER_PULSE * 1.1}}
    pulses = math.ceil((_ML_PER_PULSE * 1.1) / _ML_PER_PULSE)
    assert pulses == 2
    assert estimate_min_window_seconds(cfgs) == pytest.approx(
        1.0 + pulses * _PULSE_CYCLE_S + 0.5, rel=1e-6
    )
