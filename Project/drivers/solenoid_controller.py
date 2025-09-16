from __future__ import annotations

from typing import Dict, Iterable, Optional


class SolenoidController:
    """High-level controller for master and per-cage solenoids.

    This class wraps `RelayHandler` to manage ON/OFF states for a single master
    solenoid and multiple per-cage solenoids. It does not implement any volume
    logic; it only provides idempotent open/close operations and state mapping.
    """

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
        if not cage_to_relay_id:
            raise ValueError("cage_relays mapping is required")
        self._relay_handler = relay_handler
        self._master = int(master_relay_id)
        self._cage_map = {int(k): int(v) for k, v in cage_to_relay_id.items()}

    def open_master(self) -> bool:
        return self._relay_handler.set_relays([self._master], 1)

    def close_master(self) -> bool:
        return self._relay_handler.set_relays([self._master], 0)

    def open_cage(self, cage_id: int) -> bool:
        relay = self._cage_map.get(int(cage_id))
        if relay is None:
            raise ValueError(f"Unknown cage_id {cage_id}")
        return self._relay_handler.set_relays([relay], 1)

    def close_cage(self, cage_id: int) -> bool:
        relay = self._cage_map.get(int(cage_id))
        if relay is None:
            raise ValueError(f"Unknown cage_id {cage_id}")
        return self._relay_handler.set_relays([relay], 0)

    def close_all_cages(self) -> bool:
        return self._relay_handler.set_relays(list(self._cage_map.values()), 0)

    def all_closed(self) -> bool:
        # The underlying RelayHandler does not expose readback; for now we assume
        # commands succeed and the HAT is stateless. If readback becomes available,
        # use it here.
        return True


