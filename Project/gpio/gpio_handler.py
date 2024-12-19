# gpio/relay_handler.py

import SM16relind
import time
import datetime
import logging
from models.relay_unit import RelayUnit

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

    def _initialize_hats(self):
        """Initialize relay hat hardware"""
        self.relay_hats = []
        for i in range(self.num_hats):
            try:
                hat = SM16relind.SM16relind(i)
                hat.set_all(0)  # Initialize all relays to OFF
                self.relay_hats.append(hat)
                print(f"Initialized relay hat {i}")
            except Exception as e:
                print(f"Failed to initialize hat {i}: {e}")
                logging.error(f"Hat initialization error: {str(e)}")

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

            triggers = num_triggers.get(str(unit_id), 1)
            success = self._execute_triggers(relay_unit, triggers, stagger)
            
            if success:
                relay_info.append(f"Relay Unit {unit_id} triggered {triggers} times")
            
        return relay_info

    def _execute_triggers(self, relay_unit, num_triggers, stagger):
        """Execute the specified number of triggers for a relay unit"""
        try:
            for _ in range(num_triggers):
                # Activate relays
                self._set_relay_states(relay_unit.relay_ids, 1)
                print(f"\n{datetime.datetime.now()} - Activated Relay Unit {relay_unit.unit_id}")
                time.sleep(stagger)
                
                # Deactivate relays
                self._set_relay_states(relay_unit.relay_ids, 0)
                time.sleep(stagger)
            return True
        except Exception as e:
            print(f"Error executing triggers for unit {relay_unit.unit_id}: {e}")
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
