from datetime import datetime, timedelta
import math

class TimingCalculator:
    def __init__(self, system_controller):
        self.system_controller = system_controller
        self.settings = system_controller.settings
        self.system_controller.settings_updated.connect(self.update_settings)
        
        # Hardware constraints
        self.min_trigger_interval_ms = self.settings.get('min_trigger_interval_ms', 500)
        self.pump_volume_ul = self.settings.get('pump_volume_ul', 50)
        self.calibration_factor = self.settings.get('calibration_factor', 1.0)
        self.max_triggers_per_cycle = self.settings.get('max_triggers_per_cycle', 5)
        self.min_cycle_spacing_minutes = self.settings.get('min_cycle_spacing_minutes', 30)
        
    def update_settings(self, settings):
        """Update calculator settings"""
        self.settings = settings
        
    def calculate_staggered_timing(self, window_start, window_end, animals_data):
        """Calculate optimal staggered delivery timing with actual delivery instants"""
        window_duration = (window_end - window_start).total_seconds()
        total_animals = len(animals_data)
        
        # Calculate volume and trigger requirements for each animal
        animal_requirements = {}
        max_cycles_needed = 1
        
        for animal in animals_data:
            volume_calc = self._calculate_volume_requirements(
                animal['volume_ml'],
                window_duration
            )
            animal_requirements[animal['animal_id']] = volume_calc
            max_cycles_needed = max(max_cycles_needed, volume_calc['total_cycles'])
        
        # Calculate timing intervals
        cycle_interval = self._calculate_cycle_interval(
            window_duration, 
            max_cycles_needed,
            total_animals
        )
        
        # Calculate stagger between animals
        stagger_interval = self._calculate_stagger_interval(
            cycle_interval,
            total_animals
        )
        
        # Generate delivery schedule
        schedule = {}
        for idx, animal in enumerate(animals_data):
            animal_id = animal['animal_id']
            reqs = animal_requirements[animal_id]
            
            delivery_instants = self._generate_delivery_instants(
                window_start,
                window_end,
                animal,
                reqs,
                cycle_interval,
                stagger_interval,
                idx
            )
            
            schedule[animal_id] = {
                'triggers_per_cycle': reqs['triggers_per_cycle'],
                'total_cycles': reqs['total_cycles'],
                'cycle_start_offset': idx * stagger_interval,
                'trigger_interval_ms': self.min_trigger_interval_ms,
                'cycle_interval_seconds': cycle_interval,
                'delivery_instants': delivery_instants,
                'total_volume': animal['volume_ml']
            }
        
        return {
            'schedule': schedule,
            'cycle_interval': cycle_interval,
            'stagger_interval': stagger_interval,
            'total_cycles': max_cycles_needed
        }
    
    def _calculate_volume_requirements(self, volume_ml, window_duration):
        """Calculate volume and trigger requirements for an animal"""
        volume_ul = volume_ml * 1000
        adjusted_volume = volume_ul * self.calibration_factor
        total_triggers = math.ceil(adjusted_volume / self.pump_volume_ul)
        
        # Calculate cycles needed
        total_cycles = math.ceil(total_triggers / self.max_triggers_per_cycle)
        triggers_per_cycle = math.ceil(total_triggers / total_cycles)
        
        # Ensure minimum cycle spacing
        min_cycle_duration = self.min_cycle_spacing_minutes * 60
        min_cycles_for_spacing = math.ceil(window_duration / min_cycle_duration)
        
        total_cycles = max(total_cycles, min_cycles_for_spacing)
        triggers_per_cycle = math.ceil(total_triggers / total_cycles)
        
        return {
            'total_triggers': total_triggers,
            'triggers_per_cycle': triggers_per_cycle,
            'total_cycles': total_cycles,
            'volume_per_trigger': (self.pump_volume_ul / 1000)
        }
    
    def _calculate_cycle_interval(self, window_duration, total_cycles, total_animals):
        """Calculate optimal cycle interval"""
        min_cycle_spacing = self.min_cycle_spacing_minutes * 60
        base_interval = window_duration / total_cycles
        
        return max(base_interval, min_cycle_spacing)
    
    def _calculate_stagger_interval(self, cycle_interval, total_animals):
        """Calculate stagger interval between animals"""
        min_stagger = (self.min_trigger_interval_ms / 1000) * self.max_triggers_per_cycle
        return max(cycle_interval / total_animals, min_stagger)
    
    def _generate_delivery_instants(self, window_start, window_end, animal, reqs,
                                  cycle_interval, stagger_interval, animal_index):
        """Generate delivery instants for an animal"""
        delivery_instants = []
        remaining_triggers = reqs['total_triggers']
        
        for cycle in range(reqs['total_cycles']):
            if remaining_triggers <= 0:
                break
                
            cycle_start = window_start + timedelta(
                seconds=(cycle * cycle_interval + animal_index * stagger_interval)
            )
            
            cycle_triggers = min(reqs['triggers_per_cycle'], remaining_triggers)
            cycle_instants = self._generate_cycle_instants(
                cycle_start,
                window_end,
                cycle_triggers,
                reqs['volume_per_trigger'],
                animal['relay_unit_id'],
                cycle == (reqs['total_cycles'] - 1)
            )
            
            delivery_instants.extend(cycle_instants)
            remaining_triggers -= cycle_triggers
            
        return delivery_instants
    
    def _generate_cycle_instants(self, cycle_start, window_end, num_triggers,
                               volume_per_trigger, relay_unit_id, is_last_cycle):
        """Generate delivery instants within a cycle"""
        instants = []
        
        for i in range(num_triggers):
            if is_last_cycle:
                # Compress remaining triggers if needed
                remaining_time = (window_end - cycle_start).total_seconds()
                if remaining_time <= 0:
                    break
                    
                interval = remaining_time / (num_triggers - i)
                instant_time = cycle_start + timedelta(seconds=i * interval)
            else:
                instant_time = cycle_start + timedelta(
                    milliseconds=i * self.min_trigger_interval_ms
                )
                
            if instant_time <= window_end:
                instants.append({
                    'time': instant_time,
                    'volume': volume_per_trigger,
                    'triggers': 1,
                    'relay_unit_id': relay_unit_id
                })
                
        return instants
    
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