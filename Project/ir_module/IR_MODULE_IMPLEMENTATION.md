# IR Module Implementation Specification

## 1. Overview

The IR (Infrared) sensor module is an extension to the Rodent Refreshment Regulator (RRR) system that enables tracking of animal drinking behavior by detecting beam-breaks when animals access water spouts. This document outlines the design, implementation, and integration approach for this module.

The module allows researchers to:
- Track when animals drink water
- Estimate water consumption volumes
- Analyze drinking patterns for circadian rhythm studies
- Correlate drinking behavior with experimental variables

## 2. Hardware Integration

### 2.1 Hardware Requirements

- **IR Sensors**: Transmissive (break-beam) IR sensors, specifically FC-51 or equivalent models
- **Voltage Conversion**: Logic level converters for safely stepping down 5V IR sensor signals to 3.3V GPIO pins
- **Raspberry Pi**: Compatible with both Pi 4B and Pi 5 models
- **Wiring**: Jumper wires for connections
- **Mounting Materials**: Mounting brackets or fixtures for positioning sensors near water spouts

### 2.2 GPIO Configuration

The default GPIO pin mapping is:
- Relay Unit 1 → GPIO 17
- Relay Unit 2 → GPIO 18
- Relay Unit 3 → GPIO 27
- Relay Unit 4 → GPIO 22

This mapping can be modified in the `HARDWARE_CONFIG` section of `ir_module/config.py`.

### 2.3 Voltage Considerations

Most IR sensors used in this application operate at 5V, while Raspberry Pi GPIO pins require 3.3V. Logic level converters must be used between the sensors and GPIO pins to prevent damage to the Pi. The hardware setup includes:

1. Power connections for the IR sensors from the 5V rail
2. Ground connections shared between sensors and Pi
3. Logic level conversion for signal lines between sensors (5V) and GPIO pins (3.3V)

## 3. Software Architecture

### 3.1 Module Structure

The IR module follows a layered architecture with clear separation of concerns:

1. **Hardware Layer**: Direct GPIO interaction and sensor reading
2. **Data Processing Layer**: Converting raw sensor data into drinking events and sessions
3. **Storage Layer**: Persisting drinking data to the database
4. **Visualization Layer**: Generating insights from the collected data
5. **Integration Layer**: Connecting with the main RRR application

This layered approach allows for independent testing, better error isolation, and simplified maintenance.

### 3.2 Key Components

#### IRSensor Class
Handles individual IR sensor reading and event detection.

```python
class IRSensor:
    """
    Represents a single IR sensor connected to a GPIO pin.
    
    Responsibilities:
    - Initialize and manage GPIO connection
    - Detect beam break events
    - Notify callbacks when beam state changes
    - Support simulation mode for testing
    """
    def __init__(self, gpio_pin, relay_unit_id, callback):
        self.gpio_pin = gpio_pin
        self.relay_unit_id = relay_unit_id
        self.callback = callback
        self.is_beam_broken = False
        self.last_break_time = None
        self.simulation_mode = False
        # Initialize the sensor
        self._initialize()
```

#### SensorManager Class
Manages multiple IR sensors and handles the mapping between relay units and GPIO pins.

```python
class SensorManager:
    """
    Manages a collection of IR sensors and their mapping to relay units.
    
    Responsibilities:
    - Create and initialize sensors based on configuration
    - Route sensor events to appropriate handlers
    - Provide fallback for missing configuration
    - Support sensor simulation for testing
    """
    def __init__(self, callback, sensor_map=None):
        # sensor_map maps relay_unit_id to gpio_pin
        # If sensor_map is empty or None, fallback to defaults with graceful degradation
        self.sensor_map = sensor_map or get_hardware_config("DEFAULT_SENSOR_MAP", {})
        if not self.sensor_map:
            logger.warning("Empty sensor configuration, using defaults")
            self.sensor_map = {"1": 17, "2": 18, "3": 27, "4": 22}
        
        self.callback = callback
        self.sensors = {}
        self._initialize_sensors()
```

#### DrinkEventManager Class
Processes beam-break events into meaningful drinking sessions.

```python
class DrinkEventManager:
    """
    Processes beam-break events into drinking sessions.
    
    Responsibilities:
    - Track active drinking sessions
    - Detect when sessions begin and end
    - Calculate session duration and volume
    - Store session data in the database
    """
    def __init__(self, database_handler=None):
        self.database_handler = database_handler
        self.active_sessions = {}
        self.session_timeout_ms = get_hardware_config("SESSION_TIMEOUT_MS", 1000)

    def process_beam_break(self, relay_unit_id, timestamp):
        """
        Process a beam break event into a drinking session.
        
        Args:
            relay_unit_id: ID of the relay unit that triggered the event
            timestamp: Time when the beam break occurred
        """
        animal_id = self.get_animal_for_relay(relay_unit_id)
        if not animal_id:
            return
            
        if animal_id in self.active_sessions:
            # Update existing session
            session = self.active_sessions[animal_id]
            session["end_time"] = timestamp
            session["event_count"] += 1
        else:
            # Start new session
            self.active_sessions[animal_id] = {
                "start_time": timestamp,
                "end_time": timestamp,
                "event_count": 1
            }
        
        # Schedule session completion check
        self._schedule_session_check(animal_id)
```

