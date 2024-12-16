import datetime
import asyncio

class PumpController:
    def __init__(self, relay_handler, database_handler):
        self.relay_handler = relay_handler
        self.database_handler = database_handler
        
    async def dispense_water(self, relay_unit, volume, num_triggers):
        """
        Dispense water using relay handler with proper timing
        Returns True if successful, False otherwise
        """
        try:
            # Use existing relay handler's trigger_relays method
            relay_info = self.relay_handler.trigger_relays(
                [relay_unit.unit_id],
                {str(relay_unit.unit_id): num_triggers},
                stagger=0.5  # 500ms stagger between triggers
            )
            
            return bool(relay_info)  # Return True if relay_info contains trigger data
            
        except Exception as e:
            print(f"Error dispensing water: {e}")
            return False
