# Rodent Refreshment Regulator - Development Guide

This document provides technical information for developers who want to understand or contribute to the Rodent Refreshment Regulator (RRR) project. It covers the architecture, code organization, data flow, and contribution guidelines.

> **Database schema, ERD, and `DatabaseHandler` method reference:** see
> [`DATABASE.md`](DATABASE.md). **Update system / release pipeline:** see
> [`UPDATE_SYSTEM.md`](UPDATE_SYSTEM.md). **Hardware bench-build procedure:**
> see [`HARDWARE_SETUP.md`](HARDWARE_SETUP.md).

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
rodRefReg/
├── README.md, QUICK_REFERENCE.md      # operator documentation
├── CHANGELOG.md, CONTRIBUTING.md, CLAUDE.md
├── install.sh, bootstrap.sh           # device installer entry points
├── requirements.txt, requirements-dev.txt, pytest.ini, ruff.toml
├── scripts/install/ runtime/ release/ systemd/
├── docs/brand/
└── Project/                           # the app (a release bundle ships Project/,
    │                                  #   scripts/ and requirements.txt)
    ├── main.py, version.py
    ├── models/ controllers/ gpio/ strategies/ drivers/ notifications/ utils/
    ├── ui/ (SettingsTab.py: Delivery / Calibration / Priming / General / Updates;
    │        style/: tokens.py, app.qss.tmpl, build_qss.py → app-light.qss, app-dark.qss)
    ├── tools/                         # bench CLIs (gravimetric_check.py, …), and:
    │   ├── solenoid_api_test.py       #   a SolenoidController smoke test (--dry-run)
    │   └── solenoid_bringup.py        #   relay bring-up; never with water connected
    ├── teensy_flow_reader/
    ├── tests/ (unit/ is the pytest suite; the scripts beside it are hardware CLIs)
    └── docs/ (this guide, MAINTENANCE.md, UPDATE_SYSTEM.md, …, STL Files/)
