from __future__ import annotations

from typing import Optional

from .pump_strategy import PumpStrategy


class StrategyFactory:
    """Creates delivery strategies based on hardware mode.

    Parameters expected by create():
    - hardware_mode: 'pump' | 'solenoid' | None (defaults to 'pump')
    - pump_controller: required for pump mode
    - volume_calculator: required for pump mode
    - Additional kwargs are reserved for solenoid strategy (to be added).
    """

    @staticmethod
    def create(
        hardware_mode: Optional[str],
        *,
        pump_controller=None,
        volume_calculator=None,
        **kwargs,
    ):
        mode = (hardware_mode or "pump").strip().lower()

        if mode == "pump":
            return PumpStrategy(pump_controller, volume_calculator)

        if mode == "solenoid":
            # We will wire this once SolenoidFlowStrategy is implemented.
            raise NotImplementedError(
                "SolenoidFlowStrategy not available yet; use 'pump' mode"
            )

        # Fallback to pump mode for unknown values to preserve current behavior.
        return PumpStrategy(pump_controller, volume_calculator)


