# gpio/relay_handler.py
import RPi.GPIO as GPIO
import sm_16relind
import time
import logging

class RelayHandler:
    def __init__(self, relay_pairs, num_hats=1):
        self.relay_pairs = relay_pairs
        self.num_hats = num_hats
        GPIO.setmode(GPIO.BOARD)
        self.relay_hats = []
        self.initialize_hats()
        logging.info(f"Initialized {num_hats} relay hats.")

    def initialize_hats(self):
        for i in range(self.num_hats):
            try:
                hat = sm_16relind.SM16relind(i)
                self.relay_hats.append(hat)
                logging.info(f"Initialized relay hat {i}")
            except Exception as e:
                logging.error(f"Failed to initialize hat {i}: {e}")

    def set_all_relays(self, state):
        for hat in self.relay_hats:
            hat.set_all(state)
        logging.info(f"All relays set to state {state}")

    def trigger_relays(self, selected_relays, num_triggers, stagger):
        relay_info = []
        for relay_pair in selected_relays:
            triggers = num_triggers.get(str(relay_pair), 1)
            for _ in range(triggers):
                relay1, relay2 = relay_pair
                hat_index1, relay_index1 = divmod(relay1 - 1, 16)
                hat_index2, relay_index2 = divmod(relay2 - 1, 16)
                try:
                    self.relay_hats[hat_index1].set(relay_index1 + 1, 1)
                    self.relay_hats[hat_index2].set(relay_index2 + 1, 1)
                    logging.info(f"Activated relays {relay1} and {relay2}")
                    time.sleep(stagger)
                    self.relay_hats[hat_index1].set(relay_index1 + 1, 0)
                    self.relay_hats[hat_index2].set(relay_index2 + 1, 0)
                    logging.info(f"Deactivated relays {relay1} and {relay2}")
                    time.sleep(stagger)
                except IndexError:
                    logging.error(f"Relay hat index out of range for {relay_pair}")
                relay_info.append(f"{relay_pair} triggered {triggers} times")
        return relay_info

    def update_relay_hats(self, relay_pairs, num_hats):
        self.relay_pairs = relay_pairs
        self.num_hats = num_hats
        self.relay_hats = []
        GPIO.cleanup()  # Clean up existing GPIO settings
        GPIO.setmode(GPIO.BOARD)
        self.initialize_hats()
        logging.info(f"Relay hats updated to {num_hats} hats.")
