from .SuggestSettingsTab import SuggestSettingsTab
from .SlackCredentialsTab import SlackCredentialsTab
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QListWidget, QInputDialog, 
    QPushButton, QLabel, QMessageBox
)
import json
import os

SAVED_SETTINGS_DIR = "saved_settings"

class SuggestSettingsSection(QWidget):
    def __init__(self, settings, suggest_settings_callback, push_settings_callback, save_slack_credentials_callback, advanced_settings, run_stop_section, load_callback=None):
        super().__init__()

        self.settings = settings
        self.advanced_settings = advanced_settings  # Store the passed advanced_settings
        self.run_stop_section = run_stop_section  # Store the passed run_stop_section
        self.save_callback = save_slack_credentials_callback
        self.load_callback = load_callback

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create the tab widget
        self.tab_widget = QTabWidget(self)

        # Create the Suggest Settings Tab
        self.suggest_tab = SuggestSettingsTab(suggest_settings_callback, push_settings_callback)

        # Create the Dashboard Tab
        self.dashboard_tab = QWidget()
        self.dashboard_layout = QVBoxLayout()
        self.dashboard_tab.setLayout(self.dashboard_layout)
        self.create_dashboard_ui()

        # Create the Slack Credentials Tab
        self.slack_tab = SlackCredentialsTab(self.settings, self.save_callback)

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.suggest_tab, "Suggest Settings")
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        self.tab_widget.addTab(self.slack_tab, "Slack Bot")

        self.layout.addWidget(self.tab_widget)

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
        except Exception as e:
            print(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    def load_saved_settings(self):
        self.saved_settings_list.clear()
        if os.path.exists(SAVED_SETTINGS_DIR):
            for file_name in os.listdir(SAVED_SETTINGS_DIR):
                if file_name.endswith(".json"):
                    self.saved_settings_list.addItem(file_name[:-5])

    def create_dashboard_ui(self):
        # Save/Load Settings
        self.saved_settings_list = QListWidget()
        self.saved_settings_list.itemSelectionChanged.connect(self.validate_selection)  # Add validation for selection change
        self.dashboard_layout.addWidget(QLabel("Saved Settings"))
        self.dashboard_layout.addWidget(self.saved_settings_list)

        save_button = QPushButton("Save Current Settings")
        save_button.clicked.connect(self.save_settings)
        self.dashboard_layout.addWidget(save_button)

        self.load_button = QPushButton("Load Selected Settings")
        self.load_button.setEnabled(False)  # Disable initially
        self.load_button.clicked.connect(self.load_settings)
        self.dashboard_layout.addWidget(self.load_button)

        self.load_saved_settings()

    def validate_selection(self):
        """Enable or disable the load button based on whether a setting is selected."""
        selected_item = self.saved_settings_list.currentItem()
        if selected_item:  # If an item is selected, enable the button
            self.load_button.setEnabled(True)
            self.load_button.setStyleSheet("")
            self.load_button.setToolTip("")
                
        else:  # If no item is selected, disable the button and change the color
            self.load_button.setEnabled(False)
            self.load_button.setStyleSheet("")
            self.load_button.setToolTip("")


    def load_settings(self):
        selected_item = self.saved_settings_list.currentItem()
        if selected_item:
            file_name = f"{selected_item.text()}.json"
            full_path = os.path.join(SAVED_SETTINGS_DIR, file_name)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r') as f:
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

                    QMessageBox.information(self, "Load Success", f"Settings '{selected_item.text()}' successfully loaded.")

                except Exception as e:
                    QMessageBox.critical(self, "Load Error", f"Error loading settings: {str(e)}")
            else:
                QMessageBox.critical(self, "Load Error", f"Settings file '{full_path}' does not exist.")



    def save_slack_credentials(self):
        try:
            slack_token = self.slack_tab.slack_token_input.text()
            slack_channel = self.slack_tab.slack_channel_input.text()

            # Save Slack credentials to the existing settings file
            self.settings['slack_token'] = slack_token
            self.settings['channel_id'] = slack_channel

            # Save all settings including Slack credentials
            with open("settings.json", 'w') as f:
                json.dump(self.settings, f, indent=4)

            QMessageBox.information(self, "Success", "Slack credentials saved successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save Slack credentials: {e}")