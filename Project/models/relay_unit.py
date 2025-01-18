# models/relay_unit.py

class RelayUnit:
    def __init__(self, unit_id, relay_ids):
        self.unit_id = unit_id
        self.relay_ids = relay_ids  # Tuple of relay IDs (e.g., (1, 2))

    def __str__(self):
        return f"Relay Unit {self.unit_id} (Relays {self.relay_ids[0]} & {self.relay_ids[1]})"