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
│         SolenoidController                              │
│  • Hardware abstraction layer                           │
│  • Master + cage relay coordination                     │
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
    settings=self.settings,              # Injected configuration
    print_callback=self.print_to_terminal  # Injected logging
)
```

### 3. **Lazy Initialization**

Hardware controllers are only created when first needed:

```python
def _get_solenoid_controller(self):
    if self._solenoid_controller is None:
        # Initialize hardware only on first use
        self._solenoid_controller = SolenoidController(...)
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
- Master solenoid control (open/close)
- Individual cage relay control
- Safety interlock (master must be open before cages)
- Emergency stop (close all relays)
- Status messages emitted to the main Terminal tab (in-widget Terminal tab was removed — see commit `1ba5a46`)
- Visual state indicators

**Public API**:
```python
__init__(settings: Dict, print_callback=None)
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
        print_callback=self.print_to_terminal
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

#### 2. **Prime Tubes (Standard Procedure)**

**Step 1: Open Master Solenoid**
1. Click **"Open Master"** button
2. Verify status shows: **"Status: OPEN"** (green)
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
3. All cages automatically closed for safety

#### 3. **Emergency Stop**
- Click **"CLOSE ALL RELAYS"** at any time
- Immediately closes master + all cages
- Use if unexpected behavior occurs

### Safety Features

1. **Interlock Protection**
   - Cage relays can only open when master is open
   - Prevents dry-running or hardware damage

2. **Auto-Close on Master Close**
   - Closing master automatically closes all cages
   - Ensures consistent state

3. **Emergency Stop**
   - Direct hardware call (bypasses software layers)
   - Always accessible regardless of state

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
PrimingControlWidget(settings: Dict, print_callback=None)
```

**Parameters**:
- `settings`: System settings dict from SystemController
- `print_callback`: Optional logging function (e.g., `print_to_terminal`)

#### Methods

| Method | Description |
|--------|-------------|
| `cleanup()` | Cleanup resources, close all relays (call on destroy) |

#### Signals

| Signal | Parameters | Description |
|--------|-----------|-------------|
| `status_message` | `str` | Emitted for all status/log messages |

---

## Testing Strategy

### Unit Testing

**Test File**: `tests/ui/test_priming_control.py`

```python
def test_model_state_management():
    """Test RelayControlModel state tracking."""
    model = RelayControlModel()
    
    # Test master state
    assert not model.is_master_open
    model.set_master_open(True)
    assert model.is_master_open
    
    # Test cage state
    model.set_cage_open(1, True)
    assert model.is_cage_open(1)
    assert 1 in model.get_open_cages()

def test_safety_interlock():
    """Test that cages cannot open when master is closed."""
    # Mock hardware
    widget = PrimingControlWidget({}, lambda x: None)
    
    # Try to open cage without master
    # Should show warning dialog
    # Cage should remain closed
```

### Integration Testing

**Test File**: `tests/integration/test_priming_hardware.py`

```python
def test_hardware_priming_sequence():
    """Test complete priming sequence with real hardware."""
    widget = PrimingControlWidget(settings, logger)
    
    # 1. Open master
    widget._on_open_master_clicked()
    assert widget._model.is_master_open
    
    # 2. Open cage
    widget._on_open_cage_clicked()
    # Verify actual relay state via hardware readback
    
    # 3. Close sequence
    widget._on_close_master_clicked()
    assert not widget._model.is_master_open
    assert len(widget._model.get_open_cages()) == 0
```

### Manual Testing Checklist

- [ ] Master opens/closes correctly
- [ ] Cage selector populates with correct relays
- [ ] Safety interlock prevents cage opening when master closed
- [ ] Emergency stop closes all relays
- [ ] Activity log shows timestamped messages
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

#### 2. **"Master solenoid must be open before opening cage relays"**

**Cause**: Attempting to open cage while master is closed (safety feature)

**Solution**: Click "Open Master" button first

#### 3. **Cage selector is empty**

**Cause**: No cage relay mapping configured

**Solutions**:
- Go to Hardware tab → verify `cage_relays` setting
- Run `system_controller.ensure_solenoid_defaults()` to auto-generate mapping
- Check `settings.json` for `cage_relays` key

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