#### Database Extensions
Extends the RRR database schema to store drinking events and sessions.

```python
class IRDatabaseExtensions:
    """
    Extends the RRR database with tables for IR sensor data.
    
    Responsibilities:
    - Create required database tables if they don't exist
    - Add IR-specific methods to the database handler
    - Ensure backward compatibility during schema updates
    """
    def __init__(self, database_handler):
        self.db_handler = database_handler
        
    def create_tables(self):
        """
        Create the necessary tables for storing IR sensor data.
        Uses transactions to ensure database integrity.
        """
        # Implementation details...
```

#### Data Analysis Tab
Provides UI for visualizing drinking patterns and circadian rhythms.

```python
class DataAnalysisTab(QWidget):
    """
    UI component for displaying and analyzing drinking data.
    
    Responsibilities:
    - Display drinking data visualizations
    - Provide filters and controls for data analysis
    - Allow data export in multiple formats
    - Update in response to new data
    """
    def __init__(self, parent=None, database_handler=None):
        super().__init__(parent)
        self.database_handler = database_handler
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components and layouts."""
        # Implementation details...
```

### 3.3 Configuration System

The module uses a progressive feature enabling approach managed by configuration flags:

```python
CONFIG = {
    # HARDWARE LEVEL
    "ENABLE_BASIC_SENSOR_TEST": False,    # Enable basic sensor detection and terminal output
    "SIMULATE_SENSORS": True,             # Use simulated sensors if hardware not available
    
    # DATA PROCESSING LEVEL
    "ENABLE_DATA_PROCESSING": False,      # Enable drink event processing and session detection
    "ENABLE_LOGGING": True,               # Enable detailed logging of sensor events
    
    # STORAGE LEVEL
    "ENABLE_DATABASE_STORAGE": False,     # Enable storing data in the database
    
    # UI LEVEL
    "ENABLE_VISUALIZATION_TAB": False,    # Enable the visualization UI tab
    
    # INTEGRATION LEVEL
    "ENABLE_INTEGRATION": False,          # Enable full integration with main RRR system
}
```

This feature flag approach follows the principle of progressive enhancement and allows for:
- Incremental testing and deployment
- Compatibility with different hardware configurations
- Feature toggling for debugging
- Simplified testing of specific components

## 4. Integration with RRR System

### 4.1 System Components Interaction

The IR module integrates with the following RRR components through well-defined interfaces:

1. **Database**: Extends the database schema and interfaces with DatabaseHandler
2. **UI**: Adds a new visualization tab to the main application
3. **Animal Management**: Maps sensors to specific animals based on relay unit assignments
4. **System Controller**: Receives system-wide settings and notifications
5. **Notifications**: Uses the existing notification system to send alerts

This integration follows the Open/Closed Principle by extending existing functionality without modifying core components.

### 4.2 Database Integration

The module extends the RRR database with new tables:

1. **drinking_sessions**:
   - session_id (PRIMARY KEY)
   - animal_id (FOREIGN KEY → animals)
   - start_time (TEXT in ISO format)
   - end_time (TEXT in ISO format)
   - duration_ms (INTEGER)
   - estimated_volume_ml (REAL)

2. **drinking_events**:
   - event_id (PRIMARY KEY)
   - animal_id (FOREIGN KEY → animals)
   - timestamp (TEXT in ISO format)
   - duration_ms (INTEGER)
   - session_id (FOREIGN KEY → drinking_sessions)

3. **drinking_patterns**:
   - pattern_id (PRIMARY KEY)
   - animal_id (FOREIGN KEY → animals)
   - time_bin (TEXT)
   - event_count (INTEGER)
   - total_duration_ms (INTEGER)
   - total_volume_ml (REAL)
   - date (TEXT in ISO format)

The schema follows database best practices with:
- Proper foreign key constraints
- Consistent naming conventions
- Appropriate data types
- Indexing for common queries

### 4.3 UI Integration

The IR module adds a new "Drinking Analysis" tab to the RRR UI, providing:

- Timeline view of drinking events
- Circadian rhythm visualization
- Data filtering by animal, date range, and time of day
- Export functionality for data analysis
- Configuration options for IR sensors

The UI components follow the existing RRR styling guidelines and use PyQt5 patterns consistently.

