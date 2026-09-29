from __future__ import annotations

from typing import Optional

from .pump_strategy import PumpStrategy
from .solenoid_flow_strategy import SolenoidFlowStrategy

VALID_HARDWARE_MODES = ('solenoid', 'pump')


class StrategyFactory:
    """Creates delivery strategies based on hardware mode.

    Parameters expected by create():
    - hardware_mode: 'solenoid' | 'pump' (case and surrounding spaces are
      ignored; anything else raises ValueError)
    - pump_controller: required for pump mode
    - volume_calculator: required for pump mode
    - solenoid_controller: required for solenoid mode
    - flow_sensor: required for solenoid mode
    - calibration_store: optional for solenoid mode
    - settings: required for all modes

    Best Practices:
    - Factory Pattern: Centralized strategy creation
    - Fail-fast: Validate required dependencies, and refuse a mode it does
      not know. Unknown values used to fall back to the pump strategy; on a
      valve rig that would pulse the relays with pump trigger timing.

    Note: SolenoidFlowStrategy auto-detects pulse mode from settings
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
        database_handler=None,
        **kwargs,
    ):
        mode = hardware_mode.strip().lower() if isinstance(hardware_mode, str) else ""

        if mode == "pump":
            return PumpStrategy(pump_controller, volume_calculator)

        if mode == "solenoid":
            # Solenoid strategy auto-detects pulse mode from settings
            # Best Practice: Single strategy handles both continuous and pulse modes
            # Note: flow_sensor can be None for calibration-only mode
            if not (solenoid_controller and settings is not None):
                raise ValueError("Solenoid strategy requires solenoid_controller and settings")
            return SolenoidFlowStrategy(
                solenoid_controller=solenoid_controller,
                flow_sensor=flow_sensor,  # Can be None for calibration-only mode
                calibration_store=calibration_store,
                settings=settings,
                database_handler=database_handler,  # For per-valve calibration
            )

        raise ValueError(
            f"Unknown hardware_mode {hardware_mode!r}: expected one of "
            f"{', '.join(VALID_HARDWARE_MODES)}. Refusing to guess which hardware to drive."
        )
