"""Where the calibration wizard starts a cage's pulse width and interval (v2.1.0).

utils.pulse_profile.wizard_starting_profile, Qt-free: the cage's own usable
calibration; else the device's most recent usable one (by calibration date,
then calibration id); else the production valve's 30 ms / 1000 ms. Usable is
calibration_gate.calibration_is_usable, with a profile inside the wizard's
ranges. A calibration with no stored interval gives its pulse width and the
production 1000 ms. Also the one rule for a stored interval (NULL is the
legacy 100 ms), which deliveries share.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from utils.pulse_profile import (
    LATEST_ON_DEVICE,
    LEGACY_INTER_PULSE_INTERVAL_MS,
    PRODUCTION,
    PRODUCTION_INTER_PULSE_INTERVAL_MS,
    THIS_CAGE,
    StartingProfile,
    profile_of,
    resolve_interval_ms,
    stored_interval_ms,
    wizard_starting_profile,
)


def _row(width=30, interval=1000, volume=0.034164, date="2026-10-11T10:40:00", cal_id=1, **extra):
    return {
        'calibration_id': cal_id,
        'pulse_width_ms': width,
        'inter_pulse_interval_ms': interval,
        'volume_per_pulse_ml': volume,
        'calibration_date': date,
        'topology': 'shared_manifold',
        **extra,
    }


def test_a_cage_starts_from_its_own_calibration():
    calibrations = {
        2: _row(20, 500, date="2026-10-01T09:00:00", cal_id=4),
        3: _row(25, 800, date="2026-10-15T09:00:00", cal_id=9),  # more recent, another cage
    }
    assert wizard_starting_profile(2, calibrations) == StartingProfile(20, 500, THIS_CAGE, 2)


def test_its_own_calibration_counts_when_stale():
    """A Stale row was measured under the other topology: that changes the
    volume per pulse, not the profile the operator chose."""
    stale = {4: _row(30, 1000, topology='independent')}
    assert wizard_starting_profile(4, stale) == StartingProfile(30, 1000, THIS_CAGE, 4)


@pytest.mark.parametrize(
    "stored",
    [
        pytest.param(None, id="saved-before-v1.16.0"),
        pytest.param(0, id="zero"),
        pytest.param(-5, id="negative"),
        pytest.param("not a number", id="unreadable"),
        pytest.param(float("inf"), id="infinite"),
    ],
)
def test_a_calibration_with_no_stored_interval_gives_its_width_and_1000_ms(stored):
    """A row from before v1.16.0 has no interval (NULL), and only a hand edit
    stores one that is not a positive number. Deliveries to such a cage use
    the legacy 100 ms, but nobody chose that 100 ms, and at 20 ms it is a
    17 % duty cycle, which the wizard itself warns against: the wizard keeps
    the cage's width and starts the interval at the production 1000 ms. The
    same goes when it is the device's most recent calibration."""
    assert profile_of(_row(20, stored)) == (20, 100), "what its deliveries use"

    own = wizard_starting_profile(5, {5: _row(20, stored)})
    assert own == StartingProfile(20, PRODUCTION_INTER_PULSE_INTERVAL_MS, THIS_CAGE, 5, False)

    latest = wizard_starting_profile(
        9,
        {
            5: _row(20, stored, date="2026-08-30T14:20:00", cal_id=2),
            1: _row(30, 1000, date="2026-08-01T09:00:00", cal_id=1),
        },
    )
    assert latest == StartingProfile(20, 1000, LATEST_ON_DEVICE, 5, False)


def test_a_cage_never_calibrated_starts_from_the_device_s_most_recent_calibration():
    calibrations = {
        1: _row(30, 1000, date="2026-10-11T10:40:00", cal_id=3),
        2: _row(20, 500, date="2026-10-02T09:15:00", cal_id=8),
        3: _row(25, 800, date="2026-10-15 11:00:00", cal_id=5),  # SQLite's format, newest
    }
    assert wizard_starting_profile(9, calibrations) == StartingProfile(
        25, 800, LATEST_ON_DEVICE, 3
    )


def test_a_tie_on_the_date_goes_to_the_later_save_and_an_unreadable_date_is_oldest():
    same_day = "2026-10-11T10:40:00"
    calibrations = {
        1: _row(30, 1000, date=same_day, cal_id=12),
        2: _row(20, 500, date=same_day, cal_id=7),
        3: _row(50, 1500, date="not a date", cal_id=99),
        4: _row(40, 1200, date=None, cal_id=98),
    }
    assert wizard_starting_profile(9, calibrations) == StartingProfile(
        30, 1000, LATEST_ON_DEVICE, 1
    )


