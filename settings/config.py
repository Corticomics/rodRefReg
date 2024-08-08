import json
import os

def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as file:
            settings = json.load(file)
            settings['relay_pairs'] = create_relay_pairs(settings.get('num_hats', 1))
    else:
        settings = {}
    return settings

def save_settings(settings):
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    with open(settings_path, 'w') as file:
        json.dump(settings, file, indent=4)

def create_relay_pairs(num_hats):
    relay_pairs = []
    for hat in range(num_hats):
        start_relay = hat * 16 + 1
        for i in range(0, 16, 2):
            relay_pairs.append((start_relay + i, start_relay + i + 1))
    return relay_pairs
