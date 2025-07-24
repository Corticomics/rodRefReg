#!/usr/bin/env python3

import os
import time
import sys
import subprocess

def check_i2c_setup():
    print("Checking I2C configuration...")
    
    # Check if I2C is enabled in kernel modules
    try:
        with open('/etc/modules', 'r') as f:
            modules = f.read()
            if 'i2c-dev' not in modules:
                print("Warning: i2c-dev not found in /etc/modules")
    except Exception as e:
        print(f"Error checking modules: {e}")

    # Run i2cdetect
    try:
        result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
        print("\nI2C Device Map:")
        print(result.stdout)
    except Exception as e:
        print(f"Error running i2cdetect: {e}")

def test_relay_connection():
    print("\nTesting relay connection...")
    
    try:
        # First try the company's example exactly as written
        print("Attempting connection with SM16relind...")
        import SM16relind
        rel = SM16relind.SM16relind(0)
        return rel, "SM16relind"
    except Exception as e:
        print(f"Standard connection failed: {str(e)}")
        
        try:
            # Try alternate package name
            print("\nAttempting connection with sm_16relind...")
            import sm_16relind
            rel = sm_16relind.SM16relind(0)
            return rel, "sm_16relind"
        except Exception as e:
            print(f"Alternate connection failed: {str(e)}")
    
    return None, None

if __name__ == "__main__":
    # Check permissions
    if os.geteuid() != 0:
        print("Warning: Script not running as root. Some operations might fail.")
        print("Consider running with: sudo python3 test_relay_diagnostic.py")
    
    # Check I2C setup
    check_i2c_setup()
    
    # Test connection
    rel, package = test_relay_connection()
    
    if rel:
        print(f"\nSuccessfully connected using {package}")
        print("Running basic relay test...")
        try:
            # Test single relay
            rel.set(1, 1)
            time.sleep(1)
            rel.set(1, 0)
            print("Basic test completed!")
        except Exception as e:
            print(f"Error during basic test: {str(e)}")
        finally:
            try:
                rel.set_all(0)
            except:
                pass
    else:
        print("\nFailed to connect to relay hat")
        print("\nTroubleshooting steps:")
        print("1. Verify physical connections")
        print("2. Run: sudo raspi-config")
        print("   -> Interface Options -> I2C -> Enable")
        print("3. Run: sudo apt-get install i2c-tools")
        print("4. Run: sudo modprobe i2c-dev") 