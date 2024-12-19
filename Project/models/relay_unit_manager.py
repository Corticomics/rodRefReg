from models.relay_unit import RelayUnit

class RelayUnitManager:
    def __init__(self, settings):
        self.settings = settings
        self.relay_units = {}
        self.initialize_relay_units()
    
    def initialize_relay_units(self):
        """Initialize relay units from settings"""
        relay_pairs = self.settings.get('relay_pairs', [
            (1, 2), (3, 4), (5, 6), (7, 8),
            (9, 10), (11, 12), (13, 14), (15, 16)
        ])
        
        for unit_id, relay_pair in enumerate(relay_pairs, start=1):
            relay_unit = RelayUnit(
                unit_id=unit_id,
                relay_ids=relay_pair
            )
            self.relay_units[unit_id] = relay_unit
            
    def get_relay_unit(self, unit_id):
        """Get relay unit by ID"""
        return self.relay_units.get(unit_id)
        
    def get_all_relay_units(self):
        """Get all relay units"""
        return list(self.relay_units.values()) 