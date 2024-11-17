from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, QMessageBox, QSizePolicy
import json
import os

class SlackCredentialsTab(QWidget):
    def __init__(self, settings, save_callback=None):
        super().__init__()

        self.settings = settings
        self.save_callback = save_callback  # Callback to be invoked after saving

        layout = QVBoxLayout()
        self.slack_token_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slack_channel_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        

        # Create fields for Slack token and channel
        self.slack_token_input = QLineEdit(self)
        self.slack_token_input.setPlaceholderText("Enter Slack Token")
        self.slack_token_input.setText(settings.get('slack_token', ''))
        layout.addWidget(QLabel("Slack Token:"))
        layout.addWidget(self.slack_token_input)

        self.slack_channel_input = QLineEdit(self)
        self.slack_channel_input.setPlaceholderText("Enter Slack Channel ID")
        self.slack_channel_input.setText(settings.get('channel_id', ''))
        layout.addWidget(QLabel("Slack Channel ID:"))
        layout.addWidget(self.slack_channel_input)

        # Save button for Slack credentials
        save_button = QPushButton("Save Slack Credentials")
        save_button.clicked.connect(self.save_credentials)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def save_credentials(self):
        self.settings['slack_token'] = self.slack_token_input.text()
        self.settings['channel_id'] = self.slack_channel_input.text()

        # Save to settings.json
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f, indent=4)

            # Notify the user
            QMessageBox.information(self, "Success", "Slack credentials saved successfully.")

            # Call the save callback if exists
            if self.save_callback:
                self.save_callback()  # This should invoke save_slack_credentials_callback in RodentRefreshmentGUI

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save Slack credentials: {str(e)}")
