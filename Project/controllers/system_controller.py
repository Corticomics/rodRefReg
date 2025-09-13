from PyQt5.QtCore import QObject, pyqtSignal
import json
import os
from datetime import datetime

class SystemController(QObject):
    settings_updated = pyqtSignal(dict)
    system_status = pyqtSignal(str)
    
    def __init__(self, database_handler):
        super().__init__()
        self.database_handler = database_handler
        self.settings_file = 'settings.json'
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load settings from JSON file and database"""
        try:
            # Load from JSON
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = self._create_default_settings()
            
            # Merge with database settings
            db_settings = self._load_database_settings()
            settings.update(db_settings)
            
            return settings
        except Exception as e:
            self.system_status.emit(f"Error loading settings: {str(e)}")
            return self._create_default_settings()
    
    def save_settings(self, settings_dict):
        """Save settings to appropriate storage"""
        try:
            # Separate settings based on storage type
            json_settings = {k: v for k, v in settings_dict.items() 
                           if k in self._get_json_settings_keys()}
            db_settings = {k: v for k, v in settings_dict.items() 
                         if k in self._get_db_settings_keys()}
            
            # Save to JSON
            with open(self.settings_file, 'w') as f:
                json.dump(json_settings, f, indent=4)
            
            # Save to database
            self._save_database_settings(db_settings)
            
            self.settings = settings_dict
            self.settings_updated.emit(settings_dict)
            
        except Exception as e:
            self.system_status.emit(f"Error saving settings: {str(e)}")
    
    def _create_default_settings(self):
        """Create default settings with proper types"""
        return {
            'num_hats': 1,
            'slack_token': '',
            'channel_id': '',
            'min_trigger_interval_ms': 500,
            'cycle_interval': 3600,
            'stagger_interval': 0.5,
            'hardware_mode': 'solenoid',  # default to solenoid; UI can switch to pump
            'global_master_relay_id': 16,
            'i2c_bus': 1,
            'flow_sampling_hz': 50.0,
            'predictive_close_ms': 10.0,
            'residual_check_ms': 200.0,
            'residual_flow_threshold_ml_min': 1.0,
            'max_consecutive_sensor_errors': 10,
            'cage_relays': {},
            'debug_mode': False,
            'log_level': 2,
            'log_level_map': {
                0: 'DEBUG',
                1: 'INFO',
                2: 'WARNING',
                3: 'ERROR',
                4: 'CRITICAL'
            }
        }
    
    def _get_json_settings_keys(self):
        """Define which settings go in JSON file"""
        return {
            'num_hats', 'slack_token', 'channel_id', 'hardware_mode',
            'global_master_relay_id', 'i2c_bus', 'flow_sampling_hz',
            'predictive_close_ms', 'residual_check_ms',
            'residual_flow_threshold_ml_min', 'max_consecutive_sensor_errors',
            'cage_relays',
            'debug_mode', 'log_level'
        }
    
    def _get_db_settings_keys(self):
        """Define which settings go in database"""
        return {
            'min_trigger_interval_ms', 'cycle_interval',
            'stagger_interval'
        }

    def _get_setting_type(self, key):
        """Define type mapping for settings"""
        type_map = {
            'num_hats': int,
            'min_trigger_interval_ms': int,
            'cycle_interval': int,
            'stagger_interval': float,
            'debug_mode': bool,
            'log_level': int,
            'slack_token': str,
            'channel_id': str,
            'hardware_mode': str,
            'global_master_relay_id': int,
            'i2c_bus': int,
            'flow_sampling_hz': float,
            'predictive_close_ms': float,
            'residual_check_ms': float,
            'residual_flow_threshold_ml_min': float,
            'max_consecutive_sensor_errors': int,
        }
        return type_map.get(key, str)

    # --- Auto-detect helpers (used by UI) ---
    def detect_hats(self):
        """Attempt to detect number of relay HATs by probing stack IDs 0..7.

        Returns the detected count and does not persist automatically. UI layer
        can decide to persist by calling save_settings().
        """
        try:
            from gpio.gpio_handler import RelayHandler
            from models.relay_unit_manager import RelayUnitManager
            temp_settings = self.settings.copy()
            # Probe hats by optimistic init. RelayHandler internally logs errors.
            manager = RelayUnitManager(temp_settings)
            handler = RelayHandler(manager, temp_settings.get('num_hats', 1))
            hats = max(1, temp_settings.get('num_hats', 1))
            return hats
        except Exception:
            return self.settings.get('num_hats', 1)

    def detect_flow_sensor_bus(self):
        """Probe I2C buses for SLF3x address 0x08; return bus id or current setting."""
        try:
            import os
            from smbus2 import SMBus, i2c_msg
            for bus in range(0, 21):
                if not os.path.exists(f"/dev/i2c-{bus}"):
                    continue
                try:
                    with SMBus(bus) as b:
                        # Quick read zero bytes to see if device NACKs; fallback to a harmless read.
                        r = i2c_msg.read(0x08, 1)
                        b.i2c_rdwr(r)
                        return bus
                except Exception:
                    continue
        except Exception:
            pass
        return self.settings.get('i2c_bus', 1)

    def ensure_solenoid_defaults(self):
        """Seed solenoid settings 

        Rules (confirmed):
        - Global master is relay ID 16 on HAT #1 (fixed).
        - All other relays across all hats are cages, ascending order.
        - I2C bus is auto-detected by probing 0x08 across /dev/i2c-*. If none, keep current.
        - Do not change hardware_mode automatically; only seed maps and buses.
        """
        try:
            s = dict(self.settings)

            # Detect I2C bus (if not set or default)
            if not isinstance(s.get('i2c_bus'), int) or s.get('i2c_bus', 1) == 1:
                detected_bus = self.detect_flow_sensor_bus()
                if isinstance(detected_bus, int):
                    s['i2c_bus'] = detected_bus

            # Number of hats already configured via settings; if missing fallback to 1
            num_hats = int(s.get('num_hats', 1))

            # Global master fixed at relay 16 on first HAT
            s['global_master_relay_id'] = 16

            # Build cage map if empty: fill all relays except master across hats
            cage_map = s.get('cage_relays') or {}
            if not cage_map:
                total_relays = 16 * num_hats
                cage_id = 1
                new_map = {}
                for relay_id in range(1, total_relays + 1):
                    if relay_id == 16:  # reserved global master
                        continue
                    new_map[str(cage_id)] = relay_id
                    cage_id += 1
                s['cage_relays'] = new_map

            # Persist if anything changed
            if s != self.settings:
                self.save_settings(s)
        except Exception as e:
            self.system_status.emit(f"Solenoid auto-seed failed: {e}")

    def get_pump_controller(self):
        """Get or create a pump controller instance"""
        if not hasattr(self, '_pump_controller'):
            from controllers.pump_controller import PumpController
            self._pump_controller = PumpController(self.settings)
        return self._pump_controller 