#!/usr/bin/env python3
"""
I2C Relay Test Script

This script tests I2C bus detection and relay control for the Rodent Refreshment Regulator.
It's designed to help troubleshoot I2C connection issues, especially on systems with 
non-standard I2C bus numbering.
"""

import os
import sys
import time
import logging
import subprocess

def check_i2c_setup():
    """Check the I2C configuration on the system"""
    print("Checking I2C configuration...")
    
    # Check I2C kernel modules
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True)
        if 'i2c_bcm' in result.stdout or 'i2c_dev' in result.stdout:
            print("✓ I2C kernel modules loaded")
        else:
            print("✗ I2C kernel modules not detected")
    except Exception as e:
        print(f"Error checking kernel modules: {e}")
    
    # Check I2C devices
    try:
        i2c_devices = []
        for i in range(0, 20):
            if os.path.exists(f"/dev/i2c-{i}"):
                i2c_devices.append(i)
        
        if i2c_devices:
            print(f"✓ I2C devices found: {i2c_devices}")
        else:
            print("✗ No I2C devices found")
    except Exception as e:
        print(f"Error checking I2C devices: {e}")
    
    # Try running i2cdetect for each found device
    for bus_id in i2c_devices:
        try:
            print(f"\nScanning I2C bus {bus_id} with i2cdetect:")
            result = subprocess.run(['i2cdetect', '-y', str(bus_id)], 
                                   capture_output=True, text=True)
            print(result.stdout)
            
            # Check if any devices were detected (non-empty cells)
            if '--' not in result.stdout or any(str(x) for x in range(10) if str(x) in result.stdout):
                print(f"✓ Devices detected on bus {bus_id}")
        except Exception as e:
            print(f"Error running i2cdetect on bus {bus_id}: {e}")
    
    return i2c_devices

def test_custom_sm16relind():
    """Test the custom SM16relind module"""
    print("\nTesting custom SM16relind module...")
    
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'gpio'))
        from custom_SM16relind import SM16relind, test_connection
        
        # Run the auto-detection and connection test
        print("\nRunning automatic connection test...")
        relay, bus = test_connection()
        
        if relay:
            print(f"\n✓ Successfully connected to relay on bus {bus}")
            return True, bus
        else:
            print("\n✗ Automatic connection test failed")
            return False, None
    except Exception as e:
        print(f"\n✗ Error with custom module: {e}")
        return False, None

def test_relay_operation(relay, bus_id):
    """Test basic relay operations"""
    print(f"\nTesting relay operations on bus {bus_id}...")
    
    try:
        # First turn all relays off
        print("Setting all relays off")
        relay.set_all(0)
        time.sleep(1)
        
        # Test individual relays
        for relay_num in range(1, 5):  # Test first 4 relays
            print(f"Testing relay {relay_num}...")
            relay.set(relay_num, 1)  # Turn on
            time.sleep(0.5)
            relay.set(relay_num, 0)  # Turn off
            time.sleep(0.5)
        
        print("\n✓ Relay operation test completed successfully")
        return True
    except Exception as e:
        print(f"\n✗ Relay operation test failed: {e}")
        return False

def manual_test(i2c_buses):
    """Manually test each I2C bus"""
    print("\nStarting manual bus testing...")
    
    success = False
    
    for bus_id in i2c_buses:
        print(f"\nTesting bus {bus_id}...")
        
        try:
            # Try to import our custom module
            sys.path.append(os.path.join(os.path.dirname(__file__), 'gpio'))
            from custom_SM16relind import SM16relind
            
            # Try to initialize with this bus
            print(f"Initializing SM16relind with bus_id={bus_id}...")
            relay = SM16relind(stack=0, bus_id=bus_id)
            
            # If we get here, the initialization succeeded
            print(f"✓ Successfully connected to relay on bus {bus_id}")
            
            # Test relay operations
            if test_relay_operation(relay, bus_id):
                success = True
                break
            
        except Exception as e:
            print(f"✗ Failed to connect on bus {bus_id}: {str(e)}")
    
    if not success:
        print("\n✗ Manual testing failed on all buses")
    
    return success

def main():
    """Main function"""
    print("=" * 60)
    print("Rodent Refreshment Regulator I2C Relay Test")
    print("=" * 60)
    
    # Check I2C configuration
    i2c_buses = check_i2c_setup()
    
    if not i2c_buses:
        print("\nNo I2C buses found. Please check your I2C configuration:")
        print("1. Run 'sudo raspi-config' and enable I2C interface")
        print("2. Run 'sudo modprobe i2c-dev'")
        print("3. Run 'sudo apt-get install i2c-tools'")
        return
    
    # Try automatic detection
    success, bus = test_custom_sm16relind()
    
    if not success:
        # Fall back to manual testing
        print("\nFalling back to manual testing...")
        success = manual_test(i2c_buses)
    
    # Provide recommendations
    if success:
        print("\n✅ TEST PASSED: Found working I2C configuration")
        print("\nTo fix your application permanently, update these files:")
        print("1. Edit the SM16relind.py file to use the correct I2C bus")
        print("   OR use the custom_SM16relind.py module which auto-detects I2C buses")
        print(f"2. If modifying SM16relind.py, look for '/dev/i2c-1' and change to '/dev/i2c-{bus}'")
    else:
        print("\n❌ TEST FAILED: Could not establish working I2C configuration")
        print("\nTroubleshooting steps:")
        print("1. Check physical connections to the relay hat")
        print("2. Verify the hat is powered properly")
        print("3. Run 'sudo raspi-config' and ensure I2C interface is enabled")
        print("4. Reboot the Raspberry Pi")
        print("5. Check if you need to load additional kernel modules")

if __name__ == "__main__":
    main() 