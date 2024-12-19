import datetime
import asyncio

class PumpController:
    def __init__(self, relay_handler, database_handler):
        self.relay_handler = relay_handler
        self.database_handler = database_handler
        
    async def dispense_water(self, relay_unit_id, volume, num_triggers):
        """
        Dispense water using relay handler with proper timing
        Returns True if successful, False otherwise
        """
        try:
            # Get relay unit object
            relay_unit = self.relay_handler.get_relay_unit(relay_unit_id)
            if not relay_unit:
                print(f"Invalid relay unit ID: {relay_unit_id}")
                return False
            
            # Create proper triggers dictionary with string keys
            triggers_dict = {str(relay_unit_id): num_triggers}
            
            # Use existing relay handler's trigger_relays method
            relay_info = self.relay_handler.trigger_relays(
                [relay_unit_id],
                triggers_dict,
                stagger=0.5  # 500ms stagger between triggers
            )
            
            return bool(relay_info)
            
        except Exception as e:
            print(f"Error dispensing water: {e}")
            return False
