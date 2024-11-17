# gpio/relay_handler.py

import RPi.GPIO as GPIO
import sm_16relind
import time
import datetime

from models.relay_unit import RelayUnit

class RelayHandler:
    def __init__(self, relay_units, num_hats=1):
        self.relay_units = relay_units  # List of RelayUnit instances
        self.num_hats = num_hats
        GPIO.setmode(GPIO.BOARD)
        self.relay_hats = []
        for i in range(num_hats):
            try:
                hat = sm_16relind.SM16relind(i)
                self.relay_hats.append(hat)
                print(f"Initialized relay hat {i}")
            except Exception as e:
                print(f"Failed to initialize hat {i}: {e}")

    def set_all_relays(self, state):
        for hat in self.relay_hats:
            hat.set_all(state)

    def trigger_relays(self, selected_units, num_triggers, stagger):
        """
        Triggers the specified relay units.

        Args:
            selected_units (list): List of relay_unit_ids to trigger.
            num_triggers (dict): Dictionary mapping relay_unit_id to number of triggers.
            stagger (float): Time in seconds to wait between relay activations.
        """
        relay_info = []
        for relay_unit in self.relay_units:
            if relay_unit.unit_id in selected_units:
                triggers = num_triggers.get(relay_unit.unit_id, 1)
                for _ in range(triggers):
                    # Activate all relays in the unit
                    for relay in relay_unit.relay_ids:
                        hat_index, relay_index = divmod(relay - 1, 16)
                        try:
                            # Activate relay
                            self.relay_hats[hat_index].set(relay_index + 1, 1)
                        except IndexError:
                            print(f"Error: Relay hat index out of range for relay {relay}")
                        except Exception as e:
                            print(f"Error activating relay {relay}: {e}")
                    print(f"\n{datetime.datetime.now()} - Activated Relay Unit {relay_unit.unit_id} (Relays {relay_unit.relay_ids})\n")
                    time.sleep(stagger)
                    # Deactivate all relays in the unit
                    for relay in relay_unit.relay_ids:
                        hat_index, relay_index = divmod(relay - 1, 16)
                        try:
                            # Deactivate relay
                            self.relay_hats[hat_index].set(relay_index + 1, 0)
                        except IndexError:
                            print(f"Error: Relay hat index out of range for relay {relay}")
                        except Exception as e:
                            print(f"Error deactivating relay {relay}: {e}")
                    time.sleep(stagger)
                relay_info.append(f"Relay Unit {relay_unit.unit_id} triggered {triggers} times")
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
                hat = sm_16relind.SM16relind(i)
                self.relay_hats.append(hat)
                print(f"Reinitialized relay hat {i}")
            except Exception as e:
                print(f"Failed to initialize hat {i}: {e}")
