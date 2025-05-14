# RRR Data Analysis Module Proposal

## Executive Summary

This document outlines the implementation of a comprehensive data analysis module for the Rodent Refreshment Regulator (RRR) system. The primary focus is on enabling circadian rhythm studies through advanced visualization and analysis of water consumption patterns, with a flexible architecture designed to accommodate additional data types in the future. The tool will integrate seamlessly with the existing system while providing robust export capabilities for external statistical analysis.

## Background

The RRR system currently manages automated water delivery to research animals, ensuring precise control over hydration. With the addition of IR beam-break sensors at water delivery points, we can now capture real-time data on drinking behavior. This new capability creates an opportunity to develop sophisticated analysis tools that will significantly enhance the research value of the system.

## Proposed Data Analysis Module

### Core Capabilities

The proposed module will:

1. **Track consumption behavior** using IR beam-break sensors
2. **Visualize temporal patterns** with customizable time bins (1-60 minutes)
3. **Generate simple visualizations** (heatmaps, activity plots, event timelines)
4. **Calculate relevant statistics** for behavioral analysis
5. **Export structured data** for external complex analysis
6. **Support cross-animal comparisons** for experimental and control groups

### Technical Implementation

#### 1. Architecture Overview

The implementation follows a layered architecture with clear separation of concerns:

```
┌─────────────────────┐       ┌───────────────────────┐       ┌───────────────────┐
│ IR Sensor Hardware  │──────▶│ IRSensorController    │──────▶│ DrinkEventManager │
│ (per animal cage)   │       │ (interrupt-based)     │       │ (data processing) │
└─────────────────────┘       └───────────────────────┘       └─────────┬─────────┘
                                                                         │
                                                                         ▼
┌─────────────────────┐       ┌───────────────────────┐       ┌───────────────────┐
│ Data Analysis Tool  │◀──────│ DrinkingDataModel     │◀──────│ DatabaseHandler   │
│ (rhythmic analysis) │       │ (data aggregation)    │       │ (persistence)     │
└─────────┬───────────┘       └───────────────────────┘       └───────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ DataAnalysisTab (new UI component with visualizations and export functions)     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### 2. Database Schema Extensions

The system will require two new tables to store drinking behavior data:

```sql
-- New table for individual drinking events
CREATE TABLE drinking_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
);

-- New table for aggregated drinking sessions 
CREATE TABLE drinking_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    total_duration_ms INTEGER NOT NULL,
    estimated_volume_ml REAL NOT NULL,
    schedule_id INTEGER,
    FOREIGN KEY(animal_id) REFERENCES animals(animal_id),
    FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id)
);
```

#### 3. Data Acquisition Layer

The system will use an interrupt-driven approach for optimal accuracy and reliability:

##### IRSensorController Class

```python
class IRSensorController:
    """Controls IR sensor input using GPIO interrupts with sophisticated noise filtering"""
    
    def __init__(self, gpio_pin, relay_unit_id, callback_manager, debounce_ms=300):
        self.gpio_pin = gpio_pin
        self.relay_unit_id = relay_unit_id
        self.callback_manager = callback_manager
        self.debounce_ms = debounce_ms
        self.last_trigger_time = 0
        self.session_active = False
        self.session_start_time = None
        self.setup_gpio()
        
    def setup_gpio(self):
        # Configure GPIO pin with pull-up resistor and falling edge detection
        GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            self.gpio_pin, 
            GPIO.FALLING,  # Trigger when beam is broken
            callback=self._handle_interrupt,
            bouncetime=self.debounce_ms
        )
    
    def _handle_interrupt(self, channel):
        current_time = time.time() * 1000  # ms precision
        
        # Start new session or continue existing one
        if not self.session_active:
            self.session_active = True
            self.session_start_time = current_time
            # Emit session start event
            self.callback_manager.queue_event({
                'type': 'session_start',
                'relay_unit_id': self.relay_unit_id,
                'timestamp': current_time
            })
        
        # Update last trigger time
        self.last_trigger_time = current_time
        
        # Schedule session end check
        Timer(1.0, self._check_session_end).start()
    
    def _check_session_end(self):
        current_time = time.time() * 1000
        # If no new triggers for 1 second, end the session
        if self.session_active and (current_time - self.last_trigger_time > 1000):
            self.session_active = False
            session_duration = current_time - self.session_start_time
            
            # Emit session end event
            self.callback_manager.queue_event({
                'type': 'session_end',
                'relay_unit_id': self.relay_unit_id,
                'start_time': self.session_start_time,
                'end_time': current_time,
                'duration_ms': session_duration
            })