```

Settings and data are in the SQLite database (`~/rrr/shared/data` on a device,
`Project/` in a clone); Slack credentials are in `secrets.json` beside it.

## Data Flow

The application's data flows through four paths:

1. **Configuration:** Settings tab → `SystemController.save_settings` → the SQLite
   `system_settings` table (Slack credentials: `secrets.json`, mode 0600). RRR reads them
   at start.
2. **Scheduling:** RunStopSection → `main.run_program` → `RelayWorker` (its own
   `QThread`) → `SolenoidFlowStrategy` (`PumpStrategy` only in the legacy pump mode,
   which every start resets to solenoid) → `SolenoidController` → `RelayHandler` → relay
   HAT over I²C → solenoid valves.
3. **Notifications:** Slack only (`slack_sdk`).
4. **Logging:** what RRR prints before its main window is up goes to the terminal it was
   started from (the journal under `rrr.service`), then to the Terminal tab. Only
   start-up, close and crash records and the interrupted-runs line go to the debug log,
   `~/rrr/shared/logs/rrr_app_debug.log`. [CONTRIBUTING.md §6](../../CONTRIBUTING.md#6-hardware-adjacent-changes)
   says where each kind of line goes and how to read the journal.

## Hardware Interaction

The hardware control system interfaces with Sequent Microsystems 16-relay HATs over I²C (one stack level per HAT).

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
- Per-delivery limits, not daily ones: a pulse delivery that needs more than
  `max_pulses_per_delivery` (100) pulses, or would take longer than
  `max_pulse_delivery_time_s` (120 s), is refused before any water moves, and both
  are forced back to those values at every start; the schedule wizard takes
  0.10–50.00 mL per animal (`utils/schedule_volume.py`). Nothing caps what an animal
  gets in a day: several schedules, or a run started over, add up.
- Stop is the only way to end a running schedule: CLOSE ALL RELAYS, Close Selected and Log Out are greyed out and refused while one runs, and a Stop that cannot confirm every relay off, or whose delivery worker did not stop, hands the hardware lock to `EMERGENCY` until a CLOSE ALL RELAYS that confirms every relay off with the delivery worker stopped, or a restart

## User Interface

The UI is built with PyQt5 and uses a tab-based organization with a login gate.

### Main Components:

- `gui.py` — `RodentRefreshmentGUI` main window; hosts the tabbed Projects section and the Run/Stop section
- `login_gate_widget.py` — gates the Projects content behind authentication
- `projects_section.py` — container for the **Schedules**, **Animals**, **Wizard**, **Cages** tabs
- `schedules_hub.py` — Schedules tab; grid of schedule cards with search, multi-select, edit, drag-to-run
- `schedule_wizard.py` + `wizard_tab.py` — 4-step schedule creation wizard (Type → Animals → Parameters → Review)
- `cages_visualization_tab.py` — visual relay-board layout, inline cage naming
- `SettingsTab.py` — sub-tabs: **Delivery**, **Calibration**, **Priming**, **General**, **Updates** (`UpdatesTab.py`)
- `CalibrationWizard.py` — per-cage calibration flow, launched from Settings → Calibration
- `PrimingControlWidget.py` — prime tubing / valves
- `ScheduleProgressTracker.py` — Execution Monitor with live per-cage cards (appears as a second tab next to the Terminal during a run)
- `run_stop_section.py` — Run/Stop controls (gated by `login_system`)
- `HelpTab.py`, `UserTab.py`

### Themes:

RRR starts in the saved theme, dark by default (v2.1.0, released as 2.1.1). It draws
itself in Qt's Fusion style without the desktop's Qt theme: `main.py` calls
`detach_from_desktop_theme` before it makes the application, and `StyleManager` pins
Fusion as a second guard (`ui/style/theme.py`). Every colour is a role in
`ui/style/tokens.py`; `app-light.qss` and `app-dark.qss` are generated from
`app.qss.tmpl` by `ui/style/build_qss.py` and never edited by hand. See
[CONTRIBUTING.md §7](../../CONTRIBUTING.md#7-colours-and-themes).

### Cross-tab Synchronization:

Cage renaming uses an observer pattern: `CagesVisualizationTab.cage_names_updated` →
`SettingsTab.refresh_calibration_table`. The same names are read by the
Wizard via `database_handler.get_cages_for_dropdown()`.

### Lazy Hardware Initialization:

`main.setup()` builds the `RelayHandler` at start-up, on the GUI thread, and passes it
to each `RelayWorker`. The worker builds the rest of the hardware on its own `QThread`
when a schedule starts (`RelayWorker._initialize_hardware`: the flow sensor through
`create_flow_sensor`, then the solenoid controller), which keeps the serial port and the
sensor's start-up wait off the GUI thread. The Run/Stop section connects to the worker's
signals; the connections are reset between consecutive schedule runs (see
`run_stop_section.py` and commit `4c99f5a`).

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
- Two roles, normal and super: any logged-in user can switch with Settings > General >
  User Mode (*Switch to Super Mode*; no password is asked), and super sees every trainer's
  animals instead of only their own
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

- `models/Schedule.py` — schedule data structure (per-animal volumes, windows, mode)
- `gpio/relay_worker.py` — `RelayWorker` runs the schedule on its own thread
  (`run_staggered_cycle` / `run_instant_cycle`); both modes route deliveries
  through `_handle_delivery` → the active `DeliveryStrategy`
- `strategies/` — `StrategyFactory` picks `SolenoidFlowStrategy` (flow-sensor /
  pulse delivery) or `PumpStrategy` (legacy) by `hardware_mode`
- Run record: each run that starts delivering is recorded per animal
  (scheduled, planned, delivered, outcome) through
  `DatabaseHandler.start_schedule_run` / `finish_schedule_run`. The worker
  opens the record at its first due delivery (`_open_run_record`).
  `main._record_run_end` closes it once on the GUI thread, from
  `worker.finished` or from Stop. At start-up, before the GUI is built,
  `main._mark_interrupted_runs` marks the runs a crash left running as
  interrupted. See [STOP_AND_PARTIAL_DELIVERY.md](STOP_AND_PARTIAL_DELIVERY.md) §5
- `models/schedule_runs_repo.py` — the run history (`schedule_runs`,
  `schedule_run_animals`) behind `DatabaseHandler`; see
  [STOP_AND_PARTIAL_DELIVERY.md](STOP_AND_PARTIAL_DELIVERY.md) §4

### Delivery Modes:

1. **Instant** — animals receive their target volume at one or more specific times
2. **Staggered** — total target volume is divided uniformly across a user-defined time window
3. **Per-valve calibration** — calibration factors per cage stored in the DB and applied at runtime

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

- Python 3.11, as on Raspberry Pi OS Bookworm (CI also runs the suite on Ubuntu 24.04's
  Python 3.12; `ruff.toml` keeps 3.9 syntax as the floor)
- PyQt5 and pandas: apt on a Pi, pip on a Mac
  ([CONTRIBUTING.md §1](../../CONTRIBUTING.md#1-local-development-environment))
- For hardware testing: a Raspberry Pi with a Sequent Microsystems 16-relay HAT

### Setup Steps:

1. `git clone https://github.com/Corticomics/rodRefReg.git && cd rodRefReg`
2. On a Mac, in a venv (`python3 -m venv .venv && source .venv/bin/activate`):
   `python3 -m pip install PyQt5 pandas -r requirements.txt -r requirements-dev.txt`
