from datetime import datetime, timedelta
import math

class TimingCalculator:
    def __init__(self, settings):
        # Hardware constraints
        self.min_trigger_interval_ms = settings.get('min_trigger_interval_ms', 500)  # Minimum 500ms between triggers
        self.pump_volume_ul = settings.get('pump_volume_ul', 50)  # 50µL per trigger
        self.calibration_factor = settings.get('calibration_factor', 1.0)
        self.max_triggers_per_cycle = settings.get('max_triggers_per_cycle', 5)
        
    def calculate_staggered_timing(self, window_start, window_end, animals_data):
        """
        Calculate optimal staggered delivery timing
        animals_data: list of {animal_id, volume_ml} dicts
        Returns timing plan for uniform water distribution
        """
        window_duration = (window_end - window_start).total_seconds()
        total_animals = len(animals_data)
        
        # Calculate total triggers needed for each animal
        animal_triggers = {
            animal['animal_id']: self._calculate_triggers(animal['volume_ml'])
            for animal in animals_data
        }
        
        max_animal_triggers = max(animal_triggers.values())
        total_cycles_needed = math.ceil(max_animal_triggers / self.max_triggers_per_cycle)
        
        # Calculate timing intervals
        cycle_interval = window_duration / total_cycles_needed
        min_stagger = (self.min_trigger_interval_ms / 1000) * self.max_triggers_per_cycle
        stagger_interval = max(cycle_interval / total_animals, min_stagger)
        
        # Generate delivery schedule
        schedule = {}
        for idx, animal in enumerate(animals_data):
            animal_id = animal['animal_id']
            total_triggers = animal_triggers[animal_id]
            triggers_per_cycle = math.ceil(total_triggers / total_cycles_needed)
            
            schedule[animal_id] = {
                'triggers_per_cycle': triggers_per_cycle,
                'total_cycles': total_cycles_needed,
                'cycle_start_offset': idx * stagger_interval,
                'trigger_interval_ms': self.min_trigger_interval_ms,
                'cycle_interval_seconds': cycle_interval
            }
            
        return {
            'schedule': schedule,
            'cycle_interval': cycle_interval,
            'stagger_interval': stagger_interval,
            'total_cycles': total_cycles_needed
        }
    
    def calculate_instant_timing(self, delivery_time, animals_data):
        """
        Calculate timing for instant delivery ensuring safe intervals
        delivery_time: datetime for intended delivery
        animals_data: list of {animal_id, volume_ml} dicts
        """
        current_time = delivery_time
        schedule = {}
        
        for animal in animals_data:
            triggers = self._calculate_triggers(animal['volume_ml'])
            trigger_times = []
            
            for i in range(triggers):
                trigger_times.append(
                    current_time + timedelta(milliseconds=i * self.min_trigger_interval_ms)
                )
            
            schedule[animal['animal_id']] = {
                'start_time': current_time,
                'trigger_times': trigger_times,
                'total_triggers': triggers,
                'volume_per_trigger_ul': self.pump_volume_ul
            }
            
            # Update current_time for next animal
            current_time = trigger_times[-1] + timedelta(milliseconds=self.min_trigger_interval_ms)
            
        return schedule
    
    def _calculate_triggers(self, volume_ml):
        """Calculate number of triggers needed for desired volume"""
        volume_ul = volume_ml * 1000  # Convert to microliters
        adjusted_volume = volume_ul * self.calibration_factor
        return math.ceil(adjusted_volume / self.pump_volume_ul)