# calculations.py

import math
import logging

def calculate_triggers(desired_volume_ml, volume_per_trigger_ul):
    try:
        if desired_volume_ml <= 0:
            raise ValueError("Desired volume must be positive.")
        if volume_per_trigger_ul <= 0:
            raise ValueError("Volume per trigger must be positive.")

        volume_per_trigger_ml = volume_per_trigger_ul / 1000.0  # Convert μL to mL
        triggers = desired_volume_ml / volume_per_trigger_ml
        return int(math.ceil(triggers))  # Round up to ensure sufficient volume
    except Exception as e:
        logging.error(f"Error calculating triggers: {e}")
        raise