def test_an_unusable_calibration_is_no_start_this_cage_s_own_included():
    """Invalid rows (Settings marks them; Run refuses them) and profiles the
    wizard cannot run again (only a hand edit makes one) are no start."""
    calibrations = {
        6: _row(30, 1000, volume=0.0, date="2026-10-18T09:00:00", cal_id=20),  # Invalid
        7: _row(5, 50, date="2026-10-17T09:00:00", cal_id=19),  # outside the wizard's ranges
        8: _row(0, 1000, date="2026-10-16T09:00:00", cal_id=18),  # Invalid width
        2: _row(20, 500, date="2026-10-02T09:15:00", cal_id=4),
    }
    assert wizard_starting_profile(6, calibrations) == StartingProfile(
        20, 500, LATEST_ON_DEVICE, 2
    )


@pytest.mark.parametrize(
    "calibrations",
    [
        pytest.param({}, id="none"),
        pytest.param({3: _row(30, 1000, volume=None)}, id="only-invalid"),
        pytest.param(None, id="unreadable"),
        pytest.param(MagicMock(), id="not-a-mapping"),
    ],
)
def test_a_device_with_no_calibration_starts_from_the_production_profile(calibrations):
    assert wizard_starting_profile(1, calibrations) == StartingProfile(30, 1000, PRODUCTION)


def test_cage_ids_may_come_as_text():
    assert wizard_starting_profile("2", {"2": _row(20, 500)}) == StartingProfile(
        20, 500, THIS_CAGE, 2
    )


def test_what_the_wizard_says_about_where_it_started():
    assert StartingProfile(30, 1000, THIS_CAGE, 2).describe() == (
        "Starting from this cage's last calibration: 30 ms / 1000 ms."
    )
    assert StartingProfile(20, 1000, THIS_CAGE, 5, False).describe() == (
        "Starting from this cage's last calibration: 20 ms. It has no stored interval, so "
        "the interval starts at the recommended 1000 ms."
    )
    assert StartingProfile(25, 800, LATEST_ON_DEVICE, 3).describe() == (
        "Starting from cage 3's calibration, the most recent usable one on this device: "
        "25 ms / 800 ms."
    )
    assert StartingProfile(20, 1000, LATEST_ON_DEVICE, 5, False).describe() == (
        "Starting from cage 5's calibration, the most recent usable one on this device: "
        "20 ms. It has no stored interval, so the interval starts at the recommended 1000 ms."
    )
    assert StartingProfile(30, 1000, PRODUCTION).describe() == (
        "Starting from 30 ms / 1000 ms, RRR's recommended profile for the Parker valve: no "
        "cage on this device has a usable calibration yet."
    )


def test_most_recent_means_the_most_recent_usable_one():
    """A newer Invalid calibration on another cage is passed over, which is
    why the sentence says "the most recent usable one"."""
    calibrations = {
        1: _row(30, 1000, date="2026-10-11T10:40:00", cal_id=3),
        6: _row(30, 1000, volume=0.0, date="2026-10-18T09:00:00", cal_id=4),  # Invalid
    }
    start = wizard_starting_profile(9, calibrations)
    assert start == StartingProfile(30, 1000, LATEST_ON_DEVICE, 1)
    assert "cage 1's calibration, the most recent usable one" in start.describe()


@pytest.mark.parametrize(
    ("raw", "stored", "rest"),
    [
        (None, None, LEGACY_INTER_PULSE_INTERVAL_MS),
        (0, None, 100),
        (-5, None, 100),
        ("not a number", None, 100),
        (float("inf"), None, 100),
        (100, 100, 100),
        (750, 750, 750),
        ("1000", 1000, 1000),
    ],
)
def test_the_rest_a_delivery_uses_for_a_stored_interval(raw, stored, rest):
    assert stored_interval_ms(raw) == stored
    assert resolve_interval_ms(raw) == rest


def test_a_usable_row_s_profile_and_none_for_the_others():
    assert profile_of(_row(30, 1000)) == (30, 1000)
    assert profile_of(_row(20, None)) == (20, 100)
    assert profile_of(_row(30, 1000, volume=0.0)) is None
    assert profile_of(_row(None, 1000)) is None
    assert profile_of(None) is None
