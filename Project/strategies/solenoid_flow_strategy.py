from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class DeliveryResult:
    success: bool
    delivered_ml: float
    duration_s: float
    warning: Optional[str] = None


class SolenoidFlowStrategy:
    """Volume-based delivery using a global master + per-cage solenoids.

    Responsibilities:
    - Open/close solenoids via SolenoidController
    - Read flow sensor samples, integrate volume using trapezoidal rule
    - Predictive cutoff to compensate close-time lag
    - Residual/Leak detection post close
    """

    def __init__(
        self,
        solenoid_controller,
        flow_sensor,
        calibration_store,
        settings: Dict,
        *,
        prime_ms: int = 200,
    ) -> None:
        self._valves = solenoid_controller
        self._sensor = flow_sensor
        self._cal = calibration_store
        self._settings = settings
        self._prime_ms = int(prime_ms)
        self._logger = logging.getLogger(self.__class__.__name__)

    async def deliver(
        self,
        relay_unit_id: int,
        target_volume_ml: float,
        triggers_hint: Optional[int] = None,
    ) -> bool:
        # Treat relay_unit_id as the cage identifier and defer mapping to SolenoidController
        # This avoids reliance on a potentially stale settings snapshot.
        cage_id = int(relay_unit_id)

        # Strategy parameters
        sampling_hz = float(self._settings.get('flow_sampling_hz', 50.0))
        close_ms = float(self._settings.get('predictive_close_ms', 10.0))
        residual_check_ms = float(self._settings.get('residual_check_ms', 200.0))
        residual_flow_threshold = float(self._settings.get('residual_flow_threshold_ml_min', 1.0))
        max_sensor_errors = int(self._settings.get('max_consecutive_sensor_errors', 10))

        # Prime path (master only)
        await asyncio.sleep(0)  # yield once
        try:
            self._valves.open_master()
            await asyncio.sleep(self._prime_ms / 1000.0)
            self._valves.close_master()
            await asyncio.sleep(0.05)
        except Exception as e:
            # Hardware or mapping issue – fail fast
            return False

        # Delivery
        delivered_ul = 0.0
        target_ul = float(target_volume_ml) * 1000.0
        last_flow_ml_min = None
        sensor_errors = 0
        sample_period_s = 1.0 / max(1.0, sampling_hz)

        # Note: Flow sensor should be started once during initialization, not per-delivery
        # Starting/stopping repeatedly causes I²C conflicts with relay HATs on shared bus
        # Sensor maintains continuous measurement mode for better reliability
        # I2C coordination ensures relay operations and sensor reads don't conflict

        try:
            self._valves.open_master()
            self._valves.open_cage(cage_id)
        except Exception as e:
            self._logger.error(f"Failed to open solenoids for cage {cage_id}: {e}")
            # Ensure master is closed on any opening failure
            try:
                self._valves.close_master()
            except Exception:
                pass
            return False

        start = asyncio.get_event_loop().time()
        try:
            while True:
                # Read measurement
                try:
                    # Unified interface: raw backend returns tuple (flow_uL_min, temp_C, flags)
                    # SDK wrapper may return FlowSample(flow_ml_min, temperature_c)
                    meas = None
                    if hasattr(self._sensor, 'read') and callable(getattr(self._sensor, 'read')):
                        # Poll at sample_period_s using a direct accessor if available
                        if hasattr(self._sensor, 'read_one'):
                            # read_one() is synchronous in our driver
                            meas = self._sensor.read_one()
                        elif hasattr(self._sensor, 'read_frame'):
                            meas = self._sensor.read_frame()
                    # If unified accessors not present, try SDK style cached sample
                except Exception:
                    meas = None

                if meas is None:
                    sensor_errors += 1
                    if sensor_errors >= max_sensor_errors:
                        self._logger.error(f"Max consecutive sensor errors ({max_sensor_errors}) reached for cage {cage_id}. Aborting delivery.")
                        # Ensure all valves are closed on sensor failure
                        try:
                            self._valves.close_cage(cage_id)
                            self._valves.close_master()
                        except Exception as e:
                            self._logger.error(f"Failed to close valves during sensor error recovery: {e}")
                        return False
                    await asyncio.sleep(sample_period_s)
                    continue

                sensor_errors = 0

                # Normalize to ml/min, guard NaNs
                if isinstance(meas, tuple) and len(meas) >= 1:
                    flow_ml_min = float(meas[0]) / 1000.0  # tuple from raw backend in uL/min
                else:
                    flow_ml_min = float(getattr(meas, 'flow_ml_min', 0.0))
                if flow_ml_min != flow_ml_min:  # NaN check
                    flow_ml_min = 0.0

                # Predictive cutoff
                if last_flow_ml_min is not None:
                    avg_flow_ml_min = 0.5 * (last_flow_ml_min + flow_ml_min)
                    dt_min = sample_period_s / 60.0
                    delivered_ul += (avg_flow_ml_min * 1000.0) * dt_min
                last_flow_ml_min = flow_ml_min

                # Remaining, lag est
                avg_recent_ml_min = last_flow_ml_min
                v_lag_ul = max(0.0, (avg_recent_ml_min * (close_ms / 1000.0)) * 1000.0)
                if delivered_ul >= (target_ul - v_lag_ul):
                    # Initiate close sequence
                    self._valves.close_cage(cage_id)
                    self._valves.close_master()
                    break

                await asyncio.sleep(sample_period_s)

            # Residual check
            residual_end = asyncio.get_event_loop().time() + (residual_check_ms / 1000.0)
            residual_flag = False
            while asyncio.get_event_loop().time() < residual_end:
                try:
                    if hasattr(self._sensor, 'read_one'):
                        meas = self._sensor.read_one()
                    else:
                        meas = None
                except Exception:
                    meas = None
                if meas is not None:
                    if isinstance(meas, tuple) and len(meas) >= 1:
                        flow_ml_min = float(meas[0]) / 1000.0
                    else:
                        flow_ml_min = float(getattr(meas, 'flow_ml_min', 0.0))
                    if flow_ml_min > residual_flow_threshold:
                        residual_flag = True
                        break
                await asyncio.sleep(sample_period_s)

            if residual_flag:
                return False

            return True
        finally:
            try:
                self._valves.close_cage(cage_id)
            except Exception:
                pass
            try:
                self._valves.close_master()
            except Exception:
                pass
            # Note: Flow sensor runs continuously, don't stop after each delivery
            # This prevents I²C conflicts and maintains measurement continuity

