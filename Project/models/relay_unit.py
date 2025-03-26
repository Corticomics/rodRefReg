# models/relay_unit.py

class RelayUnit:
    def __init__(self, unit_id=None, relay_ids=None, relay_unit_id=None):
        """
        Initialize a RelayUnit instance.
        
        Args:
            unit_id (int, optional): The ID of the relay unit. Can be used interchangeably with relay_unit_id.
            relay_ids (tuple, optional): Tuple of relay IDs (e.g., (1, 2)).
            relay_unit_id (int, optional): Alternative ID parameter name for compatibility.
        """
        # Handle either unit_id or relay_unit_id for compatibility
        if relay_unit_id is not None and unit_id is None:
            self.unit_id = relay_unit_id
        else:
            self.unit_id = unit_id
            
        self.relay_ids = relay_ids  # Tuple of relay IDs (e.g., (1, 2))

    def __str__(self):
        return f"Relay Unit {self.unit_id} (Relays {self.relay_ids[0]} & {self.relay_ids[1]})"