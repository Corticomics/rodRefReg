from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Optional, Tuple
import asyncio
import logging
from smbus2 import SMBus, i2c_msg
from .i2c_coordinator import get_i2c_coordinator


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
        self._sampling_period_s = 1.0 / max(1.0, float(sampling_hz))
        self._zero_offset = float(zero_offset_ml_min)
        self._span_scale = float(span_scale)
        self._running = False
        self._backend = 'raw'
        self._bus_id = int(i2c_bus)
        self._null_reads = 0
        # Note: sensirion-i2c-slf3x package doesn't exist on PyPI
        # Use raw I2C implementation with coordination for conflict prevention
        self._coordinator = get_i2c_coordinator()
        self._addr = 0x08

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
                if self._sdk is not None:
                    reading = self._sdk.read_measurement_data()
                    flow = (reading.flow - self._zero_offset) * self._span_scale
                    yield FlowSample(flow_ml_min=flow, temperature_c=reading.temperature)
                else:
                    sample = self._read_raw_frame()
                    if sample is not None:
                        flow_ul_min, temp_c, _ = sample
                        flow_ml_min = ((flow_ul_min / 1000.0) - self._zero_offset) * self._span_scale
                        yield FlowSample(flow_ml_min=flow_ml_min, temperature_c=temp_c)
                await asyncio.sleep(self._sampling_period_s)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False

    # Debug helpers
    def backend_mode(self) -> str:
        return self._backend

    def bus_id(self) -> int:
        return self._bus_id

    # --- Raw backend helpers (CRC-8 per Sensirion) ---
    @staticmethod
    def _crc8(data: bytes) -> int:
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                crc = ((crc << 1) & 0xFF) ^ 0x31 if (crc & 0x80) else ((crc << 1) & 0xFF)
        return crc

    def _start_raw(self) -> None:
        """Start continuous measurement mode with I2C coordination.
        
        Command: 0x3608 (Start continuous measurement for liquid flow)
        Based on Sensirion I2C Implementation Guide.
        """
        def _hardware_start_operation():
            try:
                with SMBus(self._bus_id) as bus:
                    write_msg = i2c_msg.write(self._addr, [0x36, 0x08])
                    bus.i2c_rdwr(write_msg)
                    import time
                    time.sleep(0.01)  # 10ms sensor initialization time
                    return True
            except Exception as e:
                logging.warning(f"Flow sensor start I2C operation failed: {e}")
                return False
        
        try:
            success = self._coordinator.sync_exclusive_access(
                'flow_sensor',
                _hardware_start_operation
            )
            if not success:
                logging.warning(f"Flow sensor start command failed on bus {self._bus_id}")
        except Exception as e:
            logging.error(f"Flow sensor start coordination failed: {e}")

    def _stop_raw(self) -> None:
        """Stop continuous measurement mode with I2C coordination."""
        def _hardware_stop_operation():
            try:
                with SMBus(self._bus_id) as bus:
                    write_msg = i2c_msg.write(self._addr, [0x3F, 0xF9])
                    bus.i2c_rdwr(write_msg)
                    return True
            except Exception as e:
                logging.warning(f"Flow sensor stop I2C operation failed: {e}")
                return False
        
        try:
            self._coordinator.sync_exclusive_access(
                'flow_sensor',
                _hardware_stop_operation
            )
        except Exception as e:
            logging.error(f"Flow sensor stop coordination failed: {e}")

    def start(self) -> None:
        # Brief delay before flow sensor start to avoid I2C conflicts with relay initialization
        import time
        time.sleep(0.05)  # 50ms relay HAT stabilization delay
        
        self._start_raw()
        # Light debug to aid field setup
        try:
            print(f"[FlowSensor] start backend={self._backend} bus={self._bus_id}")
        except Exception:
            pass

    def read_one(self) -> Optional[Tuple[float, float, int]]:
        """Return a single sample: (flow_uL_min, temp_C, flags) or None."""
        sample = self._read_raw_frame()
        if sample is None:
            # Bound debug noise: only print occasionally at first use
            self._null_reads += 1
            if self._null_reads in (1, 5):
                try:
                    print(f"[FlowSensor] no frame on bus {self._bus_id} (attempt {self._null_reads})")
                except Exception:
                    pass
        else:
            self._null_reads = 0
        return sample

    def _read_raw_frame(self) -> Optional[Tuple[float, float, int]]:
        """Read 9-byte measurement frame with CRC validation and I2C coordination."""
        def _hardware_read_operation():
            try:
                with SMBus(self._bus_id) as bus:
                    read_msg = i2c_msg.read(self._addr, 9)
                    bus.i2c_rdwr(read_msg)
                    return bytes(read_msg)
            except Exception as e:
                # Don't log every read failure to avoid spam
                return None
        
        try:
            # Use coordinated access for flow sensor reads
            data = self._coordinator.sync_exclusive_access(
                'flow_sensor', 
                _hardware_read_operation
            )
            
            if data is None or len(data) != 9:
                return None
            
            fmsb, flsb, fcrc = data[0], data[1], data[2]
            tmsb, tlsb, tcrc = data[3], data[4], data[5]
            cmsb, clsb, ccrc = data[6], data[7], data[8]
            if self._crc8(bytes([fmsb, flsb])) != fcrc:
                return None
            if self._crc8(bytes([tmsb, tlsb])) != tcrc:
                return None
            if self._crc8(bytes([cmsb, clsb])) != ccrc:
                return None
            flow_raw = (fmsb << 8) | flsb
            temp_raw = (tmsb << 8) | tlsb
            if flow_raw & 0x8000:
                flow_raw -= 0x10000
            if temp_raw & 0x8000:
                temp_raw -= 0x10000
            flags = (cmsb << 8) | clsb
            flow_ul_min = flow_raw / 10.0
            temp_c = temp_raw / 200.0
            return (flow_ul_min, temp_c, flags)
        except Exception:
            return None

    def close(self) -> None:
        """Stop sensor and cleanup resources."""
        try:
            self._stop_raw()
        except Exception:
            pass


