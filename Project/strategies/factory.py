from __future__ import annotations

from typing import Optional

from .pump_strategy import PumpStrategy
from .solenoid_flow_strategy import SolenoidFlowStrategy


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
        solenoid_controller=None,
        flow_sensor=None,
        calibration_store=None,
        settings=None,
        **kwargs,
    ):
        mode = (hardware_mode or "pump").strip().lower()

        if mode == "pump":
            return PumpStrategy(pump_controller, volume_calculator)

        if mode == "solenoid":
            if not (solenoid_controller and flow_sensor and calibration_store and settings is not None):
                raise ValueError("Solenoid strategy requires solenoid_controller, flow_sensor, calibration_store, settings")
            return SolenoidFlowStrategy(
                solenoid_controller=solenoid_controller,
                flow_sensor=flow_sensor,
                calibration_store=calibration_store,
                settings=settings,
            )

        # Fallback to pump mode for unknown values to preserve current behavior.
        return PumpStrategy(pump_controller, volume_calculator)


