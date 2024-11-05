# app/gui/run_stop_section.py

from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QLabel, QPushButton, QVBoxLayout, 
    QHBoxLayout, QMessageBox, QDateTimeEdit, QTabWidget
)
from PyQt5.QtCore import QDateTime, QTimer

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
        self.start_time_label = QLabel("Start Time:")
        self.start_time_input = QDateTimeEdit(self.calendar_widget)
        self.start_time_input.setCalendarPopup(True)
        self.start_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_time_input.setDateTime(QDateTime.currentDateTime())  # Default to now
        self.start_time_input.setMinimumDateTime(QDateTime.currentDateTime())  # Set minimum to now

        self.end_time_label = QLabel("End Time:")
        self.end_time_input = QDateTime