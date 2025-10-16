from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QGroupBox, 
    QFormLayout, QLineEdit, QLabel, QPushButton, 
    QMessageBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFileDialog, QGridLayout, QComboBox, QHBoxLayout, QTextEdit
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
        self.hardware_settings = self._create_hardware_settings()
        self.pump_settings = self._create_pump_settings()
        self.priming_control = self._create_priming_control()
        self.system_settings = self._create_system_settings()
        self.notifications = self._create_notifications()
        self.backup_restore = self._create_backup_restore()
        self.data_import_export = self._create_data_import_export()
        
        # Add sub-tabs to settings - CHECK USABILITY OF SYSTEM AND BACKUP/RESTORE
        self.tab_widget.addTab(self.hardware_settings, "Hardware")
        self.tab_widget.addTab(self.pump_settings, "Pump Settings")
        self.tab_widget.addTab(self.priming_control, "Priming")
        #self.tab_widget.addTab(self.system_settings, "System")
        self.tab_widget.addTab(self.notifications, "Notifications")
        #self.tab_widget.addTab(self.backup_restore, "Backup/Restore")
        self.tab_widget.addTab(self.data_import_export, "Import/Export")
        
        layout.addWidget(self.tab_widget)
        
        # Add save button at bottom of settings
        save_button = QPushButton("Save All Settings")
        save_button.clicked.connect(self._save_all_settings)
        layout.addWidget(save_button)

    def _create_hardware_settings(self):
        """Create hardware configuration tab for pump/solenoid mode selection"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Hardware Mode Group
        mode_group = QGroupBox("Delivery Hardware Mode")
        mode_layout = QFormLayout()
        
        self.hardware_mode_combo = QComboBox()
        self.hardware_mode_combo.addItems(['solenoid', 'pump'])  # Solenoid first (default per requirements)
        current_mode = self.settings.get('hardware_mode', 'solenoid')
        self.hardware_mode_combo.setCurrentText(current_mode)
        self.hardware_mode_combo.currentTextChanged.connect(self._on_hardware_mode_changed)
        mode_layout.addRow("Hardware Mode:", self.hardware_mode_combo)
        
        mode_help = QLabel(
            "• <b>Solenoid</b> (default): Flow sensor-based volumetric control\n"
            "• <b>Pump</b>: Time-based peristaltic pump control"
        )
        mode_help.setWordWrap(True)
        mode_layout.addRow("", mode_help)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Flow Sensor Configuration Group (only visible in solenoid mode)
        self.flow_sensor_group = QGroupBox("Flow Sensor Configuration (Teensy Bridge)")
        flow_layout = QFormLayout()
        
        # Teensy port selection
        port_row = QHBoxLayout()
        self.teensy_port_edit = QLineEdit()
        self.teensy_port_edit.setText(self.settings.get('uart_port', '/dev/ttyACM0'))
        self.teensy_port_edit.setPlaceholderText("/dev/ttyACM0 or auto-detect")
        port_row.addWidget(self.teensy_port_edit)
        
        detect_button = QPushButton("Auto-Detect")
        detect_button.clicked.connect(self._auto_detect_teensy)
        port_row.addWidget(detect_button)
        
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self._test_teensy_connection)
        port_row.addWidget(test_button)
        
        flow_layout.addRow("Teensy Port:", port_row)
        
        # Sampling rate
        self.flow_sampling_hz = QDoubleSpinBox()
        self.flow_sampling_hz.setRange(1.0, 100.0)
        self.flow_sampling_hz.setValue(self.settings.get('flow_sampling_hz', 50.0))
        self.flow_sampling_hz.setSuffix(" Hz")
        self.flow_sampling_hz.setToolTip("Sensor measurement frequency (default: 50 Hz)")
        flow_layout.addRow("Sampling Rate:", self.flow_sampling_hz)
        
        # Safety timeouts
        self.max_valve_open_s = QDoubleSpinBox()
        self.max_valve_open_s.setRange(1.0, 60.0)
        self.max_valve_open_s.setValue(self.settings.get('max_valve_open_s', 20.0))
        self.max_valve_open_s.setSuffix(" s")
        self.max_valve_open_s.setToolTip("Maximum time valve can remain open (safety cutoff)")
        flow_layout.addRow("Max Valve Open Time:", self.max_valve_open_s)
        
        self.no_flow_timeout_s = QDoubleSpinBox()
        self.no_flow_timeout_s.setRange(0.5, 10.0)
        self.no_flow_timeout_s.setValue(self.settings.get('no_flow_timeout_s', 3.5))
        self.no_flow_timeout_s.setSuffix(" s")
        self.no_flow_timeout_s.setToolTip("Abort delivery if no flow detected for this duration")
        flow_layout.addRow("No-Flow Timeout:", self.no_flow_timeout_s)
        
        # Predictive cutoff
        self.predictive_close_ms = QDoubleSpinBox()
        self.predictive_close_ms.setRange(0.0, 100.0)
        self.predictive_close_ms.setValue(self.settings.get('predictive_close_ms', 10.0))
        self.predictive_close_ms.setSuffix(" ms")
        self.predictive_close_ms.setToolTip("Valve close lag compensation (reduces overshoot)")
        flow_layout.addRow("Predictive Close Lag:", self.predictive_close_ms)
        
        self.flow_sensor_group.setLayout(flow_layout)
        layout.addWidget(self.flow_sensor_group)
        
        # Update visibility based on current mode
        self._update_hardware_ui_visibility()
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget

    def _on_hardware_mode_changed(self, mode):
        """Handle hardware mode change"""
        self._update_hardware_ui_visibility()
        self.print_to_terminal(f"Hardware mode changed to: {mode}")
    
    def _update_hardware_ui_visibility(self):
        """Show/hide flow sensor settings based on hardware mode"""
        is_solenoid = self.hardware_mode_combo.currentText() == 'solenoid'
        self.flow_sensor_group.setVisible(is_solenoid)
    
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

    def _create_pump_settings(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Pump Configuration Group
        pump_group = QGroupBox("Pump Configuration")
        pump_layout = QFormLayout()
        
        self.pump_volume = QDoubleSpinBox()
        self.pump_volume.setRange(0, 1000)
        self.pump_volume.setValue(self.settings.get('pump_volume_ul', 50))
        self.pump_volume.setSuffix(" µL")
        pump_layout.addRow("Pump Output Volume:", self.pump_volume)
        
        self.calibration_factor = QDoubleSpinBox()
        self.calibration_factor.setRange(0.1, 10.0)
        self.calibration_factor.setValue(self.settings.get('calibration_factor', 1.0))
        self.calibration_factor.setSingleStep(0.1)
        pump_layout.addRow("Calibration Factor:", self.calibration_factor)
        
        pump_group.setLayout(pump_layout)
        layout.addWidget(pump_group)
        
        widget.setLayout(layout)
        return widget
    
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
                # Hardware settings
                'hardware_mode': self.hardware_mode_combo.currentText(),
                'uart_port': self.teensy_port_edit.text(),  # Canonical key for flow sensor factory
                'flow_sampling_hz': self.flow_sampling_hz.value(),
                'max_valve_open_s': self.max_valve_open_s.value(),
                'no_flow_timeout_s': self.no_flow_timeout_s.value(),
                'predictive_close_ms': self.predictive_close_ms.value(),
                
                # Pump settings
                'pump_volume_ul': self.pump_volume.value(),
                'calibration_factor': self.calibration_factor.value(),
                
                # Notifications
                'slack_token': self._encrypt_sensitive_data(self.slack_token.text()),
                'channel_id': self.slack_channel.text(),
                
                # System
                'log_level': self.log_level.value()
            }
            
            # Update settings via system controller (ensures persistence)
            self.settings.update(updated_settings)
            self.system_controller.save_settings(self.settings)
            
            # Emit signal for other components
            self.settings_updated.emit(self.settings)
            
            self.print_to_terminal(f"✓ Settings saved (mode: {updated_settings['hardware_mode']})")
            QMessageBox.information(self, "Success", "Settings saved successfully")
            
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