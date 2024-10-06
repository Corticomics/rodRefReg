import os
import json
import logging
from PyQt5.QtWidgets import QMessageBox

# Define the path to the settings directory and pumps.json
SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))
PUMPS_FILE = os.path.join(SETTINGS_DIR, 'pumps.json')
SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.json')

def load_settings():
    """Load application settings from settings.json."""
    if not os.path.exists(SETTINGS_FILE):
        # Return default settings if settings.json doesn't exist
        return {
            'interval': 3600,
            'stagger': 1,
            'window_start': 8,
            'window_end': 20,
            'selected_relays': [],
            'num_triggers': {},
            'slack_token': "",
            'channel_id': "",
            'num_hats': 1,
            'offline_duration': 60
        }
    try:
        with open(SETTINGS_FILE, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        QMessageBox.critical(None, "Error", f"Failed to load settings: {e}")
        return {}

def save_settings(settings):
    """Save application settings to settings.json."""
    try:
        with open(SETTINGS_FILE, 'w') as file:
            json.dump(settings, file, indent=4)
    except Exception as e:
        logging.error(f"Error saving settings: {e}")
        QMessageBox.critical(None, "Error", f"Failed to save settings: {e}")

def load_pumps():
    """Load pumps from pumps.json."""
    if not os.path.exists(PUMPS_FILE):
        # Return default pumps if pumps.json doesn't exist
        return [
            {
                "name": "Default 20μL Pump",
                "volume_per_trigger": 20.0
            }
        ]
    try:
        with open(PUMPS_FILE, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error loading pumps: {e}")
        QMessageBox.critical(None, "Error", f"Failed to load pumps: {e}")
        return [
            {
                "name": "Default 20μL Pump",
                "volume_per_trigger": 20.0
            }
        ]

def save_pumps(pumps):
    """Save pumps to pumps.json."""
    try:
        with open(PUMPS_FILE, 'w') as file:
            json.dump(pumps, file, indent=4)
    except Exception as e:
        logging.error(f"Error saving pumps: {e}")
        QMessageBox.critical(None, "Error", f"Failed to save pumps: {e}")
