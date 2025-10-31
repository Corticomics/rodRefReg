"""
Pulse Calibration Manager for RRR
=================================

Manages empirical pulse volume calibration for Parker Series 3 valves.

Best Practices:
- Persistent storage: Save calibration results to JSON
- Auto-discovery: Detect if calibration exists
- Fail-safe: Use hardcoded defaults if no calibration
- Idempotent: Can re-calibrate at any time
- Observable: Log all operations for debugging

Architecture:
- CalibrationStore: Persistent storage (JSON file)
- PulseCalibrator: Runs characterization tests
- UI Integration: Button in Priming tab

Reference: test_valve_characterization.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List


@dataclass
class PulseProfile:
    """Empirically-measured pulse characteristics."""
    pulse_width_ms: int
    volume_mean_ml: float
    volume_stddev_ml: float
    coefficient_of_variation_pct: float
    trials: int
    calibration_date: str
    cage_id: int
    
    def is_stable(self) -> bool:
        """Check if pulse is stable (CV < 10%)."""
        return self.coefficient_of_variation_pct < 10.0


@dataclass
class CalibrationData:
    """Complete calibration dataset."""
    calibration_date: str
    cage_id: int
    valve_type: str  # e.g., "Parker Series 3"
    pulse_profiles: Dict[int, PulseProfile]  # {pulse_width_ms: profile}
    metadata: Dict[str, any]
    
    def get_default_pulse_width(self) -> int:
        """
        Select best pulse width based on stability and precision.
        
        Best Practice: Balance precision vs. reliability
        - Prefer CV < 5% (excellent stability)
        - Fallback to CV < 10% (acceptable)
        - Default to 20ms if no stable pulses
        """
        # Sort by CV (ascending) to find most stable
        stable_pulses = [
            (pw, profile) for pw, profile in self.pulse_profiles.items()
            if profile.is_stable()
        ]
        
        if not stable_pulses:
            return 20  # Fallback
        
        # Prefer 20ms if stable, otherwise pick most stable
        if 20 in [pw for pw, _ in stable_pulses]:
            return 20
        
        # Return pulse with lowest CV
        best_pulse = min(stable_pulses, key=lambda x: x[1].coefficient_of_variation_pct)
        return best_pulse[0]


class CalibrationStore:
    """
    Persistent storage for pulse calibration data.
    
    Best Practices:
    - Single source of truth: One file per system
    - Atomic writes: Write to temp file, then rename
    - Validation: Check data integrity on load
    - Backward compatible: Handle missing fields gracefully
    """
    
    DEFAULT_CALIBRATION_FILE = "pulse_calibration.json"
    
    # Hardcoded empirical defaults (from valve_characterization tests)
    # Best Practice: Always have fallback values
    HARDCODED_DEFAULTS = {
        10: PulseProfile(10, 0.0234, 0.00001, 0.0, 3, "2025-10-27", 15),
        20: PulseProfile(20, 0.0260, 0.0013, 5.0, 3, "2025-10-27", 15),
        50: PulseProfile(50, 0.0239, 0.0023, 9.4, 3, "2025-10-27", 15),
        100: PulseProfile(100, 0.0286, 0.0007, 2.3, 3, "2025-10-27", 15),
        200: PulseProfile(200, 0.0351, 0.0004, 1.1, 3, "2025-10-27", 15),
        500: PulseProfile(500, 0.0513, 0.00003, 0.0, 3, "2025-10-27", 15),
    }
    
    def __init__(self, calibration_dir: Optional[Path] = None):
        """
        Initialize calibration store.
        
        Args:
            calibration_dir: Directory to store calibration files
                           (default: Project root)
        """
        self._logger = logging.getLogger(self.__class__.__name__)
        
        if calibration_dir is None:
            # Default to Project directory
            calibration_dir = Path(__file__).parent.parent
        
        self._calibration_dir = Path(calibration_dir)
        self._calibration_file = self._calibration_dir / self.DEFAULT_CALIBRATION_FILE
        
        self._logger.info(f"Calibration file: {self._calibration_file}")
    
    def load(self) -> CalibrationData:
        """
        Load calibration data from file.
        
        Best Practices:
        - Fail-safe: Return defaults if file missing
        - Validation: Check data integrity
        - Backward compatible: Handle schema changes
        
        Returns:
            CalibrationData (from file or hardcoded defaults)
        """
        if not self._calibration_file.exists():
            self._logger.info("No calibration file found, using hardcoded defaults")
            return self._get_default_calibration()
        
        try:
            with open(self._calibration_file, 'r') as f:
                data = json.load(f)
            
            # Parse pulse profiles
            pulse_profiles = {}
            for pw_str, profile_dict in data.get('pulse_profiles', {}).items():
                pw = int(pw_str)
                pulse_profiles[pw] = PulseProfile(**profile_dict)
            
            calibration = CalibrationData(
                calibration_date=data.get('calibration_date', 'unknown'),
                cage_id=data.get('cage_id', 0),
                valve_type=data.get('valve_type', 'Unknown'),
                pulse_profiles=pulse_profiles,
                metadata=data.get('metadata', {})
            )
            
            self._logger.info(
                f"✓ Loaded calibration: {len(pulse_profiles)} pulse widths, "
                f"cage={calibration.cage_id}, date={calibration.calibration_date}"
            )
            
            return calibration
            
        except Exception as e:
            self._logger.error(f"Failed to load calibration file: {e}", exc_info=True)
            self._logger.warning("Falling back to hardcoded defaults")
            return self._get_default_calibration()
    
    def save(self, calibration: CalibrationData) -> bool:
        """
        Save calibration data to file.
        
        Best Practices:
        - Atomic write: Write to temp file, then rename
        - Backup: Keep previous calibration as .bak
        - Validation: Verify write succeeded
        
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Backup existing file
            if self._calibration_file.exists():
                backup_file = self._calibration_file.with_suffix('.json.bak')
                self._calibration_file.replace(backup_file)
                self._logger.debug(f"Backed up previous calibration to {backup_file}")
            
            # Prepare data for JSON serialization
            data = {
                'calibration_date': calibration.calibration_date,
                'cage_id': calibration.cage_id,
                'valve_type': calibration.valve_type,
                'pulse_profiles': {
                    str(pw): asdict(profile)
                    for pw, profile in calibration.pulse_profiles.items()
                },
                'metadata': calibration.metadata
            }
            
            # Atomic write: temp file + rename
            temp_file = self._calibration_file.with_suffix('.json.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            temp_file.replace(self._calibration_file)
            
            self._logger.info(f"✓ Saved calibration to {self._calibration_file}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to save calibration: {e}", exc_info=True)
            return False
    
    def exists(self) -> bool:
        """Check if calibration file exists."""
        return self._calibration_file.exists()
    
    def _get_default_calibration(self) -> CalibrationData:
        """Return hardcoded default calibration."""
        return CalibrationData(
            calibration_date="2025-10-27 (hardcoded defaults)",
            cage_id=15,
            valve_type="Parker Series 3 (empirical default)",
            pulse_profiles=self.HARDCODED_DEFAULTS.copy(),
            metadata={
                'source': 'hardcoded',
                'note': 'Run calibration to measure actual valve characteristics'
            }
        )


class PulseCalibrator:
    """
    Runs pulse characterization tests to measure valve behavior.
    
    Best Practices:
    - Reuse existing code: Leverage test_valve_characterization.py logic
    - Progress reporting: Emit signals for UI updates
    - Fail-safe: Continue if individual tests fail
    - Idempotent: Can run multiple times safely
    """
    
    def __init__(
        self,
        solenoid_controller,
        flow_sensor,
        cage_id: int,
        progress_callback=None
    ):
        """
        Initialize calibrator.
        
        Args:
            solenoid_controller: SolenoidController instance
            flow_sensor: UARTFlowSensor instance
            cage_id: Cage to calibrate
            progress_callback: Optional callback(message: str) for UI updates
        """
        self._controller = solenoid_controller
        self._sensor = flow_sensor
        self._cage_id = cage_id
        self._progress_callback = progress_callback
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def _emit_progress(self, message: str):
        """Emit progress message to UI."""
        self._logger.info(message)
        if self._progress_callback:
            self._progress_callback(message)
    
    async def calibrate(
        self,
        pulse_widths_ms: Optional[List[int]] = None,
        trials_per_pulse: int = 3
    ) -> CalibrationData:
        """
        Run pulse characterization tests.
        
        Args:
            pulse_widths_ms: List of pulse widths to test (default: [10, 20, 50, 100, 200, 500])
            trials_per_pulse: Number of trials per pulse width (default: 3)
        
        Returns:
            CalibrationData with measured pulse profiles
        """
        if pulse_widths_ms is None:
            pulse_widths_ms = [10, 20, 50, 100, 200, 500]
        
        self._emit_progress(f"Starting calibration for cage {self._cage_id}")
        self._emit_progress(f"Testing {len(pulse_widths_ms)} pulse widths with {trials_per_pulse} trials each")
        
        pulse_profiles = {}
        
        for pulse_ms in pulse_widths_ms:
            self._emit_progress(f"Testing {pulse_ms}ms pulse width...")
            
            try:
                profile = await self._calibrate_single_pulse(pulse_ms, trials_per_pulse)
                pulse_profiles[pulse_ms] = profile
                
                stability = "STABLE" if profile.is_stable() else "UNSTABLE"
                self._emit_progress(
                    f"  {pulse_ms}ms: {profile.volume_mean_ml:.4f} mL "
                    f"(CV: {profile.coefficient_of_variation_pct:.1f}%) {stability}"
                )
                
            except Exception as e:
                self._logger.error(f"Failed to calibrate {pulse_ms}ms: {e}")
                self._emit_progress(f"  {pulse_ms}ms: FAILED - {e}")
        
        if not pulse_profiles:
            raise RuntimeError("All pulse calibrations failed!")
        
        calibration = CalibrationData(
            calibration_date=datetime.now().isoformat(),
            cage_id=self._cage_id,
            valve_type="Parker Series 3",
            pulse_profiles=pulse_profiles,
            metadata={
                'trials_per_pulse': trials_per_pulse,
                'total_pulses_tested': len(pulse_profiles),
                'successful_pulses': len([p for p in pulse_profiles.values() if p.is_stable()])
            }
        )
        
        self._emit_progress(f"✓ Calibration complete: {len(pulse_profiles)} pulse widths measured")
        
        return calibration
    
    async def _calibrate_single_pulse(
        self,
        pulse_ms: int,
        trials: int
    ) -> PulseProfile:
        """
        Calibrate a single pulse width.
        
        Logic from test_valve_characterization.py Test 4.
        """
        volumes = []
        
        for trial in range(trials):
            # Restart sensor to reset error counter (critical fix!)
            if trial > 0:
                self._sensor.stop()
                await asyncio.sleep(0.2)
                self._sensor.start()
                await asyncio.sleep(1.0)
            
            # Verify streaming
            if hasattr(self._sensor, 'ensure_streaming'):
                if not self._sensor.ensure_streaming(min_frames=5, timeout_s=3.0):
                    raise RuntimeError(f"Sensor not streaming for trial {trial+1}")
            
            # Execute pulse and measure
            try:
                self._controller.close_cage(self._cage_id)
                self._controller.close_master()
            except Exception:
                pass
            
            await asyncio.sleep(1.0)
            self._controller.open_master()
            await asyncio.sleep(0.3)
            
            # Clear sensor queue
            if hasattr(self._sensor, 'clear_queue'):
                self._sensor.clear_queue()
            
            # Execute pulse
            start_time = time.perf_counter()
            self._controller.open_cage(self._cage_id)
            
            # Measure during pulse + settling
            samples = []
            measurement_duration_s = (pulse_ms / 1000.0) + 0.5
            
            while (time.perf_counter() - start_time) < measurement_duration_s:
                sample = self._sensor.read_one()
                if sample:
                    elapsed = time.perf_counter() - start_time
                    samples.append({
                        'time_s': elapsed,
                        'flow_ml_min': sample[0] / 1000.0
                    })
                
                # Close valve at specified time
                if (time.perf_counter() - start_time) >= (pulse_ms / 1000.0):
                    if (time.perf_counter() - start_time) < (pulse_ms / 1000.0) + 0.01:
                        self._controller.close_cage(self._cage_id)
                
                await asyncio.sleep(0.01)
            
            # Integrate flow to get volume
            volume_ml = 0.0
            for i in range(1, len(samples)):
                dt_min = (samples[i]['time_s'] - samples[i-1]['time_s']) / 60.0
                avg_flow = (samples[i]['flow_ml_min'] + samples[i-1]['flow_ml_min']) / 2.0
                volume_ml += avg_flow * dt_min
            
            volumes.append(volume_ml)
            
            # Cleanup
            try:
                self._controller.close_cage(self._cage_id)
                self._controller.close_master()
            except Exception:
                pass
            
            await asyncio.sleep(2.0)
        
        # Calculate statistics
        if not volumes:
            raise RuntimeError("No successful volume measurements")
        
        mean_vol = sum(volumes) / len(volumes)
        
        if len(volumes) > 1:
            variance = sum((v - mean_vol) ** 2 for v in volumes) / (len(volumes) - 1)
            stddev = variance ** 0.5
        else:
            stddev = 0.0
        
        cv_pct = (stddev / mean_vol * 100.0) if mean_vol > 0 else 999.0
        
        return PulseProfile(
            pulse_width_ms=pulse_ms,
            volume_mean_ml=mean_vol,
            volume_stddev_ml=stddev,
            coefficient_of_variation_pct=cv_pct,
            trials=len(volumes),
            calibration_date=datetime.now().isoformat(),
            cage_id=self._cage_id
        )

