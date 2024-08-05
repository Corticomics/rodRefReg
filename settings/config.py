import json
import os
# settings/config.py

def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as file:
            settings = json.load(file)
            settings['relay_pairs'] = create_relay_pairs(settings.get('num_hats', 1))
    else:
        settings = {
            "relay_pairs": [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12], [13, 14], [15, 16]],
            "interval": 3600,
            "stagger": 1,
            "window_start": 8,
            "window_end": 20,
            "selected_relays": [],
            "num_triggers": {},
            "slack_token": "SLACKTOKEN",
            "channel_id": "ChannelId",
            "num_hats": 1
        }

    return settings

def create_relay_pairs(num_hats):
    relay_pairs = []
    for hat in range(num_hats):
        start_relay = hat * 16 + 1
        for i in range(0, 16, 2):
            relay_pairs

            