import datetime

class PumpController:
    def __init__(self, relay_handler, database_handler):
        self.relay_handler = relay_handler
        self.database_handler = database_handler
        self._pump_config = None
        self.load_pump_config()
        
    def load_pump_config(self):
        """Load pump configuration from database"""
        try:
            self._pump_config = self.database_handler.get_active_pump_config()
        except Exception as e:
            print(f"Error loading pump configuration: {e}")
            # Use defaults if database fails
            self._pump_config = {
                'pump_volume_ul': 50,
                'calibration_factor': 1.0
            }
    
    def calculate_runtime(self, volume_ul):
        """Calculate runtime based on volume and pump configuration"""
        if not self._pump_config:
            self.load_pump_config()
            
        triggers = volume_ul / self._pump_config['pump_volume_ul']
        return triggers * self._pump_config['calibration_factor']
        
    async def dispense_water(self, relay_unit, volume_ul):
        """Dispense water using relay handler"""
        try:
            runtime = self.calculate_runtime(volume_ul)
            
            # Trigger the relay unit
            relay_info = self.relay_handler.trigger_relays(
                [relay_unit.unit_id],
                {str(relay_unit.unit_id): 1},
                runtime
            )
            
            if relay_info:
                # Log successful dispensing
                await self.database_handler.mark_instant_completed(
                    relay_unit.unit_id,
                    volume_ul
                )
                return True
                
            return False
            
        except Exception as e:
            print(f"Error dispensing water: {e}")
            return False
            
    async def update_pump_config(self, volume_ul, calibration_factor, trainer_id):
        """Update pump configuration"""
        try:
            config_id = await self.database_handler.update_pump_config(
                volume_ul,
                calibration_factor,
                trainer_id
            )
            if config_id:
                self.load_pump_config()
                return True
            return False
        except Exception as e:
            print(f"Error updating pump configuration: {e}")
            return False

    def notify_config_update(self):
        """Notify components of pump configuration update"""
        try:
            # Get current configuration
            config = self._pump_config
            
            # Emit configuration update signal
            self.config_updated.emit(config)
            
            return True
        except Exception as e:
            print(f"Error notifying pump configuration update: {e}")
            return False