```

#### 4. Event Processing Layer

##### DrinkEventManager Class

```python
class DrinkEventManager(QObject):
    """
    Manages drinking events, handles thread synchronization, and emits Qt signals
    """
    session_started = pyqtSignal(int, float)  # relay_unit_id, timestamp
    session_ended = pyqtSignal(int, float, float, float)  # relay_unit_id, start, end, duration
    
    def __init__(self, database_handler, animal_relay_mapping):
        super().__init__()
        self.database_handler = database_handler
        self.animal_relay_mapping = animal_relay_mapping
        self.event_queue = Queue()
        self.running = True
        
        # Start the event processing thread
        self.process_thread = Thread(target=self._process_events)
        self.process_thread.daemon = True
        self.process_thread.start()
        
    def queue_event(self, event):
        """Thread-safe method to add events to the queue"""
        self.event_queue.put(event)
        
    def _process_events(self):
        """Background thread for processing events from the queue"""
        while self.running:
            try:
                # Get event with timeout to allow clean shutdown
                event = self.event_queue.get(timeout=1.0)
                self._handle_event(event)
                self.event_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logging.error(f"Error processing drink event: {e}")
    
    def _handle_event(self, event):
        """Process a single drinking event"""
        if event['type'] == 'session_start':
            # Map relay unit to animal
            animal_id = self._get_animal_for_relay(event['relay_unit_id'])
            if animal_id:
                # Emit Qt signal on the main thread
                QMetaObject.invokeMethod(
                    self, 
                    "session_started", 
                    Qt.QueuedConnection,
                    Q_ARG(int, animal_id),
                    Q_ARG(float, event['timestamp'])
                )
        
        elif event['type'] == 'session_end':
            animal_id = self._get_animal_for_relay(event['relay_unit_id'])
            if animal_id:
                # Save to database
                self._save_drinking_session(
                    animal_id,
                    event['start_time'],
                    event['end_time'],
                    event['duration_ms']
                )
                
                # Emit Qt signal
                QMetaObject.invokeMethod(
                    self, 
                    "session_ended", 
                    Qt.QueuedConnection,
                    Q_ARG(int, animal_id),
                    Q_ARG(float, event['start_time']),
                    Q_ARG(float, event['end_time']),
                    Q_ARG(float, event['duration_ms'])
                )
    
    def _save_drinking_session(self, animal_id, start_time, end_time, duration_ms):
        """Save session data to database"""
        # Convert to datetime objects
        start_dt = datetime.fromtimestamp(start_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)
        
        # Estimate volume based on duration
        # Assuming 0.1ml per second of drinking as a baseline
        estimated_volume = (duration_ms / 1000) * 0.1
        
        # Create session record
        session_id = self.database_handler.add_drinking_session(
            animal_id, 
            start_dt.isoformat(),
            end_dt.isoformat(),
            duration_ms,
            estimated_volume
        )
        
        # Also log individual event for more detailed analysis
        self.database_handler.add_drinking_event(
            animal_id,
            start_dt.isoformat(),
            duration_ms,
            session_id
        )
    
    def _get_animal_for_relay(self, relay_unit_id):
        """Map relay unit ID to current animal ID using schedule data"""
        return self.animal_relay_mapping.get_animal_for_relay(relay_unit_id)
        
    def shutdown(self):
        """Clean shutdown of the event processing thread"""
        self.running = False
        self.process_thread.join(timeout=2.0)
```

#### 5. Data Management Layer - Database Extensions

```python
# Add to existing DatabaseHandler class

def add_drinking_session(self, animal_id, start_time, end_time, duration_ms, estimated_volume):
    """Add a new drinking session to the database"""
    try:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO drinking_sessions (
                    animal_id, start_time, end_time, 
                    total_duration_ms, estimated_volume_ml
                )
                VALUES (?, ?, ?, ?, ?)
            ''', (
                animal_id, start_time, end_time, 
                duration_ms, estimated_volume
            ))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error adding drinking session: {e}")
        traceback.print_exc()
        return None

def add_drinking_event(self, animal_id, timestamp, duration_ms, session_id):
    """Add a new drinking event to the database"""
    try:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO drinking_events (
                    animal_id, timestamp, duration_ms, session_id
                )
                VALUES (?, ?, ?, ?)
            ''', (
                animal_id, timestamp, duration_ms, session_id
            ))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error adding drinking event: {e}")
        traceback.print_exc()
        return None

