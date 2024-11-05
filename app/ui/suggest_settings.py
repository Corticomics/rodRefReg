# app/ui/SuggestSettingsSection.py

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QListWidget, QInputDialog, 
    QPushButton, QLabel, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt

from .SuggestSettingsTab import SuggestSettingsTab
from .SlackCredentialsTab import SlackCredentialsTab
from .dashboard import Dashboard

SAVED_SETTINGS_DIR = "saved_settings"

class SuggestSettingsSection(QWidget):
    def __init__(self, settings, suggest_settings_callback, push_settings_callback, save_slack_credentials_callback, advanced_settings, run_stop_section, db_manager, load_callback=None):
        super().__init__()

        self.settings = settings
        self.advanced_settings = advanced_settings  # Store the passed advanced_settings
        self.run_stop_section = run_stop_section  # Store the passed run_stop_section
        self.save_callback = save_slack_credentials_callback
        self.load_callback = load_callback
        self.db_manager = db_manager  # Assign db_manager to an instance variable

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create the tab widget
        self.tab_widget = QTabWidget(self)

        # Create the Suggest Settings Tab
        self.suggest_tab = SuggestSettingsTab(suggest_settings_callback, push_settings_callback, self.db_manager)

        # Create the Dashboard Tab
        self.dashboard_tab = Dashboard(self.db_manager, self.load_callback)

        # Create the Slack Credentials Tab
        self.slack_tab = SlackCredentialsTab(self.settings, self.save_callback)

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.suggest_tab, "Suggest Settings")
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        self.tab_widget.addTab(self.slack_tab, "Slack Bot")

        self.layout.addWidget(self.tab_widget)

        # Add Checkbox for Auto-Save Project
        self.auto_save_checkbox = QCheckBox("Automatically Save Project After Pushing Settings")
        self.layout.addWidget(self.auto_save_checkbox)

        # Initialize saved settings
        self.create_dashboard_ui()

    def create_dashboard_ui(self):
        # Ensure the saved_settings directory exists
        if not os.path.exists(SAVED_SETTINGS_DIR):
            os.makedirs(SAVED_SETTINGS_DIR)

    def save_settings(self):
        try:
            # Ensure the saved_settings directory exists
            if not os.path.exists(SAVED_SETTINGS_DIR):
                os.makedirs(SAVED_SETTINGS_DIR)

            # Get the current values from the input fields
            interval = int(self.run_stop_section.interval_input.text())
            stagger = int(self.run_stop_section.stagger_input.text())

            num_triggers = self.advanced_settings.get_settings()['num_triggers']

            current_settings = {
                "interval": interval,
                "stagger": stagger,
                "num_triggers": {str(k): v for k, v in num_triggers.items()},  # Convert tuple keys to strings
            }

            name, ok = QInputDialog.getText(self, "Save Settings", "Enter a name for these settings:")
            if ok and name:
                file_name = os.path.join(SAVED_SETTINGS_DIR, f"{name}.json")
                with open(file_name, 'w') as f:
                    json.dump(current_settings, f, indent=4)
                self.load_saved_settings()
                QMessageBox.information(self, "Save Success", f"Settings '{name}' saved successfully.")
        except Exception as e:
            print(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    def load_saved_settings(self):
        self.dashboard_tab.load_projects()

    def load_settings_from_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                loaded_settings = json.load(f)

            # Convert string keys back to tuples for num_triggers
            num_triggers = {eval(k): v for k, v in loaded_settings.get("num_triggers", {}).items()}

            # Update the settings with loaded values
            self.settings.update(loaded_settings)
            self.settings['num_triggers'] = num_triggers  # Update num_triggers with tuple keys

            # Update UI fields with the loaded settings
            self.run_stop_section.interval_input.setText(str(self.settings.get('interval', '')))
            self.run_stop_section.stagger_input.setText(str(self.settings.get('stagger', '')))

            # Update advanced settings triggers
            if hasattr(self, 'advanced_settings'):
                self.advanced_settings.update_triggers(self.settings['num_triggers'])

            if self.load_callback:
                self.load_callback()

            QMessageBox.information(self, "Load Success", f"Settings loaded successfully from '{file_path}'.")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Error loading settings: {str(e)}")