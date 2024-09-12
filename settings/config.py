import json
import os
from PyQt5.QtWidgets import QMessageBox
def save_settings(settings):
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    with open(settings_path, 'w') as file:
        json.dump(settings, file, indent=4)


def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as file:
            settings = json.load(file)
            settings['relay_pairs'] = create_relay_pairs(settings.get('num_hats', 1))
    else:
        settings = {}

    # Set default values for settings if they are not already set
    settings.setdefault('interval', 3600)
    settings.setdefault('stagger', 1)
    settings.setdefault('window_start', 8)
    settings.setdefault('window_end', 20)
    settings.setdefault('selected_relays', [])
    settings.setdefault('num_triggers', {})
    settings.setdefault('slack_token', "SLACKTOKEN")
    settings.setdefault('channel_id', "ChannelId")
    settings.setdefault('num_hats', 1)
    settings.setdefault('offline_duration', 60)  # Default to 60 minutes if not set

    return settings



def save_settings(settings):
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    try:
        with open(settings_path, 'w') as file:
            json.dump(settings, file, indent=4)
    except Exception as e:
        print(f"Error saving settings (save_settings): {e}")


def create_relay_pairs(num_hats):
    relay_pairs = []
    for hat in range(num_hats):
        start_relay = hat * 16 + 1
        for i in range(0, 16, 2):
            relay_pairs.append((start_relay + i, start_relay + i + 1))
    return relay_pairs