def get_drinking_data_for_animal(self, animal_id, start_date=None, end_date=None):
    """Get drinking data for an animal, optionally within a date range"""
    try:
        with self.connect() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    s.session_id,
                    s.start_time,
                    s.end_time,
                    s.total_duration_ms,
                    s.estimated_volume_ml
                FROM drinking_sessions s
                WHERE s.animal_id = ?
            '''
            
            params = [animal_id]
            
            if start_date:
                query += " AND datetime(s.start_time) >= datetime(?)"
                params.append(start_date)
                
            if end_date:
                query += " AND datetime(s.end_time) <= datetime(?)"
                params.append(end_date)
                
            query += " ORDER BY datetime(s.start_time)"
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
    except sqlite3.Error as e:
        print(f"Database error retrieving drinking data: {e}")
        traceback.print_exc()
        return []

def get_circadian_drinking_pattern(self, animal_id, days=7, bin_minutes=5):
    """Get binned drinking data for circadian analysis"""
    try:
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Calculate the date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get all events within the time range
            cursor.execute('''
                SELECT timestamp, duration_ms, estimated_volume_ml
                FROM drinking_sessions
                WHERE animal_id = ?
                AND datetime(start_time) >= datetime(?)
                AND datetime(end_time) <= datetime(?)
                ORDER BY datetime(start_time)
            ''', (
                animal_id,
                start_date.isoformat(),
                end_date.isoformat()
            ))
            
            # Process results into time bins appropriate for circadian analysis
            results = cursor.fetchall()
            binned_data = self._bin_circadian_data(results, bin_minutes)
            
            return binned_data
            
    except sqlite3.Error as e:
        print(f"Database error retrieving circadian pattern: {e}")
        traceback.print_exc()
        return []
```

#### 6. Visualization Interface

The Data Analysis Tab provides a comprehensive UI for visualizing and analyzing drinking patterns:

```python
class DataAnalysisTab(QWidget):
    """Tab for analyzing drinking patterns with focus on circadian rhythms"""
    
    def __init__(self, database_handler, parent=None):
        super().__init__(parent)
        self.database_handler = database_handler
        self.current_animal = None
        self.bin_size_minutes = 5  # Default bin size
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main layout
        layout = QVBoxLayout()
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        # Animal selector
        animal_layout = QHBoxLayout()
        animal_layout.addWidget(QLabel("Select Animal:"))
        self.animal_selector = QComboBox()
        self.animal_selector.currentIndexChanged.connect(self.on_animal_changed)
        animal_layout.addWidget(self.animal_selector)
        header_layout.addLayout(animal_layout)
        
        # Time range selector
        time_range_layout = QHBoxLayout()
        time_range_layout.addWidget(QLabel("Period:"))
        self.time_range = QComboBox()
        self.time_range.addItems(["24 Hours", "7 Days", "30 Days", "Custom..."])
        self.time_range.currentIndexChanged.connect(self.on_time_range_changed)
        time_range_layout.addWidget(self.time_range)
        header_layout.addLayout(time_range_layout)
        
        # Bin size selector
        bin_layout = QHBoxLayout()
        bin_layout.addWidget(QLabel("Bin Size:"))
        self.bin_size = QComboBox()
        self.bin_size.addItems(["1 minute", "5 minutes", "15 minutes", "30 minutes", "60 minutes"])
        self.bin_size.setCurrentIndex(1)  # Default to 5 minutes
        self.bin_size.currentIndexChanged.connect(self.on_bin_size_changed)
        bin_layout.addWidget(self.bin_size)
        header_layout.addLayout(bin_layout)
        
        # Visualization type selector
        viz_layout = QHBoxLayout()
        viz_layout.addWidget(QLabel("View:"))
        self.viz_type = QComboBox()
        self.viz_type.addItems(["24-Hour Heatmap", "Daily Activity", "Event Timeline"])
        self.viz_type.currentIndexChanged.connect(self.update_visualization)
        viz_layout.addWidget(self.viz_type)
        header_layout.addLayout(viz_layout)
        
        # Export button
        self.export_button = QPushButton("Export to CSV")
        self.export_button.clicked.connect(self.export_data)
        header_layout.addWidget(self.export_button)
        
        layout.addLayout(header_layout)
        
        # Visualization area using matplotlib
        self.figure = plt.Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Stats area
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(100)
        layout.addWidget(self.stats_text)
        
        self.setLayout(layout)
        
        # Load animals
        self.load_animals()
```

### Hardware Integration

#### 1. Hardware Requirements

- **Raspberry Pi 5** (existing)
- **Sequent Microsystems 16-relay HAT** (existing)
- **IR Break-Beam Sensors** (one per cage/water delivery point)
  - Recommended: 3-5mm break-beam IR sensor pair
  - Operating voltage: 3.3V (compatible with Raspberry Pi GPIO)
  - Output: Digital (HIGH when beam intact, LOW when broken)

#### 2. Physical Setup

1. **Sensor Placement:** Mount IR emitter and detector on opposite sides of the water delivery bowl/spout with beam positioned to be broken when animal drinks
2. **Wiring Configuration:**
   - Connect IR emitter VCC to 3.3V
   - Connect IR detector VCC to 3.3V
   - Connect GND pins to Raspberry Pi GND
   - Connect IR detector output to Raspberry Pi GPIO pin
3. **GPIO Pin Assignment:**
   - Use available GPIO pins not utilized by the relay HAT
   - Maintain pin assignments in configuration file for flexibility

#### 3. Implementation Steps

1. **Hardware Installation:**
   - Install IR sensors at each water delivery point
   - Connect to available GPIO pins on Raspberry Pi 5
   - Secure connections to prevent disruption during operation

2. **Software Installation:**
   ```bash
   pip install RPi.GPIO pandas matplotlib
   ```

3. **Database Schema Update:**
   - Add tables for drinking_events and drinking_sessions
   - Update database_handler.py to include new methods

4. **Application Configuration:**
   - Add sensor configuration settings to settings.json
   - Map GPIO pins to specific relay units

5. **Integration with Main Application:**
   - Add IR sensor initialization to main application startup
   - Add the Data Analysis Tab to the UI
   - Connect event signals to UI updates

### Application to Circadian Rhythm Research

This tool is specifically designed to support research investigating circadian effects of automated water delivery:

1. **Pattern Identification**: Clearly visualize natural drinking rhythms
2. **Intervention Effects**: Compare patterns before/after experimental manipulations
3. **Individual Differences**: Identify outliers or subgroups with distinct patterns
4. **Correlation with Biomarkers**: Support analysis alongside ELISA measurements of stress and hydration (corticosterone, vasopressin, angiotensin II)

The system captures data with minute-level resolution while providing aggregation options (5-60 minute bins) to reduce noise and highlight meaningful patterns.

### Advantages

1. **Data Quality**:
   - Hardware interrupts ensure no drinking events are missed
   - Sophisticated session detection with debouncing prevents false readings
   - Thread-safe design prevents data loss even under high load

2. **Research Value**:
   - Captures natural behavior patterns non-invasively
   - Supports standard circadian rhythm analysis methodologies
   - Facilitates correlation with other physiological measures

3. **Flexibility**:
   - Modular design accommodates future sensor types
   - Customizable visualizations for different analysis needs
   - Raw data export for specialized statistical tools

4. **Maintainability**:
   - Clean architecture with separation of concerns
   - Extensive error handling and recovery mechanisms
   - Comprehensive logging for troubleshooting

## Technical Requirements

### Hardware
- Raspberry Pi 5 (existing)
- IR break-beam sensors (one per water delivery point)
- Sequent Microsystems 16-relay HAT (existing)
- GPIO connections for sensors

### Software Dependencies
- Python 3.x
- PyQt5 (existing)
- Matplotlib/PyQtGraph for visualization
- Pandas for data processing
- RPi.GPIO for hardware interface

## Integration with Main RRR Application

The IR sensor and data analysis components will integrate seamlessly with the existing RRR application architecture. This section details the integration points and implementation approach.

### 1. Main Application Integration

The IR sensor system will be initialized during the main application startup sequence in `main.py`. The following modifications will be made:

```python
def setup():
    global relay_handler, app_settings, gui, notification_handler, controller, database_handler, login_system, system_controller, ir_sensor_manager
    
    # Existing initialization code...
    database_handler = DatabaseHandler()
    system_controller = SystemController(database_handler)
    app_settings = system_controller.settings
    
    # Initialize relay components
    relay_unit_manager = RelayUnitManager(app_settings)
    relay_handler = RelayHandler(relay_unit_manager, app_settings['num_hats'])
    
    # Initialize the IR sensor system
    ir_sensor_manager = IRSensorManager(
        database_handler=database_handler,
        system_controller=system_controller,
        relay_unit_manager=relay_unit_manager
    )
    
    # Continue with existing initialization...
    controller = ProjectsController()
    pump_controller = PumpController(relay_handler, database_handler)
    controller.pump_controller = pump_controller
    
    # Create GUI with the new data analysis tab
    gui = RodentRefreshmentGUI(
        run_program,
        stop_program,
        change_relay_hats,
        system_controller=system_controller,
        database_handler=database_handler,
        login_system=login_system,
        relay_handler=relay_handler,
        notification_handler=notification_handler,
        ir_sensor_manager=ir_sensor_manager  # Pass the IR manager to the GUI
    )
    
    # Add the data analysis tab to the GUI
    gui.data_analysis_tab = DataAnalysisTab(
        database_handler=database_handler,
        ir_sensor_manager=ir_sensor_manager
    )
```

### 2. RelayWorker Integration

The `RelayWorker` class will be extended to maintain the mapping between relay units and animals, which is crucial for associating IR sensor events with the correct animals:

```python
class RelayWorker(QObject):
    # Existing signal declarations...
    drinking_event_detected = pyqtSignal(int, float)  # animal_id, timestamp
    
    def __init__(self, settings, relay_handler, notification_handler, system_controller):
        # Existing initialization...
        
        # Store animal-relay mapping for IR sensor events
        self.current_animal_mapping = {}
        
    def run_staggered_cycle(self):
        # Existing code...
        
        # Update the current animal mapping for IR sensor association
        for animal_id, window in self.animal_windows.items():
            if window['start'] <= current_time <= window['end']:
                relay_unit_id = window['relay_unit']
                self.current_animal_mapping[relay_unit_id] = animal_id
                
        # Share the mapping with the IR sensor manager
        if hasattr(self.system_controller, 'ir_sensor_manager'):
            self.system_controller.ir_sensor_manager.update_animal_mapping(
                self.current_animal_mapping
            )
        
        # Continue with existing code...
```

### 3. GPIO Handler Integration

The `IRSensorManager` will leverage the existing GPIO infrastructure with dedicated handling for IR sensors:

```python
class IRSensorManager:
    def __init__(self, database_handler, system_controller, relay_unit_manager):
        self.database_handler = database_handler
        self.system_controller = system_controller
        self.relay_unit_manager = relay_unit_manager
        
        # Load sensor configuration from settings
        self.settings = system_controller.settings.get('ir_sensors', {})
        
        # Create event manager
        self.event_manager = DrinkEventManager(database_handler, self)
        
        # Initialize sensor controllers
        self.sensor_controllers = {}
        self._initialize_sensors()
        
    def _initialize_sensors(self):
        """Initialize IR sensors from configuration"""
        sensor_config = self.settings.get('sensor_mapping', {})
        
        for relay_unit_id, gpio_pin in sensor_config.items():
            try:
                # Create sensor controller for each configured relay unit
                self.sensor_controllers[relay_unit_id] = IRSensorController(
                    gpio_pin=gpio_pin,
                    relay_unit_id=int(relay_unit_id),
                    callback_manager=self.event_manager,
                    debounce_ms=self.settings.get('debounce_ms', 300)
                )
                print(f"Initialized IR sensor for relay unit {relay_unit_id} on GPIO pin {gpio_pin}")
            except Exception as e:
                print(f"Failed to initialize IR sensor for relay unit {relay_unit_id}: {e}")
    
    def update_animal_mapping(self, mapping):
        """Update the current animal-to-relay mapping"""
        self.animal_relay_mapping = mapping
        
    def get_animal_for_relay(self, relay_unit_id):
        """Get the animal ID currently associated with a relay unit"""
        return self.animal_relay_mapping.get(relay_unit_id)
        
    def shutdown(self):
        """Clean shutdown of all IR sensor components"""
        for controller in self.sensor_controllers.values():
            if hasattr(controller, 'cleanup'):
                controller.cleanup()
        
        if self.event_manager:
            self.event_manager.shutdown()
```

### 4. Thread Management and Signal Handling

The system uses PyQt's signal/slot mechanism for thread-safe communication:

```python
# In main.py
def cleanup():
    global thread, worker, ir_sensor_manager
    
    # Existing cleanup code...
    
    # Shutdown IR sensor system
    if ir_sensor_manager:
        ir_sensor_manager.shutdown()
        
    # Continue with existing cleanup...
```

### 5. Database Migrations

The system will automatically create the required tables during application startup:

```python
# In database_handler.py
def initialize_database(self):
    """Initialize database with all required tables"""
    try:
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Existing table creation code...
            
            # Create drinking event tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drinking_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    animal_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    session_id INTEGER NOT NULL,
                    FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drinking_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    animal_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    total_duration_ms INTEGER NOT NULL,
                    estimated_volume_ml REAL NOT NULL,
                    schedule_id INTEGER,
                    FOREIGN KEY(animal_id) REFERENCES animals(animal_id),
                    FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id)
                )
            ''')
            
            # Add indices for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_animal ON drinking_events (animal_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON drinking_events (timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_animal ON drinking_sessions (animal_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_time ON drinking_sessions (start_time, end_time)')
            
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
```

### 6. Configuration Integration

The system will store IR sensor configuration in the same settings system used by the main application:

```json
{
  "ir_sensors": {
    "sensor_mapping": {
      "1": 17,
      "2": 18,
      "3": 27,
      "4": 22
    },
    "debounce_ms": 300,
    "min_session_duration_ms": 500,
    "max_session_gap_ms": 1000
  }
}
```

### 7. User Interface Integration

The Data Analysis Tab will be added to the main application's tabbed interface:

```python
# In gui.py
def setup_ui(self):
    # Existing UI setup code...
    
    # Create tab widget if it doesn't exist
    if not hasattr(self, 'tab_widget'):
        self.tab_widget = QTabWidget()
        self.central_layout.addWidget(self.tab_widget)
    
    # Add existing tabs...
    
    # Add the new Data Analysis tab
    if hasattr(self, 'data_analysis_tab'):
        self.tab_widget.addTab(self.data_analysis_tab, "Data Analysis")
