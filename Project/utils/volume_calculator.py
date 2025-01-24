import math

class VolumeCalculator:
    def __init__(self, settings):
        self.pump_volume_ul = settings.get('pump_volume_ul', 50)  # 50µL per trigger
        self.calibration_factor = settings.get('calibration_factor', 1.0)
        self.min_triggers = settings.get('min_triggers', 1)
    
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

    def calculate_staggered_volumes(self, target_volumes):
        calculated_volumes = {}
        for animal_id, target_volume in target_volumes.items():
            volume_ul = target_volume * 1000  # Convert to microliters
            adjusted_volume = volume_ul * self.calibration_factor
            triggers = math.ceil(adjusted_volume / self.pump_volume_ul)
            calculated_volumes[animal_id] = {
                'triggers': triggers,
                'volume_ml': (triggers * self.pump_volume_ul) / 1000
            }
        return calculated_volumes