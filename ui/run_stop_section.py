from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QDateTimeEdit, QComboBox, QFormLayout, QTabWidget)
from PyQt5.QtCore import QDateTime

class RunStop(QWidget):
    def __init__(self, run_callback, stop_callback, update_settings_callback, settings=None, parent=None):
        super().__init__(parent)
        self.run_callback = run_callback
        self.stop_callback = stop_callback
        self.update_settings_callback = update_settings_callback

        self.init_ui()
        if settings:
            self.load_settings(settings)

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Tabs for Calendar and Offline Mode
        self.tab_widget = QTabWidget()
        self.calendar_tab = QWidget()
        self.offline_tab = QWidget()

        # Calendar Tab
        calendar_layout = QFormLayout()
        self.start_time_label = QLabel("Start Time:")
        self.start_time_input = QDateTimeEdit(self)
        self.start_time_input.setCalendarPopup(True)
        self.start_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        calendar_layout.addRow(self.start_time_label, self.start_time_input)

        self.end_time_label = QLabel("End Time:")
        self.end_time_input = QDateTimeEdit(self)
        self.end_time_input.setCalendarPopup(True)
        self.end_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        calendar_layout.addRow(self.end_time_label, self.end_time_input)

        self.calendar_tab.setLayout(calendar_layout)

        # Offline Tab
        offline_layout = QFormLayout()
        self.offline_label = QLabel("Offline Duration (minutes):")
        self.offline_input = QLineEdit(self)
        self.offline_input.setPlaceholderText("Enter minutes")
        offline_layout.addRow(self.offline_label, self.offline_input)
        self.offline_tab.setLayout(offline_layout)

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.calendar_tab, "Calendar Mode")
        self.tab_widget.addTab(self.offline_tab, "Offline Mode")

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

        self.run_button.clicked.connect(self.run_callback)
        self.stop_button.clicked.connect(self.stop_callback)
        self.update_button.clicked.connect(self.update_settings)

        # Layout
        self.layout.addWidget(self.tab_widget)
        form_layout = QFormLayout()
        form_layout.addRow(self.interval_label, self.interval_input)
        form_layout.addRow(self.stagger_label, self.stagger_input)

        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.run_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.update_button)

        self.setLayout(self.layout)

    def load_settings(self, settings):
        if 'start_time' in settings:
            self.start_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['start_time']))
        if 'end_time' in settings:
            self.end_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['end_time']))
        if 'offline_duration' in settings:
            self.offline_input.setText(str(settings['offline_duration']))
        if 'interval' in settings:
            self.interval_input.setText(str(settings['interval']))
        if 'stagger' in settings:
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

    def update_settings(self):
        settings = {
            'start_time': self.get_start_time(),
            'end_time': self.get_end_time(),
            'offline_duration': self.get_offline_duration(),
            'interval': self.get_interval(),
            'stagger': self.get_stagger()
        }
        # Call the update settings callback with the new settings
        self.update_settings_callback(settings)
