from __future__ import annotations

from typing import Optional


class PumpStrategy:
    """Thin adapter around the existing PumpController.

    This keeps behavior identical to the current pump flow while conforming to
    the new `DeliveryStrategy` protocol. It delegates to PumpController and uses
    VolumeCalculator for trigger computation when a hint is not supplied.
    """

    def __init__(self, pump_controller, volume_calculator):
        if pump_controller is None:
            raise ValueError("pump_controller cannot be None")
        if volume_calculator is None:
            raise ValueError("volume_calculator cannot be None")
        self._pump_controller = pump_controller
        self._volume_calculator = volume_calculator

    async def deliver(
        self,
        relay_unit_id: int,
        target_volume_ml: float,
        triggers_hint: Optional[int] = None,
    ) -> bool:
        if relay_unit_id is None:
            raise ValueError("relay_unit_id is required")
        if target_volume_ml is None or target_volume_ml <= 0:
            raise ValueError("target_volume_ml must be positive")

        # Prefer caller-provided hint to preserve legacy scheduling semantics.
        triggers = (
            triggers_hint
            if triggers_hint is not None
            else self._volume_calculator.calculate_triggers(target_volume_ml)
        )

        # For consistency with legacy path, compute the actual volume we will command.
        volume_ml_for_command = (
            (triggers * self._volume_calculator.pump_volume_ul) / 1000.0
        )

        return await self._pump_controller.dispense_water(
            relay_unit_id,
            volume_ml_for_command,
            triggers,
        )

    async def clean(self, relay_unit_id: int, to_waste: bool = True) -> None:
        # Pump path currently has no specialized clean routine here.
        return None


