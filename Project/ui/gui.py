# ui/gui.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QPlainTextEdit, QLabel, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
import traceback
from .welcome_section import WelcomeSection
from .run_stop_section import RunStopSection
from .suggest_settings import SuggestSettingsSection
from .projects_section import ProjectsSection
from .UserTab import UserTab
from notifications.notifications import NotificationHandler
from settings.config import save_settings
from utils.volume_calculator import VolumeCalculator

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)

    def __init__(self, run_program, stop_program, change_relay_hats,
                 settings, database_handler, login_system, style='bitlearns'):
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

        # Initialize VolumeCalculator with database handler
        self.volume_calculator = VolumeCalculator(database_handler)

        # Connect pump configuration update signal
        self.suggest_settings_section.settings_tab.pump_config_saved.connect(self.handle_pump_config_update)

    def init_ui(self, style):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        # Initialize main layout first
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Apply styles
        if style == 'bitlearns':
            self.setStyleSheet("""
                QWidget {
                    background-color: #f8f9fa;
                    font-size: 14px;
                }
                QGroupBox {
                    border: none;
                    padding: 0px;
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
                }
                QLineEdit, QTextEdit {
                    border: 1px solid #ced4da;
                    padding: 5px;
                }
            """)

        # Welcome section
        self.welcome_section = WelcomeSection()
        self.welcome_scroll_area = QScrollArea()
        self.welcome_scroll_area.setWidgetResizable(True)
        self.welcome_scroll_area.setWidget(self.welcome_section)
        self.main_layout.addWidget(self.welcome_scroll_area)

        # Toggle welcome button
        self.toggle_welcome_button = QPushButton("Hide Welcome Message")
        self.toggle_welcome_button.clicked.connect(self.toggle_welcome_message)
        self.main_layout.addWidget(self.toggle_welcome_button)

        # Main content area (upper layout)
        self.upper_layout = QHBoxLayout()
        self.upper_layout.setContentsMargins(0, 0, 0, 0)
        self.upper_layout.setSpacing(10)

        # Left side setup
        left_widget = QWidget()
        self.left_layout = QVBoxLayout(left_widget)
        
        # Terminal output
        self.terminal_output = QPlainTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setPlainText("System Messages")
        self.terminal_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.terminal_output.setMinimumHeight(200)
        
        # Projects section
        self.projects_section = ProjectsSection(self.settings, self.print_to_terminal, self.database_handler, self.login_system)
        self.projects_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Add widgets to left layout with stretch
        self.left_layout.addWidget(self.terminal_output, 1)
        self.left_layout.addWidget(self.projects_section, 3)
        
        # Create left scroll area
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidget(left_widget)
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Right side setup
        right_widget = QWidget()
        self.right_layout = QVBoxLayout(right_widget)
        
        # Create sections
        self.run_stop_section = RunStopSection(
            self.run_program, 
            self.stop_program, 
            self.change_relay_hats, 
            self.settings,
            advanced_settings=None
        )
        self.suggest_settings_section = SuggestSettingsSection(
            self.settings,
            self.suggest_settings_callback,
            self.push_settings_callback,
            self.save_slack_credentials_callback,
            advanced_settings=None,
            run_stop_section=self.run_stop_section,
            login_system=self.login_system,
            volume_calculator=self.volume_calculator
        )
        
        # Add widgets to right layout with stretch
        self.right_layout.addWidget(self.suggest_settings_section, 2)
        self.right_layout.addWidget(self.run_stop_section, 1)
        
        # Create right scroll area
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidget(right_widget)
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add scroll areas to upper layout with proportion
        self.upper_layout.addWidget(self.left_scroll, 3)
        self.upper_layout.addWidget(self.right_scroll, 2)

        # Add upper layout to main layout
        self.main_layout.addLayout(self.upper_layout)

        # Connect user tab related signals
        self.user_tab = self.suggest_settings_section.user_tab
        self.user_tab.login_signal.connect(self.on_login)
        self.user_tab.logout_signal.connect(self.on_logout)
        self.user_tab.size_changed_signal.connect(self.adjust_window_size)

        # Add mode toggle button
        self.mode_toggle_button = QPushButton("Switch to Super Mode")
        self.mode_toggle_button.clicked.connect(self.toggle_mode)
        self.main_layout.addWidget(self.mode_toggle_button)

        # Connect the mode_changed signal from SchedulesTab to RunStopSection
        self.projects_section.schedules_tab.mode_changed.connect(self.run_stop_section._on_mode_changed)

        # Connect the schedules tab with run_stop_section's schedule drop area
        self.projects_section.schedules_tab.schedule_list.itemDoubleClicked.connect(
            lambda item: self.run_stop_section.schedule_drop_area.handle_schedule_drop(
                item.data(Qt.UserRole)
            )
        )

        # Load initial data
        self.load_animals_tab()

        # Maximize window on startup
        self.showMaximized()
    
    def toggle_mode(self):
        try:
            self.login_system.switch_mode()
            new_role = self.login_system.get_current_trainer()['role']
            self.mode_toggle_button.setText("Switch to Normal Mode" if new_role == 'super' else "Switch to Super Mode")
            self.print_to_terminal(f"Switched to {new_role.capitalize()} Mode.")
            # Refresh animals and schedules tabs
            self.projects_section.schedules_tab.load_animals()
            self.projects_section.animals_tab.load_animals()
        except Exception as e:
            self.print_to_terminal(f"Error toggling mode: {e}")
            QMessageBox.critical(self, "Mode Toggle Error", f"An error occurred while toggling mode: {e}")

    def print_to_terminal(self, message):
        self.terminal_output.appendPlainText(message)

    def toggle_welcome_message(self):
        visible = self.welcome_scroll_area.isVisible()
        self.welcome_scroll_area.setVisible(not visible)
        self.toggle_welcome_button.setText("Show Welcome Message" if visible else "Hide Welcome Message")

    
    def adjust_window_size(self):
        """Adjust the main window size to fit its content."""
        try:
            # Resize the main window to fit its content
            self.adjustSize()
        except Exception as e:
            self.print_to_terminal(f"Error adjusting window size: {e}")
            QMessageBox.critical(self, "Window Size Error",
                                 f"An unexpected error occurred while adjusting window size: {e}")
    @pyqtSlot(dict)
    def on_login(self, user):
        try:
            if not isinstance(user, dict) or 'username' not in user or 'trainer_id' not in user:
                raise ValueError(f"Invalid user information received during login: {user}")

            self.current_user = user
            self.print_to_terminal(f"Logged in as: {user['username']}")

            trainer_id = int(user['trainer_id'])  # Ensure trainer_id is an integer
            self.projects_section.animals_tab.trainer_id = trainer_id
            self.load_animals_tab(trainer_id=trainer_id)
        except ValueError as ve:
            self.print_to_terminal(f"Data error during login: {ve}")
            QMessageBox.critical(self, "Login Data Error", f"Error accessing user data:\n{ve}")

        except Exception as e:
            self.print_to_terminal(f"Unexpected error during login: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Login Error", f"An unexpected error occurred during login:\n{e}")

    def load_animals_tab(self, trainer_id=None):
        """Load the AnimalsTab for the specific trainer. Display all animals in guest mode."""
        try:
            if not hasattr(self.projects_section, 'animals_tab') or self.projects_section.animals_tab is None:
                raise AttributeError("animals_tab is not initialized in projects_section.")

            if trainer_id:
                self.projects_section.animals_tab.trainer_id = trainer_id
                self.print_to_terminal(f"Displaying animals for trainer ID {trainer_id}")
            else:
                self.projects_section.animals_tab.trainer_id = None
                self.print_to_terminal("Displaying all animals (guest mode)")

            # Add logging before loading animals
            print(f"About to load animals for trainer_id: {trainer_id} (type: {type(trainer_id)})")

            self.projects_section.animals_tab.load_animals()

        except Exception as e:
            self.print_to_terminal(f"Error loading animals tab: {e}")
            QMessageBox.critical(self, "Load Animals Error", f"An error occurred while loading animals:\n{e}")
            print(f"Exception in load_animals_tab: {e}")

    def on_logout(self):
        """Callback for handling user logout, reverting to guest mode, with error handling."""
        try:
            self.current_user = None
            self.projects_section.login_system.logout()  # Ensure login_system is updated
            self.print_to_terminal("Logged out. Displaying all animals (guest mode).")
            self.load_animals_tab()

        except Exception as e:
            self.print_to_terminal(f"Unexpected error during logout: {e}")
            QMessageBox.critical(self, "Logout Error", f"An unexpected error occurred during logout: {e}")

    def suggest_settings_callback(self):
        """Callback for suggesting settings based on user input."""
        values = self.suggest_settings_section.suggest_tab.entries
        try:
            # Parse relay pairs and volumes
            relay_pairs = [(1, 2), (3, 4), (5, 6), (7, 8)]
            relay_volumes = {}
            suggestion_text = "Suggested Settings:\n"
            
            for pair in relay_pairs:
                volume_key = f"relay_{pair[0]}_{pair[1]}"
                if volume_key in values:
                    volume_ml = float(values[volume_key].text())
                    triggers = self.volume_calculator.calculate_triggers(volume_ml)
                    relay_volumes[pair] = volume_ml
                    suggestion_text += f"Relay pair {pair}: {volume_ml}mL ({triggers} triggers)\n"
            
            # Store suggested settings
            self.suggested_settings = {
                "start_datetime": values["start_datetime"].dateTime(),
                "duration": int(values["duration"].text()),
                "relay_volumes": relay_volumes
            }
            
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

            # Calculate triggers based on volumes
            volume_calculator = VolumeCalculator(self.settings)
            calculated_triggers = {
                pair: volume_calculator.calculate_triggers(vol) 
                for pair, vol in settings["relay_volumes"].items()
            }
            
            if hasattr(self, 'advanced_settings') and self.advanced_settings:
                self.advanced_settings.update_triggers(calculated_triggers)
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
        self.print_to_terminal("Slack credentials saved and NotificationHandler updated.")

    def handle_pump_config_update(self, new_config):
        """Handle pump configuration updates"""
        try:
            # Update VolumeCalculator
            self.volume_calculator.load_pump_config()
            
            # Update PumpController
            self.pump_controller.load_pump_config()
            
            # Update DeliveryQueueController's VolumeCalculator
            self.delivery_queue_controller.volume_calculator.load_pump_config()
            
            # Update ScheduleController's VolumeCalculator
            self.schedule_controller.volume_calculator.load_pump_config()
            
            self.print_to_terminal(
                f"Pump configuration updated - Volume: {new_config['pump_volume_ul']}µL, "
                f"Calibration: {new_config['calibration_factor']}"
            )
            
        except Exception as e:
            self.print_to_terminal(f"Error updating pump configuration: {e}")