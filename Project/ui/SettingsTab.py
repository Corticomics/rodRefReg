from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
    QLineEdit, QLabel, QPushButton, QMessageBox
)

class SettingsTab(QWidget):
    def __init__(self, settings, save_settings_callback):
        super().__init__()
        self.settings = settings
        self.save_callback = save_settings_callback
        
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Pump Configuration Group
        pump_group = QGroupBox("Pump Configuration")
        pump_layout = QFormLayout()
        
        self.pump_volume_input = QLineEdit()
        self.pump_volume_input.setText(str(settings.get('pump_volume_ul', 50)))
        self.pump_volume_input.setPlaceholderText("Default: 50µL")
        pump_layout.addRow("Pump Output Volume (µL):", self.pump_volume_input)
        
        self.calibration_factor = QLineEdit()
        self.calibration_factor.setText(str(settings.get('calibration_factor', 1.0)))
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

        # Save Button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

    def save_settings(self):
        try:
            self.settings.update({
                'pump_volume_ul': float(self.pump_volume_input.text()),
                'calibration_factor': float(self.calibration_factor.text()),
                'slack_token': self.slack_token_input.text(),
                'channel_id': self.slack_channel_input.text()
            })
            self.save_callback()
            QMessageBox.information(self, "Success", "Settings saved successfully")
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid input: {str(e)}") 