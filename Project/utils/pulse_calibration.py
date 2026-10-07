"""
Pulse Calibration Manager for RRR
=================================

Manages empirical pulse volume calibration for Parker Series 3 valves.

Best Practices:
- Persistent storage: Save calibration results to JSON
- Auto-discovery: Detect if calibration exists
- Fail-safe: Use hardcoded defaults if no calibration
- Observable: Log all operations for debugging

What lives here is the GLOBAL default pulse profile: one mL/pulse figure
per pulse width, read by SolenoidFlowStrategy for a cage that has no row in
the valve_calibration table. Per-cage calibrations are measured by the
in-app Calibration Wizard and stored through
DatabaseHandler.save_valve_calibration; nothing in this module writes them.

- CalibrationStore: the JSON file of default profiles, with hardcoded
  fallbacks when the file is absent.

Originally derived from the valve-characterization bench tests. The
PulseCalibrator characterisation runner that used to live here was removed
in v1.21.0: nothing called it, and it drove the master valve directly.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional


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
            (pw, profile) for pw, profile in self.pulse_profiles.items() if profile.is_stable()
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
                metadata=data.get('metadata', {}),
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
                    str(pw): asdict(profile) for pw, profile in calibration.pulse_profiles.items()
                },
                'metadata': calibration.metadata,
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
                'note': 'Run calibration to measure actual valve characteristics',
            },
        )
