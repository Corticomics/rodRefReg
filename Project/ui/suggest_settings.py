# ui/suggest_settings_section.py
import json
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QPushButton, QLineEdit, QTabWidget, QDateTimeEdit
)
from PyQt5.QtCore import QDateTime
from .SuggestSettingsTab import SuggestSettingsTab
from .SlackCredentialsTab import SlackCredentialsTab
from .UserTab import UserTab
from .SettingsTab import SettingsTab

SAVED_SETTINGS_DIR = "saved_settings"

class SuggestSettingsSection(QWidget):
    def __init__(self, settings, suggest_callback, push_callback, save_slack_callback, run_stop_section=None, login_system=None):
        super().__init__()
        self.settings = settings
        self.suggest_callback = suggest_callback
        self.push_callback = push_callback
        self.save_slack_callback = save_slack_callback
        self.run_stop_section = run_stop_section
        self.login_system = login_system

        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create the suggest tab
        self.suggest_tab = SuggestTab(settings, suggest_callback, push_callback)
        self.tab_widget.addTab(self.suggest_tab, "Suggest Settings")
        
        # Create the slack tab
        self.slack_tab = SlackTab(settings, save_slack_callback)
        self.tab_widget.addTab(self.slack_tab, "Slack Settings")
        
        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

class SuggestTab(QWidget):
    def __init__(self, settings, suggest_callback, push_callback):
        super().__init__()
        self.settings = settings
        self.suggest_callback = suggest_callback
        self.push_callback = push_callback
        self.entries = {}
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create form layout for inputs
        form_layout = QFormLayout()
        
        # Add datetime picker
        self.entries["start_datetime"] = QDateTimeEdit()
        self.entries["start_datetime"].setDateTime(QDateTime.currentDateTime())
        self.entries["start_datetime"].setCalendarPopup(True)
        form_layout.addRow("Start Date/Time:", self.entries["start_datetime"])
        
        # Add duration input
        self.entries["duration"] = QLineEdit()
        self.entries["duration"].setPlaceholderText("Enter duration in days")
        form_layout.addRow("Duration (days):", self.entries["duration"])
        
        # Add frequency input
        self.entries["frequency"] = QLineEdit()
        self.entries["frequency"].setPlaceholderText("Enter frequency in hours")
        form_layout.addRow("Frequency (hours):", self.entries["frequency"])
        
        # Add volume inputs for each relay pair
        relay_pairs = [(1, 2), (3, 4), (5, 6), (7, 8)]  # Example relay pairs
        for pair in relay_pairs:
            volume_input = QLineEdit()
            volume_input.setPlaceholderText("Enter volume in mL")
            self.entries[f"relay_{pair[0]}_{pair[1]}"] = volume_input
            form_layout.addRow(f"Volume for Relay {pair[0]}-{pair[1]} (mL):", volume_input)
        
        layout.addLayout(form_layout)
        
        # Add buttons
        button_layout = QHBoxLayout()
        suggest_button = QPushButton("Suggest Settings")
        suggest_button.clicked.connect(self.suggest_callback)
        push_button = QPushButton("Push Settings")
        push_button.clicked.connect(self.push_callback)
        
        button_layout.addWidget(suggest_button)
        button_layout.addWidget(push_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

class SlackTab(QWidget):
    def __init__(self, settings, save_callback):
        super().__init__()
        self.settings = settings
        self.save_callback = save_callback
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create form layout for Slack settings
        form_layout = QFormLayout()
        
        # Add Slack token input
        self.slack_token_input = QLineEdit()
        self.slack_token_input.setText(self.settings.get('slack_token', ''))
        form_layout.addRow("Slack Token:", self.slack_token_input)
        
        # Add channel ID input
        self.slack_channel_input = QLineEdit()
        self.slack_channel_input.setText(self.settings.get('channel_id', ''))
        form_layout.addRow("Channel ID:", self.slack_channel_input)
        
        layout.addLayout(form_layout)
        
        # Add save button
        save_button = QPushButton("Save Credentials")
        save_button.clicked.connect(self.save_callback)
        layout.addWidget(save_button)
        
        self.setLayout(layout)