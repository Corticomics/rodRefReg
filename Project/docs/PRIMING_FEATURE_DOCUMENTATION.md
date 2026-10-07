# Priming Control Feature - Technical Documentation

## Overview

This document describes the **Priming Control Feature** - a modular, OOP-based system for manual relay control and tube priming in the RRR application.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Design Patterns & Best Practices](#design-patterns--best-practices)
3. [Implementation Details](#implementation-details)
4. [Usage Guide](#usage-guide)
5. [API Reference](#api-reference)
6. [Testing Strategy](#testing-strategy)
7. [Troubleshooting](#troubleshooting)

---

## Architecture

### Component Structure

```
Project/ui/
├── PrimingControlWidget.py    # Standalone priming control widget (NEW)
├── SettingsTab.py              # Settings tab (UPDATED - adds priming tab)
└── ...

Project/drivers/
├── solenoid_controller.py      # Solenoid hardware abstraction
└── ...

Project/gpio/
└── gpio_handler.py             # Low-level relay HAT control
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     SettingsTab                         │
│  (Composition: embeds PrimingControlWidget)             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ├── imports & instantiates
                         ↓
┌─────────────────────────────────────────────────────────┐
│              PrimingControlWidget                       │
│  • Modular QWidget for manual control                   │
│  • MVC pattern implementation                           │
│  • Encapsulated hardware logic                          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ├── uses (lazy initialization)
                         ↓
┌─────────────────────────────────────────────────────────┐
│          RelayControlModel                              │
│  • State management (master/cage relays)                │
│  • Observable pattern via Qt signals                    │
│  • Thread-safe operations                               │
└─────────────────────────────────────────────────────────┘
                         │
                         ├── delegates to
                         ↓
┌─────────────────────────────────────────────────────────┐
│  SolenoidController / IndependentSolenoidController     │
│  • Built by build_solenoid_controller (utils/topology)  │
│  • Master + cage relays (no master when independent)    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ├── uses
                         ↓
┌─────────────────────────────────────────────────────────┐
│            RelayHandler                                 │
│  • Low-level relay HAT control                          │
│  • I²C communication                                    │
└─────────────────────────────────────────────────────────┘
```

---

## Design Patterns & Best Practices

### 1. **Separation of Concerns**

- **PrimingControlWidget**: Self-contained UI + control logic
- **RelayControlModel**: State management only
- **SolenoidController**: Hardware abstraction
- **RelayHandler**: Low-level I²C operations

### 2. **Dependency Injection**

```python
# SettingsTab passes dependencies to PrimingControlWidget
priming_widget = PrimingControlWidget(
    settings=self.settings,                      # Injected configuration
    print_callback=self.print_to_terminal,       # Injected logging
    stop_schedule=self._stop_running_schedule,   # Stops a running schedule the way Stop does
)
```

### 3. **Lazy Initialization**

Hardware controllers are only created when first needed:

```python
def _get_solenoid_controller(self):
    if self._solenoid_controller is None:
        # Initialize hardware only on first use, for the topology this panel
        # was built for: SolenoidController (shared manifold) or
        # IndependentSolenoidController (no master valve)
        relay_handler = self._get_relay_handler()
        cage_map = self._build_cage_map()
        built_for = INDEPENDENT if self._independent else SHARED_MANIFOLD
        self._solenoid_controller = build_solenoid_controller(
            relay_handler, {**self.settings, SETTING_KEY: built_for}, cage_map
        )
    return self._solenoid_controller
```

### 4. **Observer Pattern (Qt Signals)**

Model emits signals when state changes; UI automatically updates:

```python
# Model emits signal
self._model.master_state_changed.emit(is_open)

# UI slot responds
def _on_master_state_changed(self, is_open: bool):
    # Update UI based on new state
```

### 5. **Single Responsibility Principle**

Each class has ONE clear responsibility:

- `RelayControlModel`: State tracking
- `PrimingControlWidget`: UI presentation & user interaction
- `SolenoidController`: Hardware commands
- `RelayHandler`: Low-level I²C

### 6. **Composition over Inheritance**

SettingsTab **composes** PrimingControlWidget rather than inheriting:

```python
# Composition (GOOD)
self.priming_control = PrimingControlWidget(...)

# vs. Inheritance (BAD)
# class SettingsTab(PrimingControlMixin): ...
```

### 7. **Error Handling Best Practices**

- **Graceful degradation**: UI remains functional even if hardware fails
- **User feedback**: Clear error messages via QMessageBox
- **Logging**: All operations logged for debugging
- **Fail-safe**: Emergency stop always accessible

---

## Implementation Details

### File 1: `PrimingControlWidget.py`

#### Key Classes

##### 1. `RelayControlModel`

**Purpose**: Centralized state management for relays

**Attributes**:
- `_master_open: bool` - Master solenoid state
- `_open_cages: Set[int]` - Set of open cage IDs

**Signals**:
- `master_state_changed(bool)` - Emitted when master state changes
- `cage_state_changed(int, bool)` - Emitted when cage state changes

**Methods**:
```python
set_master_open(is_open: bool) -> None
set_cage_open(cage_id: int, is_open: bool) -> None
is_cage_open(cage_id: int) -> bool
close_all_cages() -> None
reset() -> None
```

##### 2. `PrimingControlWidget`

**Purpose**: Complete UI for manual relay control

**Key Features**:
- Master solenoid control (open/close; shared-manifold topology only)
- Individual cage relay control
- Safety interlock (master must be open before cages, where a master exists)
- Emergency stop (close all relays)
- Status messages emitted to the main Terminal tab (in-widget Terminal tab was removed — see commit `1ba5a46`)
- Visual state indicators

**Public API**:
```python
__init__(settings: Dict, print_callback=None, stop_schedule=None)
cleanup() -> None  # Call when widget is destroyed
```

**Signals**:
```python
status_message = pyqtSignal(str)  # For parent logging
```

### File 2: `SettingsTab.py` (Updated)

#### Changes Made

1. **Import** the modular widget:
```python
from ui.PrimingControlWidget import PrimingControlWidget
```

2. **Create tab** using composition:
```python
def _create_priming_control(self):
    priming_widget = PrimingControlWidget(
        settings=self.settings,
        print_callback=self.print_to_terminal,
        stop_schedule=self._stop_running_schedule,
    )
    priming_widget.status_message.connect(self.print_to_terminal)
    return priming_widget
```

3. **Add to tab widget**:
```python
self.tab_widget.addTab(self.priming_control, "Priming")
```

---

## Usage Guide

### User Workflow

#### 1. **Access Priming Control**
- Navigate to: **Settings** → **Priming**

#### 2. **Prime Tubes on the Shared-Manifold Topology** (master valve; for the independent topology see 2b)

**Step 1: Open Master Solenoid**
1. Click **"Open Master"** button
2. Verify status shows: **"Status: OPEN [OK]"** (green)
3. Master close button becomes enabled

**Step 2: Open Target Cage Relay**
1. Select desired cage from dropdown
2. Click **"Open Selected"** button
3. Water flows through selected cage tube
4. Monitor Terminal tab for confirmation

**Step 3: Close Cage Relay**
1. Once primed (water flowing), click **"Close Selected"**
2. Verify closure in Terminal tab

**Step 4: Close Master**
1. Click **"Close Master"** button
2. Verify status shows: **"Status: CLOSED"** (gray)
3. The cages this panel opened are closed first, then the master. If a cage
   valve does not confirm closed, a *Hardware Error* names it; the master is
   still closed to cut its supply, and the priming session stays open until
   that valve is closed (**Close Selected**, or **CLOSE ALL RELAYS**). Cut the
   valve power if water still flows.

#### 2b. **Prime Tubes on the Independent Topology** (v1.21.0)

On a device set to `valve_topology = independent` (one syringe and one
valve per animal, no master valve — see `HARDWARE_SETUP.md` §7.2), the
Master Solenoid Control group is not shown and there is nothing to open
first:

1. Select the cage from the dropdown
2. Click **"Open Selected"** — water flows through that animal's line; the
   hardware lock is taken with the first valve opened
3. Click **"Close Selected"** once primed — the lock is released when the
   last open valve closes

**Check every syringe line daily.** A primed line holds for about three
days; a line left idle over a long weekend must be primed again before its
animal depends on it. The panel shows this reminder on the independent
topology.

#### 2c. **After the Valve Topology Changes in Settings** (v1.21.0)

The panel lays out its controls for the topology RRR started with. After a
change in **Settings → Delivery → Valve Topology**, **Open Master** and
**Open Selected** stay greyed out with the tooltip *"Restart RRR to prime
with the new valve topology"* until RRR is closed and reopened. **Close
Master**, **Close Selected** and **CLOSE ALL RELAYS** keep working. The
change itself is refused while a priming session is open, so no valve can
be left open across it.

#### 3. **Emergency Stop**
- Click **"CLOSE ALL RELAYS"** at any time
- Switches every relay on every HAT off: the master, where there is one, and every cage valve
- Stops a running schedule the way the **Stop** button does, then switches the relays off once more. The message then reads *All relays have been closed. The running schedule was stopped.* The schedule does not resume: animals it had not finished watering get no more water from it, and **Run** starts it over (staggered: every animal's whole dose again; instant: delivery times that have passed are skipped), so check what each animal has received before running it again
- If a HAT does not confirm the command, **Emergency Stop Failed** appears instead of *All relays have been closed*: disconnect the valve power supply, then check the relay HAT and its I²C connection. The panel keeps showing what may be open, and Run and calibration stay unavailable until a later **CLOSE ALL RELAYS** is confirmed or RRR is closed and reopened
- Use if unexpected behavior occurs

### Safety Features

1. **Interlock Protection** (shared-manifold topology)
   - Cage relays can only open when master is open
   - Prevents dry-running or hardware damage
   - On the independent topology there is no master; the lock follows the
     cage valves instead

2. **Close Master closes the cages first** (shared-manifold topology)
   - Closing the master first closes every cage this panel opened, one by one
   - A cage valve that does not confirm closed is named in a *Hardware Error*; the master is still closed to cut its supply, and the priming session stays open until that valve is closed: use **Close Selected** or **CLOSE ALL RELAYS**, and cut the valve power if water still flows

3. **Emergency Stop**
   - Direct hardware call first (bypasses software layers), then stops a running schedule and switches the relays off once more
   - Always accessible regardless of state
   - Frees the hardware lock only when every relay is confirmed off and nothing that can open a valve is still running

4. **Visual Feedback**
   - Color-coded buttons (green=safe, red=danger)
   - Real-time status indicators
   - Timestamped Terminal tab

---

## API Reference

### `RelayControlModel`

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `set_master_open()` | `is_open: bool` | `None` | Set master state, emit signal |
| `set_cage_open()` | `cage_id: int, is_open: bool` | `None` | Set cage state, emit signal |
| `is_cage_open()` | `cage_id: int` | `bool` | Check if cage is open |
| `close_all_cages()` | - | `None` | Close all cages, emit signals |
| `reset()` | - | `None` | Reset all states to closed |

#### Signals

| Signal | Parameters | Description |
|--------|-----------|-------------|
| `master_state_changed` | `bool` | Emitted when master state changes |
| `cage_state_changed` | `int, bool` | Emitted when cage state changes |

### `PrimingControlWidget`

#### Constructor

```python
PrimingControlWidget(settings: Dict, print_callback=None, stop_schedule=None)
```

**Parameters**:
- `settings`: System settings dict from SystemController
- `print_callback`: Optional logging function (e.g., `print_to_terminal`)
- `stop_schedule`: Optional callable that stops a running schedule the way the Stop button does and returns True if one was running; CLOSE ALL RELAYS calls it

#### Methods

| Method | Description |
|--------|-------------|
| `cleanup()` | Cleanup resources, close all relays (call on destroy) |
| `refresh_topology_state()` | Re-apply the Open button states after Settings changes the valve topology (Open stays greyed until restart) |

#### Signals

| Signal | Parameters | Description |
|--------|-----------|-------------|
| `status_message` | `str` | Emitted for all status/log messages |

---

## Testing Strategy

### Unit Testing

**Test files** (unit, no hardware; run with `pytest`):

- `Project/tests/unit/test_operation_gating.py`: priming takes and releases the hardware lock, and is refused, with its Open buttons greyed out, while a schedule holds it
- `Project/tests/unit/test_relay_write_failures.py`: an unconfirmed CLOSE ALL RELAYS says to cut the power and keeps the priming session; Close Master closes the master even when a cage did not close
- `Project/tests/unit/test_emergency_stop.py`: CLOSE ALL RELAYS stops a running schedule and frees the hardware lock only when every relay is confirmed off and nothing is still running
- `Project/tests/unit/test_settings_tab_valve_topology.py`: after a topology change in Settings, neither a shared nor an independent panel opens a valve until restart
- `Project/tests/unit/test_topology_construction_sites.py`: the panel builds the shared or the independent controller for its topology

There is no hardware integration test; use the manual checklist below on a rig.

### Manual Testing Checklist

- [ ] Master opens/closes correctly (shared manifold)
- [ ] Cage selector populates with correct relays
- [ ] Safety interlock prevents cage opening when master closed (shared manifold)
- [ ] Independent topology: no Master Solenoid Control group, a cage opens directly, and the daily syringe-line reminder shows
- [ ] After a topology change in Settings, Open Master and Open Selected stay greyed out until RRR is closed and reopened; Close and CLOSE ALL RELAYS still work
- [ ] Emergency stop closes all relays; pressed while a schedule runs it stops the schedule (Run comes back, no valve opens afterwards); with the relay HAT disconnected (power the Pi and the valve supply off to disconnect it, then start RRR) it shows **Emergency Stop Failed** and Run stays greyed out
- [ ] The main Terminal tab shows timestamped `[Priming HH:MM:SS]` messages
      when a valve is opened or closed and on emergency stop
- [ ] Button states update correctly
- [ ] Multiple cage relays can be controlled sequentially
- [ ] Cleanup properly closes all relays on widget destruction

---

## Troubleshooting

### Common Issues

#### 1. **"Failed to initialize relay handler"**

**Cause**: Relay HAT not detected or I²C bus issue

**Solutions**:
- Check relay HAT physical connection
- Verify I²C is enabled: `sudo raspi-config` → Interface → I2C
- Test I²C: `sudo i2cdetect -y 1`
- Check user in `i2c` group: `groups $USER`

#### 1b. **"Emergency Stop Failed"** (v1.21.0)

**Cause**: **CLOSE ALL RELAYS** could not confirm every relay HAT took the
command (a HAT missing at start-up or an I²C error), so a valve may still be
open. Before v1.21.0 the panel said "All relays have been closed" regardless.

**Solutions**:
- Disconnect the valve power supply, then check the relay HAT and its I²C
  connection (item 1)
- Run and calibration stay unavailable until **CLOSE ALL RELAYS** is
  confirmed: press it again once the HAT answers, or close and reopen RRR. An
  open priming session stays open, and closing its valves does not free the
  hardware (the tooltip then names *an unconfirmed emergency stop*). A
  schedule that was running has been stopped

#### 2. **"Master solenoid must be open before opening cage relays"**

**Cause**: Attempting to open cage while master is closed (safety feature)

**Solution**: Click "Open Master" button first. (This message cannot
appear on the independent topology, which has no master valve.)

#### 3. **Cage selector is empty**

**Cause**: The cage map could not be built: `num_hats` gives no relays, or the
stored `cage_relays` cannot be read (the Terminal tab then shows
`Error populating cage selector: …`). An empty `cage_relays` is not the cause:
RRR fills in the default map.

**Solutions**:
- Close and reopen RRR (the cage list is built when the panel is created)
- Check the `cage_relays` and `num_hats` rows in the `system_settings` table (settings live in the database since v1.5.0; `settings.json` is only read once, for migration)

#### 4. **Relays not responding**

**Causes & Solutions**:
- **Hardware**: Check 12V power supply to relay HAT
- **Software**: Verify `SM16relind` library installed
- **Permissions**: Ensure user in `dialout` and `i2c` groups
- **Emergency**: Use "CLOSE ALL RELAYS" to reset hardware state

#### 5. **Widget not appearing in Settings**

**Cause**: Import error or instantiation failure

**Solutions**:
- Check Python console for import errors
- Verify `PrimingControlWidget.py` exists in `Project/ui/`
- Check SettingsTab import: `from ui.PrimingControlWidget import PrimingControlWidget`

---

## Progress Toward Final Goal

### Completed (MS4 — Hardware Integration)

1. **Modular priming control system**
   - OOP-based architecture
   - Reusable components
   - Clean separation of concerns

2. **Safety features**
   - Hardware interlocks
   - Emergency stop
   - State management

3. **User experience**
   - Visual feedback
   - Logs to main Terminal tab
   - Error handling

4. **Best practices**
   - MVC pattern
   - Dependency injection
   - Lazy initialization
   - Observer pattern

### Next Steps (MS5 — Testing and Deployment)

1. **Testing**
   - [ ] Unit tests for `RelayControlModel`
   - [ ] Integration tests with hardware
   - [ ] User acceptance testing

2. **Documentation**
   - [x] Technical documentation
   - [ ] User manual with screenshots
   - [ ] Video tutorial

3. **Deployment**
   - [ ] Add priming to startup checklist
   - [ ] Include in installation guide
   - [ ] Create troubleshooting flowchart

---

## Code Change Summary

### New Files

#### `Project/ui/PrimingControlWidget.py` (NEW)
- **470 lines** of modular, reusable priming control
- **Classes**:
  - `RelayControlModel`: State management
  - `PrimingControlWidget`: UI + control logic
- **Key Features**:
  - Master/cage relay control
  - Safety interlocks
  - Emergency stop
  - Logs to main Terminal tab
  - Visual state indicators

### Modified Files

#### `Project/ui/SettingsTab.py` (UPDATED)
- **Added import**: `from ui.PrimingControlWidget import PrimingControlWidget`
- **Added method**: `_create_priming_control()` - instantiates widget via composition
- **Added tab**: "Priming" in settings tabs
- **Changes**: +16 lines (minimal, clean integration)

---

## Architectural Benefits

### 1. **Modularity**
- Priming logic isolated in dedicated widget
- Can be reused in other parts of application
- Easy to test independently

### 2. **Maintainability**
- Single source of truth for priming operations
- Clear responsibility boundaries
- Well-documented API

### 3. **Scalability**
- Easy to add new features (e.g., timed priming, volume tracking)
- Can extend `RelayControlModel` for advanced state management
- Widget can be embedded anywhere in application

### 4. **Testability**
- Pure model logic (no UI coupling)
- Mockable hardware interfaces
- Clear test boundaries

### 5. **User Experience**
- Consistent UI styling (Material Design)
- Real-time feedback
- Safety first (interlocks, emergency stop)

---

## Conclusion

The Priming Control Feature demonstrates **production-quality, OOP-based design** following industry best practices:

- **SOLID Principles**: Single Responsibility, Dependency Injection, Interface Segregation
- **Design Patterns**: MVC, Observer, Lazy Initialization, Composition
- **Clean Code**: Clear naming, documentation, error handling
- **Safety First**: Hardware interlocks, emergency controls, fail-safe design

This implementation provides a **robust, maintainable foundation** for manual hardware control and tube priming, advancing the project toward successful hardware integration and deployment (MS4 → MS5).

---

**End of Documentation**

