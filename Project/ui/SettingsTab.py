from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QGroupBox, 
    QFormLayout, QLineEdit, QLabel, QPushButton, 
    QMessageBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFileDialog, QGridLayout, QComboBox, QHBoxLayout, QTextEdit, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
import json
import os
import base64
from cryptography.fernet import Fernet
from datetime import datetime
import pandas as pd
from models.animal import Animal
from ui.PrimingControlWidget import PrimingControlWidget

class SettingsTab(QWidget):
    settings_updated = pyqtSignal(dict)
    
    def __init__(self, system_controller, suggest_callback=None, 
                 push_callback=None, save_slack_callback=None, 
                 run_stop_section=None, login_system=None,
                 print_to_terminal=None, database_handler=None):
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
        
        # Get database handler from system controller if not provided
        self.database_handler = database_handler or system_controller.database_handler
        
        if not self.database_handler:
            raise ValueError("database_handler must be provided either directly or through system_controller")
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget for settings
        self.tab_widget = QTabWidget()
        
        # Create and add settings sub-tabs
        self.hardware_pump_settings = self._create_hardware_pump_settings()  # MERGED
        self.calibration_tab = self._create_calibration_tab()  # NEW
        self.priming_control = self._create_priming_control()
        self.system_settings = self._create_system_settings()
        self.notifications = self._create_notifications()
        self.backup_restore = self._create_backup_restore()
        self.data_import_export = self._create_data_import_export()
        
        # Add sub-tabs to settings
        self.tab_widget.addTab(self.hardware_pump_settings, "Hardware & Delivery")
        self.tab_widget.addTab(self.calibration_tab, "Valve Calibration")
        self.tab_widget.addTab(self.priming_control, "Priming")
        self.tab_widget.addTab(self.notifications, "Notifications")
        self.tab_widget.addTab(self.data_import_export, "Import/Export")
        
        layout.addWidget(self.tab_widget)
        
        # Add save button at bottom of settings
        save_button = QPushButton("Save All Settings")
        save_button.clicked.connect(self._save_all_settings)
        layout.addWidget(save_button)

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
        
        # ==================== MODE SELECTION ====================
        mode_group = QGroupBox("Delivery Hardware Mode")
        mode_layout = QFormLayout()
        
        self.hardware_mode_combo = QComboBox()
        self.hardware_mode_combo.addItems(['solenoid', 'pump'])
        current_mode = self.settings.get('hardware_mode', 'solenoid')
        self.hardware_mode_combo.setCurrentText(current_mode)
        self.hardware_mode_combo.currentTextChanged.connect(self._on_hardware_mode_changed)
        mode_layout.addRow("Hardware Mode:", self.hardware_mode_combo)
        
        mode_help = QLabel(
            "• <b>Solenoid</b> (default): Flow sensor-based volumetric control with real-time feedback\n"
            "• <b>Pump</b>: Time-based peristaltic pump control (legacy mode)"
        )
        mode_help.setWordWrap(True)
        mode_help.setStyleSheet("color: #666; font-size: 10pt; padding: 5px;")
        mode_layout.addRow("", mode_help)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # ==================== SOLENOID MODE SETTINGS ====================
        self.solenoid_group = QGroupBox("Solenoid Mode Settings")
        solenoid_layout = QVBoxLayout()
        
        # Flow Sensor Configuration
        sensor_group = QGroupBox("Flow Sensor (Teensy Bridge)")
        sensor_layout = QFormLayout()
        
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
        
        # Sampling rate
        self.flow_sampling_hz = QDoubleSpinBox()
        self.flow_sampling_hz.setRange(1.0, 100.0)
        self.flow_sampling_hz.setValue(self.settings.get('flow_sampling_hz', 50.0))
        self.flow_sampling_hz.setSuffix(" Hz")
        self.flow_sampling_hz.setToolTip("Sensor measurement frequency (default: 50 Hz, max: 100 Hz)")
        sensor_layout.addRow("Sampling Rate:", self.flow_sampling_hz)
        
        sensor_group.setLayout(sensor_layout)
        solenoid_layout.addWidget(sensor_group)
        
        # Valve Safety Settings
        safety_group = QGroupBox("Safety Settings")
        safety_layout = QFormLayout()
        
        self.max_valve_open_s = QDoubleSpinBox()
        self.max_valve_open_s.setRange(1.0, 60.0)
        self.max_valve_open_s.setValue(self.settings.get('max_valve_open_s', 20.0))
        self.max_valve_open_s.setSuffix(" s")
        self.max_valve_open_s.setToolTip("Maximum time valve can remain open (emergency cutoff)")
        safety_layout.addRow("Max Valve Open Time:", self.max_valve_open_s)
        
        self.no_flow_timeout_s = QDoubleSpinBox()
        self.no_flow_timeout_s.setRange(0.5, 10.0)
        self.no_flow_timeout_s.setValue(self.settings.get('no_flow_timeout_s', 3.5))
        self.no_flow_timeout_s.setSuffix(" s")
        self.no_flow_timeout_s.setToolTip("Abort delivery if no flow detected for this duration")
        safety_layout.addRow("No-Flow Timeout:", self.no_flow_timeout_s)
        
        self.predictive_close_ms = QDoubleSpinBox()
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
        
        self.use_pulse_delivery = QCheckBox("Enable Pulse Mode")
        self.use_pulse_delivery.setChecked(self.settings.get('use_pulse_delivery', True))
        self.use_pulse_delivery.setToolTip("Use micro-pulse delivery for precision (recommended)")
        pulse_layout.addRow("", self.use_pulse_delivery)
        
        self.pulse_width_ms = QSpinBox()
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
        
        self.pump_volume = QDoubleSpinBox()
        self.pump_volume.setRange(0, 1000)
        self.pump_volume.setValue(self.settings.get('pump_volume_ul', 50))
        self.pump_volume.setSuffix(" µL")
        self.pump_volume.setToolTip("Volume delivered per pump trigger")
        pump_layout.addRow("Pump Output Volume:", self.pump_volume)
        
        self.calibration_factor = QDoubleSpinBox()
        self.calibration_factor.setRange(0.1, 10.0)
        self.calibration_factor.setValue(self.settings.get('calibration_factor', 1.0))
        self.calibration_factor.setSingleStep(0.1)
        self.calibration_factor.setDecimals(2)
        self.calibration_factor.setToolTip("Calibration multiplier to adjust for pump variance")
        pump_layout.addRow("Calibration Factor:", self.calibration_factor)
        
        self.min_triggers = QSpinBox()
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
        return widget

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
                    "Please stop the current schedule first."
                )
                # Revert to previous mode
                old_mode = self.settings.get('hardware_mode', 'solenoid')
                self.hardware_mode_combo.blockSignals(True)
                self.hardware_mode_combo.setCurrentText(old_mode)
                self.hardware_mode_combo.blockSignals(False)
                return
        
        self._update_hardware_ui_visibility()
        self.print_to_terminal(f"Hardware mode changed to: {mode}")
    
    def _update_hardware_ui_visibility(self):
        """
        Show/hide settings groups based on hardware mode.
        
        Progressive Disclosure: Only show relevant settings
        """
        is_solenoid = self.hardware_mode_combo.currentText() == 'solenoid'
        self.solenoid_group.setVisible(is_solenoid)
        self.pump_group.setVisible(not is_solenoid)
    
    def _auto_detect_teensy(self):
        """Auto-detect Teensy port using system controller"""
        try:
            port = self.system_controller.detect_teensy_port()
            if port:
                self.teensy_port_edit.setText(port)
                self.print_to_terminal(f"✓ Teensy detected on {port}")
                QMessageBox.information(self, "Auto-Detect", f"Teensy found on {port}")
            else:
                self.print_to_terminal("✗ Teensy not detected. Check USB connection.")
                QMessageBox.warning(self, "Auto-Detect", 
                    "Teensy not found. Ensure:\n"
                    "• Teensy is connected via USB\n"
                    "• Firmware is uploaded\n"
                    "• You are in 'dialout' group")
        except Exception as e:
            self.print_to_terminal(f"Auto-detect error: {e}")
            QMessageBox.critical(self, "Error", f"Auto-detect failed: {str(e)}")
    
    def _test_teensy_connection(self):
        """Test Teensy connection using basic ping with proper resource management"""
        import serial
        import json
        import time
        
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
                                self.print_to_terminal(f"✓ Teensy connection OK on {port}")
                                QMessageBox.information(self, "Connection Test", 
                                    f"Teensy responded successfully!\nPort: {port}")
                                break  # Exit loop, port closed in finally
                        except json.JSONDecodeError:
                            pass
                time.sleep(0.1)
            
            if not pong_received:
                self.print_to_terminal(f"Teensy did not respond on {port}")
                QMessageBox.warning(self, "Connection Test", 
                    f"Teensy did not respond.\n\n"
                    f"Troubleshooting:\n"
                    f"- Verify firmware is uploaded\n"
                    f"- Check serial port permissions\n"
                    f"- Try replugging USB cable")
                
        except serial.SerialException as e:
            self.print_to_terminal(f"Serial error: {e}")
            QMessageBox.critical(self, "Connection Test", 
                f"Failed to open port:\n{str(e)}\n\n"
                f"Check that no other program is using {port}")
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
        - LabAdmin role required
        - Visual indicators for calibration quality
        """
        from PyQt5.QtWidgets import (
            QTableWidget, QTableWidgetItem, QHeaderView, 
            QAbstractItemView, QPushButton, QDialog, QDialogButtonBox,
            QProgressBar
        )
        from PyQt5.QtGui import QColor
        from PyQt5.QtCore import Qt
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Header with info
        header = QLabel(
            "<b>Valve Calibration Manager</b><br>"
            "<span style='color: #666;'>Per-valve empirical calibration for precision water delivery</span>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)
        
        # Calibration table
        self.calibration_table = QTableWidget()
        self.calibration_table.setColumnCount(6)
        self.calibration_table.setHorizontalHeaderLabels([
            "Cage", "Status", "Volume/Pulse (mL)", "Quality (CV%)", "Date", "Action"
        ])
        
        # Table styling
        self.calibration_table.setAlternatingRowColors(True)
        self.calibration_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.calibration_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.calibration_table.horizontalHeader().setStretchLastSection(False)
        self.calibration_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.calibration_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.calibration_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.calibration_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.calibration_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.calibration_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        # Populate table with 15 cages
        self._populate_calibration_table()
        
        layout.addWidget(self.calibration_table)
        
        # Action buttons
        button_row = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setToolTip("Reload calibration data from database")
        refresh_btn.clicked.connect(self._populate_calibration_table)
        button_row.addWidget(refresh_btn)
        
        button_row.addStretch()
        
        calibrate_all_btn = QPushButton("Calibrate All Uncalibrated")
        calibrate_all_btn.setToolTip("Run calibration wizard for all uncalibrated valves (admin only)")
        calibrate_all_btn.clicked.connect(self._calibrate_all_uncalibrated)
        button_row.addWidget(calibrate_all_btn)
        
        export_btn = QPushButton("📊 Export Report")
        export_btn.setToolTip("Export calibration data to CSV")
        export_btn.clicked.connect(self._export_calibration_report)
        button_row.addWidget(export_btn)
        
        layout.addLayout(button_row)
        
        # Help text
        help_text = QLabel(
            "<span style='color: #666; font-size: 9pt;'>"
            "💡 <b>Tips:</b> Click 'Calibrate' to run 250-pulse characterization. "
            "Requires lab scale (±0.001g). CV% <5% = production ready."
            "</span>"
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        
        widget.setLayout(layout)
        return widget
    
    def _populate_calibration_table(self):
        """Load calibration data from database and populate table"""
        from PyQt5.QtWidgets import QPushButton
        from PyQt5.QtGui import QColor
        from PyQt5.QtCore import Qt
        from datetime import datetime
        
        self.calibration_table.setRowCount(15)  # 15 cages
        
        # Get all calibrations from database
        calibrations = {}
        try:
            calibrations = self.database_handler.get_all_valve_calibrations()
        except Exception as e:
            self.print_to_terminal(f"Error loading calibrations: {e}")
        
        for cage_id in range(1, 16):
            row = cage_id - 1
            cal = calibrations.get(cage_id)
            
            # Cage number
            cage_item = QTableWidgetItem(f"Cage {cage_id}")
            cage_item.setTextAlignment(Qt.AlignCenter)
            self.calibration_table.setItem(row, 0, cage_item)
            
            if cal:
                # Calibrated - show data
                status_item = QTableWidgetItem("✅ Calibrated")
                status_item.setForeground(QColor(0, 150, 0))
                
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
                
                # Action button - Recalibrate
                btn = QPushButton("🔄 Recalibrate")
                btn.setToolTip(f"Recalibrate cage {cage_id}")
                btn.clicked.connect(lambda checked, c=cage_id: self._launch_calibration_wizard(c))
                self.calibration_table.setCellWidget(row, 5, btn)
                
            else:
                # Not calibrated - show warning
                status_item = QTableWidgetItem("❌ Not Calibrated")
                status_item.setForeground(QColor(200, 0, 0))
                
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
                
                # Action button - Calibrate
                btn = QPushButton("⚙️ Calibrate")
                btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
                btn.setToolTip(f"Calibrate cage {cage_id} (250 pulses)")
                btn.clicked.connect(lambda checked, c=cage_id: self._launch_calibration_wizard(c))
                self.calibration_table.setCellWidget(row, 5, btn)
    
    def _launch_calibration_wizard(self, cage_id):
        """Launch calibration wizard for specific cage"""
        # Check permissions
        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in to calibrate valves.")
            return
        
        current_trainer = self.login_system.get_current_trainer()
        if not current_trainer or current_trainer.get('role') != 'super':
            QMessageBox.warning(
                self,
                "Permission Denied",
                "Valve calibration requires LabAdmin privileges.\n\n"
                "Please contact a lab administrator."
            )
            return
        
        # Check if schedule is running
        if self.run_stop_section and hasattr(self.run_stop_section, 'worker'):
            if self.run_stop_section.worker and self.run_stop_section.worker.isRunning():
                QMessageBox.warning(
                    self,
                    "Schedule Running",
                    "Cannot calibrate while a schedule is running.\n\n"
                    "Please stop the schedule first."
                )
                return
        
        # Import wizard dialog
        from ui.CalibrationWizard import CalibrationWizard
        
        wizard = CalibrationWizard(
            cage_id=cage_id,
            database_handler=self.database_handler,
            system_controller=self.system_controller,
            parent=self
        )
        
        if wizard.exec_() == QDialog.Accepted:
            # Calibration completed successfully
            self.print_to_terminal(f"✓ Cage {cage_id} calibration completed")
            self._populate_calibration_table()  # Refresh table
            QMessageBox.information(
                self,
                "Calibration Complete",
                f"Cage {cage_id} has been successfully calibrated!\n\n"
                "The new calibration is now active and will be used "
                "in all future deliveries."
            )
    
    def _calibrate_all_uncalibrated(self):
        """Sequentially calibrate all uncalibrated valves"""
        # Check permissions
        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in.")
            return
        
        current_trainer = self.login_system.get_current_trainer()
        if not current_trainer or current_trainer.get('role') != 'super':
            QMessageBox.warning(self, "Permission Denied", "Requires LabAdmin privileges.")
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
            QMessageBox.Yes | QMessageBox.No
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
                "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
            
            calibrations = self.database_handler.get_all_valve_calibrations()
            
            with open(file_path, 'w') as f:
                f.write("Cage,Status,Volume_per_Pulse_mL,CV_Percent,Num_Samples,Calibration_Date,Notes\n")
                
                for cage_id in range(1, 16):
                    if cage_id in calibrations:
                        cal = calibrations[cage_id]
                        f.write(f"{cage_id},Calibrated,{cal['volume_per_pulse_ml']:.6f},"
                               f"{cal['coefficient_of_variation_pct']:.2f},"
                               f"{cal['num_samples']},{cal['calibration_date']},"
                               f"\"{cal.get('notes', '')}\"\n")
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
        # Instantiate the modular priming control widget
        priming_widget = PrimingControlWidget(
            settings=self.settings,
            print_callback=self.print_to_terminal
        )
        
        # Connect widget signals to parent if needed
        priming_widget.status_message.connect(self.print_to_terminal)
        
        return priming_widget

    def _create_system_settings(self):
        """Create system settings tab with proper type handling"""
        system_tab = QWidget()
        layout = QFormLayout()

        # Log Level Spinner with proper type handling
        self.log_level = QSpinBox()
        self.log_level.setRange(0, 4)  # 0=DEBUG to 4=CRITICAL
        self.log_level.setValue(int(self.settings.get('log_level', 2)))
        self.log_level.valueChanged.connect(self._log_level_changed)
        
        # Add tooltip to explain log levels
        self.log_level.setToolTip(
            "0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR, 4=CRITICAL"
        )
        
        layout.addRow("Log Level:", self.log_level)
        
        # Rest of the system settings...
        system_tab.setLayout(layout)
        return system_tab

    def _log_level_changed(self, value):
        """Handle log level changes"""
        self.settings['log_level'] = value
        if self.push_callback:
            self.push_callback()

    def _create_notifications(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        slack_group = QGroupBox("Slack Integration")
        slack_layout = QFormLayout()
        
        self.slack_token = QLineEdit()
        self.slack_token.setText(self._decrypt_sensitive_data(
            self.settings.get('slack_token', '')))
        self.slack_token.setEchoMode(QLineEdit.Password)
        slack_layout.addRow("Slack Bot Token:", self.slack_token)
        
        self.slack_channel = QLineEdit()
        self.slack_channel.setText(self.settings.get('channel_id', ''))
        slack_layout.addRow("Channel ID:", self.slack_channel)
        
        slack_group.setLayout(slack_layout)
        layout.addWidget(slack_group)
        
        widget.setLayout(layout)
        return widget

    def _create_backup_restore(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        backup_group = QGroupBox("Backup and Restore")
        backup_layout = QVBoxLayout()
        
        backup_button = QPushButton("Create Backup")
        backup_button.clicked.connect(self.create_backup)
        backup_layout.addWidget(backup_button)
        
        restore_button = QPushButton("Restore from Backup")
        restore_button.clicked.connect(self.restore_from_backup)
        backup_layout.addWidget(restore_button)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        widget.setLayout(layout)
        return widget

    def _create_data_import_export(self):
        widget = QWidget()
        layout = QGridLayout()
        
        export_btn = QPushButton("Export Animals to CSV")
        export_btn.clicked.connect(self.export_animals)
        import_btn = QPushButton("Import Animals from CSV")
        import_btn.clicked.connect(self.import_animals)
        
        layout.addWidget(export_btn, 0, 0)
        layout.addWidget(import_btn, 0, 1)
        
        widget.setLayout(layout)
        return widget

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
                self, "Save Backup", 
                f"rrr_backup_{timestamp}.json",
                "JSON files (*.json)"
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
                self, "Load Backup",
                "",
                "JSON files (*.json)"
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
        self.slack_token.setText(self._decrypt_sensitive_data(self.settings.get('slack_token', '')))
        self.slack_channel.setText(self.settings.get('channel_id', ''))
        self.log_level.setValue(self.settings.get('log_level', 2))

    def _save_all_settings(self):
        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in to modify settings.")
            return
        
        try:
            # Build updated settings dictionary
            updated_settings = {
                # Hardware mode
                'hardware_mode': self.hardware_mode_combo.currentText(),
                
                # Solenoid settings
                'uart_port': self.teensy_port_edit.text(),
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
                
                # Notifications
                'slack_token': self._encrypt_sensitive_data(self.slack_token.text()) if hasattr(self, 'slack_token') else '',
                'channel_id': self.slack_channel.text() if hasattr(self, 'slack_channel') else '',
                
                # System
                'log_level': self.log_level.value() if hasattr(self, 'log_level') else 2
            }
            
            # Update settings via system controller (ensures persistence)
            self.settings.update(updated_settings)
            self.system_controller.save_settings(self.settings)
            
            # Emit signal for other components
            self.settings_updated.emit(self.settings)
            
            self.print_to_terminal(f"✓ Settings saved (mode: {updated_settings['hardware_mode']}, pulse mode: {updated_settings['use_pulse_delivery']})")
            QMessageBox.information(self, "Success", "Settings saved successfully!\n\nChanges will take effect on next schedule run.")
            
        except Exception as e:
            self.print_to_terminal(f"✗ Settings save failed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def export_animals(self):
        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in to export animals.")
            return
        
        if not self.database_handler:
            QMessageBox.critical(self, "Export Error", "Database handler not initialized")
            return
        
        try:
            file_path, file_type = QFileDialog.getSaveFileName(
                self, "Export Animals", "", 
                "Excel Files (*.xlsx);;CSV Files (*.csv)"  # Make Excel default
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
                last_weighted = (datetime.fromisoformat(animal.last_weighted).strftime('%Y-%m-%d %H:%M:%S') 
                               if animal.last_weighted else '')
                last_watering = (datetime.fromisoformat(animal.last_watering).strftime('%Y-%m-%d %H:%M:%S') 
                               if animal.last_watering else '')
                
                data.append({
                    'Lab Animal ID': animal.lab_animal_id,
                    'Name': animal.name,
                    'Sex': animal.sex or '',
                    'Initial Weight (g)': f"{animal.initial_weight:.1f}" if animal.initial_weight else '',
                    'Last Weight (g)': f"{animal.last_weight:.1f}" if animal.last_weight else '',
                    'Last Weighted': last_weighted,
                    'Last Watering': last_watering
                })
            
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
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length
                
                writer.close()
            else:
                # Mac-friendly CSV settings
                df.to_csv(file_path, 
                         index=False, 
                         encoding='utf-8-sig',  # BOM for Excel Mac
                         sep=',',
                         date_format='%Y-%m-%d %H:%M:%S')
            
            self.print_to_terminal(f"Successfully exported {len(animals)} animals to {file_path}")
            QMessageBox.information(self, "Success", f"Successfully exported {len(animals)} animals")
            
        except AttributeError as e:
            QMessageBox.critical(self, "Export Error", "Database connection error. Please check system configuration.")
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
                        sex = 'female' if row['# Females'] == 1 else 'male' if row['# Males'] == 1 else None
                        
                        # Convert birthdate to our datetime format
                        birthdate = datetime.strptime(str(row['Birthdate']), '%y%m%d')
                        
                        animal = Animal(
                            animal_id=None,
                            lab_animal_id=str(row['Ear tag ID#']) if pd.notna(row['Ear tag ID#']) else row['Cage Number #'],
                            name=row['Nickname'] if pd.notna(row['Nickname']) else '',
                            initial_weight=None,  # No weight in lab format
                            last_weight=None,
                            last_weighted=None,
                            last_watering=None,
                            sex=sex
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