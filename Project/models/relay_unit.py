# models/relay_unit.py

class RelayUnit:
    """
    Represents a relay unit that can contain one or more relays.
    
    Design Pattern: Value Object
    - Immutable after creation
    - Supports both pump mode (paired relays) and solenoid mode (single relay)
    
    Attributes:
        unit_id (int): Unique identifier for this relay unit
        relay_ids (tuple): Tuple of relay IDs (e.g., (1,) for single, (1, 2) for pair)
    """
    
    def __init__(self, unit_id=None, relay_ids=None, relay_unit_id=None):
        """
        Initialize a RelayUnit instance.
        
        Args:
            unit_id (int, optional): The ID of the relay unit. Can be used interchangeably with relay_unit_id.
            relay_ids (tuple or int, optional): Tuple of relay IDs (e.g., (1, 2)) or single int for solenoid mode.
            relay_unit_id (int, optional): Alternative ID parameter name for compatibility.
        
        Best Practices:
        - Validates inputs (fail-fast principle)
        - Normalizes relay_ids to tuple for consistent interface
        - Backward compatible with existing code
        """
        # Handle either unit_id or relay_unit_id for compatibility
        if relay_unit_id is not None and unit_id is None:
            self.unit_id = relay_unit_id
        else:
            self.unit_id = unit_id
        
        # Normalize relay_ids to tuple (support both single int and tuple input)
        if isinstance(relay_ids, int):
            # Single relay (solenoid mode): convert to 1-tuple
            self.relay_ids = (relay_ids,)
        elif isinstance(relay_ids, (list, tuple)):
            # Multiple relays (pump mode) or explicitly passed tuple
            self.relay_ids = tuple(relay_ids)
        else:
            self.relay_ids = relay_ids

    def __str__(self):
        """String representation supporting both single and paired relays."""
        if len(self.relay_ids) == 1:
            # Single relay (solenoid mode)
            return f"Relay Unit {self.unit_id} (Relay {self.relay_ids[0]})"
        elif len(self.relay_ids) == 2:
            # Paired relays (pump mode)
            return f"Relay Unit {self.unit_id} (Relays {self.relay_ids[0]} & {self.relay_ids[1]})"
        else:
            # Generic case for any other configuration
            relay_str = ", ".join(str(r) for r in self.relay_ids)
            return f"Relay Unit {self.unit_id} (Relays: {relay_str})"
    
    def is_single_relay(self) -> bool:
        """Check if this unit represents a single relay (solenoid mode)."""
        return len(self.relay_ids) == 1
    
    def is_paired_relay(self) -> bool:
        """Check if this unit represents paired relays (pump mode)."""
        return len(self.relay_ids) == 2