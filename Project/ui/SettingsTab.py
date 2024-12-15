from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
    QLineEdit, QLabel, QPushButton, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal

class SettingsTab(QWidget):
    pump_config_saved = pyqtSignal(dict)  # Signal emitted after saving pump config

    def __init__(self, settings, save_settings_callback, database_handler, login_system):
        super().__init__()
        self.settings = settings
        self.save_callback = save_settings_callback
        self.database_handler = database_handler
        self.login_system = login_system
        
        # Load current pump config from database
        self.current_config = self.database_handler.get_active_pump_config()
        
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Pump Configuration Group
        pump_group = QGroupBox("Pump Configuration")
        pump_layout = QFormLayout()
        
        self.pump_volume_input = QLineEdit()
        self.pump_volume_input.setText(str(self.current_config['pump_volume_ul']))
        self.pump_volume_input.setPlaceholderText("Default: 50µL")
        pump_layout.addRow("Pump Output Volume (µL):", self.pump_volume_input)
        
        self.calibration_factor = QLineEdit()
        self.calibration_factor.setText(str(self.current_config['calibration_factor']))
        self.calibration_factor.setPlaceholderText("Default: 1.0")
        pump_layout.addRow("Calibration Factor:", self.calibration_factor)
        
        pump_group.setLayout(pump_layout)
        layout.addWidget(pump_group)

        # Add help text
        help_label = QLabel("Note: Calibration factor adjusts for any systematic differences between expected and actual volumes")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        # Slack Configuration Group
        slack_group = QGroupBox("Slack Configuration")
        slack_layout = QFormLayout()
        
        self.slack_token_input = QLineEdit()
        self.slack_token_input.setText(settings.get('slack_token', ''))
        slack_layout.addRow("Slack Bot Token:", self.slack_token_input)
        
        self.slack_channel_input = QLineEdit()
        self.slack_channel_input.setText(settings.get('channel_id', ''))
        slack_layout.addRow("Channel ID:", self.slack_channel_input)
        
        slack_group.setLayout(slack_layout)
        layout.addWidget(slack_group)

        # Save Buttons Layout
        save_buttons_layout = QHBoxLayout()
        
        # Save Settings Button
        save_settings_button = QPushButton("Save General Settings")
        save_settings_button.clicked.connect(self.save_settings)
        save_buttons_layout.addWidget(save_settings_button)

        # Save Pump Configuration Button
        save_pump_button = QPushButton("Save Pump Configuration")
        save_pump_button.clicked.connect(self.save_pump_configuration)
        save_buttons_layout.addWidget(save_pump_button)

        layout.addLayout(save_buttons_layout)

    def save_settings(self):
        try:
            # Validate user permissions for pump config
            current_user = self.login_system.get_current_trainer()
            if not current_user:
                raise ValueError("Must be logged in to save settings")

            # Get and validate pump values
            new_volume = float(self.pump_volume_input.text())
            new_calibration = float(self.calibration_factor.text())
            
            if new_volume <= 0 or new_calibration <= 0:
                raise ValueError("Values must be positive numbers")

            # Update pump configuration if user is super
            if current_user['role'] == 'super':
                config_id = self.database_handler.update_pump_config(
                    new_volume,
                    new_calibration,
                    current_user['trainer_id']
                )
                if not config_id:
                    raise Exception("Failed to update pump configuration")

            # Update local settings
            self.settings.update({
                'slack_token': self.slack_token_input.text(),
                'channel_id': self.slack_channel_input.text()
            })
            self.save_callback()
            
            QMessageBox.information(self, "Success", "Settings saved successfully")
            
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid input: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving settings: {str(e)}")

    def save_pump_configuration(self):
        """Save pump configuration with validation and database update."""
        try:
            # Validate user permissions
            current_user = self.login_system.get_current_trainer()
            if not current_user or current_user['role'] != 'super':
                QMessageBox.warning(self, "Permission Denied", 
                                    "Only super users can update pump configuration")
                return

            # Get and validate new values
            new_volume = float(self.pump_volume_input.text())
            new_calibration = float(self.calibration_factor.text())
            
            if new_volume <= 0 or new_calibration <= 0:
                raise ValueError("Values must be positive numbers")

            # Update pump configuration in database
            config_id = self.database_handler.update_pump_config(
                pump_volume_ul=new_volume, 
                calibration_factor=new_calibration,
                trainer_id=current_user['trainer_id']
            )

            if config_id:
                # Update local settings
                self.settings.update({
                    'pump_volume_ul': new_volume,
                    'calibration_factor': new_calibration
                })
                self.save_callback()
                self.pump_config_saved.emit({
                    'pump_volume_ul': new_volume,
                    'calibration_factor': new_calibration
                })
                QMessageBox.information(self, "Success", 
                                        "Pump configuration saved successfully")
            else:
                raise Exception("Failed to update pump configuration")

        except ValueError as e:
            QMessageBox.critical(self, "Invalid Input", f"Invalid input: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving pump configuration: {str(e)}") 

    def reload_pump_config(self):
        """Reload pump configuration after changes"""
        try:
            self.current_config = self.database_handler.get_active_pump_config()
            self.pump_volume_input.setText(str(self.current_config['pump_volume_ul']))
            self.calibration_factor.setText(str(self.current_config['calibration_factor']))
            
            # Notify volume calculator to reload config
            if hasattr(self, 'volume_calculator'):
                self.volume_calculator.load_pump_config()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reload pump configuration: {e}") 