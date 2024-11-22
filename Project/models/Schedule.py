# models/schedule.py

class Schedule:
    def __init__(self, schedule_id, name, relay_unit_id, water_volume, start_time, end_time, created_by, is_super_user):
        self.schedule_id = schedule_id
        self.name = name
        self.relay_unit_id = relay_unit_id
        self.water_volume = water_volume
        self.start_time = start_time
        self.end_time = end_time
        self.created_by = created_by
        self.is_super_user = is_super_user
        self.animals = []  # List of animal IDs assigned to this schedule
        self.desired_water_outputs = {}  # {animal_id: desired_water_output}

    def to_dict(self):
        return {
            'schedule_id': self.schedule_id,
            'name': self.name,
            'relay_unit_id': self.relay_unit_id,
            'water_volume': self.water_volume,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'created_by': self.created_by,
            'is_super_user': self.is_super_user,
            'animals': self.animals,
            'desired_water_outputs': self.desired_water_outputs
        }