import json
import os

CONFIG_DIR = os.path.join("rodent-refreshment-regulator", "settings")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

def save_configuration(settings):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as config_file:
            json.dump(settings, config_file, indent=4)
        return True
    except IOError as e:
        print(f"Error saving configuration: {e}")
        return False
