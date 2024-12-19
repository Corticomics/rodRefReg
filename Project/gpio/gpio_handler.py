# gpio/relay_handler.py

import SM16relind
import time
import datetime

from models.relay_unit import RelayUnit

class RelayHandler:
    def __init__(self, relay_units, num_hats=1):
        self.relay_units = relay_units
        self.num_hats = num_hats
        self.relay_hats = []
        
        # Initialize relay hats
        for i in range(num_hats):
            try:
                hat = SM16relind.SM16relind(i)
                hat.set_all(0)  # Initialize all relays to OFF
                self.relay_hats.append(hat)
                print(f"Initialized relay hat {i}")
            except Exception as e:
                print(f"Failed to initialize hat {i}: {e}")

    def set_all_relays(self, state):
        """Set all relays to given state (0 or 1)"""
        for hat in self.relay_hats:
            try:
                hat.set_all(0 if state == 0 else 65535)  # 65535 = all relays ON
            except Exception as e:
                print(f"Error setting all relays: {e}")

    def trigger_relays(self, selected_units, num_triggers, stagger):
        """
        Triggers the specified relay units with verification
        """
        relay_info = []
        for unit_id in selected_units:
            # Find the relay unit object
            relay_unit = next((unit for unit in self.relay_units if unit.unit_id == unit_id), None)
            if not relay_unit:
                print(f"Relay unit {unit_id} not found")
                continue

            triggers = num_triggers.get(str(unit_id), 1)
            for _ in range(triggers):
                try:
                    # Activate relays
                    for relay_id in relay_unit.relay_ids:
                        hat_index, relay_num = divmod(relay_id - 1, 16)
                        if hat_index < len(self.relay_hats):
                            self.relay_hats[hat_index].set(relay_num + 1, 1)
                            
                    print(f"\n{datetime.datetime.now()} - Activated Relay Unit {unit_id}")
                    time.sleep(stagger)  # Wait for stagger period
                    
                    # Deactivate relays
                    for relay_id in relay_unit.relay_ids:
                        hat_index, relay_num = divmod(relay_id - 1, 16)
                        if hat_index < len(self.relay_hats):
                            self.relay_hats[hat_index].set(relay_num + 1, 0)
                            
                    time.sleep(stagger)  # Wait before next trigger
                    
                except Exception as e:
                    print(f"Error triggering relay unit {unit_id}: {e}")
                    continue
                    
            relay_info.append(f"Relay Unit {unit_id} triggered {triggers} times")
        return relay_info

    def update_relay_units(self, relay_units, num_hats):
        """
        Updates the relay units and reinitializes the relay hats.

        Args:
            relay_units (list): List of new RelayUnit instances.
            num_hats (int): Number of relay hats to initialize.
        """
        self.relay_units = relay_units
        self.num_hats = num_hats
        # Reinitialize relay hats
        self.relay_hats = []
        for i in range(num_hats):
            try:
                hat = SM16relind.SM16relind(i)
                hat.set_all(0)  # Initialize all relays to OFF
                self.relay_hats.append(hat)
                print(f"Reinitialized relay hat {i}")
            except Exception as e:
                print(f"Failed to initialize hat {i}: {e}")
