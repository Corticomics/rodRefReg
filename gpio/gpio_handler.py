import RPi.GPIO as GPIO
import sm_16relind
import time
import datetime

import sm_16relind
import time

class RelayHandler:
    def __init__(self, relay_pairs, num_hats):
        self.relay_pairs = relay_pairs
        self.num_hats = num_hats
        self.relay_hats = []
        for i in range(num_hats):
            try:
                hat = sm_16relind.SM16relind(i)
                self.relay_hats.append(hat)
                print(f"Initialized relay hat {i} with relay pairs: {relay_pairs}")
            except Exception as e:
                print(f"Failed to initialize hat {i}: {e}")

    def trigger_relays(self, selected_relays, num_triggers, stagger):
        relay_info = []
        for relay_pair in selected_relays:
            hat_index_1 = (relay_pair[0] - 1) // 16
            hat_index_2 = (relay_pair[1] - 1) // 16
            relay_index_1 = (relay_pair[0] - 1) % 16 + 1
            relay_index_2 = (relay_pair[1] - 1) % 16 + 1

            if hat_index_1 < len(self.relay_hats) and hat_index_2 < len(self.relay_hats):
                for _ in range(num_triggers):
                    try:
                        self.relay_hats[hat_index_1].relay_on(relay_index_1)
                        self.relay_hats[hat_index_2].relay_on(relay_index_2)
                        time.sleep(stagger)
                        self.relay_hats[hat_index_1].relay_off(relay_index_1)
                        self.relay_hats[hat_index_2].relay_off(relay_index_2)
                        relay_info.append(f"Relay pair {relay_pair[0]} & {relay_pair[1]} triggered")
                    except Exception as e:
                        print(f"Failed to trigger relay pair {relay_pair}: {e}")
            else:
                print(f"Relay pair {relay_pair[0]} & {relay_pair[1]} not available")

        return relay_info

    def set_all_relays(self, state):
        for hat in self.relay_hats:
            for relay in range(1, 17):
                try:
                    if state:
                        hat.relay_on(relay)
                    else:
                        hat.relay_off(relay)
                except Exception as e:
                    print(f"Failed to set relay {relay} on hat {hat}: {e}")

    def update_relay_hats(self, relay_pairs, num_hats):
        self.relay_pairs = relay_pairs
        self.num_hats = num_hats
        self.relay_hats = []
        for i in range(num_hats):
            try:
                hat = sm_16relind.SM16relind(i)
                self.relay_hats.append(hat)
                print(f"Updated relay hat {i} with relay pairs: {relay_pairs}")
            except Exception as e:
                print(f"Failed to update hat {i}: {e}")
