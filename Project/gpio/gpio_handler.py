# gpio/relay_handler.py

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

class RelayHandler:
    def __init__(self, relay_unit_manager, num_hats=1):
        """Initialize RelayHandler with relay unit manager and hats"""
        self.num_hats = num_hats
        self.relay_hats = []
        
        # Initialize relay units dictionary from manager
        self.relay_units = {}
        if hasattr(relay_unit_manager, 'get_all_relay_units'):
            units = relay_unit_manager.get_all_relay_units()
            for unit in units:
                self.relay_units[unit.unit_id] = unit
        else:
            # Handle legacy input where relay_unit_manager is a list of units
            for unit in relay_unit_manager:
                if isinstance(unit, RelayUnit):
                    self.relay_units[unit.unit_id] = unit
                elif isinstance(unit, tuple):
                    unit_id = len(self.relay_units) + 1
                    self.relay_units[unit_id] = RelayUnit(unit_id=unit_id, relay_ids=unit)
        
        # Initialize relay hats
        self._initialize_hats()

    def _find_available_i2c_buses(self):
        """Find available I2C buses on the system"""
        if USING_CUSTOM_MODULE:
            # Use the implementation from custom module
            return find_available_i2c_buses()
        
        # Fallback implementation
        available_buses = []
        try:
            import os
            # Check the common I2C device paths
            for i in range(0, 20):  # Check a reasonable range of I2C devices
                if os.path.exists(f"/dev/i2c-{i}"):
                    available_buses.append(i)
            
            if available_buses:
                print(f"Found I2C buses: {available_buses}")
            else:
                print("No I2C buses found. Make sure I2C is enabled.")
                
            return available_buses
        except Exception as e:
            print(f"Error finding I2C buses: {e}")
            return [0, 1]  # Default fallback

    def _initialize_hats(self):
        """Initialize relay hat hardware"""
        self.relay_hats = []
        
        # Find available I2C buses
        available_buses = self._find_available_i2c_buses()
        
        # Try to initialize hats
        success = False
        
        # First try the specific buses found
        for bus in available_buses:
            try:
                if USING_CUSTOM_MODULE:
                    hat = SM16relind(stack=0, bus_id=bus)
                else:
                    # For standard module, we'll try each bus as the stack address
                    # This is a workaround since standard module doesn't support bus_id
                    hat = SM16relind(bus)
                
                hat.set_all(0)  # Initialize all relays to OFF
                self.relay_hats.append(hat)
                print(f"Initialized relay hat on I2C bus {bus}")
                success = True
                break  # Exit once we successfully initialize a hat
            except Exception as e:
                print(f"Failed to initialize hat on I2C bus {bus}: {e}")
        
        # If no success yet, try the traditional way with address only
        if not success:
            for i in range(self.num_hats):
                try:
                    hat = SM16relind(i)
                    hat.set_all(0)  # Initialize all relays to OFF
                    self.relay_hats.append(hat)
                    print(f"Initialized relay hat {i}")
                    success = True
                except Exception as e:
                    print(f"Failed to initialize hat {i}: {e}")
                    logging.error(f"Hat initialization error: {str(e)}")
        
        if not success:
            error_msg = "Failed to initialize any relay hats. Check I2C configuration and connections."
            print(error_msg)
            logging.error(error_msg)

    def set_all_relays(self, state):
        """Set all relays to given state (0 or 1)"""
        for hat in self.relay_hats:
            try:
                hat.set_all(0 if state == 0 else 65535)  # 65535 = all relays ON
            except Exception as e:
                print(f"Error setting all relays: {e}")
                logging.error(f"Relay state error: {str(e)}")

    def trigger_relays(self, selected_units, num_triggers, stagger):
        """Triggers the specified relay units with verification"""
        relay_info = []
        
        for unit_id in selected_units:
            # Get relay unit from dictionary
            relay_unit = self.relay_units.get(unit_id)
            if not relay_unit:
                print(f"Relay unit {unit_id} not found in available units: {list(self.relay_units.keys())}")
                continue

            # Get number of triggers for this specific unit
            unit_triggers = num_triggers.get(str(unit_id))
            if unit_triggers is None:
                print(f"No trigger count specified for relay unit {unit_id}")
                continue

            success = self._execute_triggers(relay_unit, unit_triggers, stagger)
            
            if success:
                relay_info.append(f"Relay Unit {unit_id} triggered {unit_triggers} times")
        
        return relay_info
    def _execute_triggers(self, relay_unit, num_triggers, stagger):
        """Execute the specified number of triggers for a relay unit"""
        try:
            for trigger in range(num_triggers):
                # Log trigger attempt
                print(f"Executing trigger {trigger + 1}/{num_triggers} "
                      f"for relay unit {relay_unit.unit_id}")
                
                # Activate relays
                for relay_id in relay_unit.relay_ids:
                    self._set_relay_states([relay_id], 1)
                
                # Wait for activation duration
                time.sleep(stagger)
                
                # Deactivate relays
                for relay_id in relay_unit.relay_ids:
                    self._set_relay_states([relay_id], 0)
                
                # Wait between triggers
                if trigger < num_triggers - 1:  # Don't wait after last trigger
                    time.sleep(stagger)
                
            return True
            
        except Exception as e:
            logging.error(f"Trigger execution error: {str(e)}")
            return False

    def _set_relay_states(self, relay_ids, state):
        """Set the state of specified relay IDs"""
        for relay_id in relay_ids:
            hat_index, relay_num = divmod(relay_id - 1, 16)
            if hat_index < len(self.relay_hats):
                try:
                    self.relay_hats[hat_index].set(relay_num + 1, state)
                except Exception as e:
                    print(f"Error setting relay {relay_id} to state {state}: {e}")
                    logging.error(f"Relay state change error: {str(e)}")

    def update_relay_units(self, relay_units, num_hats):
        """Updates the relay units and reinitializes the relay hats"""
        self.relay_units = {unit.unit_id: unit for unit in relay_units}
        self.num_hats = num_hats
        self._initialize_hats()

    def get_relay_unit(self, unit_id):
        """Get a relay unit by ID"""
        return self.relay_units.get(unit_id)

    def get_all_relay_units(self):
        """Get all relay units"""
        return list(self.relay_units.values())
