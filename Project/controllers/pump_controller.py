class PumpController:
    def __init__(self, relay_handler, database_handler):
        if not relay_handler:
            raise ValueError("relay_handler cannot be None")
        if not database_handler:
            raise ValueError("database_handler cannot be None")

        self.relay_handler = relay_handler
        self.database_handler = database_handler

    def triggers_fired(self):
        """Triggers that switched on in the last dispense_water call, so a
        run a relay stopped part-way can be credited with them."""
        return getattr(self, '_fired', 0)

    async def dispense_water(self, relay_unit_id, volume, num_triggers):
        """
        Dispense water using relay handler with proper timing
        Returns True if successful, False otherwise
        """
        self._fired = 0
        try:
            # Validate inputs
            if not relay_unit_id:
                raise ValueError("Invalid relay unit ID")
            if volume <= 0:
                raise ValueError("Volume must be positive")

            # Get relay unit object with error handling
            relay_unit = self.relay_handler.get_relay_unit(relay_unit_id)
            if not relay_unit:
                raise ValueError(f"Invalid relay unit ID: {relay_unit_id}")

            # Create triggers dictionary with validation
            triggers_dict = {str(relay_unit_id): num_triggers}

            # Trigger relays with error handling
            relay_info = self.relay_handler.trigger_relays(
                [relay_unit_id], triggers_dict, stagger=0.5
            )
            counts = getattr(self.relay_handler, 'last_trigger_counts', None)
            if isinstance(counts, dict):
                self._fired = int(counts.get(relay_unit_id, 0) or 0)
            elif relay_info:
                self._fired = int(num_triggers)

            if not relay_info:
                raise RuntimeError("Failed to trigger relays")

            return True

        except Exception as e:
            print(f"Error dispensing water: {str(e)}")
            return False
