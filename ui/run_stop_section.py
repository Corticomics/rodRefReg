from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QDateTimeEdit, QComboBox, QFormLayout)
from PyQt5.QtCore import QDateTime

class RunStop(QWidget):
    def __init__(self, run_callback, stop_callback, update_settings_callback, change_relay_hats_callback, settings=None, parent=None):
        super().__init__(parent)
        self.run_callback = run_callback
        self.stop_callback = stop_callback
        self.update_settings_callback = update_settings_callback
        self.change_relay_hats_callback = change_relay_hats_callback

        self.init_ui()
        if settings:
            self.load_settings(settings)

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Calendar-Based Time Window Selection
        self.start_time_label = QLabel("Start Time:")
        self.start_time_input = QDateTimeEdit(self)
        self.start_time_input.setCalendarPopup(True)
        self.start_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.end_time_label = QLabel("End Time:")
        self.end_time_input = QDateTimeEdit(self)
        self.end_time_input.setCalendarPopup(True)
        self.end_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        # Offline Mode
        self.offline_label = QLabel("Offline Duration (minutes):")
        self.offline_input = QLineEdit(self)
        self.offline_input.setPlaceholderText("Enter minutes")

        # Interval and Stagger Inputs
        self.interval_label = QLabel("Interval (seconds):")
        self.interval_input = QLineEdit(self)
        self.interval_input.setPlaceholderText("Enter seconds")

        self.stagger_label = QLabel("Stagger (seconds):")
        self.stagger_input = QLineEdit(self)
        self.stagger_input.setPlaceholderText("Enter seconds")

        # Buttons
        self.run_button = QPushButton("Run", self)
        self.stop_button = QPushButton("Stop", self)
        self.update_button = QPushButton("Update Settings", self)
        self.relay_hats_button = QPushButton("Change Relay Hats", self)

        self.run_button.clicked.connect(self.run_callback)
        self.stop_button.clicked.connect(self.stop_callback)
        self.update_button.clicked.connect(self.update_settings_callback)
        self.relay_hats_button.clicked.connect(self.change_relay_hats_callback)

        # Layout
        form_layout = QFormLayout()
        form_layout.addRow(self.start_time_label, self.start_time_input)
        form_layout.addRow(self.end_time_label, self.end_time_input)
        form_layout.addRow(self.offline_label, self.offline_input)
        form_layout.addRow(self.interval_label, self.interval_input)
        form_layout.addRow(self.stagger_label, self.stagger_input)

        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.run_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.update_button)
        self.layout.addWidget(self.relay_hats_button)

        self.setLayout(self.layout)

    def load_settings(self, settings):
        # Change here to use window_start and window_end
        self.start_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_start']))
        self.end_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_end']))
        self.offline_input.setText(str(settings.get('offline_duration', 0)))  # Provide a default if offline_duration is not present
        self.interval_input.setText(str(settings['interval']))
        self.stagger_input.setText(str(settings['stagger']))

    def get_start_time(self):
        return self.start_time_input.dateTime().toPython()

    def get_end_time(self):
        return self.end_time_input.dateTime().toPython()

    def get_offline_duration(self):
        try:
            return int(self.offline_input.text())
        except ValueError:
            return 0

    def get_interval(self):
        try:
            return int(self.interval_input.text())
        except ValueError:
            return 0

    def get_stagger(self):
        try:
            return int(self.stagger_input.text())
        except ValueError:
            return 0
