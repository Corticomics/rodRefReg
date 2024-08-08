from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QDateTimeEdit, QTabWidget, QFormLayout)
from PyQt5.QtCore import QDateTime

class RunStopSection(QWidget):
    def __init__(self, run_callback, stop_callback, change_relay_hats_callback, settings=None, parent=None):
        super().__init__(parent)
        self.run_callback = run_callback
        self.stop_callback = stop_callback
        self.change_relay_hats_callback = change_relay_hats_callback

        self.init_ui()
        if settings:
            self.load_settings(settings)

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_calendar_tab(), "Calendar Mode")
        self.tab_widget.addTab(self.create_offline_tab(), "Offline Mode")
        self.layout.addWidget(self.tab_widget)

        # Interval and Stagger Inputs
        interval_layout = QFormLayout()
        self.interval_input = QLineEdit(self)
        self.interval_input.setPlaceholderText("Enter seconds")
        interval_layout.addRow("Interval (seconds):", self.interval_input)

        self.stagger_input = QLineEdit(self)
        self.stagger_input.setPlaceholderText("Enter seconds")
        interval_layout.addRow("Stagger (seconds):", self.stagger_input)

        self.layout.addLayout(interval_layout)

        # Buttons
        self.run_button = QPushButton("Run", self)
        self.stop_button = QPushButton("Stop", self)
        self.relay_hats_button = QPushButton("Change Relay Hats", self)

        self.run_button.clicked.connect(self.run_program)
        self.stop_button.clicked.connect(self.stop_callback)
        self.relay_hats_button.clicked.connect(self.change_relay_hats_callback)

        self.layout.addWidget(self.run_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.relay_hats_button)

        self.setLayout(self.layout)

    def create_calendar_tab(self):
        calendar_tab = QWidget()
        form_layout = QFormLayout()

        self.start_time_input = QDateTimeEdit(QDateTime.currentDateTime(), self)
        self.start_time_input.setCalendarPopup(True)
        form_layout.addRow(QLabel("Start Time:"), self.start_time_input)
        
        self.end_time_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600), self)
        self.end_time_input.setCalendarPopup(True)
        form_layout.addRow(QLabel("End Time:"), self.end_time_input)

        calendar_tab.setLayout(form_layout)
        return calendar_tab

    def create_offline_tab(self):
        offline_tab = QWidget()
        form_layout = QFormLayout()

        self.offline_duration_input = QLineEdit(self)
        self.offline_duration_input.setPlaceholderText("Enter duration in minutes")
        form_layout.addRow(QLabel("Offline Duration (minutes):"), self.offline_duration_input)

        offline_tab.setLayout(form_layout)
        return offline_tab

    def load_settings(self, settings):
        self.start_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_start']))
        self.end_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_end']))
        self.offline_duration_input.setText(str(settings.get('offline_duration', '')))
        self.interval_input.setText(str(settings['interval']))
        self.stagger_input.setText(str(settings['stagger']))

    def run_program(self):
        interval = int(self.interval_input.text())
        stagger = int(self.stagger_input.text())
        
        if self.tab_widget.currentIndex() == 0:  # Calendar Mode
            window_start = int(self.start_time_input.dateTime().toSecsSinceEpoch())
            window_end = int(self.end_time_input.dateTime().toSecsSinceEpoch())
        else:  # Offline Mode
            duration_minutes = int(self.offline_duration_input.text())
            window_start = int(time.time())
            window_end = window_start + duration_minutes * 60  # Convert minutes to seconds

        self.run_callback(interval, stagger, window_start, window_end)
