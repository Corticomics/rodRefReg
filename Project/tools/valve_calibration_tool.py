#!/usr/bin/env python3
"""
Valve Calibration Tool for RRR
===============================

Performs empirical calibration of solenoid valves following industry best practices.

**Method:** 
Your colleague's proven approach - Run 200-300 pulses per valve, gravimetrically 
measure total output, calculate precise mL/pulse value.

**Why This Works:**
1. Large sample size (200-300) eliminates random error
2. Gravimetric measurement is the gold standard (±0.001g resolution)
3. Per-valve calibration accounts for manufacturing tolerances
4. Direct empirical measurement beats theoretical models

**Usage:**
    # Interactive mode (with prompts)
    python valve_calibration_tool.py --cage 15 --interactive
    
    # Automated mode (for CI/testing)
    python valve_calibration_tool.py --cage 15 --num-pulses 250 \\
        --pulse-width-ms 20 --measured-ml 6.85

**Requirements:**
- Lab scale with ±0.001g precision
- Empty collection beaker
- Steady room temperature (~20-25°C)
- Verify fluid reservoir is full before starting

**Best Practices:**
- Run calibration when system is stable (30min warm-up)
- Use same pulse width as production (default: 20ms)
- Recalibrate if: valve replaced, pressure changed, fluid type changed
- Validate: CV should be <5% for production use
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Add Project directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from drivers.uart_flow_sensor import UARTFlowSensor
from gpio.solenoid_controller import SolenoidController
from models.database_handler import DatabaseHandler

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValveCalibrator:
    """
    Empirical valve calibration following colleague's proven method.

    Workflow:
    1. User prepares: tare scale, place collection beaker
    2. System: Execute N pulses (200-300 recommended)
    3. User measures: weigh beaker, record volume
    4. System: Calculate mL/pulse, save to database
    """

    DEFAULT_PULSE_WIDTH_MS = 20  # Parker Series 3 optimal
    DEFAULT_NUM_PULSES = 250  # Balance between time and precision

    def __init__(
        self,
        solenoid_controller: SolenoidController,
        database_handler: DatabaseHandler,
        flow_sensor: Optional[UARTFlowSensor] = None,
    ):
        """
        Initialize calibrator.

        Args:
            solenoid_controller: Controller for valve actuation
            database_handler: Database for storing calibration
            flow_sensor: Optional sensor for validation (not primary measurement)
        """
        self.controller = solenoid_controller
        self.db = database_handler
        self.sensor = flow_sensor
        self.logger = logging.getLogger(self.__class__.__name__)

    async def calibrate_valve(
        self,
        cage_id: int,
        relay_id: int,
        num_pulses: int = DEFAULT_NUM_PULSES,
        pulse_width_ms: int = DEFAULT_PULSE_WIDTH_MS,
        measured_volume_ml: Optional[float] = None,
        interactive: bool = True,
        calibrated_by: Optional[int] = None,
    ) -> Dict:
        """
        Run calibration workflow for a single valve.

        Args:
            cage_id: Cage identifier
            relay_id: Physical relay ID
            num_pulses: Number of pulses to execute (200-300 recommended)
            pulse_width_ms: Pulse width in milliseconds
            measured_volume_ml: Pre-measured volume (for non-interactive mode)
            interactive: If True, prompt user for measurements
            calibrated_by: Trainer ID

        Returns:
            dict with calibration results
        """
        self.logger.info("=" * 70)
        self.logger.info(f"VALVE CALIBRATION - Cage {cage_id} (Relay {relay_id})")
        self.logger.info("=" * 70)
        self.logger.info(f"Pulse width: {pulse_width_ms}ms")
        self.logger.info(f"Number of pulses: {num_pulses}")
        self.logger.info("")

        # Step 1: Pre-flight checks
        if interactive:
            self.logger.info("PRE-FLIGHT CHECKLIST:")
            self.logger.info("  1. Verify fluid reservoir is FULL")
            self.logger.info("  2. Place empty beaker under cage {cage_id} output")
            self.logger.info("  3. Tare your lab scale with empty beaker")
            self.logger.info("  4. Ensure system has been running >30min (stable temp)")
            self.logger.info("")
            input("Press ENTER when ready to begin calibration...")
            self.logger.info("")

        # Step 2: Execute pulses
        self.logger.info(f"Executing {num_pulses} pulses...")
        self.logger.info(
            "(This will take ~{:.1f} minutes)".format(
                num_pulses * pulse_width_ms / 1000 / 60 * 2  # rough estimate with delays
            )
        )

        start_time = time.time()
        pulse_count = 0

        try:
            # Open master valve
            self.controller.open_master()
            await asyncio.sleep(0.5)

            # Execute pulses with progress updates
            for i in range(num_pulses):
                # Pulse the valve
                self.controller.open_cage(cage_id)
                await asyncio.sleep(pulse_width_ms / 1000.0)
                self.controller.close_cage(cage_id)

                pulse_count += 1

                # Progress reporting every 50 pulses
                if (i + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    progress_pct = (i + 1) / num_pulses * 100
                    self.logger.info(
                        f"  Progress: {i+1}/{num_pulses} ({progress_pct:.1f}%) - "
                        f"Elapsed: {elapsed:.1f}s"
                    )

                # Small delay between pulses to prevent overheating
                await asyncio.sleep(0.1)

            # Close master valve
            self.controller.close_cage(cage_id)
            self.controller.close_master()

            total_time = time.time() - start_time
            self.logger.info(f"✓ Completed {pulse_count} pulses in {total_time:.1f}s")
            self.logger.info("")

        except Exception as e:
            self.logger.error(f"Pulse execution failed: {e}")
            # Ensure valves are closed
            try:
                self.controller.close_cage(cage_id)
                self.controller.close_master()
            except:
                pass
            raise

        # Step 3: Get measurement from user
        if measured_volume_ml is None:
            if not interactive:
                raise ValueError("measured_volume_ml required in non-interactive mode")

            self.logger.info("MEASUREMENT:")
            self.logger.info("  1. Remove beaker from under cage output")
            self.logger.info("  2. Weigh beaker on lab scale")
            self.logger.info("  3. For water: weight in grams ≈ volume in mL")
            self.logger.info("")

            while True:
                try:
                    measured_volume_ml = float(input("Enter measured volume (mL): "))
                    if measured_volume_ml <= 0:
                        self.logger.error("Volume must be positive!")
                        continue
                    if measured_volume_ml > num_pulses * 0.5:  # sanity check
                        self.logger.warning(
                            f"That seems high ({measured_volume_ml}mL for {num_pulses} pulses)"
                        )
                        confirm = input("Continue anyway? (yes/no): ")
                        if confirm.lower() != 'yes':
                            continue
                    break
                except ValueError:
                    self.logger.error("Invalid input, please enter a number")

        # Step 4: Calculate calibration
        volume_per_pulse_ml = measured_volume_ml / num_pulses

        # Estimate uncertainty based on scale precision (±0.001g) and number of pulses
        # Standard error = scale_precision / sqrt(num_pulses)
        scale_precision_ml = 0.001
        stddev_ml = scale_precision_ml / (num_pulses**0.5)
        cv_pct = (stddev_ml / volume_per_pulse_ml) * 100 if volume_per_pulse_ml > 0 else 999

        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("CALIBRATION RESULTS")
        self.logger.info("=" * 70)
        self.logger.info(f"Total volume measured:  {measured_volume_ml:.4f} mL")
        self.logger.info(f"Number of pulses:       {num_pulses}")
        self.logger.info(f"Volume per pulse:       {volume_per_pulse_ml:.6f} mL/pulse")
        self.logger.info(f"Estimated CV:           {cv_pct:.2f}%")
        self.logger.info("")

        # Quality assessment
        if cv_pct < 1.0:
            quality = "EXCELLENT"
        elif cv_pct < 3.0:
            quality = "GOOD"
        elif cv_pct < 5.0:
            quality = "ACCEPTABLE"
        else:
            quality = "POOR (Consider re-calibration with more pulses)"

        self.logger.info(f"Quality: {quality}")
        self.logger.info("")

        # Step 5: Save to database
        if interactive:
            save = input("Save this calibration to database? (yes/no): ")
            if save.lower() != 'yes':
                self.logger.info("Calibration NOT saved")
                return {
                    'cage_id': cage_id,
                    'relay_id': relay_id,
                    'volume_per_pulse_ml': volume_per_pulse_ml,
                    'saved': False,
                }

        notes = f"Empirical calibration: {num_pulses} pulses @ {pulse_width_ms}ms"

        calibration_id = self.db.save_valve_calibration(
            cage_id=cage_id,
            relay_id=relay_id,
            pulse_width_ms=pulse_width_ms,
            volume_per_pulse_ml=volume_per_pulse_ml,
            stddev_ml=stddev_ml,
            cv_pct=cv_pct,
            num_samples=num_pulses,
            calibrated_by=calibrated_by,
            notes=notes,
        )

        if calibration_id:
            self.logger.info(f"✓ Calibration saved to database (ID: {calibration_id})")
        else:
            self.logger.error("Failed to save calibration to database")

        return {
            'cage_id': cage_id,
            'relay_id': relay_id,
            'pulse_width_ms': pulse_width_ms,
            'volume_per_pulse_ml': volume_per_pulse_ml,
            'stddev_ml': stddev_ml,
            'cv_pct': cv_pct,
            'num_samples': num_pulses,
            'calibration_id': calibration_id,
            'saved': calibration_id is not None,
        }


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Empirical valve calibration tool (200-300 pulse method)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive calibration of cage 15
  python valve_calibration_tool.py --cage 15 --interactive
  
  # Automated calibration (for scripting)
  python valve_calibration_tool.py --cage 15 --num-pulses 250 \\
      --pulse-width-ms 20 --measured-ml 6.85 --trainer-id 1
  
  # Calibrate with custom pulse count
  python valve_calibration_tool.py --cage 15 --num-pulses 300 --interactive

Best Practices:
  - Use 200-300 pulses for best precision
  - Measure with lab scale (±0.001g precision)
  - For water: 1g ≈ 1mL
  - Recalibrate after valve replacement or pressure changes
        """,
    )

    parser.add_argument('--cage', type=int, required=True, help='Cage ID to calibrate (e.g., 15)')
    parser.add_argument('--relay', type=int, help='Relay ID (if different from cage ID)')
    parser.add_argument(
        '--num-pulses', type=int, default=250, help='Number of pulses to execute (default: 250)'
    )
    parser.add_argument(
        '--pulse-width-ms', type=int, default=20, help='Pulse width in milliseconds (default: 20)'
    )
    parser.add_argument(
        '--measured-ml', type=float, help='Pre-measured volume in mL (non-interactive mode)'
    )
    parser.add_argument(
        '--interactive', action='store_true', help='Interactive mode with user prompts'
    )
    parser.add_argument('--trainer-id', type=int, help='Trainer ID performing calibration')
    parser.add_argument(
        '--db-path', type=str, default='rrr_database.db', help='Path to database file'
    )

    args = parser.parse_args()

    # Initialize components
    logger.info("Initializing calibration system...")

    db = DatabaseHandler(args.db_path)

    # Build cage map (assuming sequential cage->relay mapping)
    cage_map = {str(i): i for i in range(1, 16)}  # cages 1-15 → relays 1-15

    solenoid_controller = SolenoidController(master_relay_id=16, cage_map=cage_map)

    relay_id = args.relay if args.relay is not None else args.cage

    # Create calibrator
    calibrator = ValveCalibrator(
        solenoid_controller=solenoid_controller,
        database_handler=db,
        flow_sensor=None,  # Not used for primary measurement
    )

    # Run calibration
    try:
        result = await calibrator.calibrate_valve(
            cage_id=args.cage,
            relay_id=relay_id,
            num_pulses=args.num_pulses,
            pulse_width_ms=args.pulse_width_ms,
            measured_volume_ml=args.measured_ml,
            interactive=args.interactive,
            calibrated_by=args.trainer_id,
        )

        if result['saved']:
            logger.info("\n✓ Calibration complete and saved!")
            logger.info(f"  Cage {args.cage}: {result['volume_per_pulse_ml']:.6f} mL/pulse")
            return 0
        else:
            logger.info("\n⚠ Calibration complete but NOT saved")
            return 1

    except KeyboardInterrupt:
        logger.info("\n\nCalibration cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"\n\nCalibration failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
