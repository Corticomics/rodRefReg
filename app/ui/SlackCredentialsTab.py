# app/gui/SlackCredentialsTab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QLabel, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt

class SlackCredentialsTab(QWidget):
    def __init__(self, settings, save_slack_credentials_callback):
        super().__init__()

        self.settings = settings
        self.save_callback = save_slack_credentials_callback

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        form_layout = QFormLayout()
        self.entries = {}

        # Slack Token
        slack_token_label = QLabel("Slack Bot Token:")
        self.slack_token_input = QLineEdit()
        self.slack_token_input.setPlaceholderText("Enter your Slack Bot Token")
        self.slack_token_input.setText(self.settings.get('slack_token', ''))
        form_layout.addRow(slack_token_label, self.slack_token_input)
        self.entries["slack_token"] = self.slack_token_input

        # Slack Channel ID
        slack_channel_label = QLabel("Slack Channel ID:")
        self.slack_channel_input = QLineEdit()
        self.slack_channel_input.setPlaceholderText("Enter your Slack Channel ID")
        self.slack_channel_input.setText(self.settings.get('channel_id', ''))
        form_layout.addRow(slack_channel_label, self.slack_channel_input)
        self.entries["slack_channel"] = self.slack_channel_input

        self.layout.addLayout(form_layout)

        # Save Button
        save_button = QPushButton("Save Slack Credentials")
        save_button.clicked.connect(self.save_slack_credentials)
        self.layout.addWidget(save_button)

    def save_slack_credentials(self):
        try:
            slack_token = self.slack_token_input.text().strip()
            slack_channel = self.slack_channel_input.text().strip()

            if not slack_token or not slack_channel:
                QMessageBox.warning(self, "Input Error", "Please enter both Slack Bot Token and Channel ID.")
                return

            # Update settings
            self.settings['slack_token'] = slack_token
            self.settings['channel_id'] = slack_channel

            # Call the save callback to handle saving
            self.save_callback()

            QMessageBox.information(self, "Success", "Slack credentials saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save Slack credentials: {e}")