"""Which valve topology the solenoid path is driving.

Two topologies share one codebase:

- ``shared_manifold`` (the production rig): one reservoir feeds a MASTER
  solenoid, then a manifold, then one solenoid per cage. Every delivery
  primes the manifold through the master and holds the master open while
  the cage valve pulses.
- ``independent``: one syringe and one solenoid per animal. There is no
  master valve and nothing to prime; the cage valve is the whole fluid path.

The choice is a per-device setting (``valve_topology``, persisted in the
``system_settings`` table) read when hardware is set up. The only code that
differs between the two is what happens at the master valve, so the decision
is made in exactly one place — :func:`build_solenoid_controller` — and every
site that needs a valve controller asks here instead of constructing one.

An unknown stored value falls back to the shared topology, which is today's
behaviour, and is reported rather than guessed at. "No master" is never
expressed as a relay number: the relay layer has no lower bound on ids, so a
0 or -1 sentinel would energise a real relay on the last HAT.
"""

from __future__ import annotations

from drivers.solenoid_controller import IndependentSolenoidController, SolenoidController

SETTING_KEY = 'valve_topology'
SHARED_MANIFOLD = 'shared_manifold'
INDEPENDENT = 'independent'
TOPOLOGIES = (SHARED_MANIFOLD, INDEPENDENT)
DEFAULT_MASTER_RELAY_ID = 16


def normalize(value) -> str:
    """Map a stored value to a known topology; anything else is the shared one."""
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in TOPOLOGIES:
            return candidate
    return SHARED_MANIFOLD


def topology_from(settings) -> str:
    return normalize((settings or {}).get(SETTING_KEY))


def is_independent(settings) -> bool:
    return topology_from(settings) == INDEPENDENT


def build_solenoid_controller(relay_handler, settings, cage_map):
    """The valve controller for this device's topology.

    ``cage_map`` is ``{cage_id: relay_id}``; keys may be strings, as they are
    stored in settings. On the shared topology the master relay comes from
    ``global_master_relay_id``. On the independent topology no relay is ever
    driven as a master.
    """
    if is_independent(settings):
        return IndependentSolenoidController(relay_handler, cage_map)
    master_id = int((settings or {}).get('global_master_relay_id', DEFAULT_MASTER_RELAY_ID))
    return SolenoidController(relay_handler, master_id, cage_map)
