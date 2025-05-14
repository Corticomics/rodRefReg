#!/usr/bin/env python3
"""
Standalone utility for testing IR sensors.

This script provides a simple command-line interface for testing IR sensors
without requiring the full RRR application. It is intended to be used during
hardware setup to verify that sensors are working correctly.
"""

import logging
import time
import sys
import os
import argparse
import signal

# Add the project root to the path to allow imports from ir_module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from ir_module.hardware.sensor_mapper import SensorManager
from ir_module.hardware.ir_sensor import IRSensor
from ir_module.config import print_config_status, get_hardware_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_specific_pin(gpio_pin):
    """
    Test a specific GPIO pin for IR sensor functionality.
    
    Args:
        gpio_pin (int): GPIO pin number to test.
    """
    print(f"\nTesting IR sensor on GPIO pin {gpio_pin}")
    print("Press Ctrl+C to exit")
    
    # Create sensor with simple callback
    def beam_break_callback(relay_unit_id, timestamp):
        print(f"[{time.strftime('%H:%M:%S')}] Beam break detected! (GPIO pin {gpio_pin})")
    
    # Create sensor (we use 999 as a dummy relay unit ID)
    sensor = IRSensor(
        gpio_pin=gpio_pin,
        relay_unit_id=999,
        callback=beam_break_callback
    )
    
    try:
        # Keep running until interrupted
        while True:
            status = sensor.get_status()
            sim_mode = "SIMULATION" if status["simulation_mode"] else "HARDWARE"
            print(f"\rMode: {sim_mode} | Initialized: {status['is_initialized']} | Beam broken: {status['is_beam_broken']}   ", end="")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted. Cleaning up...")
    finally:
        sensor.cleanup()

def test_configured_sensors():
    """Test all sensors configured in the config file."""
    print("\nTesting all configured IR sensors")
    print("Press Ctrl+C to exit")
    
    # Create sensor manager
    def beam_break_callback(relay_unit_id, timestamp):
        print(f"[{time.strftime('%H:%M:%S')}] Beam break detected on relay unit {relay_unit_id}")
    
    sensor_manager = SensorManager(callback=beam_break_callback)
    
    try:
        # Show sensor status
        status = sensor_manager.get_sensor_status()
        print("\nSensor Status:")
        for unit_id, sensor_status in status.items():
            sim_mode = "SIMULATION" if sensor_status["simulation_mode"] else "HARDWARE"
            print(f"Relay Unit {unit_id} (GPIO {sensor_status['gpio_pin']}): "
                  f"{sim_mode} mode | Initialized: {sensor_status['is_initialized']}")
        
        print("\nWaiting for beam breaks (real or simulated)...")
        
        # Start a simulation in the background to show it works
        if any(s["simulation_mode"] for s in status.values()):
            print("Simulated beam breaks will occur every few seconds.")
            import threading
            import random
            
            def simulate_breaks():
                while True:
                    time.sleep(random.uniform(2, 5))
                    unit_id = random.choice(list(sensor_manager.sensors.keys()))
                    sensor_manager.simulate_beam_break(unit_id)
            
            sim_thread = threading.Thread(target=simulate_breaks)
            sim_thread.daemon = True
            sim_thread.start()
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted. Cleaning up...")
    finally:
        sensor_manager.cleanup()

def main():
    """Main entry point for the sensor tester."""
    parser = argparse.ArgumentParser(description="IR Sensor Tester")
    
    # Add arguments
    parser.add_argument("--pin", type=int, help="Specific GPIO pin to test")
    parser.add_argument("--list", action="store_true", help="List configured GPIO pins from config")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print configuration
    print("\nIR Sensor Tester")
    print("===============")
    print_config_status()
    
    # List configured pins
    if args.list:
        sensor_map = get_hardware_config("DEFAULT_SENSOR_MAP", {})
        print("\nConfigured GPIO Pins:")
        for relay_id, gpio_pin in sensor_map.items():
            print(f"Relay Unit {relay_id}: GPIO {gpio_pin}")
        return
    
    # Test specific pin if provided
    if args.pin is not None:
        test_specific_pin(args.pin)
    else:
        # Otherwise test all configured sensors
        test_configured_sensors()

if __name__ == "__main__":
    main() 