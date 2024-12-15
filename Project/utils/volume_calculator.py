import math
from PyQt5.QtCore import QObject, pyqtSignal

class VolumeCalculator(QObject):
    config_updated = pyqtSignal(dict)  # Signal when pump config changes
    
    def __init__(self, database_handler):
        super().__init__()
        self.database_handler = database_handler
        self._pump_config = None
        self.load_pump_config()
    
    def load_pump_config(self):
        """Load pump configuration from database"""
        try:
            new_config = self.database_handler.get_active_pump_config()
            if new_config != self._pump_config:
                self._pump_config = new_config
                self.config_updated.emit(self._pump_config)
        except Exception as e:
            print(f"Error loading pump configuration: {e}")
            if not self._pump_config:
                self._pump_config = {
                    'pump_volume_ul': 50,
                    'calibration_factor': 1.0
                }
    
    def calculate_triggers(self, desired_volume_ml):
        """Calculate number of triggers needed for desired volume"""
        if not self._pump_config:
            self.load_pump_config()
            
        # Convert mL to µL and apply calibration
        desired_volume_ul = desired_volume_ml * 1000
        adjusted_volume = desired_volume_ul * self._pump_config['calibration_factor']
        
        return math.ceil(adjusted_volume / self._pump_config['pump_volume_ul']) 