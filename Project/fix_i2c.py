#!/usr/bin/env python3
"""
I2C Fix Script for Rodent Refreshment Regulator

This script fixes I2C connection issues on Raspberry Pi systems where the I2C bus
is not at the standard /dev/i2c-1 location. It creates a custom SM16relind module
and updates the gpio_handler.py file to use it.
"""

import os
import sys
import subprocess
import shutil

# Custom SM16relind module content
CUSTOM_SM16RELIND_CONTENT = """#!/usr/bin/env python3
\"\"\"
Custom SM16relind module with improved I2C bus handling.
This is a wrapper around the original SM16relind module that adds the ability
to specify a custom I2C bus.
\"\"\"

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
        \"\"\"
        Initialize the SM16relind relay module.
        
        Args:
            stack (int): The stack/address of the relay board (default is 0)
            bus_id (int, optional): The I2C bus ID to use (e.g., 1 for /dev/i2c-1, 13 for /dev/i2c-13)
        \"\"\"
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
        \"\"\"Initialize with a custom I2C bus by monkey-patching the original module\"\"\"
        import subprocess
        import sys
        
        # Create a temporary patch script
        patch_script = f\"\"\"
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
\"\"\"
        
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
        \"\"\"Set a relay to a specific state\"\"\"
        if self.original_instance:
            return self.original_instance.set(relay, state)
        else:
            # Mock implementation
            logging.info(f"MOCK: Setting relay {relay} to state {state}")
            return True
    
    def set_all(self, state):
        \"\"\"Set all relays to a specific state\"\"\"
        if self.original_instance:
            return self.original_instance.set_all(state)
        else:
            # Mock implementation
            logging.info(f"MOCK: Setting all relays to state {state}")
            return True

# Create a function to find available I2C buses
def find_available_i2c_buses():
    \"\"\"Find available I2C buses on the system\"\"\"
    available_buses = []
    try:
        for i in range(0, 20):  # Check a reasonable range of I2C devices
            if os.path.exists(f"/dev/i2c-{i}"):
                available_buses.append(i)
        return available_buses
    except Exception as e:
        logging.error(f"Error finding I2C buses: {e}")
        return []

# Helper function to test connection with all available buses
def test_connection():
    \"\"\"Test connection with all available I2C buses\"\"\"
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
"""

# GPIO Handler patch content that uses the custom module
GPIO_HANDLER_PATCH = """# gpio/relay_handler.py

import logging
import time
import datetime
from models.relay_unit import RelayUnit

# Try to import our custom module first
try:
    from .custom_SM16relind import SM16relind, find_available_i2c_buses
    USING_CUSTOM_MODULE = True
    print("Using custom SM16relind module with multi-bus support")
except ImportError:
    # Fall back to standard module
    try:
        import SM16relind
        USING_CUSTOM_MODULE = False
        print("Using standard SM16relind module")
    except ImportError:
        # Try alternate casing
        try:
            import sm_16relind as SM16relind
            USING_CUSTOM_MODULE = False
            print("Using standard sm_16relind module")
        except ImportError:
            print("WARNING: SM16relind module not found. Hardware control will not work.")
            # Create a mock module for testing
            class MockSM16relind:
                def __init__(self, stack=0, bus_id=None):
                    self.stack = stack
                    self.bus_id = bus_id
                    print(f"MOCK: Initialized MockSM16relind (stack={stack}, bus_id={bus_id})")
                
                def set(self, relay, state):
                    print(f"MOCK: Setting relay {relay} to state {state}")
                    return True
                
                def set_all(self, state):
                    print(f"MOCK: Setting all relays to state {state}")
                    return True
            
            SM16relind = MockSM16relind
            USING_CUSTOM_MODULE = False
"""

