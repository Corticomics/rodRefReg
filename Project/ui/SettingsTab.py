import base64
import json
import os
from datetime import datetime

import pandas as pd
from cryptography.fernet import Fernet
from models.animal import Animal
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.PrimingControlWidget import PrimingControlWidget
from ui.UpdatesTab import UpdatesTab
from ui.widgets.safe_spinbox import SafeDoubleSpinBox, SafeSpinBox


class SettingsTab(QWidget):
    settings_updated = pyqtSignal(dict)

    def __init__(
        self,
        system_controller,
        suggest_callback=None,
        push_callback=None,
        save_slack_callback=None,
        run_stop_section=None,
        login_system=None,
        print_to_terminal=None,
        database_handler=None,
        notification_handler=None,
    ):
        super().__init__()

        if not system_controller:
            raise ValueError("system_controller is required")

        self.system_controller = system_controller
        self.settings = system_controller.settings
        self.suggest_callback = suggest_callback
        self.push_callback = push_callback
        self.save_slack_callback = save_slack_callback
        self.run_stop_section = run_stop_section
        self.login_system = login_system
        self.print_to_terminal = print_to_terminal or (lambda x: None)
        # Drives the Slack Integration indicator (Phase 3 offline-resilience).
        self.notification_handler = notification_handler

        # Get database handler from system controller if not provided
        self.database_handler = database_handler or system_controller.database_handler

        if not self.database_handler:
            raise ValueError(
                "database_handler must be provided either directly or through system_controller"
            )

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Create tab widget for settings
        self.tab_widget = QTabWidget()

        # Create and add settings sub-tabs
        self.hardware_pump_settings = self._create_hardware_pump_settings()  # MERGED
        self.calibration_tab = self._create_calibration_tab()  # NEW
        self.priming_control = self._create_priming_control()
        self.general_tab = self._create_general_tab()
        self.updates_tab = UpdatesTab()

        # Add sub-tabs to settings
        # Note: Cage management moved to Projects Section (CagesVisualizationTab)
        self.tab_widget.addTab(self.hardware_pump_settings, "Delivery")
        self.tab_widget.addTab(self.calibration_tab, "Calibration")
        self.tab_widget.addTab(self.priming_control, "Priming")
        self.tab_widget.addTab(self.general_tab, "General")
        self.tab_widget.addTab(self.updates_tab, "Updates")

        layout.addWidget(self.tab_widget)

        # Update mode state when General tab is selected
        self.tab_widget.currentChanged.connect(self._on_subtab_changed)

        # Connect all settings widgets to auto-save (Best Practice: immediate persistence)
        self._connect_auto_save_handlers()

    def showEvent(self, event):
        """Update mode button state when Settings tab becomes visible."""
        super().showEvent(event)
        # Refresh mode state in case login status changed
        if hasattr(self, '_update_mode_button_state'):
            self._update_mode_button_state()

    def _on_subtab_changed(self, index: int):
        """Handle settings sub-tab changes."""
        # If General tab is selected (index 3), refresh mode state
        if index == 3 and hasattr(self, '_update_mode_button_state'):
            self._update_mode_button_state()

    def refresh_calibration_table(self) -> None:
        """
        Public method to refresh the calibration table.

        Called when cage names are updated in the Cages tab to keep
        calibration table in sync. Follows Observer pattern via Qt signals.
        """
        if hasattr(self, 'calibration_table'):
            self._populate_calibration_table()
            self.print_to_terminal("Calibration table refreshed with updated cage names")

    def _connect_auto_save_handlers(self):
        """
        Connect all settings widgets to auto-save on change.

        Best Practices:
        - Immediate persistence (no manual "Save" button needed)
        - Debounced saves to prevent excessive I/O
        - User expectations: changes persist immediately like modern apps
        """
        # Hardware mode (already has handler, but we'll enhance it)
        # Theme (already has handler)
        # Log level (already has handler, but we'll enhance it)

        # Solenoid settings
        self.teensy_port_edit.editingFinished.connect(self._auto_save_settings)
        self.flow_sensor_optional.stateChanged.connect(self._auto_save_settings)
        self.flow_sampling_hz.valueChanged.connect(self._auto_save_settings)
        self.max_valve_open_s.valueChanged.connect(self._auto_save_settings)
        self.no_flow_timeout_s.valueChanged.connect(self._auto_save_settings)
        self.predictive_close_ms.valueChanged.connect(self._auto_save_settings)
        self.use_pulse_delivery.stateChanged.connect(self._auto_save_settings)
        self.pulse_width_ms.valueChanged.connect(self._auto_save_settings)

        # Pump settings
        self.pump_volume.valueChanged.connect(self._auto_save_settings)
        self.calibration_factor.valueChanged.connect(self._auto_save_settings)
        self.min_triggers.valueChanged.connect(self._auto_save_settings)

        # Slack settings (when they exist)
        if hasattr(self, 'slack_token'):
            self.slack_token.editingFinished.connect(self._auto_save_settings)
        if hasattr(self, 'slack_channel'):
            self.slack_channel.editingFinished.connect(self._auto_save_settings)

    def _auto_save_settings(self):
        """
        Auto-save all settings to disk when any widget changes.

        This provides immediate persistence without requiring a "Save" button.
        Settings are validated and persisted via SystemController.
        """
        if not self.login_system or not self.login_system.is_logged_in():
            # Silently skip auto-save if not logged in
            return

        try:
            # Build updated settings dictionary from UI widgets
            updated_settings = {
                # Hardware mode
                'hardware_mode': self.hardware_mode_combo.currentData() or 'solenoid',
                # Theme (if exists)
                'theme': self.theme_combo.currentText()
                if hasattr(self, 'theme_combo')
                else self.settings.get('theme', 'light'),
                # Solenoid settings
                'uart_port': self.teensy_port_edit.text(),
                'flow_sensor_optional': self.flow_sensor_optional.isChecked(),
                'flow_sampling_hz': self.flow_sampling_hz.value(),
                'max_valve_open_s': self.max_valve_open_s.value(),
                'no_flow_timeout_s': self.no_flow_timeout_s.value(),
                'predictive_close_ms': self.predictive_close_ms.value(),
                'use_pulse_delivery': self.use_pulse_delivery.isChecked(),
                'pulse_width_ms': self.pulse_width_ms.value(),
                # Pump settings
                'pump_volume_ul': self.pump_volume.value(),
                'calibration_factor': self.calibration_factor.value(),
                'min_triggers': self.min_triggers.value(),
                # Notifications (if exist)
                'slack_token': self._encrypt_sensitive_data(self.slack_token.text())
                if hasattr(self, 'slack_token')
                else '',
                'channel_id': self.slack_channel.text() if hasattr(self, 'slack_channel') else '',
                # System
                'log_level': self.log_level.value() if hasattr(self, 'log_level') else 2,
            }

            # Update settings via system controller (ensures persistence)
            self.settings.update(updated_settings)
            self.system_controller.save_settings(self.settings)

            # Emit signal for other components
            self.settings_updated.emit(self.settings)

            # Optional: provide subtle feedback (no annoying popups)
            self.print_to_terminal(f"Settings auto-saved")

        except Exception as e:
            self.print_to_terminal(f"Auto-save failed: {e}")
            # Don't show error dialog - auto-save failures should be silent

    def _create_hardware_pump_settings(self):
        """
        MERGED: Hardware + Pump settings in one tab

        Best Practices:
        - Single Responsibility: One place for all delivery hardware config
        - Progressive Disclosure: Show only relevant settings per mode
        - Safety: Prevent mode switching during active schedule
        """
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ==================== MODE SELECTION ====================
        # Two-column card: a compact selector on the left, the explanatory
        # bullets filling the space to its right (top-aligned), so the wide
        # card reads as one balanced row instead of a half-width control with
        # a large blank gap beside/below it.
        mode_group = QGroupBox("Delivery Hardware Mode")
        mode_layout = QGridLayout()
        mode_layout.setContentsMargins(16, 12, 16, 12)
        mode_layout.setHorizontalSpacing(16)
        mode_layout.setVerticalSpacing(8)

        self.hardware_mode_combo = QComboBox()
        # Display capitalized labels; store the canonical lowercase value as
        # userData so the saved setting (consumed by the strategy factory /
        # relay worker) stays 'solenoid' / 'pump'.
        self.hardware_mode_combo.addItem("Solenoid", "solenoid")
        self.hardware_mode_combo.addItem("Pump", "pump")
        self.hardware_mode_combo.setMinimumWidth(150)
        self.hardware_mode_combo.setMaximumWidth(200)
        current_mode = self.settings.get('hardware_mode', 'solenoid')
        mode_idx = self.hardware_mode_combo.findData(current_mode)
        self.hardware_mode_combo.setCurrentIndex(mode_idx if mode_idx >= 0 else 0)
        self.hardware_mode_combo.currentTextChanged.connect(self._on_hardware_mode_changed)

        mode_layout.addWidget(QLabel("Hardware Mode:"), 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        mode_layout.addWidget(self.hardware_mode_combo, 0, 1, Qt.AlignLeft | Qt.AlignVCenter)

        mode_help = QLabel(
            "• <b>Solenoid</b> (default): flow-sensor volumetric control with "
            "real-time feedback<br>"
            "• <b>Pump</b>: time-based peristaltic pump control (legacy mode)"
        )
        mode_help.setWordWrap(True)
        mode_help.setObjectName("HelpText")
        mode_layout.addWidget(mode_help, 0, 2, Qt.AlignTop | Qt.AlignLeft)

        # Keep the label/control columns compact; the help column absorbs the
        # remaining width so the bullets sit top-right rather than leaving a gap.
        mode_layout.setColumnStretch(0, 0)
        mode_layout.setColumnStretch(1, 0)
        mode_layout.setColumnStretch(2, 1)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # ==================== SOLENOID MODE SETTINGS ====================
        self.solenoid_group = QGroupBox("Solenoid Mode Settings")
        solenoid_layout = QVBoxLayout()
        solenoid_layout.setContentsMargins(12, 12, 12, 12)
        solenoid_layout.setSpacing(12)

        # Flow Sensor Configuration
        sensor_group = QGroupBox("Flow Sensor (Teensy Bridge)")
        sensor_layout = QFormLayout()
        sensor_layout.setContentsMargins(12, 12, 12, 12)
        sensor_layout.setSpacing(8)
        sensor_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        sensor_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Teensy port selection
        port_row = QHBoxLayout()
        self.teensy_port_edit = QLineEdit()
        self.teensy_port_edit.setText(self.settings.get('uart_port', '/dev/teensy_flow'))
        self.teensy_port_edit.setPlaceholderText("/dev/teensy_flow (symlink) or /dev/ttyACM0")
        port_row.addWidget(self.teensy_port_edit)

        detect_button = QPushButton("Auto-Detect")
        detect_button.setToolTip("Automatically find Teensy USB port")
        detect_button.clicked.connect(self._auto_detect_teensy)
        port_row.addWidget(detect_button)

        test_button = QPushButton("Test")
        test_button.setToolTip("Test connection to Teensy (sends ping)")
        test_button.clicked.connect(self._test_teensy_connection)
        port_row.addWidget(test_button)

        sensor_layout.addRow("Teensy Port:", port_row)

        # Flow sensor optional toggle (NEW: enables calibration-only mode)
        self.flow_sensor_optional = QCheckBox("Allow schedules without flow sensor")
        self.flow_sensor_optional.setChecked(self.settings.get('flow_sensor_optional', True))
        self.flow_sensor_optional.setToolTip(
            "If enabled, schedules can run using calibration values when flow sensor is unavailable.\n"
            "The sensor acts as a 'guardrail' - comparing expected vs actual delivery when connected.\n"
            "If disabled, schedules will fail if the flow sensor is not connected."
        )
        sensor_layout.addRow("", self.flow_sensor_optional)

        sensor_optional_help = QLabel(
            "<i>When sensor unavailable, deliveries use per-valve calibration (pulse count × volume/pulse)</i>"
        )
        sensor_optional_help.setObjectName("HelpText")
        sensor_optional_help.setWordWrap(True)
        sensor_layout.addRow("", sensor_optional_help)

        # Sampling rate (SafeDoubleSpinBox prevents accidental scroll changes)
        self.flow_sampling_hz = SafeDoubleSpinBox()
        self.flow_sampling_hz.setRange(1.0, 100.0)
        self.flow_sampling_hz.setValue(self.settings.get('flow_sampling_hz', 50.0))
        self.flow_sampling_hz.setSuffix(" Hz")
        self.flow_sampling_hz.setToolTip(
            "Sensor measurement frequency (default: 50 Hz, max: 100 Hz)"
        )
        sensor_layout.addRow("Sampling Rate:", self.flow_sampling_hz)

        sensor_group.setLayout(sensor_layout)
        solenoid_layout.addWidget(sensor_group)

        # Valve Safety Settings
        safety_group = QGroupBox("Safety Settings")
        safety_layout = QFormLayout()
        safety_layout.setContentsMargins(12, 12, 12, 12)
        safety_layout.setSpacing(8)
        safety_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        safety_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.max_valve_open_s = SafeDoubleSpinBox()
        self.max_valve_open_s.setRange(1.0, 60.0)
        self.max_valve_open_s.setValue(self.settings.get('max_valve_open_s', 20.0))
        self.max_valve_open_s.setSuffix(" s")
        self.max_valve_open_s.setToolTip("Maximum time valve can remain open (emergency cutoff)")
        safety_layout.addRow("Max Valve Open Time:", self.max_valve_open_s)

        self.no_flow_timeout_s = SafeDoubleSpinBox()
        self.no_flow_timeout_s.setRange(0.5, 10.0)
        self.no_flow_timeout_s.setValue(self.settings.get('no_flow_timeout_s', 3.5))
        self.no_flow_timeout_s.setSuffix(" s")
        self.no_flow_timeout_s.setToolTip("Abort delivery if no flow detected for this duration")
        safety_layout.addRow("No-Flow Timeout:", self.no_flow_timeout_s)

        self.predictive_close_ms = SafeDoubleSpinBox()
        self.predictive_close_ms.setRange(0.0, 100.0)
        self.predictive_close_ms.setValue(self.settings.get('predictive_close_ms', 10.0))
        self.predictive_close_ms.setSuffix(" ms")
        self.predictive_close_ms.setToolTip("Valve close lag compensation (reduces overshoot)")
        safety_layout.addRow("Predictive Close Lag:", self.predictive_close_ms)

        safety_group.setLayout(safety_layout)
        solenoid_layout.addWidget(safety_group)

        # Pulse Mode Settings
        pulse_group = QGroupBox("Pulse Mode (Parker Series 3 Valves)")
        pulse_layout = QFormLayout()
        pulse_layout.setContentsMargins(12, 12, 12, 12)
        pulse_layout.setSpacing(8)
        pulse_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        pulse_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.use_pulse_delivery = QCheckBox("Enable Pulse Mode")
        self.use_pulse_delivery.setChecked(self.settings.get('use_pulse_delivery', True))
        self.use_pulse_delivery.setToolTip("Use micro-pulse delivery for precision (recommended)")
        pulse_layout.addRow("", self.use_pulse_delivery)

        self.pulse_width_ms = SafeSpinBox()
        self.pulse_width_ms.setRange(10, 500)
        self.pulse_width_ms.setValue(self.settings.get('pulse_width_ms', 20))
        self.pulse_width_ms.setSuffix(" ms")
        self.pulse_width_ms.setToolTip("Pulse duration (default: 20ms for Parker Series 3)")
        pulse_layout.addRow("Pulse Width:", self.pulse_width_ms)

        pulse_group.setLayout(pulse_layout)
        solenoid_layout.addWidget(pulse_group)

        self.solenoid_group.setLayout(solenoid_layout)
        layout.addWidget(self.solenoid_group)

        # ==================== PUMP MODE SETTINGS ====================
        self.pump_group = QGroupBox("Pump Mode Settings")
        pump_layout = QFormLayout()
        pump_layout.setContentsMargins(12, 12, 12, 12)
        pump_layout.setSpacing(8)
        pump_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        pump_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.pump_volume = SafeDoubleSpinBox()
        self.pump_volume.setRange(0, 1000)
        self.pump_volume.setValue(self.settings.get('pump_volume_ul', 50))
        self.pump_volume.setSuffix(" µL")
        self.pump_volume.setToolTip("Volume delivered per pump trigger")
        pump_layout.addRow("Pump Output Volume:", self.pump_volume)

        self.calibration_factor = SafeDoubleSpinBox()
        self.calibration_factor.setRange(0.1, 10.0)
        self.calibration_factor.setValue(self.settings.get('calibration_factor', 1.0))
        self.calibration_factor.setSingleStep(0.1)
        self.calibration_factor.setDecimals(2)
        self.calibration_factor.setToolTip("Calibration multiplier to adjust for pump variance")
        pump_layout.addRow("Calibration Factor:", self.calibration_factor)

        self.min_triggers = SafeSpinBox()
        self.min_triggers.setRange(1, 100)
        self.min_triggers.setValue(self.settings.get('min_triggers', 1))
        self.min_triggers.setToolTip("Minimum number of pump triggers per delivery")
        pump_layout.addRow("Min Triggers:", self.min_triggers)

        self.pump_group.setLayout(pump_layout)
        layout.addWidget(self.pump_group)

        # Update visibility based on current mode
        self._update_hardware_ui_visibility()

        # Add stretch to push everything to top
        layout.addStretch()

        widget.setLayout(layout)

        # Wrap in scroll area for proper overflow handling
        from PyQt5.QtWidgets import QFrame, QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.NoFrame)

        return scroll

    def _on_hardware_mode_changed(self, mode):
        """
        Handle hardware mode change with safety check.

        Best Practices:
        - Prevent mode switching during active schedule
        - Provide clear feedback to user
        - Maintain system safety
        """
        # Check if schedule is running
        if self.run_stop_section and hasattr(self.run_stop_section, 'worker'):
            if self.run_stop_section.worker and self.run_stop_section.worker.isRunning():
                QMessageBox.warning(
                    self,
                    "Cannot Change Mode",
                    "Cannot change hardware mode while a schedule is running.\n\n"
                    "Please stop the current schedule first.",
                )
                # Revert to previous mode
                old_mode = self.settings.get('hardware_mode', 'solenoid')
                old_idx = self.hardware_mode_combo.findData(old_mode)
                self.hardware_mode_combo.blockSignals(True)
                self.hardware_mode_combo.setCurrentIndex(old_idx if old_idx >= 0 else 0)
                self.hardware_mode_combo.blockSignals(False)
                return

        self._update_hardware_ui_visibility()
        self.print_to_terminal(f"Hardware mode changed to: {mode}")
        # Auto-save the mode change
        self._auto_save_settings()

    def _update_hardware_ui_visibility(self):
        """
        Show/hide settings groups based on hardware mode.

        Progressive Disclosure: Only show relevant settings
        """
        is_solenoid = self.hardware_mode_combo.currentData() == 'solenoid'
        self.solenoid_group.setVisible(is_solenoid)
        self.pump_group.setVisible(not is_solenoid)

    def _auto_detect_teensy(self):
        """Auto-detect Teensy port using system controller"""
        try:
            port = self.system_controller.detect_teensy_port()
            if port:
                self.teensy_port_edit.setText(port)
                self.print_to_terminal(f"[OK] Teensy detected on {port}")
                QMessageBox.information(self, "Auto-Detect", f"Teensy found on {port}")
            else:
                self.print_to_terminal("[X] Teensy not detected. Check USB connection.")
                QMessageBox.warning(
                    self,
                    "Auto-Detect",
                    "Teensy not found. Ensure:\n"
                    "• Teensy is connected via USB\n"
                    "• Firmware is uploaded\n"
                    "• You are in 'dialout' group",
                )
        except Exception as e:
            self.print_to_terminal(f"Auto-detect error: {e}")
            QMessageBox.critical(self, "Error", f"Auto-detect failed: {str(e)}")

    def _test_teensy_connection(self):
        """Test Teensy connection using basic ping with proper resource management"""
        import json
        import time

        import serial

        port = self.teensy_port_edit.text()
        if not port:
            QMessageBox.warning(self, "Test Error", "Please specify a Teensy port first.")
            return

        ser = None  # Initialize for finally block
        try:
            self.print_to_terminal(f"Testing connection to {port}...")
            ser = serial.Serial(port, 115200, timeout=2.0)
            time.sleep(3.5)  # Teensy CDC enumeration delay

            # Send ping
            ser.write(b'{"cmd":"ping"}\n')
            ser.flush()

            # Wait for pong
            pong_received = False
            for _ in range(10):
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            if msg.get("type") == "pong":
                                pong_received = True
                                self.print_to_terminal(f"[OK] Teensy connection OK on {port}")
                                QMessageBox.information(
                                    self,
                                    "Connection Test",
                                    f"Teensy responded successfully!\nPort: {port}",
                                )
                                break  # Exit loop, port closed in finally
                        except json.JSONDecodeError:
                            pass
                time.sleep(0.1)

            if not pong_received:
                self.print_to_terminal(f"Teensy did not respond on {port}")
                QMessageBox.warning(
                    self,
                    "Connection Test",
                    f"Teensy did not respond.\n\n"
                    f"Troubleshooting:\n"
                    f"- Verify firmware is uploaded\n"
                    f"- Check serial port permissions\n"
                    f"- Try replugging USB cable",
                )

        except serial.SerialException as e:
            self.print_to_terminal(f"Serial error: {e}")
            QMessageBox.critical(
                self,
                "Connection Test",
                f"Failed to open port:\n{str(e)}\n\n"
                f"Check that no other program is using {port}",
            )
        except Exception as e:
            self.print_to_terminal(f"Test error: {e}")
            QMessageBox.critical(self, "Connection Test", f"Test failed: {str(e)}")
        finally:
            # CRITICAL: Always close serial port and release file lock
            if ser and ser.is_open:
                try:
                    ser.close()
                    time.sleep(0.5)  # Give OS time to fully release port lock
                    self.print_to_terminal(f"Serial port {port} closed and lock released")
                except Exception as cleanup_error:
                    self.print_to_terminal(f"Warning: Error during port cleanup: {cleanup_error}")

    def _create_calibration_tab(self):
        """
        Integrated Calibration UI (Option A)

        Best Practices:
        - Table shows all cages at a glance
        - Click row to launch wizard
        - Real-time status updates
        - All users can calibrate (logged to database)
        - Visual indicators for calibration quality
        """
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import (
            QAbstractItemView,
            QFrame,
            QHeaderView,
            QPushButton,
            QScrollArea,
            QTableWidget,
        )

        widget = QWidget()
        layout = QVBoxLayout()

        # Header with info
        header = QLabel(
            "<b>Calibration</b><br>"
            "<span style='color: #666;'>Per-valve empirical calibration for precision water delivery</span>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Calibration table
        self.calibration_table = QTableWidget()
        self.calibration_table.setColumnCount(6)
        self.calibration_table.setHorizontalHeaderLabels(
            ["Cage", "Status", "mL/Pulse", "CV%", "Date", "Action"]
        )

        # Table styling - Match app's Material Design theme
        self.calibration_table.setAlternatingRowColors(True)
        self.calibration_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.calibration_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.calibration_table.setShowGrid(True)
        self.calibration_table.verticalHeader().setVisible(False)
        self.calibration_table.verticalHeader().setDefaultSectionSize(40)  # Accommodate buttons
        self.calibration_table.setMinimumHeight(300)
        # Don't set maxHeight - let the parent scroll area handle overflow
        # This ensures the table displays naturally and the tab scrolls when needed
        self.calibration_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )  # Tab scrolls instead
        self.calibration_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.calibration_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        # Rely on global QSS styling

        # Column resize modes - all fixed widths for consistent layout
        header = self.calibration_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(40)

        # Column 0: Cage - stretch to absorb slack (names vary in length)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        # Column 1: Status - compact fixed width (badge only)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(1, 120)

        # Column 2: mL/Pulse - fixed width (fits "0.001234")
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(2, 95)

        # Column 3: CV% - fixed width
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(3, 70)

        # Column 4: Date - fixed width (fits "2026-05-12")
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(4, 100)

        # Column 5: Action - fixed width for button with padding
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(5, 124)

        # Populate table with 15 cages
        self._populate_calibration_table()

        layout.addWidget(self.calibration_table)

        # Add significant spacing before action buttons to prevent invasion
        layout.addSpacing(16)

        # Action buttons - wrap in container to enforce spacing from table
        actions_container = QWidget()
        actions_container.setObjectName("TableActionBar")
        actions_container.setContentsMargins(0, 12, 0, 0)
        button_row = QHBoxLayout(actions_container)
        button_row.setSpacing(8)
        button_row.setContentsMargins(0, 0, 0, 0)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("CompactButton")
        refresh_btn.setFixedHeight(28)
        refresh_btn.setToolTip("Reload calibration data from database")
        refresh_btn.clicked.connect(self._populate_calibration_table)
        button_row.addWidget(refresh_btn)

        button_row.addStretch()

        calibrate_all_btn = QPushButton("Calibrate All Uncalibrated")
        calibrate_all_btn.setObjectName("CompactButton")
        calibrate_all_btn.setFixedHeight(28)
        calibrate_all_btn.setToolTip(
            "Run calibration wizard for all uncalibrated valves (all users)"
        )
        calibrate_all_btn.clicked.connect(self._calibrate_all_uncalibrated)
        button_row.addWidget(calibrate_all_btn)

        export_btn = QPushButton("Export Report")
        export_btn.setObjectName("CompactButton")
        export_btn.setFixedHeight(28)
        export_btn.setToolTip("Export calibration data to CSV")
        export_btn.clicked.connect(self._export_calibration_report)
        button_row.addWidget(export_btn)

        layout.addWidget(actions_container)

        # Help text
        help_text = QLabel(
            "<b>Tips:</b> Click 'Calibrate' to run 250-pulse characterization. "
            "Requires lab scale (±0.001g). CV% <5% = production ready."
        )
        help_text.setWordWrap(True)
        help_text.setObjectName("HelpText")
        layout.addWidget(help_text)

        widget.setLayout(layout)

        # Wrap in scroll area so content can overflow properly
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.NoFrame)  # Remove border for cleaner look
        return scroll

    def _populate_calibration_table(self):
        """Load calibration data from database and populate table"""
        from datetime import datetime

        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QColor
        from PyQt5.QtWidgets import QPushButton

        self.calibration_table.setRowCount(15)  # 15 cages

        # Get all calibrations from database
        calibrations = {}
        try:
            calibrations = self.database_handler.get_all_valve_calibrations()
        except Exception as e:
            self.print_to_terminal(f"Error loading calibrations: {e}")

        # Get all cage names from database (Best Practice: batch query instead of N+1)
        cage_names = {}
        try:
            cage_names = self.database_handler.get_all_cage_names()
        except Exception as e:
            self.print_to_terminal(f"Error loading cage names: {e}")

        for cage_id in range(1, 16):
            row = cage_id - 1
            cal = calibrations.get(cage_id)

            # Cage name - use custom name if set, otherwise "Cage N"
            cage_info = cage_names.get(cage_id, {})
            custom_name = cage_info.get('name', '')
            if custom_name and custom_name != f"Cage {cage_id}":
                display_name = f"{cage_id}: {custom_name}"
            else:
                display_name = f"Cage {cage_id}"

            cage_item = QTableWidgetItem(display_name)
            cage_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            cage_item.setToolTip(f"Cage {cage_id} - Relay {cage_info.get('relay_id', cage_id)}")
            self.calibration_table.setItem(row, 0, cage_item)

            if cal:
                # Calibrated - show data
                status_item = QTableWidgetItem("[OK]")
                status_item.setForeground(QColor(0, 150, 0))
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setToolTip("Calibrated")

                volume_item = QTableWidgetItem(f"{cal['volume_per_pulse_ml']:.6f}")
                volume_item.setTextAlignment(Qt.AlignCenter)

                cv_pct = cal['coefficient_of_variation_pct']
                cv_item = QTableWidgetItem(f"{cv_pct:.2f}%")
                cv_item.setTextAlignment(Qt.AlignCenter)

                # Color code quality
                if cv_pct < 1.0:
                    cv_item.setForeground(QColor(0, 150, 0))  # Excellent - green
                elif cv_pct < 3.0:
                    cv_item.setForeground(QColor(50, 150, 50))  # Good - lighter green
                elif cv_pct < 5.0:
                    cv_item.setForeground(QColor(200, 150, 0))  # Acceptable - yellow
                else:
                    cv_item.setForeground(QColor(200, 0, 0))  # Poor - red

                # Format date
                try:
                    date_obj = datetime.fromisoformat(cal['calibration_date'])
                    date_str = date_obj.strftime('%Y-%m-%d')
                except:
                    date_str = cal['calibration_date'][:10]

                date_item = QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignCenter)

                self.calibration_table.setItem(row, 1, status_item)
                self.calibration_table.setItem(row, 2, volume_item)
                self.calibration_table.setItem(row, 3, cv_item)
                self.calibration_table.setItem(row, 4, date_item)

                # Action button - Recalibrate (compact for table)
                btn = QPushButton("Recalibrate")
                btn.setStyleSheet(self._ACTION_BUTTON_STYLE)
                btn.setMinimumWidth(90)
                btn.setToolTip(f"Recalibrate cage {cage_id}")
                btn.clicked.connect(lambda checked, c=cage_id: self._launch_calibration_wizard(c))
                self.calibration_table.setCellWidget(row, 5, btn)

            else:
                # Not calibrated - show warning
                status_item = QTableWidgetItem("Not Calibrated")
                status_item.setForeground(QColor(200, 0, 0))
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setToolTip("Not calibrated")

                volume_item = QTableWidgetItem("—")
                volume_item.setTextAlignment(Qt.AlignCenter)
                volume_item.setForeground(QColor(150, 150, 150))

                cv_item = QTableWidgetItem("—")
                cv_item.setTextAlignment(Qt.AlignCenter)
                cv_item.setForeground(QColor(150, 150, 150))

                date_item = QTableWidgetItem("—")
                date_item.setTextAlignment(Qt.AlignCenter)
                date_item.setForeground(QColor(150, 150, 150))

                self.calibration_table.setItem(row, 1, status_item)
                self.calibration_table.setItem(row, 2, volume_item)
                self.calibration_table.setItem(row, 3, cv_item)
                self.calibration_table.setItem(row, 4, date_item)

                # Action button - Calibrate (compact for table)
                btn = QPushButton("Calibrate")
                btn.setProperty("variant", "primary")
                btn.setStyleSheet(self._ACTION_BUTTON_STYLE)
                btn.setMinimumWidth(90)
                btn.setToolTip(f"Calibrate cage {cage_id} (250 pulses)")
                btn.clicked.connect(lambda checked, c=cage_id: self._launch_calibration_wizard(c))
                self.calibration_table.setCellWidget(row, 5, btn)

    # Size-only stylesheet for the calibration-table action buttons. Cell-widget
    # buttons do not match the `QTableWidget QPushButton` compact rule in the
    # theme QSS, so they fall back to the base `QPushButton { min-height: 40px }`
    # and render ~42px tall — taller than the 40px row, which made them overflow
    # and straddle the boundary between two rows. An inline stylesheet (highest
    # priority) caps the height; the variant/theme colours still apply. Verified
    # on a real Pi display.
    _ACTION_BUTTON_STYLE = "QPushButton { min-height: 26px; max-height: 26px; padding: 2px 12px; }"

    def _launch_calibration_wizard(self, cage_id):
        """
        Launch calibration wizard for specific cage.

        All users can calibrate - action is logged to database with trainer_id.

        CRITICAL: Don't use print() to sys.stderr in this method - it's redirected
        through Qt signals which can corrupt during dialog operations.
        """
        # Check if logged in
        if not self.login_system or not self.login_system.is_logged_in():
            QMessageBox.warning(
                self, "Access Denied", "You must be logged in to calibrate valves."
            )
            return

        # Check if schedule is running
        if self.run_stop_section and hasattr(self.run_stop_section, 'worker'):
            if self.run_stop_section.worker and self.run_stop_section.worker.isRunning():
                QMessageBox.warning(
                    self,
                    "Schedule Running",
                    "Cannot calibrate while a schedule is running.\n\n"
                    "Please stop the schedule first.",
                )
                return

        # Import and create wizard dialog
        from ui.CalibrationWizard import CalibrationWizard

        try:
            wizard = CalibrationWizard(
                cage_id=cage_id,
                database_handler=self.database_handler,
                system_controller=self.system_controller,
                parent=self,
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            self.print_to_terminal(f"CRITICAL: Failed to create calibration wizard: {e}")
            raise

        # Execute wizard and check result
        # CRITICAL: Don't use print() to sys.stderr around dialog.exec_() -
        # it's redirected through Qt signals which can corrupt during dialog close!
        try:
            self.print_to_terminal(f"Opening calibration wizard for Cage {cage_id}...")
            # File log (safe) before exec_
            try:
                import os
                from datetime import datetime

                path = os.path.expanduser('~/rrr_app_debug.log')
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(f"{ts} [RRR] SettingsTab: calling wizard.exec_() for cage {cage_id}\n")
            except Exception:
                pass
            result = wizard.exec_()
            self.print_to_terminal(f"Wizard completed with result: {result}")
            # File log (safe) after exec_
            try:
                import os
                from datetime import datetime

                path = os.path.expanduser('~/rrr_app_debug.log')
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(f"{ts} [RRR] SettingsTab: wizard.exec_() returned {result}\n")
            except Exception:
                pass
        except Exception as e:
            import traceback

            traceback.print_exc()
            self.print_to_terminal(f"CRITICAL: Calibration wizard crashed during exec_(): {e}")
            import traceback

            error_trace = traceback.format_exc()
            self.print_to_terminal(f"Traceback:\n{error_trace}")

            # Even if wizard crashed, calibration might have been saved
            # Refresh table to show any saved data
            try:
                self.print_to_terminal("Attempting to refresh table despite error...")
                self._populate_calibration_table()
                self.print_to_terminal("Table refreshed - calibration may have been saved")
            except Exception as refresh_error:
                self.print_to_terminal(f"Failed to refresh table: {refresh_error}")
            return

        if result == QDialog.Accepted:
            # Calibration completed successfully
            self.print_to_terminal(f"[OK] Cage {cage_id} calibration completed successfully")

            # Use QTimer to do ALL post-close operations
            # This ensures wizard is fully closed and event loop is stable
            def handle_successful_calibration():
                try:
                    # Refresh table to show new calibration
                    self.print_to_terminal("Refreshing calibration table...")
                    try:
                        self._populate_calibration_table()
                        self.print_to_terminal("Table refreshed successfully")
                    except Exception as refresh_error:
                        self.print_to_terminal(
                            f"Warning: Failed to refresh table: {refresh_error}"
                        )
                        import traceback

                        self.print_to_terminal(traceback.format_exc())

                    # Show success message
                    try:
                        self.print_to_terminal("Retrieving calibration data...")
                        cal = self.database_handler.get_valve_calibration(cage_id)

                        if cal:
                            self.print_to_terminal("Showing success message...")
                            QMessageBox.information(
                                self,
                                "Calibration Complete",
                                f"Cage {cage_id} calibration saved successfully!\n\n"
                                f"Volume per pulse: {cal['volume_per_pulse_ml']:.6f} mL\n"
                                f"Quality (CV): {cal['coefficient_of_variation_pct']:.2f}%\n\n"
                                "This calibration is now active for all deliveries.",
                            )
                            self.print_to_terminal("Success message shown and dismissed")
                        else:
                            self.print_to_terminal("Warning: Calibration not found in database")
                            QMessageBox.information(
                                self,
                                "Calibration Complete",
                                f"Cage {cage_id} has been successfully calibrated!\n\n"
                                "The new calibration is now active.",
                            )
                    except Exception as msg_error:
                        self.print_to_terminal(
                            f"Warning: Failed to show success message: {msg_error}"
                        )
                        import traceback

                        self.print_to_terminal(traceback.format_exc())
                        # Don't crash - calibration is already saved

                    self.print_to_terminal("Post-calibration handling complete")

                except Exception as e:
                    self.print_to_terminal(f"Error in post-calibration handler: {e}")
                    import traceback

                    self.print_to_terminal(traceback.format_exc())

            # Schedule ALL operations for next event loop iteration
            # Give wizard 200ms to fully close and clean up
            from PyQt5.QtCore import QTimer

            self.print_to_terminal("Scheduling post-calibration operations...")
            QTimer.singleShot(200, handle_successful_calibration)

        elif result == QDialog.Rejected:
            # User cancelled/discarded calibration
            self.print_to_terminal(f"Cage {cage_id} calibration cancelled by user")
            # No further action needed - just return silently

        else:
            # Unexpected result
            self.print_to_terminal(f"Warning: Unexpected dialog result: {result}")

    def _calibrate_all_uncalibrated(self):
        """
        Sequentially calibrate all uncalibrated valves.

        All users can calibrate - actions are logged to database with trainer_id.
        """
        # Check if logged in
        if not self.login_system or not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in.")
            return

        # Get uncalibrated cages
        calibrations = self.database_handler.get_all_valve_calibrations()
        uncalibrated = [c for c in range(1, 16) if c not in calibrations]

        if not uncalibrated:
            QMessageBox.information(self, "All Calibrated", "All valves are already calibrated!")
            return

        reply = QMessageBox.question(
            self,
            "Calibrate All",
            f"Found {len(uncalibrated)} uncalibrated valves:\n{uncalibrated}\n\n"
            f"This will take approximately {len(uncalibrated) * 10} minutes.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            for cage_id in uncalibrated:
                self._launch_calibration_wizard(cage_id)
                # If user cancels one, stop the batch
                if not hasattr(self, '_last_calibration_success'):
                    break

    def _export_calibration_report(self):
        """Export calibration data to CSV"""
        try:
            from datetime import datetime

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Calibration Report",
                f"calibration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)",
            )

            if not file_path:
                return

            calibrations = self.database_handler.get_all_valve_calibrations()

            with open(file_path, 'w') as f:
                f.write(
                    "Cage,Status,Volume_per_Pulse_mL,CV_Percent,Num_Samples,Calibration_Date,Notes\n"
                )

                for cage_id in range(1, 16):
                    if cage_id in calibrations:
                        cal = calibrations[cage_id]
                        f.write(
                            f"{cage_id},Calibrated,{cal['volume_per_pulse_ml']:.6f},"
                            f"{cal['coefficient_of_variation_pct']:.2f},"
                            f"{cal['num_samples']},{cal['calibration_date']},"
                            f"\"{cal.get('notes', '')}\"\n"
                        )
                    else:
                        f.write(f"{cage_id},Not Calibrated,—,—,—,—,—\n")

            self.print_to_terminal(f"Calibration report exported to {file_path}")
            QMessageBox.information(self, "Export Complete", f"Report saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")

    def _create_priming_control(self):
        """
        Create priming control tab using modular PrimingControlWidget.

        Best Practices:
        - Composition over inheritance
        - Single Responsibility Principle
        - Dependency Injection (passing settings and callback)
        - Separation of Concerns (priming logic isolated in dedicated widget)
        """
        from PyQt5.QtWidgets import QFrame, QScrollArea

        # Instantiate the modular priming control widget
        priming_widget = PrimingControlWidget(
            settings=self.settings, print_callback=self.print_to_terminal
        )

        # Connect widget signals to parent if needed
        priming_widget.status_message.connect(self.print_to_terminal)

        # Wrap in scroll area for proper overflow handling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(priming_widget)
        scroll.setFrameShape(QFrame.NoFrame)

        return scroll

    def _create_system_settings(self):
        """Create system settings tab with proper type handling"""
        system_group = QGroupBox("System Settings")
        layout = QFormLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Log Level Spinner with proper type handling
        self.log_level = SafeSpinBox()
        self.log_level.setRange(0, 4)  # 0=DEBUG to 4=CRITICAL
        self.log_level.setValue(int(self.settings.get('log_level', 2)))
        self.log_level.valueChanged.connect(self._log_level_changed)

        # Add tooltip to explain log levels
        self.log_level.setToolTip("0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR, 4=CRITICAL")

        layout.addRow("Log Level:", self.log_level)

        system_group.setLayout(layout)
        return system_group

    def _log_level_changed(self, value):
        """Handle log level changes"""
        self.settings['log_level'] = value
        # Auto-save the log level change
        self._auto_save_settings()

    def _theme_changed(self, theme: str):
        """Apply theme immediately and persist in settings."""
        self.settings['theme'] = theme
        try:
            style_mgr = QApplication.instance().property('style_manager')
            if style_mgr:
                style_mgr.apply(theme)
        except Exception:
            pass
        # Re-render themed HTML content that QSS can't reach (Help tab).
        try:
            help_tab = getattr(self.window(), 'help_tab', None)
            if help_tab is not None and hasattr(help_tab, 'refresh_theme'):
                help_tab.refresh_theme()
        except Exception:
            pass
        # Auto-save the theme change
        self._auto_save_settings()

    def _create_notifications(self):
        slack_group = QGroupBox("Slack Integration")
        slack_layout = QFormLayout()
        slack_layout.setContentsMargins(12, 12, 12, 12)
        slack_layout.setSpacing(8)

        self.slack_token = QLineEdit()
        self.slack_token.setText(
            self._decrypt_sensitive_data(self.settings.get('slack_token', ''))
        )
        self.slack_token.setEchoMode(QLineEdit.Password)
        slack_layout.addRow("Slack Bot Token:", self.slack_token)

        self.slack_channel = QLineEdit()
        self.slack_channel.setText(self.settings.get('channel_id', ''))
        slack_layout.addRow("Channel ID:", self.slack_channel)

        # Phase 3 offline-resilience: status indicator + troubleshooting.
        # The label is refreshed every 5 s by self._slack_status_timer
        # (started below) reading NotificationHandler.last_status.
        self.slack_status_label = QLabel()
        self.slack_status_label.setWordWrap(True)
        self.slack_status_label.setMinimumHeight(48)
        self.slack_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        slack_layout.addRow("Status:", self.slack_status_label)
        self._refresh_slack_status()

        # Re-render once a second so the indicator catches up shortly after
        # the relay worker calls send_slack_notification(). Cheap — the
        # formatter is pure-Python and reads one attribute.
        self._slack_status_timer = QTimer(self)
        self._slack_status_timer.timeout.connect(self._refresh_slack_status)
        self._slack_status_timer.start(1000)

        slack_group.setLayout(slack_layout)
        return slack_group

    def _refresh_slack_status(self):
        """Render the Slack indicator from NotificationHandler.last_status."""
        # Imported lazily so a missing utils.slack_status (e.g. on a partial
        # checkout) cannot stop the settings tab from opening.
        try:
            from utils.slack_status import format_status
        except Exception:
            return

        handler = getattr(self, "notification_handler", None)
        status = getattr(handler, "last_status", None) if handler else None
        icon, message = format_status(status)

        glyph = {"ok": "✓", "warn": "⚠", "unknown": "•"}.get(icon, "•")
        # Conservative palette — readable on both light and dark themes.
        color = {"ok": "#0a7d28", "warn": "#9c4a00", "unknown": "#666666"}.get(icon, "#666666")
        self.slack_status_label.setText(f"{glyph}  {message}")
        self.slack_status_label.setStyleSheet(f"color: {color}; padding: 6px; border-radius: 4px;")

    def _create_backup_restore(self):
        backup_group = QGroupBox("Backup and Restore")
        backup_layout = QVBoxLayout()
        backup_layout.setContentsMargins(12, 12, 12, 12)
        backup_layout.setSpacing(8)

        backup_button = QPushButton("Create Backup")
        backup_button.clicked.connect(self.create_backup)
        backup_layout.addWidget(backup_button)

        restore_button = QPushButton("Restore from Backup")
        restore_button.clicked.connect(self.restore_from_backup)
        backup_layout.addWidget(restore_button)

        backup_group.setLayout(backup_layout)
        return backup_group

    def _create_data_import_export(self):
        import_export_group = QGroupBox("Data Import/Export")
        layout = QGridLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        export_btn = QPushButton("Export Animals to CSV")
        export_btn.clicked.connect(self.export_animals)
        import_btn = QPushButton("Import Animals from CSV")
        import_btn.clicked.connect(self.import_animals)

        layout.addWidget(export_btn, 0, 0)
        layout.addWidget(import_btn, 0, 1)

        import_export_group.setLayout(layout)
        return import_export_group

    def _create_general_tab(self):
        """
        Merge Notifications, Import/Export, and Theme selection into one tab.
        """
        widget = QWidget()
        v = QVBoxLayout()
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(12)

        # Appearance group (Theme)
        appearance = QGroupBox("Appearance")
        appearance_form = QFormLayout()
        appearance_form.setContentsMargins(12, 12, 12, 12)
        appearance_form.setSpacing(8)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        try:
            self.theme_combo.setCurrentText(self.settings.get('theme', 'light'))
        except Exception:
            self.theme_combo.setCurrentText("light")
        self.theme_combo.currentTextChanged.connect(self._theme_changed)
        appearance_form.addRow("Theme:", self.theme_combo)
        appearance.setLayout(appearance_form)
        v.addWidget(appearance)

        # Notifications (Slack)
        v.addWidget(self._create_notifications())

        # Backup/Restore and Import/Export
        v.addWidget(self._create_backup_restore())
        v.addWidget(self._create_data_import_export())

        # System settings (e.g., log level) merged here for clarity
        v.addWidget(self._create_system_settings())

        # User Mode Toggle (Normal/Super)
        v.addWidget(self._create_mode_toggle())

        v.addStretch()
        widget.setLayout(v)

        # Wrap in scroll area for proper overflow handling
        from PyQt5.QtWidgets import QFrame, QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.NoFrame)

        return scroll

    def _create_mode_toggle(self):
        """
        Create User Mode toggle (Normal/Super) section.

        Moved from main GUI to Settings for cleaner layout.
        """
        mode_group = QGroupBox("User Mode")
        mode_layout = QVBoxLayout()
        mode_layout.setContentsMargins(12, 12, 12, 12)
        mode_layout.setSpacing(8)

        # Description
        desc_label = QLabel(
            "Switch between Normal and Super mode to access all animals/schedules."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 11px;")
        mode_layout.addWidget(desc_label)

        # Mode toggle button
        self.mode_toggle_button = QPushButton("Switch to Super Mode")
        self.mode_toggle_button.setMinimumHeight(36)
        self.mode_toggle_button.clicked.connect(self._toggle_mode)
        mode_layout.addWidget(self.mode_toggle_button)

        # Current mode status
        self.mode_status_label = QLabel("Current Mode: Normal")
        self.mode_status_label.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(self.mode_status_label)

        # Update button text based on current mode
        self._update_mode_button_state()

        mode_group.setLayout(mode_layout)
        return mode_group

    def _toggle_mode(self):
        """Handle mode toggle from Settings tab."""
        if not self.login_system:
            QMessageBox.warning(self, "Not Logged In", "You must be logged in to switch modes.")
            return

        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Not Logged In", "You must be logged in to switch modes.")
            return

        try:
            self.login_system.switch_mode()
            self._update_mode_button_state()

            new_role = self.login_system.get_current_trainer()['role']
            self.print_to_terminal(f"Switched to {new_role.capitalize()} Mode.")

            # Refresh animals and schedules if parent GUI is available
            parent = self.window()
            if hasattr(parent, 'projects_section'):
                parent.projects_section.schedules_tab.load_animals()
                parent.projects_section.animals_tab.load_animals()
        except Exception as e:
            QMessageBox.critical(self, "Mode Toggle Error", f"An error occurred: {e}")

    def _update_mode_button_state(self):
        """Update mode toggle button text based on current state."""
        if not hasattr(self, 'mode_toggle_button'):
            return

        if self.login_system and self.login_system.is_logged_in():
            try:
                current_role = self.login_system.get_current_trainer()['role']
                if current_role == 'super':
                    self.mode_toggle_button.setText("Switch to Normal Mode")
                    self.mode_status_label.setText("Current Mode: Super")
                else:
                    self.mode_toggle_button.setText("Switch to Super Mode")
                    self.mode_status_label.setText("Current Mode: Normal")
                self.mode_toggle_button.setEnabled(True)
            except Exception:
                self.mode_toggle_button.setEnabled(False)
                self.mode_status_label.setText("Current Mode: Unknown")
        else:
            self.mode_toggle_button.setEnabled(False)
            self.mode_status_label.setText("Current Mode: Guest (login required)")

    def _get_or_create_key(self):
        key_file = "settings_key.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return base64.urlsafe_b64decode(f.read())
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(base64.urlsafe_b64encode(key))
            return key

    def _encrypt_sensitive_data(self, data):
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()

    def _decrypt_sensitive_data(self, data):
        if not data:
            return ""
        try:
            return self.fernet.decrypt(data.encode()).decode()
        except:
            return ""

    def create_backup(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Backup", f"rrr_backup_{timestamp}.json", "JSON files (*.json)"
            )

            if filename:
                with open(filename, 'w') as f:
                    json.dump(self.settings, f, indent=4)
                QMessageBox.information(self, "Success", "Backup created successfully")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create backup: {str(e)}")

    def restore_from_backup(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Load Backup", "", "JSON files (*.json)"
            )

            if filename:
                with open(filename, 'r') as f:
                    backup_settings = json.load(f)

                # Validate backup data
                required_keys = ['pump_volume_ul', 'calibration_factor']
                if not all(key in backup_settings for key in required_keys):
                    raise ValueError("Invalid backup file format")

                self.settings.update(backup_settings)
                self.load_settings()
                QMessageBox.information(self, "Success", "Settings restored successfully")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore backup: {str(e)}")

    def load_settings(self):
        """Reload all settings into UI elements"""
        self.pump_volume.setValue(self.settings.get('pump_volume_ul', 50))
        self.calibration_factor.setValue(self.settings.get('calibration_factor', 1.0))
        self.slack_token.setText(
            self._decrypt_sensitive_data(self.settings.get('slack_token', ''))
        )
        self.slack_channel.setText(self.settings.get('channel_id', ''))
        self.log_level.setValue(self.settings.get('log_level', 2))

    def export_animals(self):
        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in to export animals.")
            return

        if not self.database_handler:
            QMessageBox.critical(self, "Export Error", "Database handler not initialized")
            return

        try:
            file_path, file_type = QFileDialog.getSaveFileName(
                self,
                "Export Animals",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv)",  # Make Excel default
            )
            if not file_path:
                return

            animals = self.database_handler.get_all_animals()
            if not animals:
                QMessageBox.information(self, "Export Info", "No animals found to export")
                return

            data = []
            for animal in animals:
                # Format dates in Excel-friendly format
                last_weighted = (
                    datetime.fromisoformat(animal.last_weighted).strftime('%Y-%m-%d %H:%M:%S')
                    if animal.last_weighted
                    else ''
                )
                last_watering = (
                    datetime.fromisoformat(animal.last_watering).strftime('%Y-%m-%d %H:%M:%S')
                    if animal.last_watering
                    else ''
                )

                data.append(
                    {
                        'Lab Animal ID': animal.lab_animal_id,
                        'Name': animal.name,
                        'Sex': animal.sex or '',
                        'Initial Weight (g)': f"{animal.initial_weight:.1f}"
                        if animal.initial_weight
                        else '',
                        'Last Weight (g)': f"{animal.last_weight:.1f}"
                        if animal.last_weight
                        else '',
                        'Last Weighted': last_weighted,
                        'Last Watering': last_watering,
                    }
                )

            df = pd.DataFrame(data)

            # Ensure file has correct extension
            if not file_path.endswith(('.xlsx', '.csv')):
                file_path += '.xlsx' if 'Excel' in file_type else '.csv'

            if file_path.endswith('.xlsx'):
                # Excel-specific export settings for Mac compatibility
                writer = pd.ExcelWriter(file_path, engine='openpyxl')
                df.to_excel(writer, sheet_name='Animals', index=False)

                # Auto-adjust column widths
                worksheet = writer.sheets['Animals']
                for idx, col in enumerate(df.columns):
                    max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length

                writer.close()
            else:
                # Mac-friendly CSV settings
                df.to_csv(
                    file_path,
                    index=False,
                    encoding='utf-8-sig',  # BOM for Excel Mac
                    sep=',',
                    date_format='%Y-%m-%d %H:%M:%S',
                )

            self.print_to_terminal(f"Successfully exported {len(animals)} animals to {file_path}")
            QMessageBox.information(
                self, "Success", f"Successfully exported {len(animals)} animals"
            )

        except AttributeError as e:
            QMessageBox.critical(
                self,
                "Export Error",
                "Database connection error. Please check system configuration.",
            )
            self.print_to_terminal(f"Database error during export: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting animals: {str(e)}")
            self.print_to_terminal(f"Unexpected error during export: {str(e)}")

    def import_animals(self):
        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in to import animals.")
            return

        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Import Animals", "", "CSV Files (*.csv)"
            )
            if file_path:
                df = pd.read_csv(file_path)
                current_trainer = self.login_system.get_current_trainer()
                trainer_id = current_trainer['trainer_id'] if current_trainer else None

                imported = 0
                errors = []

                for _, row in df.iterrows():
                    try:
                        # Map lab document format to our database format
                        sex = (
                            'female'
                            if row['# Females'] == 1
                            else 'male'
                            if row['# Males'] == 1
                            else None
                        )

                        # Validate the birthdate format (raises on bad data,
                        # skipping the row). NOTE: the parsed value is not
                        # stored — Animal has no birthdate field yet; this is
                        # known debt, kept as a validation gate only.
                        datetime.strptime(str(row['Birthdate']), '%y%m%d')

                        animal = Animal(
                            animal_id=None,
                            lab_animal_id=str(row['Ear tag ID#'])
                            if pd.notna(row['Ear tag ID#'])
                            else row['Cage Number #'],
                            name=row['Nickname'] if pd.notna(row['Nickname']) else '',
                            initial_weight=None,  # No weight in lab format
                            last_weight=None,
                            last_weighted=None,
                            last_watering=None,
                            sex=sex,
                        )

                        if self.database_handler.add_animal(animal, trainer_id):
                            imported += 1

                    except Exception as e:
                        errors.append(f"Row {_+2}: {str(e)}")

                msg = f"Successfully imported {imported} animals."
                if errors:
                    msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors)

                QMessageBox.information(self, "Import Results", msg)
                self.print_to_terminal(f"Imported {imported} animals from {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error importing animals: {e}")
