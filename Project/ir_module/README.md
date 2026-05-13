# Rodent Refreshment Regulator (RRR) - IR Sensor Module

This module adds infrared (IR) beam break sensor capabilities to the Rodent Refreshment Regulator system, allowing for tracking and analysis of animal drinking patterns. The module is designed with a progressive feature enabling approach, making it suitable for both development and production use.

## Overview

The IR Sensor Module provides the following capabilities:

- Detection of beam-break events when animals drink
- Recording of timestamped drinking events
- Aggregation of events into drinking sessions
- Storage of drinking data in the database
- Visualization of drinking patterns for circadian rhythm analysis
- Integration with the main RRR application

## Hardware Requirements

- Infrared (IR) break beam sensors (one per cage/animal)
- Wiring to connect sensors to GPIO pins
- Raspberry Pi (or compatible device) with GPIO pins

## Hardware Setup

### IR Sensor Wiring

Each IR sensor typically consists of two components:
1. **Emitter**: Emits the IR beam
2. **Receiver**: Detects the IR beam

Connect the components as follows:

1. **Power connections**:
   - Connect VCC (usually red wire) to 3.3V or 5V power (check your sensor specifications)
   - Connect GND (usually black wire) to ground

2. **Signal connection**:
   - Connect the signal pin (usually yellow or white wire) to the corresponding GPIO pin
   - The default GPIO pin mapping is:
     - Relay Unit 1 → GPIO 17
     - Relay Unit 2 → GPIO 18
     - Relay Unit 3 → GPIO 27
     - Relay Unit 4 → GPIO 22

### Testing the Hardware

Use the provided sensor tester utility to verify your IR sensors are working:

```bash
# List configured GPIO pins
python3 -m ir_module.utils.sensor_tester --list

# Test a specific pin
python3 -m ir_module.utils.sensor_tester --pin 17

# Test all configured sensors
python3 -m ir_module.utils.sensor_tester
```

## Software Setup

### Configuration

The module uses a configuration system that allows features to be enabled progressively. These settings are defined in `config.py`:

```python
# Core configuration flags
CONFIG = {
    # HARDWARE LEVEL
    "ENABLE_BASIC_SENSOR_TEST": True,    # Enable basic sensor detection and terminal output
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
```

To enable features for production use, update these settings as needed.

### Integration with RRR Application

To integrate the IR module with the main RRR application:

1. **Import the integration module**:

```python
from ir_module.integration import IRModuleIntegration
```

2. **Initialize the integration**:

```python
# In your main application:
ir_integration = IRModuleIntegration(
    app_controller=your_app_controller,
    database_handler=your_database_handler
)
```

3. **Add the data analysis tab to your UI** (if visualization is enabled):

```python
# In your UI initialization:
data_tab = ir_integration.get_data_analysis_tab(parent=your_tab_widget)
if data_tab:
    your_tab_widget.addTab(data_tab, "Drinking Analysis")
```

4. **Handle application shutdown**:

```python
# In your application shutdown sequence:
ir_integration.shutdown()
```

## Database Schema

The module adds the following tables to the RRR database:

1. **drinking_sessions**: Records drinking sessions
   - `session_id`: Primary key
   - `animal_id`: ID of the animal
   - `start_time`: Start time of the session
   - `end_time`: End time of the session
   - `duration_ms`: Duration in milliseconds
   - `estimated_volume_ml`: Estimated water volume in ml

2. **drinking_events**: Records individual beam break events
   - `event_id`: Primary key
   - `animal_id`: ID of the animal
   - `timestamp`: Time of the event
   - `duration_ms`: Duration in milliseconds
   - `session_id`: ID of the associated session

3. **drinking_patterns**: Records aggregated time-bin data
   - `pattern_id`: Primary key
   - `animal_id`: ID of the animal
   - `time_bin`: Time bin (format HH:MM)
   - `event_count`: Number of events in this bin
   - `total_duration_ms`: Total duration in milliseconds
   - `total_volume_ml`: Total volume in ml
   - `date`: Date of the pattern

## Development Guidelines

### Adding New Features

1. Create a configuration flag in `config.py`
2. Use `is_feature_enabled()` to check if the feature should be activated
3. Add your feature implementation with appropriate conditional logic

### Testing

For development and testing without physical hardware:

1. Set `SIMULATE_SENSORS = True` in the configuration
2. Use the test utilities in `ir_module.utils.test_utilities`

Example:

```python
from ir_module.utils.test_utilities import SensorSimulator

# Create a simulator
simulator = SensorSimulator(sensor_manager)

# Simulate a single beam break
simulator.simulate_single_event(relay_unit_id=1)

# Start random simulation
simulator.start_random_simulation()

# Stop simulation
simulator.stop_simulation()
```

## Troubleshooting

### Common Issues

1. **Sensors not detecting in hardware mode**:
   - Check wiring connections
   - Verify GPIO pin configuration in `config.py`
   - Run the sensor tester utility to isolate the issue

2. **Database errors**:
   - Check that the database migration has been applied
   - Use `check_migration_needed()` to verify

3. **Module not appearing in UI**:
   - Verify that visualization is enabled in configuration
   - Check PyQt5 installation

### Logging

The module uses the Python logging system. To enable debug logging:

```python
import logging
logging.getLogger('ir_module').setLevel(logging.DEBUG)
```

## License and Credits

The IR Sensor Module is part of the Rodent Refreshment Regulator (RRR) system.

- **Authors**: RRR Development Team
- **Version**: 0.1.0 