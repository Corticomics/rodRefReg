import json
import sqlite3
from datetime import datetime

def get_setting_type(value):
    """Determine the correct type for a setting value"""
    if isinstance(value, bool):
        return 'bool'
    elif isinstance(value, int):
        return 'int'
    elif isinstance(value, float):
        return 'float'
    else:
        return 'str'

def migrate_settings(force=False):
    """Migrate settings with proper type handling"""
    try:
        # Load existing JSON settings
        with open('settings.json', 'r') as f:
            json_settings = json.load(f)
        
        # Connect to database
        conn = sqlite3.connect('rrr_database.db')
        cursor = conn.cursor()
        
        # Migrate each setting with proper type
        for key, value in json_settings.items():
            setting_type = get_setting_type(value)
            cursor.execute('''
                INSERT OR REPLACE INTO system_settings 
                (setting_key, setting_value, setting_type, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (key, str(value), setting_type, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        print("Settings migration completed successfully")
        
    except Exception as e:
        print(f"Error during settings migration: {e}") 