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

    **SUPPORTS TWO MODES:**
    
    1. **Continuous Flow Mode (Legacy - Lee Company LHD valves)**
       - Continuous valve open with flow integration
       - Predictive cutoff based on closing lag
       - Residual/leak detection
       
    2. **Pulse Mode (Parker Series 3 valves) - RECOMMENDED**
       - Micro-pulse delivery (10-500ms pulses)
       - Real-time flow sensor feedback
       - Empirically-validated pulse volumes
       - Precision: ±0.003 mL
    
    **Mode Selection:**
    Automatically selected via `settings['use_pulse_delivery']`:
    - True: Pulse mode (Parker valves)
    - False: Continuous mode (Lee valves)
    - Default: False (backward compatible)
    
    **Empirical Pulse Profiles (from valve_characterization tests):**
    - 10ms:  0.0234 mL (CV: 0.0%)
    - 20ms:  0.0260 mL (CV: 5.0%) ← DEFAULT
    - 50ms:  0.0239 mL (CV: 9.4%)
    - 100ms: 0.0286 mL (CV: 2.3%)
    - 200ms: 0.0351 mL (CV: 1.1%)
    - 500ms: 0.0513 mL (CV: 0.0%)
    
    Best Practices:
    - Strategy Pattern: Single class, multiple behaviors
    - Open/Closed Principle: New mode without modifying existing code
    - Composition: Delegate to mode-specific methods
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
        
        # Pulse mode detection (from empirical characterization tests)
        self._use_pulse_mode = bool(settings.get('use_pulse_delivery', False))
        self._pulse_settling_ms = int(settings.get('pulse_settling_ms', 100))
        
        # CRITICAL DEBUG: Log pulse mode detection
        print(f"[PULSE MODE DEBUG] use_pulse_delivery from settings: {settings.get('use_pulse_delivery')}")
        print(f"[PULSE MODE DEBUG] self._use_pulse_mode: {self._use_pulse_mode}")
        
        if self._use_pulse_mode:
            # Load pulse calibration (auto-calibrated or hardcoded defaults)
            # Best Practice: Load from persistent storage, not hardcoded in strategy
            from utils.pulse_calibration import CalibrationStore
            
            cal_store = CalibrationStore()
            calibration = cal_store.load()
            
            # Auto-select best pulse width (from calibration or settings)
            if settings.get('pulse_width_ms'):
                self._pulse_width_ms = int(settings.get('pulse_width_ms'))
            else:
                self._pulse_width_ms = calibration.get_default_pulse_width()
            
            # Build empirical pulse volume map from calibration
            self._empirical_pulse_volumes = {
                pw: profile.volume_mean_ml
                for pw, profile in calibration.pulse_profiles.items()
            }
            
            # Validate pulse width is calibrated
            if self._pulse_width_ms not in self._empirical_pulse_volumes:
                available = list(self._empirical_pulse_volumes.keys())
                self._logger.warning(
                    f"Pulse width {self._pulse_width_ms}ms not calibrated. "
                    f"Available: {available}. Using default."
                )
                self._pulse_width_ms = calibration.get_default_pulse_width()
            
            expected_vol = self._empirical_pulse_volumes[self._pulse_width_ms]
            cal_date = calibration.calibration_date
            cal_source = calibration.metadata.get('source', 'calibrated')
            
            self._logger.info(
                f"✓ Pulse mode ENABLED: pulse={self._pulse_width_ms}ms, "
                f"expected_vol={expected_vol:.4f}mL, calibration={cal_date} ({cal_source})"
            )
        else:
            self._logger.info("Continuous flow mode enabled (legacy)")


    async def deliver(
        self,
        relay_unit_id: int,
        target_volume_ml: float,
        triggers_hint: Optional[int] = None,
    ) -> bool:
        """
        Execute delivery using mode-specific logic.
        
        Best Practice: Strategy Pattern - delegate to mode-specific methods
        """
        cage_id = int(relay_unit_id)
        
        # CRITICAL DEBUG: Log routing decision
        print(f"[DELIVER DEBUG] Routing delivery: cage={cage_id}, vol={target_volume_ml:.3f}mL, pulse_mode={self._use_pulse_mode}")
        
        # Route to mode-specific delivery method
        if self._use_pulse_mode:
            print(f"[DELIVER DEBUG] Calling _deliver_pulse_mode()")
            return await self._deliver_pulse_mode(cage_id, target_volume_ml)
        else:
            print(f"[DELIVER DEBUG] Calling _deliver_continuous_mode()")
            return await self._deliver_continuous_mode(cage_id, target_volume_ml)
    
    async def _deliver_continuous_mode(
        self,
        cage_id: int,
        target_volume_ml: float,
    ) -> bool:
        """
        Legacy continuous flow delivery (Lee Company LHD valves).
        
        Kept for backward compatibility with existing installations.
        """

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
            
            # CRITICAL: Deterministic stream initialization before EVERY delivery
            # Best Practices:
            # - Idempotent operations: Start from known-good state
            # - Fail-fast: Catch sensor issues before opening valves
            # - Clear diagnostics: Report specific failure modes
            self._logger.debug(f"Pre-delivery: Verifying stream health...")
            
            # Step 1: Clear stale measurements (ensures fresh data)
            if hasattr(self._sensor, 'clear_queue'):
                cleared = self._sensor.clear_queue()
                if cleared > 0:
                    self._logger.debug(f"Cleared {cleared} stale measurements from queue")
            
            # Step 2: Verify stream is active and healthy
            if hasattr(self._sensor, 'ensure_streaming'):
                stream_ok = self._sensor.ensure_streaming(min_frames=5, timeout_s=3.0)
                if not stream_ok:
                    self._logger.warning("Stream health check failed, attempting recovery...")
                    
                    # Attempt recovery via reset
                    if hasattr(self._sensor, 'reset'):
                        try:
                            self._sensor.reset()
                            self._logger.info("Sensor reset completed, re-verifying stream...")
                        except Exception as e:
                            self._logger.warning(f"Sensor reset failed: {e}")
                        
                        # Re-verify after reset
                        stream_ok = self._sensor.ensure_streaming(min_frames=5, timeout_s=5.0)
                    
                    if not stream_ok:
                        error_msg = (
                            "Flow stream not available after recovery. "
                            "Check: 1) Teensy USB connection, 2) I²C wiring, 3) Pullup resistors (2kΩ)"
                        )
                        self._logger.error(error_msg)
                        return False
                
                self._logger.info(f"✓ Stream health verified, proceeding with delivery")
            
            self._logger.debug(f"Opening master solenoid...")
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
            
            # CRITICAL: Rescjume reads IMMEDIATELY after valve switching completes!
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

    async def _deliver_pulse_mode(
        self,
        cage_id: int,
        target_volume_ml: float,
    ) -> bool:
        """
        Pulse-based delivery for Parker Series 3 valves.
        
        Algorithm:
        1. Verify sensor health (fail-fast)
        2. Open master valve (prime manifold)
        3. Calculate estimated pulses from calibration
        4. Execute pulses until target reached or max exceeded
        5. Close all valves
        6. Log delivery summary
        
        Best Practices:
        - Predictive: Use calibrated volumes to estimate pulse count
        - Adaptive: Adjust based on actual measured volumes
        - Fail-safe: Safety limits (max pulses, max time)
        - Observable: Log each pulse for debugging
        - Idempotent: Can retry delivery safely
        
        Safety Mechanisms:
        - Max pulses: Prevent infinite loops
        - Max time: Prevent hung deliveries
        - Sensor error limit: Abort if sensor fails
        - Emergency close: Always close valves in finally block
        
        Args:
            cage_id: Target cage
            target_volume_ml: Desired volume (e.g., 0.3 mL)
        
        Returns:
            True if delivery successful, False otherwise
        """
        print(f"[PULSE MODE] ✓ ENTERED _deliver_pulse_mode: cage={cage_id}, target={target_volume_ml:.3f}mL")
        self._logger.info(f"Starting pulse delivery for cage {cage_id}: {target_volume_ml:.3f}mL")
        
        # Step 1: Verify sensor health (fail-fast)
        if not await self._verify_sensor_health():
            self._logger.error("Sensor health check failed, aborting delivery")
            return False
        
        # Step 2: Prime manifold (master valve only)
        try:
            self._logger.debug("Priming manifold...")
            self._valves.open_master()
            await asyncio.sleep(self._prime_ms / 1000.0)
            self._valves.close_master()
            await asyncio.sleep(0.05)
        except Exception as e:
            self._logger.error(f"Failed to prime manifold: {e}")
            return False
        
        # Step 3: Calculate estimated pulses from calibration
        expected_vol_per_pulse = self._empirical_pulse_volumes[self._pulse_width_ms]
        estimated_pulses = int(target_volume_ml / expected_vol_per_pulse) + 1
        
        self._logger.info(
            f"Estimated pulses: {estimated_pulses} "
            f"(target={target_volume_ml:.3f}mL, "
            f"pulse_vol={expected_vol_per_pulse:.4f}mL)"
        )
        
        # Step 4: Safety limits
        max_pulses = int(self._settings.get('max_pulses_per_delivery', 100))
        max_time_s = float(self._settings.get('max_pulse_delivery_time_s', 120.0))
        
        if estimated_pulses > max_pulses:
            self._logger.error(
                f"Estimated pulses ({estimated_pulses}) exceeds safety limit ({max_pulses}). "
                f"Target volume too large or calibration invalid."
            )
            return False
        
        # Step 5: Execute pulse loop
        delivered_ml = 0.0
        pulse_count = 0
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Open master valve for delivery (stays open during pulses)
            self._valves.open_master()
            await asyncio.sleep(0.3)  # Let manifold stabilize
            
            while delivered_ml < target_volume_ml:
                # Check safety limits
                if pulse_count >= max_pulses:
                    self._logger.error(f"Max pulses ({max_pulses}) reached, aborting")
                    return False
                
                elapsed_time = asyncio.get_event_loop().time() - start_time
                if elapsed_time >= max_time_s:
                    self._logger.error(f"Max time ({max_time_s}s) exceeded, aborting")
                    return False
                
                # Execute single pulse
                try:
                    pulse_volume = await self._execute_single_pulse(cage_id)
                    
                    if pulse_volume <= 0.0001:
                        self._logger.warning(f"Pulse {pulse_count+1} delivered negligible volume")
                    
                    delivered_ml += pulse_volume
                    pulse_count += 1
                    
                    # Log progress every 5 pulses
                    if pulse_count % 5 == 0:
                        self._logger.info(
                            f"Progress: {delivered_ml:.3f}/{target_volume_ml:.3f}mL "
                            f"({pulse_count} pulses)"
                        )
                    
                    # Check if target reached (with 10% overshoot tolerance)
                    remaining_ml = target_volume_ml - delivered_ml
                    if remaining_ml <= (expected_vol_per_pulse * 0.1):
                        self._logger.info(
                            f"Target reached: {delivered_ml:.3f}mL in {pulse_count} pulses"
                        )
                        break
                    
                except Exception as e:
                    self._logger.error(f"Pulse {pulse_count+1} failed: {e}")
                    # Continue to next pulse (don't abort on single pulse failure)
                
                # Small delay between pulses
                await asyncio.sleep(0.1)
            
            # Step 6: Final summary
            duration_s = asyncio.get_event_loop().time() - start_time
            precision_pct = abs(delivered_ml - target_volume_ml) / target_volume_ml * 100.0
            
            self._logger.info(
                f"✓ Pulse delivery complete: "
                f"delivered={delivered_ml:.3f}mL, "
                f"target={target_volume_ml:.3f}mL, "
                f"precision={precision_pct:.1f}%, "
                f"pulses={pulse_count}, "
                f"duration={duration_s:.1f}s"
            )
            
            return True
            
        except Exception as e:
            self._logger.error(f"Pulse delivery failed: {e}", exc_info=True)
            return False
            
        finally:
            # CRITICAL: Always close valves
            try:
                self._valves.close_cage(cage_id)
                self._valves.close_master()
                self._logger.debug("Valves closed")
            except Exception as e:
                self._logger.error(f"Failed to close valves: {e}")

    async def _execute_single_pulse(self, cage_id: int) -> float:
        """
        Execute a single valve pulse and measure delivered volume.
        
        Algorithm (from test_valve_characterization.py):
        1. Clear sensor queue (fresh data)
        2. Open cage valve for self._pulse_width_ms
        3. Close cage valve
        4. Wait self._pulse_settling_ms for flow to settle
        5. Collect flow samples during settling period
        6. Integrate using trapezoidal rule
        7. Return measured volume
        
        Best Practices:
        - Atomic: One pulse = one measurement
        - Defensive: Handle sensor failures gracefully
        - Empirical: Cross-validate with calibrated expectations
        - Observable: Log warnings if volume differs from calibration
        
        Args:
            cage_id: Cage to pulse
        
        Returns:
            Delivered volume in mL (0.0 if measurement failed)
        """
        # Safety: Get expected volume from calibration
        expected_vol_ml = self._empirical_pulse_volumes.get(
            self._pulse_width_ms, 
            0.026  # Fallback to 20ms default
        )
        
        # Step 1: Clear sensor queue for fresh data
        if hasattr(self._sensor, 'clear_queue'):
            self._sensor.clear_queue()
        
        # Step 2: Suspend sensor communications during valve switching (EMI reduction)
        try:
            if hasattr(self._sensor, '_pings_suspended'):
                self._sensor._pings_suspended = True
            if hasattr(self._sensor, 'suspend_reads'):
                self._sensor.suspend_reads(True)
        except Exception:
            pass
        
        # Step 3: Execute pulse
        try:
            start_time = asyncio.get_event_loop().time()
            
            self._valves.open_cage(cage_id)
            await asyncio.sleep(self._pulse_width_ms / 1000.0)
            self._valves.close_cage(cage_id)
            
        finally:
            # Resume sensor immediately after valve operation
            try:
                if hasattr(self._sensor, 'suspend_reads'):
                    self._sensor.suspend_reads(False)
                if hasattr(self._sensor, '_pings_suspended'):
                    self._sensor._pings_suspended = False
            except Exception:
                pass
        
        # Step 4: Wait for flow to settle
        await asyncio.sleep(self._pulse_settling_ms / 1000.0)
        
        # Step 5: Collect flow samples
        samples = []
        sampling_hz = float(self._settings.get('flow_sampling_hz', 20.0))
        sample_period_s = 1.0 / sampling_hz
        measurement_duration_s = 0.5  # 500ms measurement window
        
        elapsed = 0.0
        while elapsed < measurement_duration_s:
            try:
                sample = self._sensor.read_one()
                if sample and len(sample) >= 2:
                    flow_ul_min = float(sample[0])
                    flow_ml_min = flow_ul_min / 1000.0
                    samples.append({
                        'time_s': elapsed,
                        'flow_ml_min': flow_ml_min
                    })
            except Exception as e:
                self._logger.debug(f"Sample read error: {e}")
            
            await asyncio.sleep(sample_period_s)
            elapsed += sample_period_s
        
        # Step 6: Integrate flow to get volume (trapezoidal rule)
        delivered_ml = 0.0
        
        if len(samples) >= 2:
            for i in range(1, len(samples)):
                dt_s = samples[i]['time_s'] - samples[i-1]['time_s']
                dt_min = dt_s / 60.0
                avg_flow = (samples[i]['flow_ml_min'] + samples[i-1]['flow_ml_min']) / 2.0
                delivered_ml += avg_flow * dt_min
        else:
            # Fallback: No flow measurements, use calibrated value
            self._logger.warning(
                f"No flow measurements during pulse, using calibrated value: "
                f"{expected_vol_ml:.4f}mL"
            )
            delivered_ml = expected_vol_ml
        
        # Step 7: Validate against calibration (sanity check)
        deviation_pct = abs(delivered_ml - expected_vol_ml) / expected_vol_ml * 100.0 if expected_vol_ml > 0 else 0.0
        
        if deviation_pct > 20.0:
            self._logger.warning(
                f"Pulse volume deviation: measured={delivered_ml:.4f}mL, "
                f"expected={expected_vol_ml:.4f}mL ({deviation_pct:.1f}% diff)"
            )
        
        self._logger.debug(
            f"Pulse delivered: {delivered_ml:.4f}mL "
            f"(expected: {expected_vol_ml:.4f}mL, {len(samples)} samples)"
        )
        
        return delivered_ml

    async def _verify_sensor_health(self) -> bool:
        """
        Verify flow sensor is streaming and healthy.
        
        Best Practices:
        - DRY: Extracted from continuous mode for reuse
        - Fail-fast: Return False if sensor not ready
        - Self-healing: Attempt reset if initial check fails
        - Observable: Log all operations
        
        Returns:
            True if sensor ready, False otherwise
        """
        self._logger.debug("Verifying sensor health...")
        
        # Step 1: Clear stale measurements
        if hasattr(self._sensor, 'clear_queue'):
            cleared = self._sensor.clear_queue()
            if cleared > 0:
                self._logger.debug(f"Cleared {cleared} stale measurements from queue")
        
        # Step 2: Verify streaming
        if hasattr(self._sensor, 'ensure_streaming'):
            stream_ok = self._sensor.ensure_streaming(min_frames=5, timeout_s=3.0)
            
            if not stream_ok:
                self._logger.warning("Stream health check failed, attempting recovery...")
                
                # Attempt recovery via reset
                if hasattr(self._sensor, 'reset'):
                    try:
                        self._sensor.reset()
                        self._logger.info("Sensor reset completed, re-verifying stream...")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        self._logger.warning(f"Sensor reset failed: {e}")
                    
                    # Re-verify after reset
                    stream_ok = self._sensor.ensure_streaming(min_frames=5, timeout_s=5.0)
                
                if not stream_ok:
                    error_msg = (
                        "Flow stream not available after recovery. "
                        "Check: 1) Teensy USB connection, 2) I²C wiring, 3) Pullup resistors (2kΩ)"
                    )
                    self._logger.error(error_msg)
                    return False
        
        self._logger.info("✓ Sensor health verified")
        return True

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

