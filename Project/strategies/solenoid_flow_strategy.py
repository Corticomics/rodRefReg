from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Tuple


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
        # Safety/timeouts and debug sampling
        max_valve_open_s = float(self._settings.get('max_valve_open_s', 20.0))
        no_flow_threshold_ml_min = float(self._settings.get('no_flow_threshold_ml_min', 0.05))
        no_flow_timeout_s = float(self._settings.get('no_flow_timeout_s', 3.5))
        no_flow_accum_s = 0.0

        # Note: Flow sensor should be started once during initialization, not per-delivery
        # Starting/stopping repeatedly causes I²C conflicts with relay HATs on shared bus
        # Sensor maintains continuous measurement mode for better reliability
        # I2C coordination ensures relay operations and sensor reads don't conflict

        try:
            self._logger.info(f"Starting delivery for cage {cage_id}: {target_volume_ml:.3f}mL")
            self._logger.debug(f"Opening master solenoid...")
            # Gate delivery on active stream: require N frames before opening (reads must NOT be suspended)
            try:
                if hasattr(self._sensor, 'ensure_streaming'):
                    if not self._sensor.ensure_streaming(min_frames=3, timeout_s=3.0):
                        # Attempt datasheet-compliant recovery via reset if available
                        if hasattr(self._sensor, 'reset'):
                            try:
                                self._sensor.reset()
                            except Exception:
                                pass
                            if not self._sensor.ensure_streaming(min_frames=5, timeout_s=5.0):
                                self._logger.error("Flow stream not available after reset; aborting delivery")
                                return False
                        else:
                            self._logger.error("Flow stream not available; aborting delivery")
                            return False
            except Exception as _:
                pass
            # Suspend UART pings and serial reads during valve switching to reduce contention
            try:
                if hasattr(self._sensor, '_pings_suspended'):
                    self._sensor._pings_suspended = True
                if hasattr(self._sensor, 'suspend_reads'):
                    self._sensor.suspend_reads(True)
            except Exception:
                pass
            # Quiet period before switching relays to reduce collisions
            quiet_ms = float(self._settings.get('valve_switch_quiet_ms', 800.0))
            await asyncio.sleep(max(0.0, quiet_ms) / 1000.0)
            self._valves.open_master()
            self._logger.debug(f"Opening cage {cage_id} solenoid...")
            self._valves.open_cage(cage_id)
            self._logger.info(f"Solenoids opened successfully for cage {cage_id}")
            
            # CRITICAL: Resume reads IMMEDIATELY after valve switching completes!
            # The delivery loop NEEDS sensor data to measure flow
            try:
                if hasattr(self._sensor, 'suspend_reads'):
                    self._sensor.suspend_reads(False)
                    self._logger.debug("Sensor reads resumed after valve switching")
                if hasattr(self._sensor, '_pings_suspended'):
                    self._sensor._pings_suspended = False
            except Exception as e:
                self._logger.warning(f"Failed to resume reads: {e}")
        except Exception as e:
            self._logger.error(f"Failed to open solenoids for cage {cage_id}: {e}")
            # Ensure master is closed on any opening failure
            try:
                self._valves.close_master()
            except Exception:
                pass
            return False

        loop_ref = asyncio.get_event_loop()
        start = loop_ref.time()
        last_log = start
        try:
            while True:
                # Read measurement with robust error handling (Sensirion best practices)
                meas = await self._read_sensor_robust(cage_id, max_sensor_errors)
                
                if meas is None:
                    sensor_errors += 1
                    if sensor_errors == 1:  # Log first sensor error
                        self._logger.warning(f"Sensor read failed for cage {cage_id}, attempt {sensor_errors}/{max_sensor_errors}")
                    elif sensor_errors % 5 == 0:  # Log every 5th error to avoid spam
                        self._logger.warning(f"Sensor read failed for cage {cage_id}, attempt {sensor_errors}/{max_sensor_errors}")
                    
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

                # No-flow detection window (occlusion/EMI stall)
                if abs(flow_ml_min) < no_flow_threshold_ml_min:
                    no_flow_accum_s += sample_period_s
                else:
                    no_flow_accum_s = 0.0
                if no_flow_accum_s >= no_flow_timeout_s:
                    self._logger.error(
                        f"No flow detected for {no_flow_accum_s:.1f}s (< {no_flow_threshold_ml_min:.3f} mL/min). Aborting delivery.")
                    try:
                        self._valves.close_cage(cage_id)
                        self._valves.close_master()
                    except Exception:
                        pass
                    return False

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
                    self._logger.info(f"Target reached for cage {cage_id}: {delivered_ul:.1f}µL delivered, closing valves")
                    self._valves.close_cage(cage_id)
                    self._valves.close_master()
                    break

                # Max-open safety cutoff
                now = loop_ref.time()
                if (now - start) >= max_valve_open_s:
                    self._logger.error(
                        f"Max valve open time {max_valve_open_s:.1f}s exceeded. Delivered {delivered_ul/1000.0:.3f}mL; aborting.")
                    try:
                        self._valves.close_cage(cage_id)
                        self._valves.close_master()
                    except Exception:
                        pass
                    return False

                # 1 Hz debug summary
                if (now - last_log) >= 1.0:
                    self._logger.debug(
                        f"cage={cage_id} flow={flow_ml_min:.3f} mL/min delivered={delivered_ul/1000.0:.3f} mL")
                    last_log = now

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
            # Resume UART pings after valve operations
            try:
                if hasattr(self._sensor, '_pings_suspended'):
                    self._sensor._pings_suspended = False
                if hasattr(self._sensor, 'suspend_reads'):
                    self._sensor.suspend_reads(False)
            except Exception:
                pass

    async def _read_sensor_robust(self, cage_id: int, max_errors: int) -> Optional[Tuple]:
        """
        Robust sensor reading with Sensirion SLF3x best practices.
        
        Based on Sensirion documentation and embedded systems guidelines:
        - Handle "0 bytes" as normal for idle/no-flow conditions
        - Implement retry logic with appropriate delays
        - Validate data ranges and filter anomalies
        - Use timeout protection to prevent hanging
        
        Args:
            cage_id: Cage identifier for logging
            max_errors: Maximum consecutive errors before giving up
            
        Returns:
            Sensor measurement tuple (flow_uL_min, temp_C, flags) or None if failed
        """
        max_attempts = 3  # Per Sensirion guidelines: retry transient failures
        attempt_delay = 0.02  # 20ms between attempts (SLF3x measurement cycle is ~10ms)
        
        for attempt in range(max_attempts):
            try:
                # Multiple access patterns for different sensor backends
                meas = None
                
                # Method 1: Direct read_one() call (preferred for UART)
                if hasattr(self._sensor, 'read_one'):
                    meas = self._sensor.read_one()
                
                # Method 2: Frame-based reading (for I2C backends)
                elif hasattr(self._sensor, 'read_frame'):
                    meas = self._sensor.read_frame()
                
                # Method 3: Generic read() interface
                elif hasattr(self._sensor, 'read') and callable(getattr(self._sensor, 'read')):
                    meas = self._sensor.read()
                
                # Validate measurement data
                if meas is not None:
                    # Handle different return formats
                    if isinstance(meas, tuple) and len(meas) >= 2:
                        flow_val, temp_val = meas[0], meas[1]
                    elif hasattr(meas, 'flow_ml_min') and hasattr(meas, 'temperature_c'):
                        # SDK-style object
                        flow_val = meas.flow_ml_min * 1000.0  # Convert to µL/min
                        temp_val = meas.temperature_c
                        meas = (flow_val, temp_val)
                    else:
                        # Unexpected format
                        self._logger.debug(f"Unexpected sensor data format: {type(meas)}")
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(attempt_delay)
                            continue
                        return None
                    
                    # Validate data ranges (Sensirion SLF3S-0600F specifications)
                    # Flow: -40 to +40 mL/min (±40000 µL/min)
                    # Temperature: -10 to +70°C (sensor operating range)
                    if self._is_measurement_valid(flow_val, temp_val):
                        if attempt > 0:
                            self._logger.debug(f"Sensor read successful on attempt {attempt + 1} for cage {cage_id}")
                        return meas
                    else:
                        self._logger.debug(f"Invalid sensor data: flow={flow_val}, temp={temp_val}")
                
                # Measurement failed or invalid - check if this is a "0 bytes" case
                if attempt < max_attempts - 1:
                    self._logger.debug(f"Sensor read attempt {attempt + 1} failed for cage {cage_id}, retrying...")
                    await asyncio.sleep(attempt_delay)
                    continue
                
            except Exception as e:
                self._logger.debug(f"Sensor read exception (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(attempt_delay)
                    continue
        
        # All attempts failed
        self._logger.debug(f"All {max_attempts} sensor read attempts failed for cage {cage_id}")
        return None
    
    def _is_measurement_valid(self, flow_ul_min: float, temp_c: float) -> bool:
        """
        Validate sensor measurements against Sensirion SLF3S-0600F specifications.
        
        Args:
            flow_ul_min: Flow rate in µL/min
            temp_c: Temperature in Celsius
            
        Returns:
            True if measurement is within valid ranges
        """
        try:
            # Flow range: ±40 mL/min = ±40000 µL/min (SLF3S-0600F spec)
            if not (-40000 <= flow_ul_min <= 40000):
                return False
            
            # Temperature range: -10 to +70°C (sensor operating range)
            if not (-10 <= temp_c <= 70):
                return False
            
            # Check for NaN or infinite values
            if not (float('-inf') < flow_ul_min < float('inf')):
                return False
            if not (float('-inf') < temp_c < float('inf')):
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False

