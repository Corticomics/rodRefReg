# models/schedule.py

from datetime import datetime

class Schedule:
    def __init__(self, schedule_id, name, water_volume, start_time, end_time, 
                 created_by, is_super_user, delivery_mode='staggered', cycles_per_day=1):
        self.schedule_id = schedule_id
        self.name = name
        self.water_volume = water_volume
        self.start_time = start_time
        self.end_time = end_time
        self.created_by = created_by
        self.is_super_user = is_super_user
        self.delivery_mode = delivery_mode
        self.cycles_per_day = cycles_per_day
        
        # For staggered mode
        self.animals = []
        self.desired_water_outputs = {}
        
        # For instant mode
        self.instant_deliveries = []
        
        # Track relay unit assignments
        self.relay_unit_assignments = {}  # {animal_id: relay_unit_id}

    def add_instant_delivery(self, animal_id, delivery_datetime, volume, relay_unit_id):
        self.instant_deliveries.append({
            'animal_id': animal_id,
            'datetime': delivery_datetime,
            'volume': volume,
            'relay_unit_id': relay_unit_id
        })
        self.relay_unit_assignments[str(animal_id)] = relay_unit_id

    def to_dict(self):
        data = {
            'schedule_id': self.schedule_id,
            'name': self.name,
            'water_volume': self.water_volume,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'created_by': self.created_by,
            'is_super_user': self.is_super_user,
            'delivery_mode': self.delivery_mode,
            'relay_unit_assignments': self.relay_unit_assignments
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

    def update_time_window(self, start_time, end_time):
        """Update the schedule's time window"""
        if isinstance(start_time, (int, float)):
            # Convert from timestamp if needed
            start_time = datetime.fromtimestamp(start_time).isoformat()
        if isinstance(end_time, (int, float)):
            # Convert from timestamp if needed
            end_time = datetime.fromtimestamp(end_time).isoformat()
            
        self.start_time = start_time
        self.end_time = end_time