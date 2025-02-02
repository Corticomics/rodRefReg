# models/schedule.py

from datetime import datetime, timedelta

class Schedule:
    def __init__(self, schedule_id, name, water_volume, start_time, end_time, 
                 created_by, is_super_user, delivery_mode='staggered', cycles_per_day=1, window_data=None):
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
        self.window_data = window_data if window_data else {}
        
        # For instant mode
        self.instant_deliveries = []
        
        # Track relay unit assignments
        self.relay_unit_assignments = {}  # {animal_id: relay_unit_id}
        
        # Tracking attributes
        self.status = 'pending'
        self.delivered_volumes = {}       # {animal_id: volume}
        self.last_delivery = {}          # {animal_id: datetime}
        
    def add_animal(self, animal_id, relay_unit_id, desired_volume=None):
        """Add an animal to the schedule with its relay unit and desired volume"""
        self.animals.append(animal_id)
        self.relay_unit_assignments[str(animal_id)] = relay_unit_id
        if desired_volume is not None:
            self.desired_water_outputs[str(animal_id)] = desired_volume
        else:
            self.desired_water_outputs[str(animal_id)] = self.water_volume
            
    def add_instant_delivery(self, animal_id, delivery_datetime, volume, relay_unit_id):
        """Add an instant delivery for an animal"""
        if self.delivery_mode != 'instant':
            raise ValueError("Cannot add instant delivery to staggered schedule")
            
        self.instant_deliveries.append({
            'animal_id': animal_id,
            'datetime': delivery_datetime,
            'volume': volume,
            'relay_unit_id': relay_unit_id
        })
        if str(animal_id) not in self.relay_unit_assignments:
            self.relay_unit_assignments[str(animal_id)] = relay_unit_id
            
    def calculate_delivery_windows(self):
        """Calculate delivery windows based on mode and cycles"""
        if self.delivery_mode == 'instant':
            return [{
                'start_time': d['datetime'],
                'end_time': d['datetime'],
                'animal_id': d['animal_id'],
                'volume': d['volume']
            } for d in self.instant_deliveries]
            
        # For staggered mode
        windows = []
        day_start = datetime.fromisoformat(self.start_time)
        day_end = datetime.fromisoformat(self.end_time)
        window_duration = (day_end - day_start) / self.cycles_per_day
        
        for cycle in range(self.cycles_per_day):
            window_start = day_start + (window_duration * cycle)
            window_end = window_start + window_duration
            
            for animal_id in self.animals:
                volume = self.desired_water_outputs.get(str(animal_id), self.water_volume)
                cycle_volume = volume / self.cycles_per_day
                
                windows.append({
                    'start_time': window_start,
                    'end_time': window_end,
                    'animal_id': animal_id,
                    'volume': cycle_volume
                })
                
        return windows
    
    def update_delivery_progress(self, animal_id, volume, timestamp):
        """Update delivery progress for an animal"""
        animal_id_str = str(animal_id)
        
        # Update delivered volume
        current_volume = self.delivered_volumes.get(animal_id_str, 0)
        self.delivered_volumes[animal_id_str] = current_volume + volume
        
        # Update last delivery time
        self.last_delivery[animal_id_str] = timestamp
        
        # Update window progress
        current_time = datetime.fromisoformat(timestamp)
        for window in self.window_data.get(animal_id_str, []):
            if (window['start_time'] <= current_time <= window['end_time']):
                window['delivered'] = window.get('delivered', 0) + volume
                break
                
    def get_remaining_volume(self, animal_id):
        """Get remaining volume to be delivered for an animal"""
        animal_id_str = str(animal_id)
        target = self.desired_water_outputs.get(animal_id_str, self.water_volume)
        delivered = self.delivered_volumes.get(animal_id_str, 0)
        return max(0, target - delivered)
    
    def is_complete(self):
        """Check if schedule is complete"""
        if self.status == 'completed':
            return True
            
        for animal_id in self.animals:
            if self.get_remaining_volume(animal_id) > 0:
                return False
        return True
    
    def to_dict(self):
        """Convert schedule to dictionary representation"""
        data = {
            'schedule_id': self.schedule_id,
            'name': self.name,
            'water_volume': self.water_volume,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'created_by': self.created_by,
            'is_super_user': self.is_super_user,
            'delivery_mode': self.delivery_mode,
            'cycles_per_day': self.cycles_per_day,
            'status': self.status,
            'relay_unit_assignments': self.relay_unit_assignments,
            'delivered_volumes': self.delivered_volumes
        }

        if self.delivery_mode == 'staggered':
            data.update({
                'animals': self.animals,
                'desired_water_outputs': self.desired_water_outputs,
                'window_data': self.window_data
            })
        else:
            data['instant_deliveries'] = self.instant_deliveries

        return data
    
    def get_unit_data(self, unit_id):
        """Get delivery data for a specific relay unit"""
        try:
            # Find animals assigned to this unit
            unit_animals = [
                animal_id for animal_id, relay_id 
                in self.relay_unit_assignments.items()
                if relay_id == unit_id
            ]
            
            if not unit_animals:
                return None
                
            if self.delivery_mode == 'staggered':
                windows = self.calculate_delivery_windows()
                return {
                    'delivery_schedule': [
                        w for w in windows 
                        if str(w['animal_id']) in unit_animals
                    ]
                }
            else:
                unit_deliveries = [
                    d for d in self.instant_deliveries 
                    if d['relay_unit_id'] == unit_id
                ]
                return {
                    'delivery_schedule': unit_deliveries
                } if unit_deliveries else None
                
        except Exception as e:
            print(f"Error getting unit data: {e}")
            return None

    def get_delivery_windows(self):
        """Get all delivery windows for the schedule"""
        if self.delivery_mode.lower() == 'staggered':
            return [{
                'start_time': datetime.fromisoformat(self.start_time),
                'end_time': datetime.fromisoformat(self.end_time)
            }]
        else:
            return [{
                'start_time': d['datetime'],
                'end_time': d['datetime']
            } for d in self.instant_deliveries]