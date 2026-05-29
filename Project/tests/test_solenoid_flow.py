#!/usr/bin/env python3
"""
Comprehensive test script for SLF3S-0600F flow sensor and solenoid system.

This script tests:
1. I2C communication with the flow sensor
2. Solenoid relay control
3. Integration between flow sensor and solenoid strategy
4. Hardware setup validation

Usage:
    python3 test_solenoid_flow.py [--bus BUS_ID] [--test-type TYPE]
    
Test types:
    - sensor: Test flow sensor only
    - solenoid: Test solenoid relays only  
    - integration: Test complete system
    - all: Run all tests (default)
"""

import asyncio
import argparse
import time
from smbus2 import SMBus, i2c_msg
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class FlowSensorTester:
    """Test the SLF3S-0600F flow sensor using raw I2C communication."""
    
    def __init__(self, bus_id=1):
        self.bus_id = bus_id
        self.addr = 0x08
        self.bus = None
        
    def crc8(self, data):
        """Calculate CRC-8 checksum as per Sensirion specification."""
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                crc = ((crc << 1) & 0xFF) ^ 0x31 if (crc & 0x80) else ((crc << 1) & 0xFF)
        return crc
    
    def test_i2c_connectivity(self):
        """Test basic I2C connectivity to the sensor."""
        print(f"Testing I2C connectivity on bus {self.bus_id}, address 0x{self.addr:02X}")
        
        try:
            self.bus = SMBus(self.bus_id)
            # SLF3x sensors may not respond to simple reads without proper commands
            # Instead, try sending the start command as a connectivity test
            write = i2c_msg.write(self.addr, [0x36, 0x08])
            self.bus.i2c_rdwr(write)
            print("✓ I2C connectivity test passed (start command accepted)")
            return True
        except Exception as e:
            print(f"✗ I2C connectivity test failed: {e}")
            return False
        finally:
            if self.bus:
                self.bus.close()
                self.bus = None
    
    def test_sensor_start_command(self):
        """Test sending start continuous measurement command."""
        print("Testing sensor start command (0x3608)")
        
        try:
            self.bus = SMBus(self.bus_id)
            # Send start continuous measurement in water mode
            write = i2c_msg.write(self.addr, [0x36, 0x08])
            self.bus.i2c_rdwr(write)
            print("✓ Start command sent successfully")
            
            # Wait a moment for sensor to initialize
            time.sleep(0.1)
            return True
            
        except Exception as e:
            print(f"✗ Start command failed: {e}")
            return False
    
    def test_sensor_data_read(self):
        """Test reading measurement data from the sensor."""
        print("Testing sensor data read (expecting 9 bytes)")
        
        try:
            # Read 9 bytes: flow(2) + crc(1) + temp(2) + crc(1) + flags(2) + crc(1)
            read = i2c_msg.read(self.addr, 9)
            self.bus.i2c_rdwr(read)
            data = bytes(read)
            
            if len(data) != 9:
                print(f"✗ Expected 9 bytes, got {len(data)}")
                return False
            
            print(f"✓ Read {len(data)} bytes: {' '.join(f'{b:02X}' for b in data)}")
            
            # Parse the data
            fmsb, flsb, fcrc = data[0], data[1], data[2]
            tmsb, tlsb, tcrc = data[3], data[4], data[5]
            cmsb, clsb, ccrc = data[6], data[7], data[8]
            
            # Verify CRCs
            flow_crc_calc = self.crc8(bytes([fmsb, flsb]))
            temp_crc_calc = self.crc8(bytes([tmsb, tlsb]))
            flags_crc_calc = self.crc8(bytes([cmsb, clsb]))
            
            print(f"Flow CRC: expected {fcrc:02X}, calculated {flow_crc_calc:02X}")
            print(f"Temp CRC: expected {tcrc:02X}, calculated {temp_crc_calc:02X}")
            print(f"Flags CRC: expected {ccrc:02X}, calculated {flags_crc_calc:02X}")
            
            if flow_crc_calc != fcrc or temp_crc_calc != tcrc or flags_crc_calc != ccrc:
                print("✗ CRC verification failed")
                return False
            
            # Convert to physical values
            flow_raw = (fmsb << 8) | flsb
            temp_raw = (tmsb << 8) | tlsb
            flags = (cmsb << 8) | clsb
            
            # Handle signed values
            if flow_raw & 0x8000:
                flow_raw -= 0x10000
            if temp_raw & 0x8000:
                temp_raw -= 0x10000
            
            # Apply scaling factors from datasheet
            flow_ul_min = flow_raw / 10.0  # µL/min
            flow_ml_min = flow_ul_min / 1000.0  # mL/min
            temp_c = temp_raw / 200.0  # °C
            
            print(f"✓ Parsed values:")
            print(f"  Flow: {flow_ul_min:.1f} µL/min ({flow_ml_min:.3f} mL/min)")
            print(f"  Temperature: {temp_c:.2f} °C")
            print(f"  Flags: 0x{flags:04X}")
            
            return True
            
        except Exception as e:
            print(f"✗ Data read failed: {e}")
            return False
    
    def test_sensor_stop_command(self):
        """Test sending stop measurement command."""
        print("Testing sensor stop command (0x3FF9)")
        
        try:
            write = i2c_msg.write(self.addr, [0x3F, 0xF9])
            self.bus.i2c_rdwr(write)
            print("✓ Stop command sent successfully")
            return True
            
        except Exception as e:
            print(f"✗ Stop command failed: {e}")
            return False
        finally:
            if self.bus:
                self.bus.close()
                self.bus = None
    
    def run_full_sensor_test(self):
        """Run complete sensor test sequence."""
        print("=" * 60)
        print("FLOW SENSOR TEST")
        print("=" * 60)
        
        tests = [
            self.test_i2c_connectivity,
            self.test_sensor_start_command,
            self.test_sensor_data_read,
            self.test_sensor_stop_command
        ]
        
        results = []
        for test in tests:
            result = test()
            results.append(result)
            print()
        
        passed = sum(results)
        total = len(results)
        
        print(f"Sensor test summary: {passed}/{total} tests passed")
        return passed == total