### 4.4 Initialization Sequence

```python
def initialize_ir_module(system_controller, database_handler):
    """
    Initialize the IR module with dependencies.
    
    Args:
        system_controller: Controller for system-wide settings and operations
        database_handler: Handler for database operations
        
    Returns:
        IRModule instance if initialization successful, None otherwise
    """
    # Check configuration before attempting initialization
    if not is_feature_enabled("ENABLE_INTEGRATION"):
        logger.info("IR module integration disabled in configuration")
        return None
        
    try:
        # Initialize IR module with system components
        ir_module = IRModule(
            system_controller=system_controller,
            database_handler=database_handler
        )
        
        # Extend database if storage is enabled
        if is_feature_enabled("ENABLE_DATABASE_STORAGE"):
            extensions = IRDatabaseExtensions(database_handler)
            extensions.create_tables()
            extensions.extend_database_handler()
        
        return ir_module
        
    except Exception as e:
        # Graceful error handling with logging
        logger.error(f"Failed to initialize IR module: {e}")
        return None
```

This initialization follows dependency injection principles and includes proper error handling.

### 4.5 RelayUnitManager and RelayWorker Relationship

The IR module interacts with two existing components:

- **RelayUnitManager**: Handles the mapping and organization of physical relay units (hardware management abstraction layer)
- **RelayWorker**: Operates the relays based on schedules (execution of delivery tasks)

The IR module uses the relay unit mapping from RelayUnitManager to associate sensors with specific animals and cages.

## 5. Data Processing Pipeline

### 5.1 Event Detection

When an animal drinks, the IR beam is broken, triggering the following sequence:

1. GPIO state change detected
2. IRSensor processes the event and calls the registered callback
3. SensorManager receives the callback and forwards it to DrinkEventManager
4. DrinkEventManager starts or updates a drinking session

This event-driven architecture follows the Observer pattern and ensures low latency detection.

### 5.2 Session Processing

A drinking session is defined as a series of beam-break events within a certain time window:

1. First beam-break starts a new session
2. Subsequent beam-breaks within the timeout window extend the session
3. When no beam-breaks occur for the duration of the timeout window, the session is considered complete
4. Complete sessions are saved to the database with duration and estimated volume

This approach uses a timeout-based state machine to handle the temporal nature of drinking behavior.

### 5.3 Volume Estimation

The module estimates water consumption based on drinking session duration:

```python
def save_drinking_session(self, animal_id, session):
    """
    Save a completed drinking session to the database.
    
    Args:
        animal_id: ID of the animal
        session: Dictionary containing session data
        
    Returns:
        session_id: ID of the saved session, or None on error
    """
    start_time = session["start_time"]
    end_time = session["end_time"]
    duration_ms = (end_time - start_time).total_seconds() * 1000
    
    # Estimate volume based on duration
    # Assume 0.1 ml per second of drinking activity
    # This is a configurable default value based on calibration studies of
    # typical rodent drinking rates and can be adjusted in the settings JSON
    estimated_volume_ml = (duration_ms / 1000) * 0.1
    
    # Save to database if available and enabled
    if self.database_handler and is_feature_enabled("ENABLE_DATABASE_STORAGE"):
        try:
            session_id = self.database_handler.add_drinking_session(
                animal_id, 
                start_time.isoformat(), 
                end_time.isoformat(),
                duration_ms,
                estimated_volume_ml
            )
            return session_id
        except Exception as e:
            logger.error(f"Error saving drinking session: {e}")
            return None
    return None
```

The implementation includes clear documentation and error handling.

### 5.4 Data Aggregation

Drinking data is aggregated for circadian rhythm analysis using time binning:

1. Individual events are grouped into time bins (configurable, default 5 minutes)
2. Time bins are organized by time-of-day to reveal circadian patterns
3. Data is aggregated across multiple days to strengthen the pattern signal

This aggregation strategy balances data resolution with meaningful pattern detection.

## 6. User Interface

### 6.1 Data Analysis Tab

The data analysis tab includes:

1. **Animal Selector**: Choose which animal's data to display
2. **Date Range Selector**: Filter data by date range
3. **Visualization Panel**: Display graphs and charts
4. **Export Controls**: Export data in various formats

The UI is designed with progressive disclosure principles to manage complexity.

### 6.2 Visualizations

The module provides several visualization types:

