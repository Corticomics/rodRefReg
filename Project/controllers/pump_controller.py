import datetime

class PumpController:
    def __init__(self, relay_handler, database_handler):
        self.relay_handler = relay_handler
        self.database_handler = database_handler
        self.flow_rate = 1.0  # mL per second
        
    async def dispense_water(self, relay_unit, volume):
        """Dispense water using relay handler"""
        try:
            runtime = volume / self.flow_rate
            
            # Trigger the relay unit
            relay_info = self.relay_handler.trigger_relays(
                [relay_unit.unit_id],
                {str(relay_unit.unit_id): 1},
                runtime
            )
            
            return True if relay_info else False
            
        except Exception as e:
            print(f"Error dispensing water: {e}")
            return False
