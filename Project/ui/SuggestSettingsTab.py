from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QLabel, QPushButton, QVBoxLayout, 
    QHBoxLayout, QMessageBox, QComboBox, QDateTimeEdit
)
from PyQt5.QtCore import QDateTime, Qt

class SuggestSettingsTab(QWidget):
    def __init__(self, suggest_settings_callback, push_settings_callback):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        form_layout = QFormLayout()
        self.entries = {}

        # Volume input per relay pair (optional, no validation required for button enable/disable)
        relay_pairs = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]
        for relay_pair in relay_pairs:
            volume_label = QLabel(f"Water Volume for Cage Pair (Relays {relay_pair[0]} & {relay_pair[1]}) (mL):")
            volume_input = QLineEdit()
            volume_input.setPlaceholderText(f"Volume for {relay_pair[0]} & {relay_pair[1]}")
            form_layout.addRow(volume_label, volume_input)
            self.entries[f"relay_{relay_pair[0]}_{relay_pair[1]}"] = volume_input

        # Frequency (required field)
        frequency_label = QLabel("Dispensing Frequency (times per day):")
        self.frequency_input = QLineEdit()
        self.frequency_input.setPlaceholderText("Enter number of times per day")
        form_layout.addRow(frequency_label, self.frequency_input)
        self.entries["frequency"] = self.frequency_input

        # Duration (required field)
        duration_label = QLabel("Duration (days):")
        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("Enter duration in days")
        form_layout.addRow(duration_label, self.duration_input)
        self.entries["duration"] = self.duration_input

        # Start Date and Time (required field)
        start_datetime_label = QLabel("Start Date and Time:")
        self.start_datetime_input = QDateTimeEdit()
        self.start_datetime_input.setCalendarPopup(True)
        self.start_datetime_input.setDateTime(QDateTime.currentDateTime())
        form_layout.addRow(start_datetime_label, self.start_datetime_input)
        self.entries["start_datetime"] = self.start_datetime_input

        self.layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()

        suggest_button = QPushButton("Suggest Settings")
        suggest_button.clicked.connect(suggest_settings_callback)
        button_layout.addWidget(suggest_button)

        self.push_button = QPushButton("Push Settings")
        self.push_button.clicked.connect(push_settings_callback)
        self.push_button.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.push_button)

        self.layout.addLayout(button_layout)

        # Connect signals to enable/disable the push button based on form validation
        self.frequency_input.textChanged.connect(self.validate_form)
        self.duration_input.textChanged.connect(self.validate_form)
        self.start_datetime_input.dateTimeChanged.connect(self.validate_form)

        self.update_button_states()

    def validate_form(self):
        """Validate if all required fields are filled."""
        frequency_valid = bool(self.frequency_input.text().strip())
        duration_valid = bool(self.duration_input.text().strip())
        start_datetime_valid = bool(self.start_datetime_input.dateTime().isValid())

        # If all required fields are valid, enable the Push button
        if frequency_valid and duration_valid and start_datetime_valid:
            self.push_button.setEnabled(True)
            self.push_button.setStyleSheet("")
            self.push_button.setToolTip("")
        else:
            self.push_button.setEnabled(False)
            self.push_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)

    def update_button_states(self):
        """Initial setup of the Push button state."""
        self.validate_form()  # Initial validation on creation