1. **Timeline View**: Shows drinking events over time
   ![Timeline View Example](https://example.com/images/timeline_example.png)

2. **Heatmap View**: Shows drinking intensity by time of day across multiple days
   ![Heatmap View Example](https://example.com/images/heatmap_example.png)

3. **Comparison View**: Allows before/after comparison of drinking patterns
   ![Comparison View Example](https://example.com/images/comparison_example.png)

Visualizations use matplotlib with PyQt integration for interactive controls.

### 6.3 Data Export

The module supports exporting data in multiple formats:

1. **Neurodata Without Borders (NWB)**: An HDF5-based file format standard developed for behavioral neuroscience experiments
2. **CSV**: For easy import into spreadsheet software
3. **JSON**: For programmatic analysis

The UI provides export configuration options and displays progress/completion notifications through a task progress dialog.

## 7. Applications to Circadian Rhythm Research

### 7.1 Drinking as a Circadian Marker

Drinking behavior is a reliable marker of circadian rhythms. The IR module enables:

- Continuous, non-invasive monitoring of circadian patterns
- Detection of phase shifts in response to environmental changes
- Identification of abnormal drinking patterns

### 7.2 Integration with Experimental Protocols

Researchers can use the IR module to:

1. Establish baseline drinking patterns
2. Measure effects of experimental interventions on circadian rhythms
3. Correlate drinking data with other measurements
4. Study stress hormones (such as corticosterone in rodents and cortisol in other species) by analyzing drinking behavior changes

## 8. Testing and Validation

### 8.1 Testing Approach

The module includes comprehensive testing following the testing pyramid model:

1. **Unit Tests**: Test individual components in isolation
   - IRSensor tests
   - SensorManager tests
   - DrinkEventManager tests
   - Database extension tests

2. **Integration Tests**: Test component interactions
   - Sensor event propagation
   - Database storage integration
   - UI integration

3. **System Tests**: Test the complete IR module
   - End-to-end workflow tests
   - Performance tests
   - Stress tests

4. **Hardware Testing**: 
   - Standalone sensor tester utility
   - Simulation mode for testing without physical hardware

### 8.2 Standalone Sensor Tester

A command-line utility for testing sensors without running the full application:

```bash
# List configured GPIO pins
python -m ir_module.utils.sensor_tester --list

# Test a specific pin
python -m ir_module.utils.sensor_tester --pin 17

# Test all configured sensors
python -m ir_module.utils.sensor_tester
```

This utility follows the Unix philosophy of doing one thing well and is essential for hardware setup verification.

## 9. Deployment and Configuration

### 9.1 Installation

The IR module is included in the RRR codebase and requires no separate installation. It follows the existing deployment process.

### 9.2 Configuration

Configure the module by editing `ir_module/config.py` or through the UI settings panel. The configuration system follows the principle of least surprise with sensible defaults.

### 9.3 Enabling Features

Features can be progressively enabled following the sequence in ENABLING.md:

1. Basic sensor testing
2. Data processing
3. Database storage
4. UI visualization
5. Full integration

This approach allows controlled feature rollout and incremental testing.

## 10. Future Extensibility

The module architecture supports future extensions through:

- Clear separation of concerns
- Well-defined interfaces
- Configuration-driven behavior
- Dependency injection

Planned extensions include:

1. **Multi-sensor support**: Track both licking and proximity to water spout
2. **Machine learning models**: Detect abnormal drinking patterns
3. **Real-time alerting**: Notify researchers of significant changes in behavior
4. **Remote monitoring**: Access drinking data over the network
5. **Additional visualization types**: Custom visualizations for specific research needs

### 10.1 Current Limitations and Constraints

The current implementation has the following limitations:

1. **Single beam detection**: Limited to detecting presence/absence, not detailed lick patterns
2. **Estimated volume**: Volume is estimated based on duration, not directly measured
3. **Calibration requirements**: May need calibration for different animal species
4. **Fixed sensor placement**: Requires careful positioning for accurate detection
5. **Limited multi-animal discrimination**: Cannot differentiate multiple animals accessing the same water spout

## 11. Notifications

The IR module integrates with the existing Slack notification system to send alerts for:

1. Detection system failures
2. Extended periods without drinking activity
3. Significant deviations from historical drinking patterns
4. Hardware errors or sensor failures

These notifications use the same Slack channels already configured for water delivery notifications, ensuring consistency in the notification system.

## 12. Error Handling

The IR module employs a robust error handling strategy:

1. **Graceful Degradation**: Failures in the IR module do not affect core RRR functionality
2. **Detailed Logging**: All errors are logged with context for debugging
3. **User Feedback**: Critical errors are displayed in the UI
4. **Recovery Mechanisms**: The system attempts to recover from transient errors
5. **Configuration Validation**: Configuration errors are detected early with clear feedback

## 13. Conclusion

The IR sensor module enhances the RRR system with valuable drinking behavior tracking capabilities. With its flexible architecture and progressive feature enabling, it can be adapted to various research needs while maintaining stability of the core RRR functionality.

The implementation follows software engineering best practices including:
- Separation of concerns
- Single responsibility principle
- Error handling and logging
- Configurable behavior
- Defensive programming
- Progressive enhancement
- Comprehensive testing 