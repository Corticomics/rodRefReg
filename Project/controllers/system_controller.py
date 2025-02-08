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
            'num_hats', 'slack_token', 'channel_id',
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
            'channel_id': str
        }
        return type_map.get(key, str) 