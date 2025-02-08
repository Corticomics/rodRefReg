# ui/suggest_settings_section.py
import json
import os

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QListWidget, QInputDialog, QPushButton, QLabel, QMessageBox
from .SuggestSettingsTab import SuggestSettingsTab
from .SlackCredentialsTab import SlackCredentialsTab
from .UserTab import UserTab
from .SettingsTab import SettingsTab
from .HelpTab import HelpTab

SAVED_SETTINGS_DIR = "saved_settings"

class HelpContent:
    def __init__(self):
        self.content = {}
        self.load_content()

    def load_content(self):
        """Load help content from storage"""
        # This would typically load from JSON/YAML files or a database
        self.content = {
            "Getting Started": {
                "title": "Getting Started with RRR",
                "content": """
                <h1>Welcome to Rodent Refreshment Regulator</h1>
                <p>This guide will help you get started with the system...</p>
                """,
                "keywords": ["start", "setup", "introduction"]
            }
            # Add more content entries
        }

    def get_content(self, topic):
        """Retrieve content for a specific topic"""
        return self.content.get(topic, {}).get("content", "Topic not found")

    def search_content(self, query):
        """Search through help content"""
        results = []
        query = query.lower()
        for topic, data in self.content.items():
            if (query in topic.lower() or 
                any(query in keyword for keyword in data["keywords"])):
                results.append(topic)
        return results

class SuggestSettingsSection(QWidget):
    def __init__(self, settings, suggest_settings_callback, push_settings_callback, 
                 save_slack_credentials_callback, run_stop_section, login_system, load_callback=None):
        super().__init__()

        self.settings = settings
        self.run_stop_section = run_stop_section
        self.save_callback = save_slack_credentials_callback
        self.load_callback = load_callback

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create the tab widget
        self.tab_widget = QTabWidget(self)

        # Suggest Settings Tab
        self.suggest_tab = SuggestSettingsTab(suggest_settings_callback, push_settings_callback)
        self.tab_widget.addTab(self.suggest_tab, "Suggest Settings")

        # Dashboard Tab
        self.dashboard_tab = QWidget()
        self.dashboard_layout = QVBoxLayout()
        self.dashboard_tab.setLayout(self.dashboard_layout)
        self.create_dashboard_ui()
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")

        # Settings Tab
        self.settings_tab = SettingsTab(self.settings, self.save_callback)
        self.tab_widget.addTab(self.settings_tab, "Settings")

        # User/Profile Tab
        self.user_tab = UserTab(login_system)
        self.user_tab.login_signal.connect(self.on_login)
        self.user_tab.logout_signal.connect(self.on_logout)
        self.tab_widget.addTab(self.user_tab, "Profile")

        # Help Tab
        self.help_tab = HelpTab()
        self.tab_widget.addTab(self.help_tab, "Help")

        self.layout.addWidget(self.tab_widget)

    def create_dashboard_ui(self):
        """Sets up the dashboard tab UI."""
        self.saved_settings_list = QListWidget()
        self.dashboard_layout.addWidget(QLabel("Saved Settings"))
        self.dashboard_layout.addWidget(self.saved_settings_list)
        # Additional dashboard components as needed

    def on_login(self, user_info):
        """Updates the Profile tab after login."""
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.user_tab), user_info['username'])
        #self.adjust_window_size()

    def on_logout(self):
        """Reverts the Profile tab to guest mode after logout."""
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.user_tab), "Profile")
        self.user_tab.set_guest_view()
       #self.adjust_window_size()

    def save_settings(self):
        try:
            # Ensure the saved_settings directory exists
            if not os.path.exists(SAVED_SETTINGS_DIR):
                os.makedirs(SAVED_SETTINGS_DIR)

            # Get the current values from the input fields
            interval = int(self.run_stop_section.interval_input.text())
            stagger = int(self.run_stop_section.stagger_input.text())

            current_settings = {
                "interval": interval,
                "stagger": stagger,
            }

            name, ok = QInputDialog.getText(self, "Save Settings", "Enter a name for these settings:")
            if ok and name:
                file_name = os.path.join(SAVED_SETTINGS_DIR, f"{name}.json")
                with open(file_name, 'w') as f:
                    json.dump(current_settings, f, indent=4)
                self.load_saved_settings()
        except Exception as e:
            print(f" settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    def load_saved_settings(self):
        self.saved_settings_list.clear()
        if os.path.exists(SAVED_SETTINGS_DIR):
            for file_name in os.listdir(SAVED_SETTINGS_DIR):
                if file_name.endswith(".json"):
                    self.saved_settings_list.addItem(file_name[:-5])

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

                    # Update the settings with loaded values
                    self.settings.update(loaded_settings)

                    # Update UI fields with the loaded settings
                    self.run_stop_section.interval_input.setText(str(self.settings.get('interval', '')))
                    self.run_stop_section.stagger_input.setText(str(self.settings.get('stagger', '')))

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