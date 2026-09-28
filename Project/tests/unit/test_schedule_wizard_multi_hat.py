"""Cage ids and relay ids are different number spaces in the schedule wizard.

Relay 16 is the master solenoid, so cages are numbered over every OTHER
relay: on one HAT cages 1-15 drive relays 1-15; on a second HAT cage 16
drives relay 17 and cage 31 drives relay 32. The wizard's validation used
to compare the cage id with the master RELAY id, so on the production
device (two HATs) cage 16 was rejected as "reserved for the master" even
though the wizard itself had offered it. The check now resolves the relay
a cage drives and compares relay to relay.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

from ui.schedule_wizard import (  # noqa: E402
    build_schedule_from_config,
    get_available_cages,
    relay_for_cage,
)


def _controller(**settings):
    base = {"num_hats": 1, "global_master_relay_id": 16}
    base.update(settings)
    return SimpleNamespace(settings=base)


def _instant_config(cage_id, animal_id=1):
    return {
        "schedule_type": "instant",
        "animals": [animal_id],
        "parameters": {
            "name": "x",
            "animal_configs": {
                animal_id: {
                    "delivery_time": datetime(2026, 10, 1, 9, 0, 0),
                    "volume": 0.6,
                    "cage_id": cage_id,
                }
            },
        },
    }


def test_two_hats_offer_thirty_one_cages_including_sixteen():
    max_cages, master, valid = get_available_cages(_controller(num_hats=2))
    assert (max_cages, master) == (31, 16)
    assert valid == set(range(1, 32))


@pytest.mark.parametrize(
    "num_hats,cage_id,relay",
    [(1, 1, 1), (1, 15, 15), (1, 16, None), (2, 15, 15), (2, 16, 17), (2, 31, 32), (2, 32, None)],
)
def test_relay_for_cage_skips_the_master(num_hats, cage_id, relay):
    assert relay_for_cage(_controller(num_hats=num_hats), cage_id) == relay


def test_relay_for_cage_honours_a_custom_master_and_a_stored_map():
    assert relay_for_cage(_controller(global_master_relay_id=1), 1) == 2
    stored = _controller(cage_relays={"1": 5, "2": 9})
    assert relay_for_cage(stored, 2) == 9
    assert relay_for_cage(stored, 3) is None


def test_cage_sixteen_is_a_valid_cage_on_two_hats():
    """The production device has two HATs; its 16th cage drives relay 17."""
    schedule = build_schedule_from_config(
        _instant_config(cage_id=16), trainer=None, system_controller=_controller(num_hats=2)
    )
    assert schedule.instant_deliveries[0]["relay_unit_id"] == 16


def test_cage_sixteen_is_still_invalid_on_one_hat():
    with pytest.raises(ValueError, match="invalid cage"):
        build_schedule_from_config(
            _instant_config(cage_id=16), trainer=None, system_controller=_controller()
        )


def test_a_cage_wired_to_the_master_relay_is_refused():
    """A stored cage map that points a cage at relay 16 is a wiring mistake, not a cage."""
    misconfigured = _controller(num_hats=2, cage_relays={"1": 1, "5": 16})
    with pytest.raises(ValueError, match="reserved for the master"):
        build_schedule_from_config(
            _instant_config(cage_id=5), trainer=None, system_controller=misconfigured
        )
