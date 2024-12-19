import math

class VolumeCalculator:
    def __init__(self, settings):
        self.pump_volume_ul = settings.get('pump_volume_ul', 50)  # 50µL per trigger
        self.calibration_factor = settings.get('calibration_factor', 1.0)
    
    def calculate_triggers(self, desired_volume_ml):
        """Calculate number of triggers needed for desired volume"""
        # Convert mL to µL and apply calibration
        desired_volume_ul = desired_volume_ml * 1000  # Convert to microliters
        adjusted_volume = desired_volume_ul * self.calibration_factor
        
        # Calculate minimum triggers needed
        min_triggers = math.ceil(adjusted_volume / self.pump_volume_ul)
        return max(min_triggers, 1)  # Ensure at least 1 trigger