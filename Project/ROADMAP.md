# Rodent Refreshment Regulator - Development Roadmap

## Version: 2.1.0 (Sprint Complete) → 2.2.0 (Next Sprint)

**Last Updated:** December 27, 2025  
**Sprint Duration:** 2 weeks  
**Methodology:** Agile/Scrum with Test-Driven Development (TDD)

### Sprint 2.1.0 Summary
- **Completed:** 17 story points across 8 tasks
- **Pass Rate:** 97.6% (41/42 automated tests)
- **Key Deliverables:** Security gating, timer overflow fix, UI consistency, button states

---

## 1. Testing Summary (49 Samples Collected)

### 1.1 Test Results Overview

| Metric | Value | Status |
|--------|-------|--------|
| Total Samples | 49 | ✅ |
| Hardware Mode | Solenoid + Pulse Delivery | ✅ |
| Valve Calibration | Per-cage calibration active | ✅ |
| Flow Sensor | Optional mode (calibration fallback) | ✅ |

### 1.2 Known Issues Identified

| ID | Category | Severity | Description | Status |
|----|----------|----------|-------------|--------|
| BUG-001 | Security | **High** | Controls accessible without login | ✅ Fixed (Dec 27) |
| BUG-002 | UI | Medium | Progress tracker inconsistent styling | ✅ Fixed (Dec 27) |
| BUG-003 | UI | Medium | Settings tab text cutoff | ✅ Fixed (Dec 27) |
| BUG-004 | Backend | **High** | Timer overflow for long schedules (32-bit int) | ✅ Fixed (Dec 27) |
| BUG-005 | Hardware | Medium | Valve circuit diagnostics needed | 🟡 Investigation |
| BUG-006 | UI | Low | Button states not resetting after stop | ✅ Fixed (Dec 27) |

---

## 2. Architecture Assessment

### 2.1 Current Architecture (MVC)

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  gui.py (Main Window)                                            │
│  ├── UserTab (Authentication)                                   │
│  ├── SettingsTab (Configuration)                                │
│  ├── ProjectsSection → LoginGateWidget                          │
│  │   ├── SchedulesTab                                           │
│  │   └── AnimalsTab                                             │
│  ├── RunStopSection (⚠️ NOT GATED)                              │
│  │   ├── ScheduleProgressTracker                                │
│  │   └── ScheduleDropArea                                       │
│  └── HelpTab                                                    │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BUSINESS LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  controllers/                                                    │
│  ├── system_controller.py (Settings, State Management)          │
│  ├── schedule_controller.py (Schedule Logic)                    │
│  └── delivery_queue_controller.py (Delivery Orchestration)      │
│                                                                  │
│  strategies/                                                     │
│  ├── solenoid_flow_strategy.py (Pulse-based delivery)           │
│  └── pump_strategy.py (Legacy time-based delivery)              │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│  models/                                                         │
│  ├── database_handler.py (SQLite ORM)                           │
│  ├── login_system.py (Authentication State)                     │
│  ├── animal.py, Schedule.py, relay_unit.py                      │
│  └── relay_unit_manager.py                                      │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       HARDWARE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  gpio/                                                           │
│  ├── gpio_handler.py (I2C Relay HAT Control)                    │
│  └── relay_worker.py (QThread for async hardware ops)           │
│                                                                  │
│  drivers/                                                        │
│  ├── solenoid_controller.py (Valve Logic)                       │
│  ├── uart_flow_sensor.py (Teensy Bridge)                        │
│  └── i2c_coordinator.py (Bus Conflict Prevention)               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Security Gap Analysis

**Finding:** `RunStopSection` bypasses authentication gate.

**Current Flow:**
```python
# gui.py - Current Implementation
self.projects_section = ProjectsSection(...)
self.login_gate = LoginGateWidget(self.projects_section, self.login_system)  # ✅ Gated
left_layout.addWidget(self.login_gate)

self.run_stop_section = RunStopSection(...)  # ⚠️ NOT GATED
right_layout.addWidget(self.run_stop_section)
```

**Required Flow:**
```python
# All operational controls must check login status
# Either via LoginGateWidget or internal permission checks
```

---

## 3. Sprint Backlog (Current)

### 3.1 Priority 1: Security & Critical Bugs ✅ COMPLETE

| Task ID | Story Points | Description | Status |
|---------|--------------|-------------|--------|
| SEC-001 | 3 | Gate RunStopSection controls behind login | ✅ Done |
| SEC-002 | 2 | Add permission checks to Run/Stop/Edit buttons | ✅ Done |
| BUG-004 | 3 | Fix timer overflow (cap to 2 weeks) | ✅ Done |

### 3.2 Priority 2: UI Consistency ✅ COMPLETE

| Task ID | Story Points | Description | Status |
|---------|--------------|-------------|--------|
| UI-001 | 2 | Unify ScheduleProgressTracker styling with QSS theme | ✅ Done |
| UI-002 | 2 | Fix Settings tab label truncation | ✅ Done |
| UI-003 | 1 | Remove inline styles, use CSS variables | ✅ Done |
| UI-004 | 1 | Fix button state transitions (Run/Stop) | ✅ Done |

