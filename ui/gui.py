import sys
import os
from PyQt5.QtCore import Qt

from .terminal_output import TerminalOutput
from .welcome_section import WelcomeSection
from .advanced_settings import AdvancedSettingsSection
from .suggest_settings import SuggestSettings
from .run_stop_section import RunStopSection

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'settings'))
from settings.config import load_settings

from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDateTimeEdit

class RunStopSection(QGroupBox):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback):
        super().__init__("Run/Stop Program")
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback

        layout = QVBoxLayout()

        # Calendar input for start and end times
        calendar_layout = QHBoxLayout()
        self.start_datetime_edit = QDateTimeEdit()
        self.start_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        calendar_layout.addWidget(QLabel("Start Date & Time:"))
        calendar_layout.addWidget(self.start_datetime_edit)

        self.end_datetime_edit = QDateTimeEdit()
        self.end_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        calendar_layout.addWidget(QLabel("End Date & Time:"))
        calendar_layout.addWidget(self.end_datetime_edit)

        layout.addLayout(calendar_layout)

        # Offline mode input for hours and minutes
        offline_layout = QHBoxLayout()
        self.offline_hours_entry = QLineEdit()
        self.offline_hours_entry.setPlaceholderText("Hours")
        offline_layout.addWidget(QLabel("Offline Mode Hours:"))
        offline_layout.addWidget(self.offline_hours_entry)

        self.offline_minutes_entry = QLineEdit()
        self.offline_minutes_entry.setPlaceholderText("Minutes")
        offline_layout.addWidget(QLabel("Offline Mode Minutes:"))
        offline_layout.addWidget(self.offline_minutes_entry)

        layout.addLayout(offline_layout)

        self.run_button = QPushButton("Run Program")
        self.run_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        self.run_button.clicked.connect(self.run_program)
        layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Stop Program")
        self.stop_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        self.stop_button.clicked.connect(self.stop_program)
        layout.addWidget(self.stop_button)

        self.change_relay_hats_button = QPushButton("Change Relay Hats")
        self.change_relay_hats_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        self.change_relay_hats_button.clicked.connect(self.change_relay_hats)
        layout.addWidget(self.change_relay_hats_button)

        self.setLayout(layout)

    def run_program(self):
        interval = int(self.interval_entry.text())
        stagger = int(self.stagger_entry.text())
        window_start = self.start_datetime_edit.dateTime().toString("yyyy-MM-dd HH:mm")
        window_end = self.end_datetime_edit.dateTime().toString("yyyy-MM-dd HH:mm")
        offline_hours = int(self.offline_hours_entry.text() or 0)
        offline_minutes = int(self.offline_minutes_entry.text() or 0)
        self.run_program_callback(interval, stagger, window_start, window_end, offline_hours, offline_minutes)

    def stop_program(self):
        self.stop_program_callback()

    def change_relay_hats(self):
        self.change_relay_hats_callback()