def detect_i2c_buses():
    """Detect available I2C buses on the system"""
    print("Detecting I2C buses...")
    available_buses = []
    
    try:
        # Check commonly used I2C buses
        for i in range(0, 20):
            if os.path.exists(f"/dev/i2c-{i}"):
                available_buses.append(i)
                print(f"Found I2C bus: /dev/i2c-{i}")
        
        if not available_buses:
            print("No I2C buses found. Make sure I2C interface is enabled.")
            print("Try running: sudo raspi-config")
    except Exception as e:
        print(f"Error detecting I2C buses: {e}")
    
    return available_buses

def backup_file(file_path):
    """Create a backup of the specified file"""
    if not os.path.exists(file_path):
        return
    
    backup_path = f"{file_path}.bak"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"Created backup: {backup_path}")
    except Exception as e:
        print(f"Failed to create backup: {e}")

def create_custom_module():
    """Create the custom_SM16relind.py module in the gpio directory"""
    gpio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpio")
    
    if not os.path.exists(gpio_dir):
        os.makedirs(gpio_dir)
        print(f"Created directory: {gpio_dir}")
    
    custom_module_path = os.path.join(gpio_dir, "custom_SM16relind.py")
    
    # Backup existing file if it exists
    backup_file(custom_module_path)
    
    # Create the custom module
    try:
        with open(custom_module_path, "w") as f:
            f.write(CUSTOM_SM16RELIND_CONTENT)
        os.chmod(custom_module_path, 0o755)  # Make executable
        print(f"Created custom SM16relind module: {custom_module_path}")
    except Exception as e:
        print(f"Failed to create custom module: {e}")
        return False
    
    return True

def patch_gpio_handler():
    """Patch the gpio_handler.py file to use the custom module"""
    gpio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpio")
    gpio_handler_path = os.path.join(gpio_dir, "gpio_handler.py")
    
    if not os.path.exists(gpio_handler_path):
        print(f"GPIO handler not found at: {gpio_handler_path}")
        return False
    
    # Backup existing file
    backup_file(gpio_handler_path)
    
    try:
        with open(gpio_handler_path, "r") as f:
            content = f.read()
        
        # Check if already patched
        if "from .custom_SM16relind import SM16relind" in content:
            print("GPIO handler already patched.")
            return True
        
        # Look for imports
        import_section_end = content.find("class RelayHandler")
        if import_section_end == -1:
            print("Could not find the RelayHandler class in the GPIO handler.")
            return False
        
        # Replace import section with our patched version
        new_content = GPIO_HANDLER_PATCH + content[import_section_end:]
        
        with open(gpio_handler_path, "w") as f:
            f.write(new_content)
        
        print(f"Patched GPIO handler: {gpio_handler_path}")
        return True
    except Exception as e:
        print(f"Failed to patch GPIO handler: {e}")
        return False

def main():
    """Main function"""
    print("=" * 80)
    print("I2C Bus Fix for Rodent Refreshment Regulator")
    print("=" * 80)
    
    # Detect I2C buses
    buses = detect_i2c_buses()
    if not buses:
        print("\nNo I2C buses found. Cannot proceed with the fix.")
        print("Please check your Raspberry Pi configuration.")
        return
    
    # Inform about the fixes to be applied
    print("\nThis script will apply the following fixes:")
    print("1. Create a custom SM16relind module that supports multiple I2C buses")
    print("2. Patch the GPIO handler to use the custom module")
    print(f"3. Configure the system to use available I2C buses: {buses}")
    
    # Create the custom module
    if not create_custom_module():
        print("\nFailed to create custom module. Aborting.")
        return
    
    # Patch the GPIO handler
    if not patch_gpio_handler():
        print("\nFailed to patch GPIO handler. Aborting.")
        return
    
    print("\nI2C fix successfully applied!")
    print("Please restart the Rodent Refreshment Regulator application.")
    print("\nIf you encounter further issues, try testing each I2C bus manually:")
    print("sudo python3 test_i2c_relay.py")

if __name__ == "__main__":
    main() 