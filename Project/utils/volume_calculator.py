import math
from datetime import timedelta

class VolumeCalculator:
    def __init__(self, settings):
        self.pump_volume_ul = settings.get('pump_volume_ul', 50)  # 50µL per trigger
        self.calibration_factor = settings.get('calibration_factor', 1.0)
        self.min_triggers = settings.get('min_triggers', 1)
        self.max_triggers_per_cycle = settings.get('max_triggers_per_cycle', 20)
        self.min_cycle_spacing = settings.get('min_cycle_spacing_minutes', 30)
        
    def calculate_triggers(self, desired_volume_ml):
        """Calculate number of triggers needed for desired volume"""
        if not desired_volume_ml or desired_volume_ml <= 0:
            return self.min_triggers
            
        # Convert mL to µL and apply calibration
        desired_volume_ul = desired_volume_ml * 1000
        adjusted_volume = desired_volume_ul * self.calibration_factor
        
        # Calculate required triggers
        required_triggers = max(
            round(adjusted_volume / self.pump_volume_ul),
            self.min_triggers
        )
        
        return required_triggers

    def calculate_staggered_volumes(self, target_volumes, cycles_per_day=1):
        """Calculate volumes and triggers for staggered delivery with cycles"""
        calculated_volumes = {}
        
        for animal_id, target_volume in target_volumes.items():
            # Calculate volume per cycle
            volume_per_cycle = target_volume / cycles_per_day
            volume_ul = volume_per_cycle * 1000  # Convert to microliters
            adjusted_volume = volume_ul * self.calibration_factor
            
            # Calculate triggers per cycle
            triggers_per_cycle = min(
                math.ceil(adjusted_volume / self.pump_volume_ul),
                self.max_triggers_per_cycle
            )
            
            # Calculate actual volume that will be delivered
            actual_volume_per_cycle = (triggers_per_cycle * self.pump_volume_ul) / 1000
            total_daily_volume = actual_volume_per_cycle * cycles_per_day
            
            calculated_volumes[animal_id] = {
                'triggers_per_cycle': triggers_per_cycle,
                'volume_per_cycle_ml': actual_volume_per_cycle,
                'total_triggers': triggers_per_cycle * cycles_per_day,
                'total_volume_ml': total_daily_volume,
                'cycles': cycles_per_day
            }
            
        return calculated_volumes
    
    def calculate_cycle_timing(self, window_start, window_end, num_cycles):
        """Calculate optimal timing for cycles within a window"""
        window_duration = window_end - window_start
        min_spacing = timedelta(minutes=self.min_cycle_spacing)
        
        # Ensure minimum spacing between cycles
        if num_cycles > 1:
            total_spacing_needed = min_spacing * (num_cycles - 1)
            if total_spacing_needed >= window_duration:
                raise ValueError(
                    f"Window duration {window_duration} too short for "
                    f"{num_cycles} cycles with {min_spacing} minimum spacing"
                )
        
        # Calculate even spacing between cycles
        if num_cycles > 1:
            cycle_spacing = window_duration / (num_cycles - 1)
            cycle_spacing = max(cycle_spacing, min_spacing)
        else:
            cycle_spacing = window_duration
            
        cycle_times = []
        for i in range(num_cycles):
            cycle_time = window_start + (cycle_spacing * i)
            cycle_times.append(cycle_time)
            
        return cycle_times
    
    def validate_volume_constraints(self, volume_ml, cycles_per_day):
        """Validate if volume can be delivered within constraints"""
        volume_per_cycle = volume_ml / cycles_per_day
        volume_ul = volume_per_cycle * 1000
        adjusted_volume = volume_ul * self.calibration_factor
        triggers_needed = math.ceil(adjusted_volume / self.pump_volume_ul)
        
        if triggers_needed > self.max_triggers_per_cycle:
            max_volume_per_cycle = (self.max_triggers_per_cycle * self.pump_volume_ul) / 1000
            raise ValueError(
                f"Volume {volume_per_cycle}mL per cycle exceeds maximum "
                f"({max_volume_per_cycle}mL) for {self.max_triggers_per_cycle} triggers"
            )
            
        return True