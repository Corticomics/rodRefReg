from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QGroupBox, 
    QFormLayout, QLineEdit, QLabel, QPushButton, 
    QMessageBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
import json
import os
import base64
from cryptography.fernet import Fernet
from datetime import datetime

class SettingsTab(QWidget):
    settings_updated = pyqtSignal(dict)
    
    def __init__(self, system_controller, suggest_callback=None, 
                 push_callback=None, slack_callback=None, 
                 run_stop_section=None, login_system=None):
        super().__init__()
        self.system_controller = system_controller
        self.suggest_callback = suggest_callback
        self.push_callback = push_callback
        self.slack_callback = slack_callback
        self.run_stop_section = run_stop_section
        self.login_system = login_system
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.tab_widget.addTab(self._create_pump_settings(), "Pump Settings")
        self.tab_widget.addTab(self._create_system_settings(), "System")
        self.tab_widget.addTab(self._create_notifications(), "Notifications")
        self.tab_widget.addTab(self._create_backup_restore(), "Backup/Restore")
        
        layout.addWidget(self.tab_widget)
        
        # Add save button
        save_button = QPushButton("Save All Settings")
        save_button.clicked.connect(self._save_all_settings)
        layout.addWidget(save_button)

    def _create_pump_settings(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Pump Configuration Group
        pump_group = QGroupBox("Pump Configuration")
        pump_layout = QFormLayout()
        
        self.pump_volume = QDoubleSpinBox()
        self.pump_volume.setRange(0, 1000)
        self.pump_volume.setValue(self.system_controller.get('pump_volume_ul', 50))
        self.pump_volume.setSuffix(" µL")
        pump_layout.addRow("Pump Output Volume:", self.pump_volume)
        
        self.calibration_factor = QDoubleSpinBox()
        self.calibration_factor.setRange(0.1, 10.0)
        self.calibration_factor.setValue(self.system_controller.get('calibration_factor', 1.0))
        self.calibration_factor.setSingleStep(0.1)
        pump_layout.addRow("Calibration Factor:", self.calibration_factor)
        
        pump_group.setLayout(pump_layout)
        layout.addWidget(pump_group)
        
        widget.setLayout(layout)
        return widget

    def _create_system_settings(self):
        """Create system settings tab with proper type handling"""
        system_tab = QWidget()
        layout = QFormLayout()

        # Log Level Spinner with proper type handling
        self.log_level = QSpinBox()
        self.log_level.setRange(0, 4)  # 0=DEBUG to 4=CRITICAL
        self.log_level.setValue(int(self.system_controller.get('log_level', 2)))
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
        self.system_controller['log_level'] = value
        if self.push_callback:
            self.push_callback()

    def _create_notifications(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        slack_group = QGroupBox("Slack Integration")
        slack_layout = QFormLayout()
        
        self.slack_token = QLineEdit()
        self.slack_token.setText(self._decrypt_sensitive_data(
            self.system_controller.get('slack_token', '')))
        self.slack_token.setEchoMode(QLineEdit.Password)
        slack_layout.addRow("Slack Bot Token:", self.slack_token)
        
        self.slack_channel = QLineEdit()
        self.slack_channel.setText(self.system_controller.get('channel_id', ''))
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
                    json.dump(self.system_controller, f, indent=4)
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
                
                self.system_controller.update(backup_settings)
                self.load_settings()
                QMessageBox.information(self, "Success", "Settings restored successfully")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore backup: {str(e)}")

    def load_settings(self):
        """Reload all settings into UI elements"""
        self.pump_volume.setValue(self.system_controller.get('pump_volume_ul', 50))
        self.calibration_factor.setValue(self.system_controller.get('calibration_factor', 1.0))
        self.slack_token.setText(self._decrypt_sensitive_data(self.system_controller.get('slack_token', '')))
        self.slack_channel.setText(self.system_controller.get('channel_id', ''))
        self.log_level.setValue(self.system_controller.get('log_level', 2))

    def _save_all_settings(self):
        try:
            self.system_controller.update({
                'pump_volume_ul': self.pump_volume.value(),
                'calibration_factor': self.calibration_factor.value(),
                'slack_token': self._encrypt_sensitive_data(self.slack_token.text()),
                'channel_id': self.slack_channel.text(),
                'log_level': self.log_level.value()
            })
            
            self.push_callback()
            self.settings_updated.emit(self.system_controller)
            QMessageBox.information(self, "Success", "Settings saved successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}") 