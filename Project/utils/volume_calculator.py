import math

class VolumeCalculator:
    def __init__(self, settings):
        self.settings = settings
    
    def calculate_triggers(self, desired_volume_ml):
        """Calculate number of triggers needed for desired volume"""
        pump_volume_ul = self.settings.get('pump_volume_ul', 50)
        calibration_factor = self.settings.get('calibration_factor', 1.0)
        
        # Convert mL to µL and apply calibration
        desired_volume_ul = desired_volume_ml * 1000
        adjusted_volume = desired_volume_ul * calibration_factor
        
        return math.ceil(adjusted_volume / pump_volume_ul) 