```

### 8. Error Handling and Recovery

The IR sensor system includes robust error handling integrated with the existing error management:

```python
# In IRSensorController
def setup_gpio(self):
    try:
        # GPIO setup code...
    except Exception as e:
        logging.error(f"GPIO setup error for pin {self.gpio_pin}: {e}")
        # Report to notification system if available
        if hasattr(self, 'notification_handler') and self.notification_handler:
            self.notification_handler.send_slack_notification(
                f"IR sensor error on relay unit {self.relay_unit_id}: {e}"
            )
```

### 9. Startup/Shutdown Sequence

The complete startup and shutdown sequence ensures proper initialization and cleanup:

1. Application starts
2. Database initialized with new tables if needed
3. GPIO and relay systems initialized
4. IR sensor system initialized and linked to existing database and relay mapping
5. UI created with new Data Analysis tab
6. On shutdown, all GPIO resources properly released
7. Database connections closed cleanly

This integration approach minimizes changes to existing code while providing a complete new capability that works seamlessly with the current application architecture.

## Future Extensibility

While initially focused on circadian rhythm analysis, the module's architecture supports future expansion:

1. **Additional Sensor Types**
   - Weight sensors for real-time body mass monitoring
   - Temperature sensors for thermoregulation studies
   - Activity sensors for coordinated behavior analysis

2. **Advanced Analytics**
   - Machine learning for pattern detection
   - Anomaly detection for health monitoring
   - Cross-correlation with environmental factors

3. **Integration with External Systems**
   - Export to specialized research software
   - Integration with institutional data repositories
   - API access for automated analysis pipelines

This design ensures the RRR system can grow with research needs while maintaining its core reliability and ease of use.

