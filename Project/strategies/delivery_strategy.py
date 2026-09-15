from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass
class DeliveryResult:
    """What a delivery actually did, as opposed to what was asked of it.

    ``delivered_ml`` is the strategy's best estimate of the volume that
    physically left the valve — pulses fired times the calibrated volume per
    pulse, or the sensor-corrected figure where a flow sensor is fitted. It
    is reported on failure too: a delivery that aborts part-way has still put
    water in the cage, and the scheduling layer has to know that or it will
    re-send the whole dose.

    ``success`` is the only field that says whether the request was met.
    Never test the result object itself for truthiness — a dataclass instance
    is always truthy, so ``if result:`` would treat every failure as a
    success.
    """

    success: bool
    delivered_ml: float = 0.0
    duration_s: float = 0.0
    pulses: int = 0
    volume_per_pulse_ml: Optional[float] = None
    warning: Optional[str] = None


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
    ) -> DeliveryResult:
        """Deliver the requested volume to the specified relay unit.

        Returns a :class:`DeliveryResult`. Check ``.success`` for the
        outcome and ``.delivered_ml`` for what was actually dispensed —
        including on failure, where a partial volume may already be in the
        cage.
        """
        ...

    async def clean(self, relay_unit_id: int, to_waste: bool = True) -> None:
        """Optional cleaning/flush routine for the specified relay path."""
        ...