3. On a Pi, install RRR with `./install.sh` (or the README's `bootstrap.sh` one-liner):
   it builds the release under `~/rrr` that a device runs.
4. Run from the clone: `cd Project && python3 main.py`. Without the launcher, `RRR_DATA`
   is unset, so the database is `Project/rrr_database.db` (a device uses
   `~/rrr/shared/data`) and in-app updates are unavailable. On a Pi, the next
   `./install.sh` copies such a database into `~/rrr/shared/data` when that folder has
   none.

### Hardware diagnostic scripts:

The scripts directly under `Project/tests/` are hardware CLIs that pytest does not
collect. On a Pi, run them with the venv's Python, which has the relay driver, and with
RRR closed: `~/rrr/shared/venv/bin/python3 ~/rodRefReg/Project/tests/test_relay_connection.py`
(and `test_relay_diagnostic.py`). Both switch relays on: run them only with no water
connected or the valve supply off.

### Mock Hardware:

Without the relay library (a laptop, or CI) the app still starts, but no relay HAT
initialises. When neither `SM16relind` nor `sm_16relind` can be imported,
`gpio/gpio_handler.py` prints `WARNING: SM16relind module not found. Hardware control will
not work.`, then `Failed to initialize hat stack=0: SM16relind class not found in module`
and `Failed to initialize any relay hats. …`. Every relay write then fails and says so
(`Relay N not switched: no initialised relay HAT for it (0 of 1 initialised)`; an all-off
prints `Relay HAT(s) missing: 0 of 1 initialised; …`): a delivery stops at its first valve
command (`[VALVE ERROR]`), a calibration fails at its first pulse, and CLOSE ALL RELAYS
shows Emergency Stop Failed (v1.21.0). For tests, use `FakeRelayHandler` from
`Project/tests/unit/conftest.py`: it records every write in order, so a test can assert
the exact relay sequence.

## Testing Guidelines

For testing the RRR, focus on the following areas:

- **Unit Tests**: Test individual components such as schedule validation
- **Integration Tests**: Test component interactions like controller-model communication
- **UI Tests**: plain pytest, with Qt offscreen (`QT_QPA_PLATFORM=offscreen`, which the
  Qt test files set and CI exports); no pytest-qt. Prefer Qt-free tests
  ([CONTRIBUTING.md §2](../../CONTRIBUTING.md#2-running-the-tests)).
- **Hardware Tests**: the diagnostic scripts above, on a dry rig. Two bench tools in
  `Project/tools/`, `solenoid_api_test.py` and `solenoid_bringup.py`, print their usage
  with `--help`. With `--dry-run` they open and close no valve, but they still build a
  `RelayHandler`, which switches every relay off on a Pi: run them with RRR closed.

### Writing Tests:

```python
# A Qt-free rule, tested on its own (Project/tests/unit/test_schedule_volume.py)
from utils.schedule_volume import schedule_amount

def test_the_amount_to_schedule_rounds_half_up():
    assert str(schedule_amount(0.365)) == "0.37"
```

## Contribution Guidelines

> **Releasing a change?** See [MAINTENANCE.md](MAINTENANCE.md) for the
> full recipe — when to cut a release, how to pick the SemVer bump,
> tagging procedure, CI verification, and recovery from a bad release.
> The section below is the short version for any PR.

### Submitting Changes:

Follow [CONTRIBUTING.md §3](../../CONTRIBUTING.md#3-branch-commit-pr-workflow)
([MAINTENANCE.md §7](MAINTENANCE.md#7-branch--commit-conventions) has the full
conventions): branch off `main` as `<type>/<short-kebab-slug>`, add a test with any
non-trivial change, run `pytest`, `ruff check .` and `ruff format --check .` from the repo
root, stage only this change's files, commit in Conventional Commits form, push the
branch and open a PR.

### Code Style:

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Include docstrings for all functions, classes, and modules
- Keep functions short and focused on a single task

### Commit Messages:

`<type>(<scope>): <one-line summary>`, the body saying why. Types: feat, fix, refactor,
test, docs, chore, style, perf, ci.

### Hardware Safety Guidelines:

When modifying hardware control code:

1. Never remove safety checks
2. Test extensively without animals before deployment
3. Include detailed comments explaining hardware interactions
4. Document changes to hardware control in both code and documentation

---

Thank you for contributing to the Rodent Refreshment Regulator project. By following these guidelines, you help ensure the reliability and safety of the system for researchers and their animals. 