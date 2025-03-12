# Rodent Refreshment Regulator - Development Guide

This document provides technical information for developers who want to understand or contribute to the Rodent Refreshment Regulator (RRR) project. It covers the architecture, code organization, data flow, and contribution guidelines.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Code Organization](#code-organization)
- [Data Flow](#data-flow)
- [Hardware Interaction](#hardware-interaction)
- [User Interface](#user-interface)
- [Authentication System](#authentication-system)
- [Scheduling System](#scheduling-system)
- [Notification System](#notification-system)
- [Logging System](#logging-system)
- [Development Environment Setup](#development-environment-setup)
- [Testing Guidelines](#testing-guidelines)
- [Contribution Guidelines](#contribution-guidelines)

## Architecture Overview

The RRR follows the Model-View-Controller (MVC) architecture pattern:

- **Model**: Manages data, logic, and rules of the application.
- **View**: Handles the user interface components using PyQt5.
- **Controller**: Processes user inputs and updates both the model and view accordingly.

### Key Components:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      View       │     │    Controller   │     │      Model      │
│  (PyQt5 UI)     │◄───►│ (Input Handler) │◄───►│  (Data & Logic) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       ▲                       ▲
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User Input    │     │Hardware Control │     │   Database      │
│                 │     │ (GPIO & Relays) │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Code Organization

The project is structured as follows:

```
rodent-refreshment-regulator/
├── README.md                # User documentation
├── DEVELOPMENT.md           # Developer documentation
├── installer/               # Installation scripts and utilities
│   ├── main.py              # Installer entry point
│   ├── ui/                  # Installer UI components
│   ├── utils/               # Installer utility functions  
│   └── requirements.txt     # Python dependencies for installer
├── Project/                 # Main application code
│   ├── main.py              # Application entry point
│   ├── settings.json        # Configuration file
│   ├── rrr_database.db      # SQLite database
│   ├── models/              # Data models
│   │   ├── animal.py        # Animal data model
│   │   ├── Schedule.py      # Water schedule model
│   │   ├── database_handler.py # Database operations
│   │   ├── login_system.py  # User authentication model
│   │   ├── relay_unit.py    # Relay unit model
│   │   └── relay_unit_manager.py # Relay unit management
│   ├── views/ (ui/)         # UI components
│   │   ├── gui.py           # Main application window
│   │   ├── welcome_section.py # Welcome & instructions UI
│   │   ├── SettingsTab.py   # Settings configuration UI
│   │   ├── UserTab.py       # User management UI
│   │   ├── animals_tab.py   # Animal management UI
│   │   ├── schedules_tab.py # Schedule management UI
│   │   ├── HelpTab.py       # Help documentation UI
│   │   ├── run_stop_section.py # Run/stop controls
│   │   ├── terminal_output.py # Terminal display component
│   │   └── [additional UI components]
│   ├── controllers/         # Business logic
│   │   ├── system_controller.py   # System configuration
│   │   ├── pump_controller.py     # Pump control
│   │   ├── projects_controller.py # Project management
│   │   ├── schedule_controller.py # Schedule management
│   │   └── delivery_queue_controller.py # Water delivery management
│   ├── gpio/                # Hardware interaction
│   │   ├── gpio_handler.py  # GPIO pin control
│   │   ├── relay_worker.py  # Relay HAT worker thread
│   │   └── mock_gpio_handler.py # Mock for testing
│   ├── utils/               # Utility functions
│   │   ├── volume_calculator.py   # Water volume calculations
│   │   ├── timing_calculator.py   # Timing calculations
│   │   └── help_content_manager.py # Help content
│   ├── notifications/       # Notification systems
│   │   └── notifications.py # Notification handling
│   ├── settings/            # Settings management
│   │   └── config.py        # Configuration management
│   └── saved_settings/      # Saved configuration profiles
├── docs/                    # Additional documentation
│   └── FAQ.md               # Frequently asked questions
└── STL Files/               # 3D printing files for hardware
```

## Data Flow

The application's data flows through several key paths:

### 1. Configuration Flow

```
User Input → Controller → Model → Config File → Controller → Hardware
```

1. User inputs settings via the GUI
2. Controller processes and validates inputs
3. Model stores configuration
4. Configuration is saved to disk
5. Controller applies settings to hardware

### 2. Scheduling Flow

```
Schedule Model → Schedule Controller → Hardware Controller → Relay HAT → Pumps
```

1. Schedule model stores delivery timing and volume data
2. Schedule controller determines when to trigger deliveries
3. Hardware controller receives trigger commands
4. Commands are sent to relay HATs
5. Relays activate pumps to deliver water

### 3. Notification Flow

```
Hardware Event → Controller → Notification System → External Service
```

1. Hardware events (triggers, errors) are detected
2. Controller processes events
3. Notification system formats messages
4. Messages are sent to email/Slack services

### 4. Logging Flow

```
System Events → Logger → Terminal Display + Log Files
```

1. Events throughout the system are captured
2. Logger processes and formats messages
3. Messages are displayed in the terminal UI
4. Messages are also written to log files

## Hardware Interaction

The hardware control system interfaces with Sequent Microsystems Relay HATs using the GPIO pins on the Raspberry Pi.

### Key Classes:

- `gpio_handler.py`: Manages all hardware interactions through `RelayHandler` class
- `relay_worker.py`: Worker thread for asynchronous hardware operations
- `RelayUnitManager`: Manages relay units configuration
- `relay_unit.py`: Represents a relay unit and its operations

### HAT Communication:

The system uses Sequent Microsystems' library to communicate with the HATs. The `RelayHandler` class provides methods for:

- Initializing HATs based on their stack level
- Sending trigger commands to specific relays
- Reading HAT status
- Error detection and recovery

### Safety Mechanisms:

- Stagger timing between triggers to prevent power surges
- Validation of HAT addresses before operations
- Error handling for failed triggers
- Maximum daily water limits

## User Interface

The UI is built with PyQt5 and follows a tab-based organization.

### Main Components:

- `gui.py`: The application's main window class `RodentRefreshmentGUI`
- `welcome_section.py`: Provides instructions and overview
- `SettingsTab.py`: Detailed configuration settings
- `animals_tab.py`: Animal management
- `schedules_tab.py`: Schedule creation and management
- `run_stop_section.py`: Controls for starting and stopping delivery
- `terminal_output.py`: Displays system messages
- `HelpTab.py`: Provides searchable help content

### UI Data Binding:

The UI components connect to controllers using PyQt5's signal-slot mechanism:

```python
# Example of signal-slot connection
self.runButton.clicked.connect(self.controller.start_schedule)
self.settingsForm.valueChanged.connect(self.controller.update_settings)
```

## Authentication System

The authentication system allows different access levels based on user roles.

### Key Features:

- User registration and login
- Role-based permissions (Administrator, Technician, Observer)
- Password security with salted hashing
- Session management
- Guest mode with limited functionality

### Data Flow:

1. User enters credentials
2. Authentication controller validates credentials
3. User model is updated with permissions
4. UI elements are enabled/disabled based on permissions

## Scheduling System

The scheduling system manages when water is delivered to each animal.

### Components:

- `Schedule.py`: Data structure for delivery timing and volumes
- `schedule_controller.py`: Logic for running schedules
- `delivery_queue_controller.py`: System for managing delivery queue

### Scheduling Algorithms:

1. **Fixed Interval**: Water delivered at fixed time intervals
2. **Time Window**: Restricts deliveries to specific hours
3. **Staggered Delivery**: Prevents simultaneous triggers

## Notification System

The notification system alerts users to important events.

### Supported Methods:

- **Slack Notifications**: Using Slack's API through the slack_sdk

### Implementation:

```python
# Slack notification example (from notifications.py)
def send_slack_notification(self, message):
    if not self.slack_token or not self.channel_id:
        print("Slack credentials not set, skipping notification")
        return False
    
    try:
        response = self.client.chat_postMessage(
            channel=self.channel_id,
            text=message
        )
        return response["ok"]
    except Exception as e:
        print(f"Error sending Slack notification: {e}")
        return False
```

## Logging System

The logging system records system events for monitoring and debugging.

### Log Levels:

- `DEBUG`: Detailed information for debugging
- `INFO`: General information about system operation
- `WARNING`: Issues that don't prevent operation
- `ERROR`: Problems that prevent specific functions
- `CRITICAL`: System-wide failures

### Implementation:

The application uses stream redirection to capture output and display it in the UI terminal:

```python
# StreamRedirector from main.py
class StreamRedirector(QObject):
    message_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
    def write(self, message):
        if message.strip():
            self.message_signal.emit(message)
    def flush(self):
        pass
```

## Development Environment Setup

### Prerequisites:

- Python 3.6+
- PyQt5
- Raspberry Pi (for hardware testing)
- Sequent Microsystems Relay HATs (for hardware testing)

### Setup Steps:

1. **Clone the repository**:
   ```sh
   git clone https://github.com/yourusername/rodent-refreshment-regulator.git
   cd rodent-refreshment-regulator
   ```

2. **Create a virtual environment**:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```sh
   pip install -r installer/requirements.txt
   ```

4. **Run the installer** (if setting up for the first time):
   ```sh
   cd installer
   python main.py
   ```

5. **Run the application** (after installation):
   ```sh
   cd Project
   python main.py
   ```

### Running in Development Mode:

You can run the application with various test files for debugging hardware:

```sh
python test_relay_connection.py  # Test basic relay connectivity
python test_relay_diagnostic.py  # Run diagnostics
```

### Mock Hardware:

For development without physical hardware, use the mock hardware module by modifying the `gpio_handler.py` to use `mock_gpio_handler.py`.

## Testing Guidelines

For testing the RRR, focus on the following areas:

- **Unit Tests**: Test individual components such as schedule validation
- **Integration Tests**: Test component interactions like controller-model communication
- **UI Tests**: Test UI functionality using pytest-qt
- **Hardware Tests**: Use the provided test scripts for hardware interaction

### Writing Tests:

```python
# Example test approach for schedule validation
def test_schedule_validation():
    # Setup
    schedule = Schedule(name="Test Schedule", interval=60, triggers=2, window_start=8, window_end=20)
    
    # Test valid input
    assert schedule.is_valid() == True
    
    # Test invalid input
    schedule.interval = -10
    assert schedule.is_valid() == False
```

## Contribution Guidelines

### Submitting Changes:

1. Fork the repository
2. Create a new branch for your feature (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test your changes with the test scripts provided
5. Commit your changes (`git commit -am 'Add new feature'`)
6. Push to the branch (`git push origin feature/my-feature`)
7. Create a new Pull Request

### Code Style:

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Include docstrings for all functions, classes, and modules
- Keep functions short and focused on a single task

### Commit Messages:

Follow the conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: feat, fix, docs, style, refactor, test, chore

### Hardware Safety Guidelines:

When modifying hardware control code:

1. Never remove safety checks
2. Test extensively without animals before deployment
3. Include detailed comments explaining hardware interactions
4. Document changes to hardware control in both code and documentation

---

Thank you for contributing to the Rodent Refreshment Regulator project. By following these guidelines, you help ensure the reliability and safety of the system for researchers and their animals. 