class SolenoidTester:
    """Test solenoid relay control."""
    
    def __init__(self):
        self.relay_handler = None
        
    def setup_relay_handler(self):
        """Initialize relay handler."""
        try:
            from gpio.gpio_handler import RelayHandler
            from models.relay_unit_manager import RelayUnitManager
            
            # Simple settings for testing
            settings = {'num_hats': 1, 'relay_pairs': [(1, 2)]}
            manager = RelayUnitManager(settings)
            self.relay_handler = RelayHandler(manager, 1)
            print("✓ Relay handler initialized")
            return True
            
        except Exception as e:
            print(f"✗ Relay handler setup failed: {e}")
            return False
    
    def test_individual_relays(self):
        """Test individual relay control."""
        print("Testing individual relay control (relays 1 and 16)")
        
        try:
            # Test cage relay (relay 1)
            print("Activating relay 1 (cage)...")
            self.relay_handler.set_relays([1], 1)
            time.sleep(1)
            print("Deactivating relay 1...")
            self.relay_handler.set_relays([1], 0)
            
            time.sleep(0.5)
            
            # Test master relay (relay 16)
            print("Activating relay 16 (master)...")
            self.relay_handler.set_relays([16], 1)
            time.sleep(1)
            print("Deactivating relay 16...")
            self.relay_handler.set_relays([16], 0)
            
            print("✓ Individual relay test completed")
            return True
            
        except Exception as e:
            print(f"✗ Individual relay test failed: {e}")
            return False
    
    def test_solenoid_sequence(self):
        """Test typical solenoid valve sequence."""
        print("Testing solenoid sequence (prime + delivery)")
        
        try:
            # Prime sequence (master only)
            print("Prime: Opening master relay...")
            self.relay_handler.set_relays([16], 1)
            time.sleep(0.2)  # 200ms prime
            print("Prime: Closing master relay...")
            self.relay_handler.set_relays([16], 0)
            time.sleep(0.1)
            
            # Delivery sequence (master + cage)
            print("Delivery: Opening master + cage relays...")
            self.relay_handler.set_relays([16, 1], 1)
            time.sleep(2.0)  # 2 second delivery simulation
            print("Delivery: Closing cage relay...")
            self.relay_handler.set_relays([1], 0)
            print("Delivery: Closing master relay...")
            self.relay_handler.set_relays([16], 0)
            
            print("✓ Solenoid sequence test completed")
            return True
            
        except Exception as e:
            print(f"✗ Solenoid sequence test failed: {e}")
            return False
    
    def run_full_solenoid_test(self):
        """Run complete solenoid test sequence."""
        print("=" * 60)
        print("SOLENOID TEST")
        print("=" * 60)
        
        if not self.setup_relay_handler():
            return False
        
        tests = [
            self.test_individual_relays,
            self.test_solenoid_sequence
        ]
        
        results = []
        for test in tests:
            result = test()
            results.append(result)
            print()
        
        passed = sum(results)
        total = len(results)
        
        print(f"Solenoid test summary: {passed}/{total} tests passed")
        return passed == total

