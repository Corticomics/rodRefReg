#!/usr/bin/env python3
"""
Simple test script for solenoid-flow sensor integration.

This script opens the master solenoid and displays real-time flow sensor data
to verify the hardware integration is working correctly.

Usage:
    python test_solenoid_flow.py [--bus BUS_ID] [--master-relay RELAY_ID] [--duration SECONDS]
"""

import asyncio
import argparse
import sys
import time
from datetime import datetime
from typing import Optional

# Add project root to Python path for imports
sys.path.insert(0, '.')

from drivers.flow_sensor import SLF3S0600FDriver, FlowSample
from drivers.solenoid_controller import SolenoidController
from gpio.gpio_handler import RelayHandler
# Pump-era RelayUnitManager is not needed for solenoid tests


class SolenoidFlowTester:
    """Simple test class for solenoid-flow sensor integration."""
    
    def __init__(
        self,
        i2c_bus: int = 1,
        master_relay_id: int = 16,
        sampling_hz: float = 10.0,
        num_hats: int = 1
    ):
        """Initialize the test system.
        
        Args:
            i2c_bus: I2C bus number for flow sensor (default: 1)
            master_relay_id: Relay ID for master solenoid (default: 16)
            sampling_hz: Flow sensor sampling rate (default: 10 Hz for testing)
            num_hats: Number of relay HATs (default: 1)
        """
        self.i2c_bus = i2c_bus
        self.master_relay_id = master_relay_id
        self.sampling_hz = sampling_hz
        
        print(f"[Init] Setting up solenoid-flow test system...")
        print(f"[Init] I2C Bus: {i2c_bus}, Master Relay: {master_relay_id}, Sampling: {sampling_hz} Hz")
        
        # Initialize relay system
        try:
            # Initialize RelayHandler directly for solenoid control; we only need HAT access
            self.relay_handler = RelayHandler([], num_hats=num_hats)
            print("[Init] ✓ Relay system initialized")
        except Exception as e:
            print(f"[Init] ✗ Failed to initialize relay system: {e}")
            raise
        
        # Initialize flow sensor
        try:
            self.flow_sensor = SLF3S0600FDriver(
                i2c_bus=i2c_bus,
                sampling_hz=sampling_hz
            )
            print(f"[Init] ✓ Flow sensor initialized (backend: {self.flow_sensor.backend_mode()})")
        except Exception as e:
            print(f"[Init] ✗ Failed to initialize flow sensor: {e}")
            raise
        
        # Initialize solenoid controller
        try:
            # Create a minimal cage map for testing (just one cage for now)
            cage_map = {1: 1}  # Cage 1 -> Relay 1 (example)
            self.solenoid_controller = SolenoidController(
                relay_handler=self.relay_handler,
                master_relay_id=master_relay_id,
                cage_to_relay_id=cage_map
            )
            print("[Init] ✓ Solenoid controller initialized")
        except Exception as e:
            print(f"[Init] ✗ Failed to initialize solenoid controller: {e}")
            raise
        
        self._running = False
        self._total_volume_ml = 0.0
        self._sample_count = 0
        self._start_time = None

    def _print_header(self):
        """Print the data table header."""
        print("\n" + "="*80)
        print("SOLENOID-FLOW SENSOR TEST")
        print("="*80)
        print(f"{'Time':<12} {'Flow (mL/min)':<15} {'Temp (°C)':<12} {'Volume (mL)':<15} {'Notes':<20}")
        print("-"*80)

    def _print_sample(self, sample: FlowSample, notes: str = ""):
        """Print a flow sensor sample in tabular format."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        self._sample_count += 1
        
        # Simple volume integration (rectangular rule for simplicity)
        if self._sample_count > 1:
            dt_min = (1.0 / self.sampling_hz) / 60.0  # Convert sampling period to minutes
            volume_increment = sample.flow_ml_min * dt_min
            self._total_volume_ml += volume_increment
        
        print(f"{elapsed:>8.1f}s    {sample.flow_ml_min:>8.2f}        "
              f"{sample.temperature_c:>6.1f}      {self._total_volume_ml:>8.3f}        {notes}")

    async def test_flow_sensor_only(self, duration: float = 10.0):
        """Test flow sensor readings without opening solenoids.
        
        Args:
            duration: Test duration in seconds
        """
        print(f"\n[Test] Testing flow sensor for {duration} seconds (solenoids closed)...")
        
        try:
            self.flow_sensor.start()
            self._print_header()
            self._start_time = time.time()
            self._running = True
            
            async for sample in self.flow_sensor.read():
                if not self._running:
                    break
                    
                elapsed = time.time() - self._start_time
                if elapsed >= duration:
                    break
                    
                self._print_sample(sample, "Baseline")
                
        except KeyboardInterrupt:
            print("\n[Test] Test interrupted by user")
        except Exception as e:
            print(f"\n[Test] ✗ Flow sensor test failed: {e}")
        finally:
            self.flow_sensor.stop()
            print(f"\n[Test] Flow sensor test completed. Baseline volume: {self._total_volume_ml:.3f} mL")

    async def test_master_solenoid_flow(self, duration: float = 30.0):
        """Test master solenoid with flow sensor readings.
        
        Args:
            duration: Test duration in seconds
        """
        print(f"\n[Test] Testing master solenoid + flow sensor for {duration} seconds...")
        
        try:
            # Start flow sensor
            self.flow_sensor.start()
            await asyncio.sleep(0.5)  # Let sensor stabilize
            
            # Reset counters
            self._total_volume_ml = 0.0
            self._sample_count = 0
            
            self._print_header()
            self._start_time = time.time()
            
            # Open master solenoid
            print("[Solenoid] Opening master solenoid...")
            success = self.solenoid_controller.open_master()
            if not success:
                print("[Solenoid] ✗ Failed to open master solenoid")
                return
            
            print("[Solenoid] ✓ Master solenoid opened")
            
            # Read flow data
            self._running = True
            async for sample in self.flow_sensor.read():
                if not self._running:
                    break
                    
                elapsed = time.time() - self._start_time
                if elapsed >= duration:
                    break
                    
                # Determine status based on flow
                if sample.flow_ml_min > 5.0:
                    status = "FLOWING"
                elif sample.flow_ml_min > 1.0:
                    status = "Low flow"
                else:
                    status = "No flow"
                
                self._print_sample(sample, status)
                
        except KeyboardInterrupt:
            print("\n[Test] Test interrupted by user")
        except Exception as e:
            print(f"\n[Test] ✗ Master solenoid test failed: {e}")
        finally:
            # Always close the solenoid
            try:
                print("\n[Solenoid] Closing master solenoid...")
                self.solenoid_controller.close_master()
                print("[Solenoid] ✓ Master solenoid closed")
            except Exception as e:
                print(f"[Solenoid] ✗ Error closing master solenoid: {e}")
            
            self.flow_sensor.stop()
            self._running = False
            
            print(f"\n[Test] Master solenoid test completed. Total volume: {self._total_volume_ml:.3f} mL")

    async def test_cage_solenoid_flow(self, cage_id: int = 1, duration: float = 15.0):
        """Test cage solenoid with master + flow sensor readings.
        
        Args:
            cage_id: Cage ID to test (default: 1)
            duration: Test duration in seconds
        """
        print(f"\n[Test] Testing cage {cage_id} solenoid + master + flow sensor for {duration} seconds...")
        
        try:
            # Start flow sensor
            self.flow_sensor.start()
            await asyncio.sleep(0.5)  # Let sensor stabilize
            
            # Reset counters
            self._total_volume_ml = 0.0
            self._sample_count = 0
            
            self._print_header()
            self._start_time = time.time()
            
            # Open master solenoid first
            print("[Solenoid] Opening master solenoid...")
            success = self.solenoid_controller.open_master()
            if not success:
                print("[Solenoid] ✗ Failed to open master solenoid")
                return
            
            await asyncio.sleep(0.5)  # Brief delay
            
            # Open cage solenoid
            print(f"[Solenoid] Opening cage {cage_id} solenoid...")
            success = self.solenoid_controller.open_cage(cage_id)
            if not success:
                print(f"[Solenoid] ✗ Failed to open cage {cage_id} solenoid")
                return
            
            print(f"[Solenoid] ✓ Both master and cage {cage_id} solenoids opened")
            
            # Read flow data
            self._running = True
            async for sample in self.flow_sensor.read():
                if not self._running:
                    break
                    
                elapsed = time.time() - self._start_time
                if elapsed >= duration:
                    break
                    
                # Determine status based on flow
                if sample.flow_ml_min > 10.0:
                    status = "HIGH FLOW"
                elif sample.flow_ml_min > 5.0:
                    status = "Good flow"
                elif sample.flow_ml_min > 1.0:
                    status = "Low flow"
                else:
                    status = "No flow"
                
                self._print_sample(sample, status)
                
        except KeyboardInterrupt:
            print("\n[Test] Test interrupted by user")
        except Exception as e:
            print(f"\n[Test] ✗ Cage solenoid test failed: {e}")
        finally:
            # Always close both solenoids
            try:
                print(f"\n[Solenoid] Closing cage {cage_id} solenoid...")
                self.solenoid_controller.close_cage(cage_id)
                print("[Solenoid] Closing master solenoid...")
                self.solenoid_controller.close_master()
                print("[Solenoid] ✓ All solenoids closed")
            except Exception as e:
                print(f"[Solenoid] ✗ Error closing solenoids: {e}")
            
            self.flow_sensor.stop()
            self._running = False
            
            print(f"\n[Test] Cage solenoid test completed. Total volume: {self._total_volume_ml:.3f} mL")

    def cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'flow_sensor'):
                self.flow_sensor.close()
            if hasattr(self, 'solenoid_controller'):
                # Ensure all solenoids are closed
                self.solenoid_controller.close_master()
                if hasattr(self.solenoid_controller, 'close_all_cages'):
                    self.solenoid_controller.close_all_cages()
            print("[Cleanup] ✓ Resources cleaned up")
        except Exception as e:
            print(f"[Cleanup] ⚠ Error during cleanup: {e}")


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test solenoid-flow sensor integration")
    parser.add_argument('--bus', type=int, default=1, help='I2C bus number (default: 1)')
    parser.add_argument('--master-relay', type=int, default=16, help='Master relay ID (default: 16)')
    parser.add_argument('--duration', type=float, default=30.0, help='Test duration in seconds (default: 30)')
    parser.add_argument('--test-mode', choices=['sensor', 'master', 'cage', 'all'], default='all',
                       help='Test mode: sensor only, master solenoid, cage solenoid, or all (default: all)')
    parser.add_argument('--cage-id', type=int, default=1, help='Cage ID for cage test (default: 1)')
    parser.add_argument('--sampling-hz', type=float, default=10.0, help='Flow sensor sampling rate (default: 10 Hz)')
    
    args = parser.parse_args()
    
    print("SOLENOID-FLOW SENSOR INTEGRATION TEST")
    print("=" * 50)
    print(f"I2C Bus: {args.bus}")
    print(f"Master Relay: {args.master_relay}")
    print(f"Test Duration: {args.duration}s")
    print(f"Test Mode: {args.test_mode}")
    print(f"Sampling Rate: {args.sampling_hz} Hz")
    print("=" * 50)
    
    tester = None
    
    try:
        # Initialize tester
        tester = SolenoidFlowTester(
            i2c_bus=args.bus,
            master_relay_id=args.master_relay,
            sampling_hz=args.sampling_hz
        )
        
        if args.test_mode in ['sensor', 'all']:
            await tester.test_flow_sensor_only(duration=10.0)
            if args.test_mode == 'all':
                await asyncio.sleep(2.0)  # Brief pause between tests
        
        if args.test_mode in ['master', 'all']:
            await tester.test_master_solenoid_flow(duration=args.duration)
            if args.test_mode == 'all':
                await asyncio.sleep(2.0)  # Brief pause between tests
        
        if args.test_mode in ['cage', 'all']:
            await tester.test_cage_solenoid_flow(cage_id=args.cage_id, duration=args.duration)
        
        print("\n" + "=" * 80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Verify flow readings make sense for your system")
        print("2. Check that solenoids open/close properly")
        print("3. Validate volume measurements against known volumes")
        print("4. Run calibration procedures if needed")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if tester:
            tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
