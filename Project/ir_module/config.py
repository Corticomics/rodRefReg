"""
Configuration module for the IR Sensor Module.

This module centralizes all configuration flags that control which features
of the IR sensor module are enabled. By changing these flags, different
components can be progressively enabled as development and testing proceeds.
"""

# Core configuration dictionary with boolean flags
CONFIG = {
    # HARDWARE LEVEL
    "ENABLE_BASIC_SENSOR_TEST": False,    # Enable basic sensor detection and terminal output
    "SIMULATE_SENSORS": True,            # Use simulated sensors if hardware not available
    
    # DATA PROCESSING LEVEL
    "ENABLE_DATA_PROCESSING": False,     # Enable drink event processing and session detection
    "ENABLE_LOGGING": True,              # Enable detailed logging of sensor events
    
    # STORAGE LEVEL
    "ENABLE_DATABASE_STORAGE": False,    # Enable storing data in the database
    
    # UI LEVEL
    "ENABLE_VISUALIZATION_TAB": False,   # Enable the visualization UI tab
    
    # INTEGRATION LEVEL
    "ENABLE_INTEGRATION": False,         # Enable full integration with main RRR system
}

# Paths and hardware configuration
HARDWARE_CONFIG = {
    "DEFAULT_SENSOR_MAP": {
        # Maps relay unit IDs to GPIO pins
        "1": 17,  # Relay Unit 1 -> GPIO 17
        "2": 18,  # Relay Unit 2 -> GPIO 18
        "3": 27,  # Relay Unit 3 -> GPIO 27
        "4": 22   # Relay Unit 4 -> GPIO 22
    },
    "DEBOUNCE_MS": 300,            # Debounce time in milliseconds
    "SESSION_TIMEOUT_MS": 1000,    # Time after which a session is considered finished
}

# Functions to check if features are enabled
def is_feature_enabled(feature_name):
    """Check if a specific feature is enabled in the configuration."""
    return CONFIG.get(feature_name, False)

def get_hardware_config(key, default=None):
    """Get a hardware configuration value."""
    return HARDWARE_CONFIG.get(key, default)

def print_config_status():
    """Print the current configuration status to the terminal."""
    print("\n=== IR SENSOR MODULE CONFIGURATION ===")
    for key, value in CONFIG.items():
        status = "ENABLED" if value else "DISABLED"
        print(f"{key}: {status}")
    print("=====================================\n") 