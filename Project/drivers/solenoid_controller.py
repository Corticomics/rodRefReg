from __future__ import annotations

from typing import Dict


def _cage_map_from(cage_to_relay_id: Dict[int, int]) -> Dict[int, int]:
    """Normalise a cage->relay map and refuse relay ids the HAT layer would misroute.

    RelayHandler routes ids with divmod(id - 1, 16) and no lower bound, so a
    0 or -1 would energise relay 16 or 15 on the LAST HAT — on a one-HAT
    shared rig that is the master valve, on a stacked rig another animal's.
    """
    if not cage_to_relay_id:
        raise ValueError("cage_relays mapping is required")
    cage_map = {int(k): int(v) for k, v in cage_to_relay_id.items()}
    bad = {cage: relay for cage, relay in cage_map.items() if relay < 1}
    if bad:
        raise ValueError(f"cage relay ids must be >= 1, got {bad}")
    return cage_map


def _say(*args, **kwargs) -> None:
    """Print a diagnostic line. Never raises: a broken stdout (the journal
    pipe gone) must not stop a relay write, above all a close."""
    try:
        print(*args, **kwargs)
    except Exception:
        pass


class SolenoidController:
    """High-level controller for master and per-cage solenoids.

    This class wraps `RelayHandler` to manage ON/OFF states for a single master
    solenoid and multiple per-cage solenoids. It does not implement any volume
    logic; it only provides idempotent open/close operations and state mapping.

    Construct one through ``utils.topology.build_solenoid_controller`` so the
    device's valve topology picks between this class and
    :class:`IndependentSolenoidController`.
    """

    # Whether a master (shutoff) valve exists on this topology. The delivery
    # strategy consults it to decide whether to prime and hold the master.
    has_master = True

    def __init__(
        self,
        relay_handler,
        master_relay_id: int,
        cage_to_relay_id: Dict[int, int],
    ) -> None:
        if relay_handler is None:
            raise ValueError("relay_handler is required")
        if master_relay_id is None:
            raise ValueError("master_relay_id is required")
        cage_map = _cage_map_from(cage_to_relay_id)
        master = int(master_relay_id)
        if master < 1:
            # Same misrouting hazard as for cage ids (see _cage_map_from).
            # "No master" is a topology (IndependentSolenoidController), not a
            # number.
            raise ValueError(f"master_relay_id must be >= 1, got {master_relay_id!r}")
        self._relay_handler = relay_handler
        self._master = master
        self._cage_map = cage_map

        # Diagnostic: Print configuration on init
        _say(f"[SolenoidController] Initialized with master_relay={self._master}")
        _say(f"[SolenoidController] Cage-to-relay map: {self._cage_map}")

    def open_master(self) -> bool:
        _say(f"[SOLENOID] OPEN MASTER (relay {self._master})")
        result = self._relay_handler.set_relays([self._master], 1)
        _say(f"[SOLENOID] OPEN MASTER result: {result}")
        return result

    def close_master(self) -> bool:
        _say(f"[SOLENOID] CLOSE MASTER (relay {self._master})")
        result = self._relay_handler.set_relays([self._master], 0)
        _say(f"[SOLENOID] CLOSE MASTER result: {result}")
        return result

    def open_cage(self, cage_id: int) -> bool:
        relay = self._cage_map.get(int(cage_id))
        if relay is None:
            _say(
                f"[SOLENOID] ERROR: Unknown cage_id {cage_id}! Map keys: {list(self._cage_map.keys())}"
            )
            raise ValueError(f"Unknown cage_id {cage_id}")
        _say(f"[SOLENOID] OPEN CAGE {cage_id} → relay {relay}")
        result = self._relay_handler.set_relays([relay], 1)
        _say(f"[SOLENOID] OPEN CAGE {cage_id} result: {result}")
        return result

    def close_cage(self, cage_id: int) -> bool:
        relay = self._cage_map.get(int(cage_id))
        if relay is None:
            _say(
                f"[SOLENOID] ERROR: Unknown cage_id {cage_id}! Map keys: {list(self._cage_map.keys())}"
            )
            raise ValueError(f"Unknown cage_id {cage_id}")
        _say(f"[SOLENOID] CLOSE CAGE {cage_id} → relay {relay}")
        result = self._relay_handler.set_relays([relay], 0)
        _say(f"[SOLENOID] CLOSE CAGE {cage_id} result: {result}")
        return result

    def close_all_cages(self) -> bool:
        _say(f"[SOLENOID] CLOSE ALL CAGES (relays {list(self._cage_map.values())})")
        result = self._relay_handler.set_relays(list(self._cage_map.values()), 0)
        _say(f"[SOLENOID] CLOSE ALL CAGES result: {result}")
        return result

    def all_closed(self) -> bool:
        # The underlying RelayHandler does not expose readback; for now we assume
        # commands succeed and the HAT is stateless. If readback becomes available,
        # use it here.
        return True


class IndependentSolenoidController(SolenoidController):
    """Valve controller for the independent topology: one syringe and one
    solenoid per animal, no master valve.

    The cage operations are inherited unchanged. The master operations exist
    so the delivery choreography — open master, pulse the cage, close master in
    every finally block — keeps working unmodified: they succeed without
    touching any relay. Nothing on this controller ever drives a relay it was
    not given as a cage.
    """

    has_master = False

    def __init__(self, relay_handler, cage_to_relay_id: Dict[int, int]) -> None:
        if relay_handler is None:
            raise ValueError("relay_handler is required")
        self._relay_handler = relay_handler
        self._master = None
        self._cage_map = _cage_map_from(cage_to_relay_id)

        _say("[SolenoidController] Initialized with NO master valve (independent topology)")
        _say(f"[SolenoidController] Cage-to-relay map: {self._cage_map}")

    def open_master(self) -> bool:
        _say("[SOLENOID] no master valve on this topology; nothing to open")
        return True

    def close_master(self) -> bool:
        _say("[SOLENOID] no master valve on this topology; nothing to close")
        return True
