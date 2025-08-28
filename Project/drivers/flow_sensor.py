from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Optional
import asyncio


@dataclass
class FlowSample:
    flow_ml_min: float
    temperature_c: float


class SLF3S0600FDriver:
    """Async wrapper for Sensirion SLF3S-0600F using sensirion-i2c-slf3x.

    The official driver exposes synchronous reads; we adapt to an async iterator
    with a configurable sampling rate suitable for integration. All calibration
    is applied as a zero offset and optional span factor.

    References
    ---------
    - Sensirion "sensirion-i2c-slf3x" Python package documentation.
    - SLF3S-0600F Datasheet: measurement units (ml/min), I2C addressing, CRC-8.
    """

    def __init__(
        self,
        i2c_bus,
        sampling_hz: float = 50.0,
        zero_offset_ml_min: float = 0.0,
        span_scale: float = 1.0,
    ) -> None:
        # We defer import to runtime to keep tests lightweight.
        from sensirion_i2c_slf3x import Slf3xI2cDevice
        from sensirion_i2c_driver import I2cConnection

        self._sampling_period_s = 1.0 / max(1.0, float(sampling_hz))
        self._zero_offset = float(zero_offset_ml_min)
        self._span_scale = float(span_scale)

        self._device = Slf3xI2cDevice(I2cConnection(i2c_bus))
        self._running = False

    def zero_calibrate(self) -> None:
        """Set the current zero offset to 0; caller should compute offset.
        This method is a simple setter to keep the interface minimal.
        """
        self._zero_offset = 0.0

    def set_zero_offset(self, offset_ml_min: float) -> None:
        self._zero_offset = float(offset_ml_min)

    def set_span_scale(self, scale: float) -> None:
        self._span_scale = float(scale)

    async def read(self) -> AsyncIterator[FlowSample]:
        self._running = True
        try:
            while self._running:
                # Sensirion API returns flow in ml/min and temperature in degC
                reading = self._device.read_measurement_data()
                flow = (reading.flow - self._zero_offset) * self._span_scale
                yield FlowSample(flow_ml_min=flow, temperature_c=reading.temperature)
                await asyncio.sleep(self._sampling_period_s)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False


