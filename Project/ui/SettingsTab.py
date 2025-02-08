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
    
    def __init__(self, settings, save_settings_callback):
        super().__init__()
        self.settings = settings
        self.save_callback = save_settings_callback
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create tab widget for different settings categories
        self.tab_widget = QTabWidget()
        
        # Add settings category tabs
        self.tab_widget.addTab(self._create_pump_settings(), "Pump Settings")
        self.tab_widget.addTab(self._create_slack_settings(), "Notifications")
        self.tab_widget.addTab(self._create_system_settings(), "System")
        self.tab_widget.addTab(self._create_backup_settings(), "Backup/Restore")
        
        layout.addWidget(self.tab_widget)
        
        # Add save button
        save_button = QPushButton("Save All Settings")
        save_button.clicked.connect(self.save_all_settings)
        layout.addWidget(save_button)

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

    def _create_slack_settings(self):
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

    def _create_system_settings(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        system_group = QGroupBox("System Configuration")
        system_layout = QFormLayout()
        
        self.debug_mode = QCheckBox()
        self.debug_mode.setChecked(self.settings.get('debug_mode', False))
        system_layout.addRow("Debug Mode:", self.debug_mode)
        
        self.log_level = QSpinBox()
        self.log_level.setRange(0, 4)
        self.log_level.setValue(self.settings.get('log_level', 2))
        system_layout.addRow("Log Level (0-4):", self.log_level)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        widget.setLayout(layout)
        return widget

    def _create_backup_settings(self):
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
        self.debug_mode.setChecked(self.settings.get('debug_mode', False))
        self.log_level.setValue(self.settings.get('log_level', 2))

    def save_all_settings(self):
        try:
            self.settings.update({
                'pump_volume_ul': self.pump_volume.value(),
                'calibration_factor': self.calibration_factor.value(),
                'slack_token': self._encrypt_sensitive_data(self.slack_token.text()),
                'channel_id': self.slack_channel.text(),
                'debug_mode': self.debug_mode.isChecked(),
                'log_level': self.log_level.value()
            })
            
            self.save_callback()
            self.settings_updated.emit(self.settings)
            QMessageBox.information(self, "Success", "Settings saved successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}") 