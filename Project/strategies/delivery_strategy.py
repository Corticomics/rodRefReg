from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class DeliveryStrategy(Protocol):
    """Abstract delivery strategy for dispensing water.

    This protocol defines the minimal contract required by the scheduling layer.
    Implementations may use pumps, solenoids with a master valve, or other
    actuation mechanisms. The interface is volume-centric and accepts a
    relay-unit identifier to align with existing RRR mappings.

    Notes
    -----
    - `relay_unit_id
    por` refers to the logical unit used by `RelayHandler`.
    - `target_volume_ml` is the desired volume in milliliters.
    - `triggers_hint` can be provided when applicable (e.g., legacy pump path)
      to avoid recalculating triggers. Implementations may ignore it.
    """

    async def deliver(
        self,
        relay_unit_id: int,
        target_volume_ml: float,
        triggers_hint: Optional[int] = None,
    ) -> bool:
        """Deliver the requested volume to the specified relay unit.

        Returns True on success; False on handled failure.
        """
        ...

    async def clean(self, relay_unit_id: int, to_waste: bool = True) -> None:
        """Optional cleaning/flush routine for the specified relay path."""
        ...
