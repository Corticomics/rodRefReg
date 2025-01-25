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
        Calculate optimal staggered delivery timing with actual delivery instants
        
        Args:
            window_start (datetime): Start time of delivery window
            window_end (datetime): End time of delivery window
            animals_data: list of {animal_id, volume_ml} dicts
        
        Returns:
            Dict with timing plan and delivery instants for each animal
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
        
        # Generate delivery schedule with actual instants
        schedule = {}
        for idx, animal in enumerate(animals_data):
            animal_id = animal['animal_id']
            total_triggers = animal_triggers[animal_id]
            volume_per_trigger = (animal['volume_ml'] * 1000 / total_triggers) / 1000  # in mL
            
            # Calculate triggers per cycle, ensuring even distribution
            triggers_per_cycle = math.ceil(total_triggers / total_cycles_needed)
            cycle_start_offset = idx * stagger_interval
            
            # Generate actual delivery instants
            delivery_instants = []
            remaining_triggers = total_triggers
            
            for cycle in range(total_cycles_needed):
                if remaining_triggers <= 0:
                    break
                    
                cycle_triggers = min(triggers_per_cycle, remaining_triggers)
                cycle_start_time = window_start + timedelta(
                    seconds=(cycle * cycle_interval + cycle_start_offset)
                )
                
                # Generate instants for this cycle
                for trigger in range(cycle_triggers):
                    instant_time = cycle_start_time + timedelta(
                        milliseconds=trigger * self.min_trigger_interval_ms
                    )
                    
                    if instant_time >= window_end:
                        # Adjust timing if we're near window end
                        remaining_time = (window_end - cycle_start_time).total_seconds()
                        if remaining_time > 0:
                            # Compress remaining triggers into available time
                            compressed_interval = remaining_time / (cycle_triggers - trigger)
                            instant_time = cycle_start_time + timedelta(
                                seconds=trigger * compressed_interval
                            )
                        else:
                            continue
                    
                    delivery_instants.append({
                        'time': instant_time,
                        'volume': volume_per_trigger,
                        'triggers': 1
                    })
                
                remaining_triggers -= cycle_triggers
            
            schedule[animal_id] = {
                'triggers_per_cycle': triggers_per_cycle,
                'total_cycles': total_cycles_needed,
                'cycle_start_offset': cycle_start_offset,
                'trigger_interval_ms': self.min_trigger_interval_ms,
                'cycle_interval_seconds': cycle_interval,
                'delivery_instants': delivery_instants,
                'total_volume': animal['volume_ml']
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