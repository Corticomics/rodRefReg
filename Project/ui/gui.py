# ui/gui.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QPlainTextEdit, QLabel, QMessageBox, QSizePolicy, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
import traceback
from .welcome_section import WelcomeSection
from .run_stop_section import RunStopSection
from .projects_section import ProjectsSection
from .UserTab import UserTab
from notifications.notifications import NotificationHandler
from settings.config import save_settings
from utils.volume_calculator import VolumeCalculator
from .login_gate_widget import LoginGateWidget
from .SettingsTab import SettingsTab
from .HelpTab import HelpTab

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)

    def __init__(self, run_callback, stop_callback, change_relay_callback, 
                 system_controller, database_handler, login_system, 
                 relay_handler, notification_handler):
        super().__init__()
        self.system_controller = system_controller
        
        # Connect to system settings updates
        self.system_controller.settings_updated.connect(self._handle_settings_update)
        
        # Initialize with current settings
        self.settings = system_controller.settings
        
        # Store callbacks with correct signatures
        self.run_program = lambda schedule, mode, window_start, window_end: run_callback(schedule, mode, window_start, window_end)
        self.stop_program = stop_callback
        self.change_relay_hats = change_relay_callback
        self.database_handler = database_handler
        self.login_system = login_system
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler

        # Default to guest mode
        self.current_user = None

        # Connect system message signal
        self.system_message_signal.connect(self.print_to_terminal)

        # Initialize the UI with the selected style
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        # First, set the base styles
        base_style = """
            QWidget {
                background-color: #f8f9fa;
                color: #2c3e50;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """
        
        # Then add the modern component styles
        modern_style = """
            /* Modern Table Styling */
            QTableWidget {
                background-color: white;
                border: 1px solid #e0e4e8;
                border-radius: 8px;
                padding: 4px;
                gridline-color: transparent;
                selection-background-color: #e8f0fe;
            }
            
            QTableWidget QHeaderView::section {
                background-color: #f8f9fa;
                color: #5f6368;
                padding: 16px;
                border: none;
                border-bottom: 2px solid #e0e4e8;
                font-weight: bold;
                font-size: 13px;
                text-align: left;
            }
            
            QTableWidget::item {
                padding: 16px;
                border-bottom: 1px solid #f0f0f0;
                color: #202124;
                font-size: 13px;
            }
            
            QTableWidget::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
            
            /* Scrollbar Styling */
            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                margin: 0;
            }
            
            QScrollBar::handle:vertical {
                background-color: #dadce0;
                min-height: 30px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #1a73e8;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            /* Button Styling */
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 13px;
                min-width: 100px;
            }
            
            QPushButton:hover {
                background-color: #1557b0;
            }
            
            QPushButton:pressed {
                background-color: #104d92;
            }
            
            /* Input Styling */
            QLineEdit {
                border: 1px solid #dadce0;
                border-radius: 4px;
                padding: 8px 12px;
                background: white;
                font-size: 13px;
                color: #202124;
            }
            
            QLineEdit:focus {
                border-color: #1a73e8;
                background: white;
            }
            
            /* Tab Styling */
            QTabWidget::pane {
                border: 1px solid #e0e4e8;
                border-radius: 8px;
                background-color: white;
                top: -1px;
            }
            
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #5f6368;
                padding: 8px 16px;
                margin-right: 4px;
                border: 1px solid #e0e4e8;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 13px;
                min-width: 100px;
            }
            
            QTabBar::tab:selected {
                background-color: white;
                color: #1a73e8;
                border-bottom: 2px solid #1a73e8;
            }
            
            /* ComboBox Styling */
            QComboBox {
                background-color: white;
                border: 1px solid #dadce0;
                border-radius: 4px;
                padding: 8px 12px;
                min-width: 150px;
                font-size: 13px;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: url(:/icons/down-arrow.png);
            }
        """
        
        # Apply the styles in order
        self.setStyleSheet(base_style + modern_style)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Welcome section at top
        self.welcome_section = WelcomeSection()
        self.welcome_scroll_area = QScrollArea()
        self.welcome_scroll_area.setWidgetResizable(True)
        self.welcome_scroll_area.setWidget(self.welcome_section)
        
        # Toggle welcome button
        self.toggle_welcome_button = QPushButton("Hide Welcome Message")
        self.toggle_welcome_button.clicked.connect(self.toggle_welcome_message)
        
        main_layout.addWidget(self.welcome_scroll_area)
        main_layout.addWidget(self.toggle_welcome_button)

        # Content area
        content_layout = QHBoxLayout()
        
        # Left side
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Terminal output
        self.terminal_output = QPlainTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setPlainText("System Messages")
        self.terminal_output.setMinimumHeight(150)
        left_layout.addWidget(self.terminal_output)
        
        # Projects section with login gate
        self.projects_section = ProjectsSection(
            self.settings,
            self.print_to_terminal,
            self.database_handler,
            self.login_system
        )
        self.login_gate = LoginGateWidget(self.projects_section, self.login_system)
        left_layout.addWidget(self.login_gate)
        
        # Right side
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Create Run/Stop section first
        self.run_stop_section = RunStopSection(
            self.run_program,
            self.stop_program,
            self.change_relay_hats,
            self.system_controller,
            database_handler=self.database_handler,
            relay_handler=self.relay_handler,
            notification_handler=self.notification_handler
        )
        
        # Tab widget
        self.main_tab_widget = QTabWidget()
        
        # Create tabs
        self.settings_tab = SettingsTab(
            system_controller=self.system_controller,
            suggest_callback=self.suggest_settings_callback,
            push_callback=self.push_settings_callback,
            save_slack_callback=self.save_slack_credentials_callback,
            run_stop_section=self.run_stop_section,
            login_system=self.login_system
        )
        
        # Profile Tab
        self.user_tab = UserTab(self.login_system)
        self.user_tab.login_signal.connect(self.on_login)
        self.user_tab.logout_signal.connect(self.on_logout)
        
        # Help Tab
        self.help_tab = HelpTab()
        
        # Add tabs in desired order
        self.main_tab_widget.addTab(self.user_tab, "Profile")  # Profile tab first
        self.main_tab_widget.addTab(self.settings_tab, "Settings")
        self.main_tab_widget.addTab(self.help_tab, "Help")
        
        # Set the initial tab to Profile
        self.main_tab_widget.setCurrentWidget(self.user_tab)
        
        right_layout.addWidget(self.main_tab_widget)
        right_layout.addWidget(self.run_stop_section)
        
        # Add to content layout
        content_layout.addWidget(left_widget, 3)
        content_layout.addWidget(right_widget, 2)
        
        # Add content layout to main layout
        main_layout.addLayout(content_layout)
        
        # Mode toggle button at bottom
        self.mode_toggle_button = QPushButton("Switch to Super Mode")
        self.mode_toggle_button.clicked.connect(self.toggle_mode)
        main_layout.addWidget(self.mode_toggle_button)
        
        # Connect signals
        self.projects_section.schedules_tab.mode_changed.connect(
            self.run_stop_section._on_mode_changed
        )
        
        # Initialize
        self.load_animals_tab()
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
        """Print message to terminal output"""
        if hasattr(self, 'terminal_output'):
            self.terminal_output.appendPlainText(str(message))

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

            trainer_id = int(user['trainer_id'])
            self.projects_section.animals_tab.trainer_id = trainer_id
            self.load_animals_tab(trainer_id=trainer_id)
            
            # Login gate will automatically update due to login_system signal
            
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
            self.projects_section.login_system.logout()
            self.print_to_terminal("Logged out. Displaying all animals (guest mode).")
            self.load_animals_tab()
            
            # Login gate will automatically update due to login_system signal
            
        except Exception as e:
            self.print_to_terminal(f"Unexpected error during logout: {e}")
            QMessageBox.critical(self, "Logout Error", f"An unexpected error occurred during logout: {e}")

    def suggest_settings_callback(self):
        """Callback for suggesting settings based on user input."""
        values = self.settings_section.entries
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
        """Apply the suggested settings to the Run/Stop section."""
        if not hasattr(self, 'suggested_settings'):
            self.print_to_terminal("No suggested settings available.")
            return

        try:
            settings = self.suggested_settings
            self.run_stop_section.start_time_input.setDateTime(settings["start_datetime"])
            end_datetime = settings["start_datetime"].addDays(settings["duration"])
            self.run_stop_section.end_time_input.setDateTime(end_datetime)
            self.print_to_terminal("Settings applied successfully.")

        except Exception as e:
            self.print_to_terminal(f"Error applying settings: {e}")

    def save_slack_credentials_callback(self):
        """Save Slack credentials and reinitialize NotificationHandler."""
        self.settings['slack_token'] = self.settings_section.slack_token_input.text()
        self.settings['channel_id'] = self.settings_section.slack_channel_input.text()
        save_settings(self.settings)

        # Update NotificationHandler
        global notification_handler
        notification_handler = NotificationHandler(self.settings['slack_token'], self.settings['channel_id'])
        self.print_to_terminal("Slack credentials saved and NotificationHandler updated.")

    def change_relay_hats(self):
        # Execute the callback to change the relay hats
        self.change_relay_hats_callback()
        
        # Reset the UI to ensure no lingering data or state
        self.reset_ui()
        
        # Update the button states to reflect the new configuration
        self.update_button_states()

    @pyqtSlot(dict)
    def on_settings_updated(self, updated_settings):
        """Handle settings updates from SettingsTab"""
        try:
            # Update notification handler if Slack credentials changed
            if ('slack_token' in updated_settings or 'channel_id' in updated_settings):
                self.notification_handler = NotificationHandler(
                    updated_settings['slack_token'],
                    updated_settings['channel_id']
                )
            
            # Update any components that depend on settings
            self.run_stop_section.update_settings(updated_settings)
            self.print_to_terminal("Settings updated successfully")
            
        except Exception as e:
            self.print_to_terminal(f"Error applying settings updates: {e}")
            QMessageBox.critical(self, "Settings Update Error", 
                               f"Failed to apply settings updates: {str(e)}")

    def _handle_settings_update(self, settings):
        """Handle system settings updates"""
        self.settings = settings
        self._update_ui_from_settings()

    def _update_ui_from_settings(self):
        # Implement the logic to update the UI based on the new settings
        pass