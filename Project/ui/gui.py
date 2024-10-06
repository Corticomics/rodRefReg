# ui/gui.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton
from PyQt5.QtCore import pyqtSignal, Qt

from settings.config import save_settings
from .terminal_output import TerminalOutput
from .welcome_section import WelcomeSection
from .advanced_settings import AdvancedSettingsSection
from .suggest_settings import SuggestSettingsSection
from .run_stop_section import RunStopSection
from .SlackCredentialsTab import SlackCredentialsTab
from .styles import get_default_styles  # Import the centralized styles
import logging

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)

    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, settings):
        super().__init__()

        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback
        self.settings = settings

        # Connect the system message signal to the print_to_terminal method
        self.system_message_signal.connect(self.print_to_terminal)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        # Apply centralized styles
        self.setStyleSheet(get_default_styles())

        self.main_layout = QVBoxLayout()

        # Welcome Section
        self.welcome_section = WelcomeSection()
        self.welcome_scroll_area = QScrollArea()
        self.welcome_scroll_area.setWidgetResizable(True)
        self.welcome_scroll_area.setWidget(self.welcome_section)
        self.welcome_scroll_area.setMinimumHeight(self.height() // 2)
        self.welcome_scroll_area.setMaximumHeight(self.height() // 2)
        self.main_layout.addWidget(self.welcome_scroll_area)

        # Toggle Welcome Message Button
        self.toggle_welcome_button = QPushButton("Hide Welcome Message")
        self.toggle_welcome_button.clicked.connect(self.toggle_welcome_message)
        self.main_layout.addWidget(self.toggle_welcome_button)

        # Upper Layout for Advanced Settings and Suggest Settings
        self.upper_layout = QHBoxLayout()

        # Left Layout: Terminal Output and Advanced Settings
        self.left_layout = QVBoxLayout()

        self.terminal_output = TerminalOutput()
        self.left_layout.addWidget(self.terminal_output)

        self.advanced_settings = AdvancedSettingsSection(self.settings, self.print_to_terminal)
        self.left_layout.addWidget(self.advanced_settings)

        self.upper_layout.addLayout(self.left_layout)

        # Right Layout: Suggest Settings and Run/Stop Section
        self.right_layout = QVBoxLayout()

        self.suggest_settings_section = SuggestSettingsSection(
            self.settings,
            self.run_program_callback,
            self.stop_program_callback,
            self.save_slack_credentials_callback,
            self.advanced_settings,
            None  # Will be set after RunStopSection is initialized
        )
        self.right_layout.addWidget(self.suggest_settings_section)

        self.run_stop_section = RunStopSection(
            self.run_program_callback,
            self.stop_program_callback,
            self.change_relay_hats_callback,
            self.settings,
            self.advanced_settings
        )
        self.right_layout.addWidget(self.run_stop_section)

        self.upper_layout.addLayout(self.right_layout)

        self.main_layout.addLayout(self.upper_layout)
        self.setLayout(self.main_layout)

    def print_to_terminal(self, message):
        """Safely print messages to the terminal."""
        self.terminal_output.print_to_terminal(message)
        logging.info(message)

    def toggle_welcome_message(self):
        if self.welcome_scroll_area.isVisible():
            self.welcome_scroll_area.setVisible(False)
            self.toggle_welcome_button.setText("Show Welcome Message and Instructions")
        else:
            self.welcome_scroll_area.setVisible(True)
            self.toggle_welcome_button.setText("Hide Welcome Message")
        self.adjust_ui()

    def adjust_ui(self):
        if self.welcome_scroll_area.isVisible():
            self.welcome_scroll_area.setMaximumHeight(self.height() // 2)
            self.welcome_scroll_area.setMinimumHeight(self.height() // 2)
        else:
            self.welcome_scroll_area.setMaximumHeight(0)
            self.welcome_scroll_area.setMinimumHeight(0)

        self.left_layout.setMaximumHeight(self.height() - self.welcome_scroll_area.maximumHeight() - self.toggle_welcome_button.height())
        self.right_layout.setMaximumHeight(self.height() - self.welcome_scroll_area.maximumHeight() - self.toggle_welcome_button.height())

        self.left_layout.setMinimumHeight(self.height() - self.welcome_scroll_area.minimumHeight() - self.toggle_welcome_button.height())
        self.right_layout.setMinimumHeight(self.height() - self.welcome_scroll_area.minimumHeight() - self.toggle_welcome_button.height())

    def save_slack_credentials_callback(self):
        # Update settings with the new Slack credentials
        self.settings['slack_token'] = self.suggest_settings_section.slack_tab.slack_token_input.text()
        self.settings['channel_id'] = self.suggest_settings_section.slack_tab.slack_channel_input.text()

        # Save settings to the settings.json file
        from settings.config import save_settings
        save_settings(self.settings)
        self.print_to_terminal("Slack credentials saved.")

        # Reinitialize the NotificationHandler with the new credentials
        from notifications.notifications import NotificationHandler
        self.parent().notification_handler = NotificationHandler(self.settings['slack_token'], self.settings['channel_id'])
        self.print_to_terminal("NotificationHandler reinitialized with updated Slack credentials.")
    def reinitialize_advanced_settings(self):
        """Reinitialize the advanced settings UI after changing relay hats."""
        self.advanced_settings.update_relay_hats(self.settings['relay_pairs'])