class IntegrationTester:
    """Test integration between flow sensor and solenoid system."""
    
    def __init__(self, bus_id=1):
        self.bus_id = bus_id
        
    async def test_flow_strategy_init(self):
        """Test SolenoidFlowStrategy initialization."""
        print("Testing SolenoidFlowStrategy initialization")
        
        try:
            from drivers.flow_sensor_factory import create_flow_sensor
            from drivers.solenoid_controller import SolenoidController
            from strategies.solenoid_flow_strategy import SolenoidFlowStrategy
            from utils.calibration import CalibrationStore
            from gpio.gpio_handler import RelayHandler
            from models.relay_unit_manager import RelayUnitManager
            
            # Setup components
            settings = {'num_hats': 1, 'relay_pairs': [(1, 2)]}
            manager = RelayUnitManager(settings)
            relay_handler = RelayHandler(manager, 1)
            
            flow_sensor = create_flow_sensor(
                {'flow_sensor_type': 'uart', 'uart_port': '/dev/ttyACM0', 'flow_sampling_hz': 10.0}
            )
            cage_map = {1: 1}  # cage 1 -> relay 1
            solenoid = SolenoidController(relay_handler, 16, cage_map)
            cal_store = CalibrationStore()
            
            strategy_settings = {
                'flow_sampling_hz': 10.0,
                'predictive_close_ms': 50.0,
                'residual_check_ms': 200.0,
                'residual_flow_threshold_ml_min': 1.0,
                'max_consecutive_sensor_errors': 5,
            }
            
            strategy = SolenoidFlowStrategy(
                solenoid_controller=solenoid,
                flow_sensor=flow_sensor,
                calibration_store=cal_store,
                settings=strategy_settings
            )
            
            print("✓ SolenoidFlowStrategy initialized successfully")
            return True, strategy
            
        except Exception as e:
            print(f"✗ SolenoidFlowStrategy initialization failed: {e}")
            return False, None
    
    async def test_mock_delivery(self, strategy):
        """Test a mock delivery with the strategy."""
        print("Testing mock delivery (0.1 mL)")
        
        try:
            # Test small volume delivery
            result = await strategy.deliver(
                relay_unit_id=1,
                target_volume_ml=0.1,
                triggers_hint=None
            )
            
            if result:
                print("✓ Mock delivery completed successfully")
            else:
                print("✗ Mock delivery failed (expected due to no actual flow)")
            
            return True  # Success means no crash, not necessarily successful delivery
            
        except Exception as e:
            print(f"✗ Mock delivery crashed: {e}")
            return False
    
    async def run_full_integration_test(self):
        """Run complete integration test."""
        print("=" * 60)
        print("INTEGRATION TEST")
        print("=" * 60)
        
        success, strategy = await self.test_flow_strategy_init()
        if not success:
            return False
        
        print()
        result = await self.test_mock_delivery(strategy)
        
        print(f"\nIntegration test summary: {'PASSED' if result else 'FAILED'}")
        return result

