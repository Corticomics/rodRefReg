import RPi.GPIO as GPIO
import sm_16relind
import time
import datetime

class RelayHandler:
    def __init__(self, relay_pairs, num_hats=1):
        self.relay_pairs = relay_pairs
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

    def trigger_relays(self, selected_relays, num_triggers, stagger):
        relay_info = []
        for relay_pair in self.relay_pairs:
            relay_pair_str = str(relay_pair)  # Ensure relay_pair is a string key
            
            if isinstance(num_triggers, dict):
                triggers = num_triggers.get(relay_pair_str, 1)  # Default to 1 if not found
                
                # Ensure triggers is an integer
                if not isinstance(triggers, int):
                    raise ValueError(f"Expected 'triggers' to be an integer, got {type(triggers)} instead.")
            else:
                raise ValueError(f"Expected 'num_triggers' to be a dictionary, got {type(num_triggers)} instead.")

            if relay_pair in selected_relays:
                for _ in range(triggers):
                    relay1, relay2 = relay_pair
                    hat_index1, relay_index1 = divmod(relay1 - 1, 16)
                    hat_index2, relay_index2 = divmod(relay2 - 1, 16)
                    try:
                        self.relay_hats[hat_index1].set(relay_index1 + 1, 1)
                        self.relay_hats[hat_index2].set(relay_index2 + 1, 1)
                        print(f"\n{datetime.datetime.now()} - Pumps connected to {relay_pair} triggered\n")
                        time.sleep(stagger)
                        self.relay_hats[hat_index1].set(relay_index1 + 1, 0)
                        self.relay_hats[hat_index2].set(relay_index2 + 1, 0)
                        time.sleep(stagger)
                    except IndexError:
                        print(f"Error: Relay hat index out of range for {relay_pair}")
                    relay_info.append(f"{relay_pair} triggered {triggers} times")
        return relay_info



    def update_relay_hats(self, relay_pairs, num_hats):
        self.relay_pairs = relay_pairs
        self.num_hats = num_hats
        self.relay_hats = []
        for i in range(num_hats):
            try:
                hat = sm_16relind.SM16relind(i)
                self.relay_hats.append(hat)
                print(f"Initialized relay hat {i}")
            except Exception as e:
                print(f"Failed to initialize hat {i}: {e}")