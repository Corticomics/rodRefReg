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


def is_known(value) -> bool:
    """Whether a stored value names a topology (case and whitespace aside)."""
    return isinstance(value, str) and value.strip().lower() in TOPOLOGIES


def normalize(value) -> str:
    """Map a stored value to a known topology; anything else is the shared one."""
    if is_known(value):
        return value.strip().lower()
    return SHARED_MANIFOLD


def describe(topology: str) -> str:
    """One line an operator can read: what the topology means for the master valve."""
    if normalize(topology) == INDEPENDENT:
        return "one syringe and one valve per animal; no master valve is ever driven"
    return "master valve + manifold; the master is primed and held around every delivery"


def topology_from(settings) -> str:
    return normalize((settings or {}).get(SETTING_KEY))


def is_independent(settings) -> bool:
    return topology_from(settings) == INDEPENDENT


# --- calibrations -------------------------------------------------------------
#
# A calibration is measured under one topology: the manifold's head and the
# master valve (or their absence) shape the volume per pulse. From v1.21.0
# every saved calibration records the topology it was measured under;
# rows saved before that carry NULL, and every device then ran the shared
# manifold, so an untagged row reads as shared_manifold ("legacy").


def calibration_topology(calibration) -> str:
    """The topology a stored calibration row was measured under."""
    return normalize((calibration or {}).get('topology'))


def calibration_is_legacy(calibration) -> bool:
    """Whether the row predates the topology tag (NULL in the database)."""
    return not is_known((calibration or {}).get('topology'))


def calibration_label(calibration) -> str:
    """What an operator sees: the topology, marked '(legacy)' when untagged."""
    topology = calibration_topology(calibration)
    return f"{topology} (legacy)" if calibration_is_legacy(calibration) else topology


def calibration_is_stale(calibration, settings) -> bool:
    """Whether a stored calibration was measured under the other topology.

    None (no calibration) is not stale: it is uncalibrated, a different gap.
    """
    if calibration is None:
        return False
    return calibration_topology(calibration) != topology_from(settings)


def cage_map_from(settings) -> dict[int, int]:
    """
    The device's cage -> relay map, ``{cage_id: relay_id}`` with int keys.

    The stored ``cage_relays`` wins when present. Otherwise cages are
    numbered sequentially over every relay in the stack except the master
    (``global_master_relay_id``), which is how the delivery path builds its
    own map: one HAT gives cages 1-15 on relays 1-15, a second HAT adds
    cages 16-31 on relays 17-32. Cage ids and relay ids are different
    number spaces; never assume ``relay == cage``.
    """
    settings = settings or {}
    stored = settings.get('cage_relays') or {}
    if stored:
        return {int(cage): int(relay) for cage, relay in stored.items()}
    num_hats = int(settings.get('num_hats', 1))
    master_id = int(settings.get('global_master_relay_id', DEFAULT_MASTER_RELAY_ID))
    relays = [relay for relay in range(1, 16 * num_hats + 1) if relay != master_id]
    return {cage: relay for cage, relay in enumerate(relays, start=1)}


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


# --- wording --------------------------------------------------------------------


def reserved_relay_reason(settings) -> str:
    """Why ``global_master_relay_id`` takes no cage, worded for the device.

    On the shared manifold it drives the master valve. On the independent
    topology nothing is wired to it, but it stays reserved, so both rigs
    number their cages the same way.
    """
    if is_independent(settings):
        return "reserved and unused on this device"
    return "reserved for the master solenoid"