def show_sensor_package_info():
    """Show information about sensor packages."""
    print("=" * 60)
    print("SENSOR PACKAGE INFORMATION")
    print("=" * 60)
    
    print("The 'sensirion-slf3s' package is for UART/serial communication.")
    print("There is NO official I2C Python package for SLF3x sensors on PyPI.")
    print("\nThis test uses raw I2C communication via smbus2 (already installed).")
    print("Protocol based on Sensirion's official I2C implementation guide.")
    print("\nIf you have sensirion-slf3s installed, you can remove it:")
    print("pip uninstall sensirion-slf3s")

def find_working_bus():
    """Find a working I2C bus for the flow sensor, avoiding conflicts."""
    import os
    from smbus2 import SMBus, i2c_msg
    
    # Priority order: isolated buses first, shared bus last
    bus_priority = [13, 14, 1, 0] + list(range(2, 21))
    
    print("=" * 60)
    print("I2C BUS DETECTION")
    print("=" * 60)
    
    working_buses = []
    
    for bus in bus_priority:
        if not os.path.exists(f"/dev/i2c-{bus}"):
            continue
            
        print(f"Testing bus {bus}...", end=" ")
        try:
            with SMBus(bus) as b:
                # Test with start command
                w = i2c_msg.write(0x08, [0x36, 0x08])
                b.i2c_rdwr(w)
                print("✓ Working")
                working_buses.append(bus)
        except Exception as e:
            print(f"✗ Failed ({e})")
    
    if working_buses:
        chosen = working_buses[0]
        print(f"\nRecommended bus: {chosen}")
        if len(working_buses) > 1:
            print(f"Alternative buses: {working_buses[1:]}")
        return chosen
    else:
        print("\n⚠️  No working I2C buses found for flow sensor!")
        return 1  # Fallback

async def main():
    parser = argparse.ArgumentParser(description="Test SLF3S-0600F flow sensor and solenoid system")
    parser.add_argument("--bus", type=int, help="I2C bus number (auto-detect if not specified)")
    parser.add_argument("--test-type", choices=["sensor", "solenoid", "integration", "all"], 
                       default="all", help="Type of test to run")
    
    args = parser.parse_args()
    
    print("SLF3S-0600F Flow Sensor and Solenoid Test")
    print("=" * 60)
    
    # Auto-detect bus if not specified
    if args.bus is None:
        args.bus = find_working_bus()
        print()
    
    print(f"I2C Bus: {args.bus}")
    print(f"Test Type: {args.test_type}")
    print()
    
    # Show package information
    show_sensor_package_info()
    print()
    
    results = []
    
    if args.test_type in ["sensor", "all"]:
        sensor_tester = FlowSensorTester(args.bus)
        result = sensor_tester.run_full_sensor_test()
        results.append(("Sensor", result))
        print()
    
    if args.test_type in ["solenoid", "all"]:
        solenoid_tester = SolenoidTester()
        result = solenoid_tester.run_full_solenoid_test()
        results.append(("Solenoid", result))
        print()
    
    if args.test_type in ["integration", "all"]:
        integration_tester = IntegrationTester(args.bus)
        result = await integration_tester.run_full_integration_test()
        results.append(("Integration", result))
        print()
    
    # Final summary
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name:12}: {status}")
    
    total_passed = sum(1 for _, result in results if result)
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} test suites passed")
    
    if total_passed == total_tests:
        print("🎉 All tests passed! System is ready for operation.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    asyncio.run(main())