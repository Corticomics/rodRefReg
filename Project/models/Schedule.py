# models/schedule.py

class Schedule:
    def __init__(self, schedule_id, name, relay_unit_id, water_volume, start_time, end_time, 
                 created_by, is_super_user, delivery_mode='staggered', cycles_per_day=1):
        self.schedule_id = schedule_id
        self.name = name
        self.relay_unit_id = relay_unit_id
        self.water_volume = water_volume
        self.start_time = start_time
        self.end_time = end_time
        self.created_by = created_by
        self.is_super_user = is_super_user
        self.delivery_mode = delivery_mode
        self.cycles_per_day = cycles_per_day #needed?
        
        # For staggered mode
        self.animals = []  # List of animal IDs
        self.desired_water_outputs = {}  # {animal_id: desired_water_output}
        
        # For instant mode
        self.instant_deliveries = []  # List of {animal_id, datetime, volume} dicts

    def add_instant_delivery(self, animal_id, delivery_datetime, volume):
        """Add an instant delivery time for an animal"""
        self.instant_deliveries.append({
            'animal_id': animal_id,
            'datetime': delivery_datetime,
            'volume': volume
        })

    def to_dict(self):
        data = {
            'schedule_id': self.schedule_id,
            'name': self.name,
            'relay_unit_id': self.relay_unit_id,
            'water_volume': self.water_volume,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'created_by': self.created_by,
            'is_super_user': self.is_super_user,
            'delivery_mode': self.delivery_mode
        }

        if self.delivery_mode == 'staggered':
            data.update({
                'animals': self.animals,
                'desired_water_outputs': self.desired_water_outputs
            })
        else:
            data['instant_deliveries'] = self.instant_deliveries

        return data

    def get_volume_for_unit(self, relay_unit_id):
        """Get water volume for a specific relay unit"""
        if self.delivery_mode == 'staggered':
            return self.desired_water_outputs.get(str(relay_unit_id), self.water_volume)
        return self.water_volume