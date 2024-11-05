# app/ui/gui.py

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QSplitter, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from .terminal_output import TerminalOutput
from .welcome_section import WelcomeSection
from .advanced_settings import AdvancedSettingsSection
from .suggest_settings import SuggestSettingsSection
from .run_stop_section import RunStopSection
from .SlackCredentialsTab import SlackCredentialsTab
from .ProjectsSection import ProjectsSection  # New ProjectsSection
from shared.notifications.notifications import NotificationHandler
from shared.models.database import DatabaseManager  # Ensure this import is correct

from shared.settings.config import load_settings, save_settings

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)

    def __init__(self, run_program, stop_program, change_relay_hats, settings, db_manager, style='bitlearns'):
        super().__init__()

        self.run_program = run_program
        self.stop_program = stop_program
        self.change_relay_hats = change_relay_hats

        self.settings = settings
        self.db_manager = db_manager  # Assign db_manager
        self.selected_relays = self.settings.get('selected_relays', [])
        self.num_triggers = self.settings.get('num_triggers', {})

        # Connect the system message signal to the print_to_terminal method
        self.system_message_signal.connect(self.print_to_terminal)

        self.init_ui(style)

    def init_ui(self, style):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        if style == 'bitlearns':
            self.setStyleSheet("""
                QWidget {
                    background-color: #f8f9fa;
                    font-size: 14px;
                }
                QGroupBox {
                    background-color: #ffffff;
                    border: 1px solid #ced4da;
                    border-radius: 5px;
                    padding: 15px;
                }
                QPushButton {
                    background-color: #007bff;
                    border: 1px solid #007bff;
                    border-radius: 5px;
                    color: #ffffff;
                    padding: 10px;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
                QPushButton:hover:!disabled {
                    background-color: #0056b3;
                }
                QLabel {
                    color: #343a40;
                    background-color: #ffffff;
                }
                QLineEdit, QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #ced4da;
                    padding: 5px;
                }
            """)

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

        # Upper Layout containing Left and Right Sections
        self.upper_layout = QHBoxLayout()

        # Left Layout: System Messages and Advanced Settings
        self.left_layout = QVBoxLayout()

        # Use QSplitter to make the system messages section resizable
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Terminal Output
        self.terminal_output = TerminalOutput()
        self.splitter.addWidget(self.terminal_output)

        # Advanced Settings Section
        self.advanced_settings_scroll_area = QScrollArea()
        self.advanced_settings_scroll_area.setWidgetResizable(True)

        self.advanced_settings = AdvancedSettingsSection(self.settings, self.print_to_terminal)
        self.advanced_settings_scroll_area.setWidget(self.advanced_settings)
        self.splitter.addWidget(self.advanced_settings_scroll_area)

        self.left_layout.addWidget(self.splitter)

        self.left_content = QWidget()
        self.left_content.setLayout(self.left_layout)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setWidget(self.left_content)
        self.upper_layout.addWidget(self.left_scroll)

        # Right Layout: Suggest Settings, Run/Stop, and Projects
        self.right_layout = QVBoxLayout()

        # Initialize RunStopSection before SuggestSettingsSection
        self.run_stop_section = RunStopSection(
            self.run_program, 
            self.stop_program, 
            self.change_relay_hats, 
            self.settings, 
            self.advanced_settings
        )

        # Add the Suggest Settings Section (with the tab widget) directly to the layout
        self.suggest_settings_section = SuggestSettingsSection(
            self.settings, 
            self.suggest_settings_callback, 
            self.push_settings_callback,
            self.save_slack_credentials_callback,
            self.advanced_settings,
            self.run_stop_section,
            self.db_manager,  # Pass db_manager here
            load_callback=self.load_project_into_ui  # Callback to handle project loading
        )

        self.right_layout.addWidget(self.suggest_settings_section)
        self.right_layout.addWidget(self.run_stop_section)

        # Add Projects Section
        self.projects_section = ProjectsSection(
            self.db_manager,
            self.print_to_terminal,
            self.run_program,
            self.stop_program,
            self.settings
        )
        self.right_layout.addWidget(self.projects_section)

        self.right_content = QWidget()
        self.right_content.setLayout(self.right_layout)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setWidget(self.right_content)
        self.upper_layout.addWidget(self.right_scroll)

        self.main_layout.addLayout(self.upper_layout)
        self.setLayout(self.main_layout)

    def print_to_terminal(self, message):
        """Safely print messages to the terminal."""
        self.terminal_output.print_to_terminal(message)

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

        self.left_scroll.setMaximumHeight(self.height() - self.welcome_scroll_area.maximumHeight() - self.toggle_welcome_button.height())
        self.right_scroll.setMaximumHeight(self.height() - self.welcome_scroll_area.maximumHeight() - self.toggle_welcome_button.height())

        self.left_scroll.setMinimumHeight(self.height() - self.welcome_scroll_area.minimumHeight() - self.toggle_welcome_button.height())
        self.right_scroll.setMinimumHeight(self.height() - self.welcome_scroll_area.minimumHeight() - self.toggle_welcome_button.height())

    def suggest_settings_callback(self):
        """Callback for suggesting settings based on user input."""
        try:
            self.suggest_settings_section.suggest_tab.generate_suggestions()
        except Exception as e:
            self.print_to_terminal(f"Error generating suggestions: {e}")

    def push_settings_callback(self):
        """Callback for pushing the suggested settings to the control panel."""
        try:
            self.suggest_settings_section.suggest_tab.push_settings()
        except Exception as e:
            self.print_to_terminal(f"Error pushing settings: {e}")

    def push_settings_callback_wrapper(self):
        """Wrapper to handle auto-save functionality."""
        try:
            # Push settings as usual
            self.push_settings_callback()

            # Check if auto-save is enabled
            if self.suggest_settings_section.auto_save_checkbox.isChecked():
                self.suggest_settings_section.save_project()
        except Exception as e:
            self.print_to_terminal(f"Error pushing settings: {e}")

    def save_slack_credentials_callback(self):
        """Callback for saving Slack credentials."""
        try:
            self.suggest_settings_section.slack_tab.save_slack_credentials()
        except Exception as e:
            self.print_to_terminal(f"Error saving Slack credentials: {e}")

    def load_project_into_ui(self, project_id):
        """Callback to load a selected project into the ProjectBuilder."""
        project = self.db_manager.get_project_by_id(project_id)
        if project:
            self.run_stop_section.run_program(
                interval=self.settings.get('interval', 60),
                stagger=self.settings.get('stagger', 5),
                window_start=project.start_time,
                window_end=project.end_time
            )
            self.print_to_terminal(f"Project '{project.project_id}' loaded successfully.")
        else:
            self.print_to_terminal(f"Project ID: {project_id} not found.")