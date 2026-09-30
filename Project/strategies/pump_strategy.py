from __future__ import annotations

import threading
import time
from typing import Optional

from strategies.delivery_strategy import DeliveryResult


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
        # Symmetry with SolenoidFlowStrategy so the worker can call
        # request_cancel() uniformly. A pump dispense is effectively
        # atomic (a single PumpController call), so cancellation can only
        # prevent a not-yet-started dispatch — there is no mid-flight
        # loop to poll. Honest about that limitation.
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        """Request cancellation. Prevents a not-yet-dispatched deliver()."""
        self._cancel_event.set()

    def reset_cancel(self) -> None:
        """Clear the cancellation token. Call once at schedule start.

        Symmetric with SolenoidFlowStrategy.reset_cancel — the worker
        clears once per run, never per chunk, so a mid-schedule cancel
        is never wiped.
        """
        self._cancel_event.clear()

    async def deliver(
        self,
        relay_unit_id: int,
        target_volume_ml: float,
        triggers_hint: Optional[int] = None,
    ) -> DeliveryResult:
        if relay_unit_id is None:
            raise ValueError("relay_unit_id is required")
        if target_volume_ml is None or target_volume_ml <= 0:
            raise ValueError("target_volume_ml must be positive")

        # Honor a cancel that landed before dispatch. Does NOT clear —
        # clearing is the worker's once-per-run responsibility.
        if self._cancel_event.is_set():
            return DeliveryResult(success=False, warning="cancelled before dispatch")

        # Prefer caller-provided hint to preserve legacy scheduling semantics.
        triggers = (
            triggers_hint
            if triggers_hint is not None
            else self._volume_calculator.calculate_triggers(target_volume_ml)
        )

        # For consistency with legacy path, compute the actual volume we will command.
        volume_ml_for_command = (triggers * self._volume_calculator.pump_volume_ul) / 1000.0

        started = time.monotonic()
        ok = await self._pump_controller.dispense_water(
            relay_unit_id,
            volume_ml_for_command,
            triggers,
        )
        # The pump path is open-loop: it commands a trigger count and has no
        # way to observe what came out. The commanded volume is the honest
        # figure, and the warning says it is unmeasured. A run a relay
        # stopped part-way is credited with the triggers that fired, so the
        # retry asks only for the rest.
        fired = int(triggers) if ok else self._triggers_fired(int(triggers))
        return DeliveryResult(
            success=bool(ok),
            delivered_ml=fired * self._ml_per_trigger(),
            duration_s=time.monotonic() - started,
            pulses=fired,
            warning="pump mode: volume is commanded, not measured",
        )

    def _triggers_fired(self, commanded: int) -> int:
        """How many of the commanded triggers the controller says switched on."""
        fired_of = getattr(self._pump_controller, 'triggers_fired', None)
        if not callable(fired_of):
            return 0
        try:
            return max(0, min(commanded, int(fired_of())))
        except (TypeError, ValueError):
            return 0

    def _ml_per_trigger(self) -> float:
        """The volume one trigger stands for, as calculate_triggers plans it:
        the pump volume divided by the calibration factor."""
        try:
            factor = float(getattr(self._volume_calculator, 'calibration_factor', 1.0))
        except (TypeError, ValueError):
            factor = 1.0
        if not factor > 0:
            factor = 1.0
        return self._volume_calculator.pump_volume_ul / factor / 1000.0

    async def clean(self, relay_unit_id: int, to_waste: bool = True) -> None:
        # Pump path currently has no specialized clean routine here.
        return None
