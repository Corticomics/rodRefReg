# ui/gui.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QPlainTextEdit, QLabel, QMenu, QAction, QInputDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from .welcome_section import WelcomeSection
from .run_stop_section import RunStopSection
from .suggest_settings import SuggestSettingsSection
from .projects_section import ProjectsSection
from .UserIcon import UserIcon
from notifications.notifications import NotificationHandler
from settings.config import save_settings

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)

    def __init__(self, run_program, stop_program, change_relay_hats, settings, database_handler, login_system, style='bitlearns'):
        super().__init__()

        self.run_program = run_program
        self.stop_program = stop_program
        self.change_relay_hats = change_relay_hats
        self.settings = settings
        self.database_handler = database_handler
        self.login_system = login_system

        # Default to guest mode
        self.current_user = None

        # Connect system message signal
        self.system_message_signal.connect(self.print_to_terminal)

        # Initialize the UI with the selected style
        self.init_ui(style)

    def init_ui(self, style):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        # Apply stylesheet
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

        # Main layout setup
        self.main_layout = QVBoxLayout(self)

        # User icon for login and profile actions
        self.user_icon = UserIcon(self, self.database_handler, self.login_system)
        self.user_icon.login_signal.connect(self.on_login)
        self.user_icon.logout_signal.connect(self.on_logout)
        self.main_layout.addWidget(self.user_icon, alignment=Qt.AlignRight)

        # Welcome section
        self.welcome_section = WelcomeSection()
        self.welcome_scroll_area = QScrollArea()
        self.welcome_scroll_area.setWidgetResizable(True)
        self.welcome_scroll_area.setWidget(self.welcome_section)
        self.main_layout.addWidget(self.welcome_scroll_area)

        # Toggle welcome message
        self.toggle_welcome_button = QPushButton("Hide Welcome Message")
        self.toggle_welcome_button.clicked.connect(self.toggle_welcome_message)
        self.main_layout.addWidget(self.toggle_welcome_button)

        # Main layout
        self.upper_layout = QHBoxLayout()

        # Left layout (messages and projects)
        self.left_layout = QVBoxLayout()
        self.terminal_output = QPlainTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setPlainText("System Messages")
        self.left_layout.addWidget(self.terminal_output)
        self.projects_section = ProjectsSection(self.settings, self.print_to_terminal, self.database_handler)
        self.left_layout.addWidget(self.projects_section)
        self.left_content = QWidget()
        self.left_content.setLayout(self.left_layout)
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setWidget(self.left_content)
        self.upper_layout.addWidget(self.left_scroll)

        # Right layout (suggested settings and run/stop)
        self.right_layout = QVBoxLayout()
        self.run_stop_section = RunStopSection(self.run_program, self.stop_program, self.change_relay_hats, self.settings)
        # Inside the __init__ method of RodentRefreshmentGUI, after setting up suggest_settings_section
        self.suggest_settings_section = SuggestSettingsSection(
            self.settings,
            self.suggest_settings_callback,
            self.push_settings_callback,
            self.save_slack_credentials_callback,
            advanced_settings=None,
            run_stop_section=self.run_stop_section,
            login_system=self.login_system
        )

        # Add the suggest_settings_section to the right layout
        self.right_layout.addWidget(self.suggest_settings_section)

        # Initial adjustment on startup
        self.adjust_window_size()

        # Connect tab change to adjust window size
        self.suggest_settings_section.tab_widget.currentChanged.connect(self.adjust_window_size)
        
        self.right_layout.addWidget(self.run_stop_section)
        self.right_content = QWidget()
        self.right_content.setLayout(self.right_layout)
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setWidget(self.right_content)
        self.upper_layout.addWidget(self.right_scroll)
        self.main_layout.addLayout(self.upper_layout)

        # Load initial data in guest mode
        self.load_animals_tab()

    def print_to_terminal(self, message):
        """Display messages in the system message section."""
        self.terminal_output.appendPlainText(message)

    def toggle_welcome_message(self):
        visible = self.welcome_scroll_area.isVisible()
        self.welcome_scroll_area.setVisible(not visible)
        self.toggle_welcome_button.setText("Show Welcome Message" if visible else "Hide Welcome Message")

    def adjust_window_size(self):
        """Adjusts the window size based on the current tab content, with error handling."""
        try:
            current_tab_index = self.suggest_settings_section.tab_widget.currentIndex()
            current_tab = self.suggest_settings_section.tab_widget.widget(current_tab_index)
            
            # Adjust the window height based on the current tab's height
            if current_tab:
                self.resize(self.width(), current_tab.sizeHint().height() + 100)  # Added padding
        except Exception as e:
            self.print_to_terminal(f"Error adjusting window size: {e}")
            QMessageBox.critical(self, "Window Size Error", f"An unexpected error occurred while adjusting window size: {e}")

    def on_login(self, user):
        """Callback for handling user login with error handling."""
        try:
            self.current_user = user
            self.print_to_terminal(f"Logged in as: {user['trainer_name']}")
            self.load_animals_tab(trainer_id=user['trainer_id'])
        except KeyError as e:
            self.print_to_terminal(f"Data error: missing key {e} in user data.")
            QMessageBox.critical(self, "Login Data Error", f"Error accessing user data: missing key {e}")
        except Exception as e:
            self.print_to_terminal(f"Unexpected error during login: {e}")
            QMessageBox.critical(self, "Login Error", f"An unexpected error occurred during login: {e}")

    def on_logout(self):
        """Callback for handling user logout, reverting to guest mode, with error handling."""
        try:
            self.current_user = None
            self.print_to_terminal("Logged out. Displaying all animals (guest mode).")
            self.load_animals_tab()
        except Exception as e:
            self.print_to_terminal(f"Unexpected error during logout: {e}")
            QMessageBox.critical(self, "Logout Error", f"An unexpected error occurred during logout: {e}")




    def load_animals_tab(self, trainer_id=None):
        """Load the AnimalsTab for the specific trainer. Display all animals in guest mode."""
        if trainer_id:
            self.projects_section.animals_tab.trainer_id = trainer_id
            self.print_to_terminal(f"Displaying animals for trainer ID {trainer_id}")
        else:
            self.projects_section.animals_tab.trainer_id = None
            self.print_to_terminal("Displaying all animals (guest mode)")
        self.projects_section.animals_tab.load_animals()

    def suggest_settings_callback(self):
        """Callback for suggesting settings based on user input."""
        values = self.suggest_settings_section.suggest_tab.entries
        try:
            # Parse relay pairs and volumes, frequency, duration
            relay_pairs = [(1, 2), (3, 4), (5, 6), (7, 8)]
            relay_volumes = {pair: float(values[f"relay_{pair[0]}_{pair[1]}"].text()) for pair in relay_pairs}
            frequency = int(values["frequency"].text())
            duration = int(values["duration"].text())
            start_datetime = values["start_datetime"].dateTime()

            # Store the suggested settings
            self.suggested_settings = {
                "start_datetime": start_datetime,
                "duration": duration,
                "relay_volumes": relay_volumes,
                "frequency": frequency
            }

            # Print suggestions to terminal
            suggestion_text = f"Suggested Settings:\nStart: {start_datetime.toString()}\nFrequency: {frequency}\nDuration: {duration}\n"
            for pair, volume in relay_volumes.items():
                suggestion_text += f"Volume for Relays {pair}: {volume} mL\n"
            self.print_to_terminal(suggestion_text)

        except Exception as e:
            self.print_to_terminal(f"Error generating suggestions: {e}")

    def push_settings_callback(self):
        """Apply the suggested settings to the Run/Stop and Advanced sections."""
        if not hasattr(self, 'suggested_settings'):
            self.print_to_terminal("No suggested settings available.")
            return

        try:
            settings = self.suggested_settings
            self.run_stop_section.start_time_input.setDateTime(settings["start_datetime"])
            end_datetime = settings["start_datetime"].addDays(settings["duration"])
            self.run_stop_section.end_time_input.setDateTime(end_datetime)
            self.run_stop_section.interval_input.setText("86400")  # Assume daily for example
            self.run_stop_section.stagger_input.setText("5")

            self.advanced_settings.update_triggers({pair: int(vol * 2) for pair, vol in settings["relay_volumes"].items()})
            self.print_to_terminal("Settings applied successfully.")

        except Exception as e:
            self.print_to_terminal(f"Error applying settings: {e}")

    def save_slack_credentials_callback(self):
        """Save Slack credentials and reinitialize NotificationHandler."""
        self.settings['slack_token'] = self.suggest_settings_section.slack_tab.slack_token_input.text()
        self.settings['channel_id'] = self.suggest_settings_section.slack_tab.slack_channel_input.text()
        save_settings(self.settings)

        # Update NotificationHandler
        global notification_handler
        notification_handler = NotificationHandler(self.settings['slack_token'], self.settings['channel_id'])
        self.print_to_terminal("Slack credentials saved and NotificationHandler updated.")# ui/gui.py

