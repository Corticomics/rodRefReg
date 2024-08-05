from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QDateTimeEdit, QFormLayout, QTabWidget, QHBoxLayout)
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

        # Create Tabs
        self.tab_widget = QTabWidget(self)
        self.calendar_tab = QWidget()
        self.offline_tab = QWidget()
        
        self.tab_widget.addTab(self.calendar_tab, "Calendar Mode")
        self.tab_widget.addTab(self.offline_tab, "Offline Mode")

        # Calendar Mode UI
        self.start_time_label = QLabel("Start Time:")
        self.start_time_input = QDateTimeEdit(self)
        self.start_time_input.setCalendarPopup(True)
        self.start_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.end_time_label = QLabel("End Time:")
        self.end_time_input = QDateTimeEdit(self)
        self.end_time_input.setCalendarPopup(True)
        self.end_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        # Offline Mode UI
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

        # Calendar Tab Layout
        calendar_layout = QFormLayout()
        calendar_layout.addRow(self.start_time_label, self.start_time_input)
        calendar_layout.addRow(self.end_time_label, self.end_time_input)
        self.calendar_tab.setLayout(calendar_layout)

        # Offline Tab Layout
        offline_layout = QFormLayout()
        offline_layout.addRow(self.offline_label, self.offline_input)
        self.offline_tab.setLayout(offline_layout)

        # Interval and Stagger Layout
        interval_stagger_layout = QFormLayout()
        interval_stagger_layout.addRow(self.interval_label, self.interval_input)
        interval_stagger_layout.addRow(self.stagger_label, self.stagger_input)

        # Add widgets to main layout
        self.layout.addWidget(self.tab_widget)
        self.layout.addLayout(interval_stagger_layout)

        # Buttons Layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.relay_hats_button)

        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)

    def load_settings(self, settings):
        # Load settings for calendar mode
        if 'window_start' in settings and 'window_end' in settings:
            self.start_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_start']))
            self.end_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_end']))

        # Load settings for offline mode
        if 'offline_duration' in settings:
            self.offline_input.setText(str(settings['offline_duration']))

        # Load common settings
        self.interval_input.setText(str(settings.get('interval', 0)))
        self.stagger_input.setText(str(settings.get('stagger', 0)))

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
