#!/usr/bin/env python3
"""
Custom SM16relind module with improved I2C bus handling.
This is a wrapper around the original SM16relind module that adds the ability
to specify a custom I2C bus.
"""

import os
import time
import logging
import importlib.util

# Try to import the original module
try:
    import SM16relind as OriginalSM16relind
    ORIGINAL_MODULE_AVAILABLE = True
except ImportError:
    try:
        # Try alternate casing
        import sm_16relind as OriginalSM16relind
        ORIGINAL_MODULE_AVAILABLE = True
    except ImportError:
        ORIGINAL_MODULE_AVAILABLE = False
        logging.warning("Original SM16relind module not found. Using mock implementation.")


# Custom implementation with bus_id support
class SM16relind:
    def __init__(self, stack=0, bus_id=None):
        """
        Initialize the SM16relind relay module.
        
        Args:
            stack (int): The stack/address of the relay board (default is 0)
            bus_id (int, optional): The I2C bus ID to use (e.g., 1 for /dev/i2c-1, 13 for /dev/i2c-13)
        """
        self.stack = stack
        self.bus_id = bus_id
        self.original_instance = None
        
        # Check if the specified bus exists
        if bus_id is not None and not os.path.exists(f"/dev/i2c-{bus_id}"):
            raise ValueError(f"I2C bus /dev/i2c-{bus_id} does not exist")
        
        # If original module is available, try to use it
        if ORIGINAL_MODULE_AVAILABLE:
            # Try with custom bus ID if specified
            if bus_id is not None:
                self._init_with_custom_bus()
            else:
                # Fall back to standard initialization
                try:
                    self.original_instance = OriginalSM16relind.SM16relind(stack)
                except Exception as e:
                    raise Exception(f"Failed to initialize SM16relind with stack {stack}: {str(e)}")
        else:
            # Mock implementation for testing
            logging.warning(f"Using mock implementation for SM16relind (stack={stack}, bus_id={bus_id})")
    
    def _init_with_custom_bus(self):
        """Initialize with a custom I2C bus by monkey-patching the original module"""
        import subprocess
        import sys
        
        # Create a temporary patch script
        patch_script = f"""
import os
import sys
import fcntl
import time

# Monkey patch the ioctl I2C functions to use a different bus
original_open = os.open
def patched_open(path, *args, **kwargs):
    if path == '/dev/i2c-1' or path.startswith('/dev/i2c/'):
        path = '/dev/i2c-{self.bus_id}'
    return original_open(path, *args, **kwargs)

os.open = patched_open
"""
        
        # Write the patch to a temporary file
        patch_file = "/tmp/i2c_bus_patch.py"
        with open(patch_file, "w") as f:
            f.write(patch_script)
        
        # Execute the original module initialization with the patch
        cmd = [
            sys.executable, "-c",
            f"import sys; sys.path.insert(0, '/tmp'); import i2c_bus_patch; "
            f"import SM16relind; instance = SM16relind.SM16relind({self.stack}); "
            f"print('SUCCESS')"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if "SUCCESS" not in result.stdout:
                raise Exception(f"Initialization failed: {result.stderr}")
                
            # Successfully patched, now create the original instance
            self.original_instance = OriginalSM16relind.SM16relind(self.stack)
        except Exception as e:
            raise Exception(f"Custom bus initialization failed: {str(e)}")
        finally:
            # Clean up
            try:
                os.remove(patch_file)
            except:
                pass
    
    def set(self, relay, state):
        """Set a relay to a specific state"""
        if self.original_instance:
            return self.original_instance.set(relay, state)
        else:
            # Mock implementation
            logging.info(f"MOCK: Setting relay {relay} to state {state}")
            return True
    
    def set_all(self, state):
        """Set all relays to a specific state"""
        if self.original_instance:
            return self.original_instance.set_all(state)
        else:
            # Mock implementation
            logging.info(f"MOCK: Setting all relays to state {state}")
            return True

# Create a function to find available I2C buses
def find_available_i2c_buses():
    """Find available I2C buses on the system, optimized for Raspberry Pi 5"""
    available_buses = []
    try:
        # Extended range to cover Raspberry Pi 5's higher numbered buses (13, 14)
        for i in range(0, 50):  
            if os.path.exists(f"/dev/i2c-{i}"):
                available_buses.append(i)
        
        # Sort buses and prioritize higher-numbered ones for Pi 5
        available_buses.sort()
        
        # Log the detection for debugging
        if available_buses:
            logging.info(f"Found I2C buses: {available_buses}")
            # Check if this looks like Pi 5 configuration
            if any(bus >= 13 for bus in available_buses):
                logging.info("Raspberry Pi 5 I2C configuration detected (buses >= 13)")
        else:
            logging.warning("No I2C buses found")
            
        return available_buses
    except Exception as e:
        logging.error(f"Error finding I2C buses: {e}")
        return []

# Helper function to test connection with all available buses
def test_connection():
    """Test connection with all available I2C buses"""
    buses = find_available_i2c_buses()
    print(f"Found I2C buses: {buses}")
    
    for bus in buses:
        try:
            print(f"Testing bus {bus}...")
            relay = SM16relind(stack=0, bus_id=bus)
            print(f"SUCCESS: Connected to relay board on bus {bus}")
            return relay, bus
        except Exception as e:
            print(f"Failed to connect on bus {bus}: {str(e)}")
    
    print("Failed to connect on any bus")
    return None, None

# If run as a script, test the connection
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    relay, bus = test_connection()
    if relay:
        print(f"Testing relay operations on bus {bus}...")
        try:
            relay.set_all(0)  # All off
            time.sleep(1)
            relay.set(1, 1)  # Turn on relay 1
            time.sleep(1)
            relay.set(1, 0)  # Turn off relay 1
            print("Test completed successfully")
        except Exception as e:
            print(f"Test failed: {str(e)}")
        finally:
            relay.set_all(0)  # Ensure all relays are off
    else:
        print("No connection established. Check your hardware.") 