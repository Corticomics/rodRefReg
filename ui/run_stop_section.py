from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QDateTimeEdit, QTabWidget, QFormLayout)
from PyQt5.QtCore import QDateTime

class RunStopSection(QWidget):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, settings=None, parent=None):
        super().__init__(parent)
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback
        self.settings = settings

        self.init_ui()
        if settings:
            self.load_settings(settings)

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Tab widget for Calendar and Offline modes
        self.tab_widget = QTabWidget()
        self.calendar_widget = QWidget()
        self.offline_widget = QWidget()

        # Calendar-Based Time Window Selection
        self.start_time_label = QLabel("Start Time:")
        self.start_time_input = QDateTimeEdit(self.calendar_widget)
        self.start_time_input.setCalendarPopup(True)
        self.start_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.end_time_label = QLabel("End Time:")
        self.end_time_input = QDateTimeEdit(self.calendar_widget)
        self.end_time_input.setCalendarPopup(True)
        self.end_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        calendar_layout = QFormLayout()
        calendar_layout.addRow(self.start_time_label, self.start_time_input)
        calendar_layout.addRow(self.end_time_label, self.end_time_input)
        self.calendar_widget.setLayout(calendar_layout)

        # Offline Mode
        self.offline_label = QLabel("Offline Duration (minutes):")
        self.offline_input = QLineEdit(self.offline_widget)
        self.offline_input.setPlaceholderText("Enter minutes")

        offline_layout = QFormLayout()
        offline_layout.addRow(self.offline_label, self.offline_input)
        self.offline_widget.setLayout(offline_layout)

        self.tab_widget.addTab(self.calendar_widget, "Calendar Mode")
        self.tab_widget.addTab(self.offline_widget, "Offline Mode")

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
        self.relay_hats_button = QPushButton("Change Relay Hats", self)

        self.run_button.clicked.connect(self.run_program)
        self.stop_button.clicked.connect(self.stop_program)
        self.relay_hats_button.clicked.connect(self.change_relay_hats_callback)

        # Layout
        form_layout = QFormLayout()
        form_layout.addRow(self.interval_label, self.interval_input)
        form_layout.addRow(self.stagger_label, self.stagger_input)

        self.layout.addWidget(self.tab_widget)
        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.run_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.relay_hats_button)

        self.setLayout(self.layout)

    def load_settings(self, settings):
        self.start_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_start']))
        self.end_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_end']))
        self.offline_input.setText(str(settings.get('offline_duration', 60)))  # Use default if not found
        self.interval_input.setText(str(settings['interval']))
        self.stagger_input.setText(str(settings['stagger']))

    def run_program(self):
        try:
            interval = int(self.interval_input.text())
            stagger = int(self.stagger_input.text())
            if self.tab_widget.currentIndex() == 0:  # Calendar Mode
                window_start = self.start_time_input.dateTime().toSecsSinceEpoch()
                window_end = self.end_time_input.dateTime().toSecsSinceEpoch()
            else:  # Offline Mode
                duration = int(self.offline_input.text()) * 60  # Convert minutes to seconds
                window_start = int(QDateTime.currentSecsSinceEpoch())
                window_end = window_start + duration

            self.settings['interval'] = interval
            self.settings['stagger'] = stagger
            self.settings['window_start'] = window_start
            self.settings['window_end'] = window_end

            # Get updated relay settings
            advanced_settings = self.advanced_settings.get_settings()
            self.settings.update(advanced_settings)

            self.run_program_callback(interval, stagger, window_start, window_end)
        except Exception as e:
            print(f"Error running program: {e}")


    def stop_program(self):
        self.stop_program_callback()

    def change_relay_hats(self):
        self.change_relay_hats_callback()