### 3.3 Priority 3: UX Improvements ✅ COMPLETE

| Task ID | Story Points | Description | Status |
|---------|--------------|-------------|--------|
| UX-001 | 2 | Add visual feedback for disabled controls in guest mode | ✅ Done |
| UX-002 | 1 | Improve "Drop Schedule Here" placeholder styling | 🟡 Deferred |

---

## 4. Technical Debt Register

| ID | Component | Issue | Impact | Effort |
|----|-----------|-------|--------|--------|
| TD-001 | ScheduleProgressTracker | Inline CSS styles bypass theme | Medium | Low |
| TD-002 | relay_worker.py | 32-bit timer overflow possible | High | Low |
| TD-003 | SettingsTab | QFormLayout doesn't handle long labels | Medium | Low |
| TD-004 | Multiple UI files | Mixed styling (inline + QSS) | Low | Medium |

---

## 5. Implementation Plan

### Phase 1: Security Hardening (Days 1-2)

1. **Add login gate to RunStopSection controls**
   - Reference: [PyQt5 QStackedWidget](https://doc.qt.io/qt-5/qstackedwidget.html)
   - Pattern: Follow existing `LoginGateWidget` implementation

2. **Add explicit permission checks**
   - Check `login_system.is_logged_in()` before any operation
   - Disable buttons visually when not logged in

### Phase 2: Timer Overflow Fix (Day 2)

1. **Cap QTimer.singleShot delays**
   - Reference: [Qt QTimer Documentation](https://doc.qt.io/qt-5/qtimer.html#singleShot)
   - Qt uses 32-bit signed int (max ~24.8 days in ms)
   - Cap to 1 hour (3,600,000 ms), reschedule as needed

### Phase 3: UI Consistency (Days 3-4)

1. **Remove inline styles from ScheduleProgressTracker**
   - Use objectName + QSS selectors
   - Reference: [Qt Style Sheets](https://doc.qt.io/qt-5/stylesheet-syntax.html)

2. **Fix Settings tab label width**
   - Use `QFormLayout.setLabelAlignment()`
   - Add `min-width` to labels via QSS

### Phase 4: Testing & Validation (Day 5)

1. Manual testing of all permission gates
2. UI regression testing
3. Hardware integration verification

---

## 6. Acceptance Criteria

### SEC-001: Controls Gated Behind Login ✅ VERIFIED
- [x] Run button disabled when not logged in
- [x] Stop button disabled when not logged in
- [x] Edit Schedule button disabled when not logged in
- [x] Change Relay Hats button disabled when not logged in
- [x] Drop Schedule area shows login prompt when not logged in
- [x] Visual indication (grayed out) when controls are disabled

### BUG-004: Timer Overflow Fixed ✅ VERIFIED
- [x] Schedules with >24 day windows don't crash
- [x] Timer reschedules correctly after 2-week cap
- [x] No "argument overflowed" exceptions in logs

### UI-001: Consistent Styling ✅ VERIFIED
- [x] ScheduleProgressTracker uses theme colors
- [x] No inline `setStyleSheet()` calls in MaterialCard
- [x] Progress bars match app-wide style

### UI-004: Button State Transitions ✅ VERIFIED
- [x] Run button shows "Starting..." immediately on click
- [x] Run button transitions to "Running" after prep
- [x] Stop button shows "Stopping..." during stop
- [x] Both buttons reset to initial text after stop completes

---

## 7. Definition of Done

- [ ] Code reviewed and approved
- [ ] Unit tests pass (where applicable)
- [ ] Manual testing completed
- [ ] No new linter errors
- [ ] Documentation updated
- [ ] Committed with conventional commit message

---

## 8. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing schedules with timer fix | Low | High | Test with 1-year schedule edge case |
| UI changes affect usability | Medium | Medium | A/B test with lab users |
| Permission changes lock out users | Low | High | Keep guest mode for viewing only |

---

## 9. Next Sprint Preview

- Hardware diagnostic mode (valve circuit testing)
- Automated calibration verification
- Export delivery logs to CSV
- Multi-Pi network support (JConeDataBase integration)

---

## Appendix A: File Change Matrix

| File | Changes Required |
|------|------------------|
| `ui/gui.py` | Add login state observer for RunStopSection |
| `ui/run_stop_section.py` | Add permission checks, visual disabled state |
| `ui/ScheduleProgressTracker.py` | Remove inline styles, add objectNames |
| `ui/style/app-light.qss` | Add MaterialCard, ProgressTracker selectors |
| `ui/style/app-dark.qss` | Add MaterialCard, ProgressTracker selectors |
| `gpio/relay_worker.py` | Cap timer delays to prevent overflow |
| `ui/SettingsTab.py` | Fix form layout label sizing |

---

*Document maintained by: Development Team*  
*Review cycle: Per sprint*

