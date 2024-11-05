# app/ui/gui.py

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QSplitter, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal

from .terminal_output import TerminalOutput
from .welcome_section import WelcomeSection
from .advanced_settings import AdvancedSettingsSection
from .suggest_settings import SuggestSettingsSection
from .run_stop_section import RunStopSection
from .SlackCredentialsTab import SlackCredentialsTab
from shared.notifications.notifications import NotificationHandler

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'settings'))
from shared.settings.config import load_settings, save_settings

from .ProjectsSection import ProjectsSection  # Ensure this import is present
from .suggest_settings import SuggestSettingsSection  # Ensure this import is present

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)
    
    def __init__(self, run_program, stop_program, change_relay_hats, settings, db_manager, style='bitlearns'):
        super().__init__()

        self.run_program = run_program
        self.stop_program = stop_program
        self.change_relay_hats = change_relay_hats

        self.settings = settings
        self.selected_relays = self.settings['selected_relays']
        self.num_triggers = self.settings['num_triggers']

        self.db_manager = db_manager
        self.print_to_terminal = self.print_to_terminal

        # Define the callback attributes to avoid AttributeError
        self.suggest_settings_callback = self.suggest_settings_callback  # Defined as a placeholder
        self.push_settings_callback = self.push_settings_callback_wrapper  # Defined as wrapper

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
                QPushButton:hover {
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

        self.welcome_section = WelcomeSection()
        self.welcome_scroll_area = QScrollArea()
        self.welcome_scroll_area.setWidgetResizable(True)
        self.welcome_scroll_area.setWidget(self.welcome_section)
        self.welcome_scroll_area.setMinimumHeight(self.height() // 2)
        self.welcome_scroll_area.setMaximumHeight(self.height() // 2)
        self.main_layout.addWidget(self.welcome_scroll_area)

        self.toggle_welcome_button = QPushButton("Hide Welcome Message")
        self.toggle_welcome_button.clicked.connect(self.toggle_welcome_message)
        self.main_layout.addWidget(self.toggle_welcome_button)

        self.upper_layout = QHBoxLayout()

        self.left_layout = QVBoxLayout()

        # Use QSplitter to make the system messages section resizable
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.terminal_output = TerminalOutput()
        self.splitter.addWidget(self.terminal_output)

        # Create a scroll area for the Advanced Settings section
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

        self.right_layout = QVBoxLayout()

        # Initialize run_stop_section before SuggestSettingsSection
        self.run_stop_section = RunStopSection(
            self.run_program,
            self.stop_program,
            self.change_relay_hats,
            self.settings,
            self.advanced_settings
        )

        # Add the Suggest Settings Section (with the tab widget) directly to the layout
        # Initialize SuggestSettingsSection with the correct callbacks
        self.suggest_settings_section = SuggestSettingsSection(
            self.db_manager,                       # db_manager
            self.settings,                         # settings
            self.suggest_settings_callback,        # suggest_settings_callback
            self.push_settings_callback,           # push_settings_callback
            self.save_slack_credentials_callback,  # save_slack_credentials_callback
            self.advanced_settings,                # advanced_settings
            self.run_stop_section                  # run_stop_section
        )
        self.right_layout.addWidget(self.suggest_settings_section)

        self.right_layout.addWidget(self.run_stop_section)

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
        values = self.suggest_settings_section.suggest_tab.entries
        try:
            # Loop over each relay pair and fetch the corresponding water volume
            relay_pairs = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]
            relay_volumes = {}

            for relay_pair in relay_pairs:
                volume_input = values.get(f"relay_{relay_pair[0]}_{relay_pair[1]}", QLineEdit()).text().strip()
                water_volume = float(volume_input) if volume_input else 0.0  # Default to 0 if empty
                relay_volumes[relay_pair] = water_volume

            # Parse frequency and duration
            frequency_input = values.get("frequency", QLineEdit()).text().strip()
            frequency = int(frequency_input) if frequency_input else 0  # Default to 0 if empty
            duration_input = values.get("duration", QLineEdit()).text().strip()
            duration = int(duration_input) if duration_input else 0  # Default to 0 if empty

            # Start datetime
            start_datetime = values.get("start_datetime", QDateTimeEdit()).dateTime()

            # Calculate total sessions and interval between sessions
            total_sessions = frequency * duration
            interval_seconds = 86400 / frequency if frequency > 0 else 0  # Avoid division by zero

            # Store the suggested settings
            self.suggested_settings = {
                "start_datetime": start_datetime,
                "duration": duration,
                "relay_volumes": relay_volumes,  # Store water volume per relay pair
                "frequency": frequency,
                "interval_seconds": interval_seconds,
                "total_sessions": total_sessions
            }

            # Prepare suggestion text to print
            suggestion_text = f"--- Suggested Settings ---\n"
            suggestion_text += f"Start Date & Time: {start_datetime.toString('yyyy-MM-dd HH:mm:ss')}\n"
            suggestion_text += f"Duration: {duration} day(s)\n"
            suggestion_text += f"Dispensing Frequency: {frequency} times per day\n"
            suggestion_text += f"Total Sessions: {total_sessions}\n"
            suggestion_text += f"Interval Between Sessions: {interval_seconds / 60:.2f} minutes\n"

            for relay_pair, volume in relay_volumes.items():
                suggestion_text += f"Water Volume for Relays {relay_pair[0]} & {relay_pair[1]}: {volume} mL\n"

            self.print_to_terminal(suggestion_text)

        except ValueError as ve:
            self.print_to_terminal(f"Input Error: {ve}")
        except Exception as e:
            self.print_to_terminal(f"An unexpected error occurred: {e}")

    def push_settings_callback_wrapper(self):
        """Wrapper to handle auto-save functionality."""
        try:
            # Push settings as usual
            self.push_settings_callback()

            # Check if auto-save is enabled
            if self.suggest_settings_section.suggest_tab.auto_save_checkbox.isChecked():
                self.save_project()
        except Exception as e:
            self.print_to_terminal(f"Error pushing settings: {e}")

    def save_project(self):
        """Automatically save the project after pushing settings."""
        try:
            # Gather all necessary data to create a project
            selected_mouse_text = self.suggest_settings_section.suggest_tab.mouse_selector.currentText()
            if selected_mouse_text == "Manual Input":
                weight_text = self.suggest_settings_section.suggest_tab.current_weight_input.text().strip()
                if not weight_text:
                    QMessageBox.warning(self, "Input Required", "Please enter the current weight.")
                    return
                body_weight = float(weight_text)
                mouse_id = "Manual"
            else:
                mouse_id = selected_mouse_text.split(' - ')[0]
                mouse = self.db_manager.get_animal_by_id(mouse_id)
                body_weight = mouse.body_weight if mouse else 0.0

            # Gather relay pair assignments and volumes
            relay_volumes = {}
            relay_pairs = self.settings.get('relay_pairs', [])
            for pair in relay_pairs:
                volume = self.suggest_settings_section.suggest_tab.entries.get(f"relay_{pair[0]}_{pair[1]}", QLineEdit()).text().strip()
                relay_volumes[pair] = float(volume) if volume else 0.0

            # Create project name based on timestamp
            import datetime
            project_name = f"AutoProject_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Create project in the database
            if mouse_id != "Manual":
                animal = self.db_manager.get_animal_by_id(mouse_id)
                animals = [animal] if animal else []
            else:
                animals = []  # Handle manual input assignment if applicable

            project = self.db_manager.create_project(project_name, animals, relay_volumes)
            if project:
                self.print_to_terminal(f"Auto-saved project '{project.project_id}' successfully.")
                QMessageBox.information(self, "Auto-Save Success", f"Project '{project.project_id}' saved successfully.")
            else:
                self.print_to_terminal("Failed to auto-save project.")
                QMessageBox.critical(self, "Auto-Save Error", "Failed to auto-save project.")
        except Exception as e:
            self.print_to_terminal(f"Error auto-saving project: {e}")
            QMessageBox.critical(self, "Auto-Save Error", f"Error auto-saving project: {e}")
def main(run_program, stop_program, change_relay_hats):
    app = QApplication(sys.argv)
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, load_settings(), style='bitlearns')
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
