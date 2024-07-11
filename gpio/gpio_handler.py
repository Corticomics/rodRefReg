import RPi.GPIO as GPIO
import sm_16relind
import time
import datetime

class RelayHandler:
    def __init__(self, relay_pairs, num_hats=1):
        self.relay_pairs = relay_pairs
        self.num_hats = num_hats
        GPIO.setmode(GPIO.BOARD)
        self.relay_hats = self.initialize_relay_hats(num_hats)
    
    def initialize_relay_hats(self, num_hats):
        relay_hats = []
        for i in range(num_hats):
            try:
                relay_hat = sm_16relind.SM16relind(stack=i)
                relay_hats.append(relay_hat)
                print(f"Initialized relay hat {i}")
                relay_hat.set_all(0)
            except Exception as e:
                print(f"Failed to initialize hat {i}: {e}")
                relay_hats.append(None)
        return relay_hats

    def set_all_relays(self, state):
        for hat in self.relay_hats:
            if hat is not None:
                hat.set_all(state)

    def trigger_relays(self, selected_relays, num_triggers, stagger):
        relay_info = []
        for relay_pair in self.relay_pairs:
            if relay_pair in selected_relays:
                triggers = num_triggers.get(relay_pair, 1)
                for _ in range(triggers):
                    relay1, relay2 = relay_pair
                    hat_index1, relay_index1 = divmod(relay1 - 1, 16)
                    hat_index2, relay_index2 = divmod(relay2 - 1, 16)
                    if self.relay_hats[hat_index1] and self.relay_hats[hat_index2]:
                        self.relay_hats[hat_index1].set(relay_index1 + 1, 1)
                        self.relay_hats[hat_index2].set(relay_index2 + 1, 1)
                        print(f"Pumps connected to {relay_pair} triggered")
                        time.sleep(stagger)
                        self.relay_hats[hat_index1].set(relay_index1 + 1, 0)
                        self.relay_hats[hat_index2].set(relay_index2 + 1, 0)
                        time.sleep(stagger)
                    relay_info.append(f"{relay_pair} triggered {triggers} times")
        return relay_info
