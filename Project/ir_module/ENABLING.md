# Enabling IR Sensor Module Features

The IR Sensor Module is designed with a progressive feature enabling approach, making it suitable for both development and production use. By default, all features are disabled to avoid disrupting current functionality. This document explains how to enable and test the features when you're ready.

## Configuration Controls

All IR module features are controlled by configuration flags in `ir_module/config.py`. These flags allow you to progressively enable features as you're ready to test them:

```python
CONFIG = {
    # HARDWARE LEVEL
    "ENABLE_BASIC_SENSOR_TEST": False,    # Basic sensor detection and terminal output
    "SIMULATE_SENSORS": True,             # Use simulated sensors if hardware not available
    
    # DATA PROCESSING LEVEL
    "ENABLE_DATA_PROCESSING": False,      # Drink event processing and session detection
    "ENABLE_LOGGING": True,               # Detailed logging of sensor events
    
    # STORAGE LEVEL
    "ENABLE_DATABASE_STORAGE": False,     # Storing data in the database
    
    # UI LEVEL
    "ENABLE_VISUALIZATION_TAB": False,    # UI tab for visualization
    
    # INTEGRATION LEVEL
    "ENABLE_INTEGRATION": False,          # Full integration with main RRR system
}
```

## Recommended Enabling Sequence

When you're ready to start testing the IR module, it's recommended to enable features in this order:

1. **Initial Testing (Hardware Level):**
   ```python
   "ENABLE_BASIC_SENSOR_TEST": True
   "SIMULATE_SENSORS": True  # Keep simulation enabled for initial testing
   ```
   
   This will allow you to test basic sensor functionality without affecting the main application.

2. **Data Processing:**
   ```python
   "ENABLE_DATA_PROCESSING": True
   ```
   
   This enables processing of IR sensor events into drinking sessions.

3. **Database Storage:**
   ```python
   "ENABLE_DATABASE_STORAGE": True
   ```
   
   This enables storing drinking sessions and events in the database.

4. **UI Features:**
   ```python
   "ENABLE_VISUALIZATION_TAB": True
   ```
   
   This enables the data analysis tab in the UI.

5. **Full Integration:**
   ```python
   "ENABLE_INTEGRATION": True
   ```
   
   This fully integrates the IR module with the main application.

## Testing Hardware Without Integration

To test the IR sensor hardware without enabling full integration, use the standalone tester utility:

```bash
# List configured GPIO pins
python -m ir_module.utils.sensor_tester --list

# Test a specific pin
python -m ir_module.utils.sensor_tester --pin 17

# Test all configured sensors
python -m ir_module.utils.sensor_tester
```

## Troubleshooting

If you encounter issues when enabling features:

1. Check the logs for errors
2. Try enabling features one at a time
3. Verify hardware connections if using physical sensors
4. Ensure database migrations have been applied when enabling storage

## Hardware Configuration

The default GPIO pin mapping is:
- Relay Unit 1 → GPIO 17
- Relay Unit 2 → GPIO 18
- Relay Unit 3 → GPIO 27
- Relay Unit 4 → GPIO 22

To modify these mappings, update the `HARDWARE_CONFIG` section in `ir_module/config.py`. 