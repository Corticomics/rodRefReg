from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout
from utils.config_handler import save_configuration

class ConfigWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Settings")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        self.slack_token_label = QLabel("Slack Token:")
        layout.addWidget(self.slack_token_label)

        self.slack_token_input = QLineEdit()
        layout.addWidget(self.slack_token_input)

        self.channel_id_label = QLabel("Channel ID:")
        layout.addWidget(self.channel_id_label)

        self.channel_id_input = QLineEdit()
        layout.addWidget(self.channel_id_input)

        self.save_button = QPushButton("Save Configuration")
        self.save_button.clicked.connect(self.save_configuration)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def save_configuration(self):
        settings = {
            "slack_token": self.slack_token_input.text(),
            "channel_id": self.channel_id_input.text(),
        }
        if save_configuration(settings):
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Failed to save configuration")
