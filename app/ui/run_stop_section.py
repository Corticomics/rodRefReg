# app/gui/run_stop_section.py

from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QLabel, QPushButton, QVBoxLayout, 
    QHBoxLayout, QMessageBox, QDateTimeEdit, QTabWidget
)
from PyQt5.QtCore import QDateTime, QTimer, Qt

class RunStopSection(QWidget):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, settings=None, advanced_settings=None, parent=None):
        super().__init__(parent)
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback
        self.settings = settings
        self.advanced_settings = advanced_settings  # Pass advanced settings here

        # Track the state of the job
        self.job_in_progress = False

        self.init_ui()

        # Create a QTimer to keep updating the minimum date/time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_minimum_datetime)
        self.timer.start(1000)  # Update every second

        if settings:
            self.load_settings(settings)

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Tab widget for Calendar and Offline modes
        self.tab_widget = QTabWidget()
        self.calendar_widget = QWidget()
        self.offline_widget = QWidget()

        # Calendar-Based Time Window Selection
        self.calendar_layout = QFormLayout()
        self.start_time_label = QLabel("Start Time:")
        self.start_time_input = QDateTimeEdit()
        self.start_time_input.setCalendarPopup(True)
        self.start_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_time_input.setDateTime(QDateTime.currentDateTime())  # Default to now
        self.start_time_input.setMinimumDateTime(QDateTime.currentDateTime())  # Set minimum to now

        self.end_time_label = QLabel("End Time:")
        self.end_time_input = QDateTimeEdit()
        self.end_time_input.setCalendarPopup(True)
        self.end_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_time_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # Default to now +1 hour
        self.end_time_input.setMinimumDateTime(QDateTime.currentDateTime().addSecs(60))  # At least 1 minute later

        self.calendar_layout.addRow(self.start_time_label, self.start_time_input)
        self.calendar_layout.addRow(self.end_time_label, self.end_time_input)

        self.calendar_widget.setLayout(self.calendar_layout)

        # Offline Mode Selection (Placeholder)
        self.offline_layout = QVBoxLayout()
        self.offline_label = QLabel("Offline Mode: Manual control of relays.")
        self.offline_layout.addWidget(self.offline_label)
        self.offline_widget.setLayout(self.offline_layout)

        # Add tabs
        self.tab_widget.addTab(self.calendar_widget, "Calendar Mode")
        self.tab_widget.addTab(self.offline_widget, "Offline Mode")

        self.layout.addWidget(self.tab_widget)

        # Buttons
        button_layout = QHBoxLayout()

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_program)
        button_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_program)
        self.stop_button.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.stop_button)

        self.change_relay_hats_button = QPushButton("Change Relay Hats")
        self.change_relay_hats_button.clicked.connect(self.change_relay_hats)
        button_layout.addWidget(self.change_relay_hats_button)

        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)

    def run_program(self):
        if not self.job_in_progress:
            self.job_in_progress = True
            self.run_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            # Fetch settings
            start_datetime = self.start_time_input.dateTime()
            end_datetime = self.end_time_input.dateTime()
            current_time = QDateTime.currentDateTime()
            if start_datetime < current_time:
                QMessageBox.warning(self, "Invalid Start Time", "Start time cannot be in the past.")
                self.job_in_progress = False
                self.run_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                return
            if end_datetime <= start_datetime:
                QMessageBox.warning(self, "Invalid End Time", "End time must be after start time.")
                self.job_in_progress = False
                self.run_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                return
            # Call the run_program_callback with necessary parameters
            interval = self.settings.get('interval', 60)
            stagger = self.settings.get('stagger', 5)
            window_start = start_datetime.toSecsSinceEpoch()
            window_end = end_datetime.toSecsSinceEpoch()
            self.run_program_callback(interval, stagger, window_start, window_end)
        else:
            QMessageBox.information(self, "Job In Progress", "A job is already in progress.")

    def stop_program(self):
        if self.job_in_progress:
            self.stop_program_callback()
            self.job_in_progress = False
            self.run_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        else:
            QMessageBox.information(self, "No Job", "No job is currently running.")

    def change_relay_hats(self):
        self.change_relay_hats_callback()

    def load_settings(self, settings):
        try:
            self.start_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings.get('window_start', QDateTime.currentDateTime().toSecsSinceEpoch())))
            self.end_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings.get('window_end', QDateTime.currentDateTime().addSecs(3600).toSecsSinceEpoch())))
            self.run_button.setText("Run")
            self.stop_button.setText("Stop")
        except Exception as e:
            # Assuming print_to_terminal is accessible; adjust as needed
            if hasattr(self, 'print_to_terminal'):
                self.print_to_terminal(f"Error loading settings: {e}")
            else:
                print(f"Error loading settings: {e}")

    def update_minimum_datetime(self):
        current_datetime = QDateTime.currentDateTime()
        self.start_time_input.setMinimumDateTime(current_datetime)
        self.end_time_input.setMinimumDateTime(current_datetime.addSecs(60))  # Ensure end time is at least 1 minute after start