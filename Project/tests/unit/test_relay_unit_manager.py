"""Tests for :class:`RelayUnitManager` (multi-HAT contract).

Locks the behavior that change_relay_hats() depends on:

- With ``cage_relays`` empty, the manager auto-generates a 1:1 cage-to-
  relay map skipping the master relay, scaling with ``num_hats``.
- The "one global master" semantics (single master across the whole
  setup, default relay 16) yields 31 cages for 2 HATs, not 30 — because
  only ONE master is excluded, not one per HAT.
- With ``cage_relays`` populated, the manager honors it as-is. This is
  intentional: bespoke installations can pin custom mappings. But the
  upshot is that whoever owns the num_hats change must also clear the
  cached map, which main.change_relay_hats does explicitly.

See Project/models/relay_unit_manager.py:_initialize_solenoid_mode.
"""

from __future__ import annotations

import pytest

# The RelayUnit model used by the manager touches PyQt5 transitively in
# some imports paths; gate the module the same way other tests do so
# contributors without PyQt5 see "skipped" not "ImportError".
pytest.importorskip("PyQt5")

from models.relay_unit_manager import RelayUnitManager  # noqa: E402


def _solenoid_settings(num_hats: int, master_id: int = 16, cage_relays=None):
    """Build the minimal settings dict the manager actually reads."""
    return {
        'hardware_mode': 'solenoid',
        'num_hats': num_hats,
        'global_master_relay_id': master_id,
        'cage_relays': cage_relays if cage_relays is not None else {},
    }


# ---------------------------------------------------------------------------
# Auto-generate when cage_relays is empty
# ---------------------------------------------------------------------------

def test_one_hat_yields_15_cages_with_master_at_16():
    manager = RelayUnitManager(_solenoid_settings(num_hats=1))
    units = manager.get_all_relay_units()
    assert len(units) == 15
    relay_ids = {next(iter(u.relay_ids)) if isinstance(u.relay_ids, tuple)
                 else u.relay_ids for u in units}
    assert 16 not in relay_ids
    assert relay_ids == set(range(1, 16))


def test_two_hats_with_one_global_master_yields_31_cages():
    """Per project decision (Phase 3.4 plan): one global master, not per-HAT.

    HAT 0 contributes relays 1-15 (16 is master, skipped).
    HAT 1 contributes relays 17-32 (no relay equals 16 here, none skipped).
    Total: 31 cages.
    """
    manager = RelayUnitManager(_solenoid_settings(num_hats=2))
    units = manager.get_all_relay_units()
    assert len(units) == 31
    relay_ids = sorted(
        next(iter(u.relay_ids)) if isinstance(u.relay_ids, tuple) else u.relay_ids
        for u in units
    )
    expected = list(range(1, 16)) + list(range(17, 33))
    assert relay_ids == expected


def test_four_hats_with_one_global_master_yields_63_cages():
    """Scales linearly. Only relay 16 is ever skipped."""
    manager = RelayUnitManager(_solenoid_settings(num_hats=4))
    assert len(manager.get_all_relay_units()) == 63


def test_custom_master_relay_id_is_honored():
    """Non-default master still skipped exactly once, regardless of HAT count."""
    manager = RelayUnitManager(_solenoid_settings(num_hats=2, master_id=8))
    units = manager.get_all_relay_units()
    relay_ids = sorted(
        next(iter(u.relay_ids)) if isinstance(u.relay_ids, tuple) else u.relay_ids
        for u in units
    )
    expected = [r for r in range(1, 33) if r != 8]
    assert relay_ids == expected
    assert len(units) == 31


# ---------------------------------------------------------------------------
# Caller responsibility: stale cage_relays survives unchanged
# ---------------------------------------------------------------------------

def test_stale_cage_relays_for_one_hat_persists_under_two_hats():
    """If cage_relays already has 15 entries, the manager keeps them.

    This is the bug change_relay_hats() guards against: without an
    explicit ``app_settings['cage_relays'] = {}`` before building the
    manager, the 1-HAT cached map silently caps the new 2-HAT setup at
    15 cages. The test documents that the manager itself is not
    responsible for invalidating the cache — the caller is.
    """
    stale = {str(i): i for i in range(1, 16)}  # the 1-HAT map
    manager = RelayUnitManager(
        _solenoid_settings(num_hats=2, cage_relays=stale)
    )
    assert len(manager.get_all_relay_units()) == 15  # bug-documenting


def test_empty_cage_relays_under_two_hats_yields_31():
    """Counter-example to the previous test: clear the cache, get 31."""
    manager = RelayUnitManager(
        _solenoid_settings(num_hats=2, cage_relays={})
    )
    assert len(manager.get_all_relay_units()) == 31
