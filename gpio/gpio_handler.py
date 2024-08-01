import RPi.GPIO as GPIO
import sm_16relind
import time
import datetime

class RelayHandler:
    def __init__(self, relay_pairs, num_hats):
        self.relay_pairs = relay_pairs
        self.num_hats = num_hats
        self.relay_hats = [sm_16relind.SM16relind(i) for i in range(num_hats)]
        print(f"Initialized {num_hats} relay hats with relay pairs: {relay_pairs}")

    def trigger_relays(self, selected_relays, num_triggers, stagger):
        relay_info = []
        for relay_pair in selected_relays:
            for _ in range(num_triggers):
                if relay_pair[0] <= len(self.relay_hats) * 16:
                    print(f"Triggering relay pair: {relay_pair}")
                    self.relay_hats[(relay_pair[0] - 1) // 16].relay_on(relay_pair[0])
                    self.relay_hats[(relay_pair[1] - 1) // 16].relay_on(relay_pair[1])
                    time.sleep(stagger)
                    self.relay_hats[(relay_pair[0] - 1) // 16].relay_off(relay_pair[0])
                    self.relay_hats[(relay_pair[1] - 1) // 16].relay_off(relay_pair[1])
                    relay_info.append(f"Relay pair {relay_pair[0]} & {relay_pair[1]} triggered")
                else:
                    print(f"Relay pair {relay_pair[0]} & {relay_pair[1]} not available")
        return relay_info

    def set_all_relays(self, state):
        for hat in self.relay_hats:
            for relay in range(1, 17):
                if state:
                    hat.relay_on(relay)
                else:
                    hat.relay_off(relay)
