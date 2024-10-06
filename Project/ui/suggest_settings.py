# ui/SuggestSettingsSection.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QListWidget, QInputDialog,
    QPushButton, QLabel, QMessageBox
)
import logging
from .SuggestSettingsTab import SuggestSettingsTab
from .SlackCredentialsTab import SlackCredentialsTab
from .PumpSettingsTab import PumpSettingsTab
from .AddPumpDialog import AddPumpDialog
from settings.config import load_pumps, save_pumps

class SuggestSettingsSection(QWidget):
    def __init__(
        self, settings, suggest_settings_callback, push_settings_callback,
        save_slack_credentials_callback, advanced_settings, run_stop_section,
        load_callback=None
    ):
        super().__init__()

        self.settings = settings
        self.advanced_settings = advanced_settings
        self.run_stop_section = run_stop_section
        self.save_callback = save_slack_credentials_callback
        self.load_callback = load_callback

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create the tab widget
        self.tab_widget = QTabWidget(self)

        # Load pumps with error handling
        try:
            self.pumps = load_pumps()
            if not self.pumps:
                raise ValueError("No pumps available.")
        except Exception as e:
            logging.error(f"Error loading pumps: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load pumps: {e}")
            self.pumps = [{'name': 'Default 20μL Pump', 'volume_per_trigger': 20.0}]

        self.selected_pump = self.pumps[0]  # Default pump

        # Create the Pump Settings Tab
        self.pump_tab = PumpSettingsTab(
            self.pumps, self.on_pump_selected, self.add_custom_pump
        )
        self.tab_widget.addTab(self.pump_tab, "Pump Settings")

        # Create other tabs...
        self.suggest_tab = SuggestSettingsTab(suggest_settings_callback, push_settings_callback)
        self.slack_tab = SlackCredentialsTab(self.settings, self.save_callback)
        self.tab_widget.addTab(self.suggest_tab, "Suggest Settings")
        self.tab_widget.addTab(self.slack_tab, "Slack Bot")

        self.layout.addWidget(self.tab_widget)

    def on_pump_selected(self, pump):
        try:
            self.selected_pump = pump
            logging.info(f"Pump selected: {pump['name']}")
        except Exception as e:
            logging.error(f"Error in pump selection callback: {e}")
            QMessageBox.critical(self, "Error", f"Failed to select pump: {e}")

    def add_custom_pump(self):
        try:
            dialog = AddPumpDialog(self.pumps)
            if dialog.exec_():
                new_pump = dialog.get_pump()
                if new_pump:
                    self.pumps.append(new_pump)
                    save_pumps(self.pumps)
                    self.pump_tab.update_pump_list()
                    QMessageBox.information(self, "Success", "Custom pump added successfully.")
                else:
                    raise ValueError("No pump data returned from dialog.")
        except Exception as e:
            logging.error(f"Error adding custom pump: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add custom pump: {e}")
