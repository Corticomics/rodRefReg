# gpio_handler.py

import logging
import time
import datetime
from models.relay_unit import RelayUnit
import os
# Prefer the vendor's standard module by default. Only use the custom module
# when explicitly enabled via environment (to avoid multi-bus side effects).
USE_CUSTOM_SM16 = os.getenv('RRR_USE_CUSTOM_SM16', '0') == '1'
# Import I2C coordination for hardware-level conflict prevention
try:
    from drivers.i2c_coordinator import get_i2c_coordinator
    I2C_COORDINATION_AVAILABLE = True
except ImportError:
    I2C_COORDINATION_AVAILABLE = False
    print("I2C coordination not available, relay operations may conflict with sensors")

if USE_CUSTOM_SM16:
    try:
        from .custom_SM16relind import SM16relind, find_available_i2c_buses
        USING_CUSTOM_MODULE = True
        print("Using custom SM16relind module with multi-bus support (RRR_USE_CUSTOM_SM16=1)")
    except ImportError:
        USING_CUSTOM_MODULE = False
        print("Custom SM16relind not available; falling back to standard module")

if not USE_CUSTOM_SM16 or not 'USING_CUSTOM_MODULE' in globals() or not USING_CUSTOM_MODULE:
    # Fall back to standard module
    try:
        import SM16relind as _sm_mod
        # Determine if module contains a class named SM16relind or is the class itself
        if hasattr(_sm_mod, 'SM16relind'):
            SM16relind = _sm_mod.SM16relind
        else:
            SM16relind = _sm_mod
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
        
        # Initialize I2C coordinator for hardware-level conflict prevention
        if I2C_COORDINATION_AVAILABLE:
            self._coordinator = get_i2c_coordinator()
        else:
            self._coordinator = None
        
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
            # Use the implementation from custom module only if explicitly enabled
            try:
                return find_available_i2c_buses()
            except Exception:
                pass
        
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
        """Initialize relay hat hardware.

        Standard module (SM16relind):
          - Instantiate with stack index 0..num_hats-1 (per Sequent docs).
        Custom module (custom_SM16relind):
          - Supports bus_id; iterate detected I2C buses and stacks.
        """
        self.relay_hats = []

        success = False

        if USING_CUSTOM_MODULE:
            # When custom module is explicitly enabled, still prefer the default Pi bus (1)
            # to avoid unintended bus probing that can disrupt the flow sensor.
            preferred_buses = [1]
            for bus in preferred_buses:
                for stack in range(self.num_hats):
                    try:
                        hat = SM16relind(stack=stack, bus_id=bus)
                        hat.set_all(0)
                        self.relay_hats.append(hat)
                        print(f"Initialized relay hat stack={stack} on I2C bus {bus}")
                        success = True
                    except Exception as e:
                        print(f"Failed to initialize custom hat stack={stack} bus={bus}: {e}")
            if not success:
                error_msg = "Failed to initialize relay hats via custom module on preferred buses."
                print(error_msg)
                logging.error(error_msg)
            return

        # Standard module path: use stack indices only
        for stack in range(self.num_hats):
            try:
                ctor = getattr(SM16relind, 'SM16relind', None)
                if ctor is None:
                    raise AttributeError("SM16relind class not found in module")
                hat = ctor(stack)
                hat.set_all(0)
                self.relay_hats.append(hat)
                print(f"Initialized relay hat stack={stack}")
                success = True
            except Exception as e:
                print(f"Failed to initialize hat stack={stack}: {e}")
                logging.error(f"Hat initialization error: {str(e)}")

        if not success:
            error_msg = "Failed to initialize any relay hats. Check I2C configuration and connections."
            print(error_msg)
            logging.error(error_msg)

    def set_all_relays(self, state):
        """Set all relays to given state (0 or 1) with I2C coordination"""
        def _hardware_set_all_operation():
            for hat in self.relay_hats:
                try:
                    hat.set_all(0 if state == 0 else 65535)  # 65535 = all relays ON
                except Exception as e:
                    print(f"Error setting all relays: {e}")
                    logging.error(f"Relay state error: {str(e)}")
        
        # Use I2C coordination if available
        if self._coordinator:
            try:
                self._coordinator.sync_exclusive_access(
                    'relay', 
                    _hardware_set_all_operation
                )
            except Exception as e:
                logging.error(f"I2C coordination failed for set_all operation: {e}")
                _hardware_set_all_operation()
        else:
            _hardware_set_all_operation()

    def trigger_relays(self, selected_units, num_triggers, stagger):
        """Triggers the specified relay units with verification"""
        relay_info = []

        if not self.relay_hats:
            logging.error("Trigger requested but no relay hats are initialized")
            return []
        
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
        """Set the state of specified relay IDs with I2C coordination"""
        def _hardware_relay_operation():
            for relay_id in relay_ids:
                hat_index, relay_num = divmod(relay_id - 1, 16)
                if hat_index < len(self.relay_hats):
                    try:
                        self.relay_hats[hat_index].set(relay_num + 1, state)
                    except Exception as e:
                        print(f"Error setting relay {relay_id} to state {state}: {e}")
                        logging.error(f"Relay state change error: {str(e)}")
        
        # Use I2C coordination if available, otherwise fall back to direct control
        if self._coordinator:
            try:
                self._coordinator.sync_exclusive_access(
                    'relay', 
                    _hardware_relay_operation
                )
            except Exception as e:
                logging.error(f"I2C coordination failed for relay operation: {e}")
                # Fall back to direct control
                _hardware_relay_operation()
        else:
            _hardware_relay_operation()

    def set_relays(self, relay_ids, state):
        """Public method to set one or more relay channels ON (1) or OFF (0).

        This wraps the internal `_set_relay_states` and should be preferred by
        higher-level controllers (e.g., solenoid controller) instead of calling
        `_execute_triggers` when a sustained ON/OFF state is desired.
        """
        try:
            self._set_relay_states(relay_ids, 1 if state else 0)
            return True
        except Exception as e:
            logging.error(f"set_relays error: {str(e)}")
            return False

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
