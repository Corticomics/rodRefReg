# ui/gui.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QPlainTextEdit, QLabel, QMessageBox, QSizePolicy, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
import traceback
from .run_stop_section import RunStopSection
from .projects_section import ProjectsSection
from .UserTab import UserTab
from .ScheduleProgressTracker import ScheduleProgressTracker
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
        
        # Execution monitor state
        self._schedule_running = False
        self._hide_timer = None

        # Connect system message signal
        self.system_message_signal.connect(self.print_to_terminal)

        # Initialize the UI with the selected style
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        # Use centralized app-level QSS (StyleManager). No per-widget styles here.

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Content area
        content_layout = QHBoxLayout()
        
        # Left side
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # === TERMINAL / EXECUTION MONITOR TABBED INTERFACE ===
        # When schedule runs, Execution Monitor tab appears
        self.terminal_tab_widget = QTabWidget()
        self.terminal_tab_widget.setMinimumHeight(180)
        
        # Terminal tab (always visible)
        terminal_container = QWidget()
        terminal_layout = QVBoxLayout(terminal_container)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        self.terminal_output = QPlainTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setPlainText("System Messages")
        terminal_layout.addWidget(self.terminal_output)
        self.terminal_tab_widget.addTab(terminal_container, "Terminal")
        
        # Execution Monitor tab (hidden until schedule runs)
        monitor_container = QWidget()
        monitor_layout = QVBoxLayout(monitor_container)
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_tracker = ScheduleProgressTracker()
        self.progress_tracker.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        monitor_layout.addWidget(self.progress_tracker)
        self.execution_monitor_index = self.terminal_tab_widget.addTab(monitor_container, "Execution Monitor")
        
        # Hide Execution Monitor tab initially
        self.terminal_tab_widget.setTabVisible(self.execution_monitor_index, False)
        
        left_layout.addWidget(self.terminal_tab_widget)
        
        # Initial stretch: Projects section gets more space, Terminal is compact
        # This is adjusted dynamically when switching to Execution Monitor
        left_layout.setStretch(0, 1)  # Terminal area (compact by default)
        
        # Projects section with login gate
        self.projects_section = ProjectsSection(
            self.settings,
            self.print_to_terminal,
            self.database_handler,
            self.login_system
        )
        self.login_gate = LoginGateWidget(self.projects_section, self.login_system)
        left_layout.addWidget(self.login_gate)
        left_layout.setStretch(1, 3)  # Projects section (expanded by default)
        
        # Right side
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.right_layout = right_layout
        
        # Create Run/Stop section with login system for access control
        # Security: RunStopSection gates controls behind login status
        self.run_stop_section = RunStopSection(
            self.run_program,
            self.stop_program,
            self.change_relay_hats,
            self.system_controller,
            database_handler=self.database_handler,
            relay_handler=self.relay_handler,
            notification_handler=self.notification_handler,
            login_system=self.login_system
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
            login_system=self.login_system,
            print_to_terminal=self.print_to_terminal,
            database_handler=self.database_handler
        )
        
        # Profile Tab
        self.user_tab = UserTab(self.login_system)
        self.user_tab.login_signal.connect(self.on_login)
        self.user_tab.logout_signal.connect(self.on_logout)
        
        # Help Tab
        self.help_tab = HelpTab()
        
        # Add tabs in desired order
        self.main_tab_widget.addTab(self.user_tab, "Profile")  # Profile tab first
        self.settings_tab_index = self.main_tab_widget.addTab(self.settings_tab, "Settings")
        self.help_tab_index = self.main_tab_widget.addTab(self.help_tab, "Help")
        
        # Initially disable restricted tabs
        self._update_tab_access()
        
        # Set the initial tab to Profile
        self.main_tab_widget.setCurrentWidget(self.user_tab)
        
        # Make run/stop section expand when needed
        self.run_stop_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(self.main_tab_widget)
        right_layout.addWidget(self.run_stop_section)
        # Default stretch favors tab content; adjusted dynamically below
        right_layout.setStretch(0, 3)
        right_layout.setStretch(1, 1)
        
        # Add to content layout
        content_layout.addWidget(left_widget, 3)
        content_layout.addWidget(right_widget, 2)
        
        # Add content layout to main layout
        main_layout.addLayout(content_layout)
        
        # Connect tab changes to dynamic layout adjustment
        self.terminal_tab_widget.currentChanged.connect(self._on_terminal_tab_changed)
        
        # Store left layout reference for dynamic resizing
        self.left_layout = left_layout
        self.left_widget = left_widget
        self.content_layout = content_layout
        
        # Connect signals
        self.projects_section.schedules_tab.mode_changed.connect(
            self.run_stop_section._on_mode_changed
        )
        
        # Reactive layout: adjust stretches when main tab or settings subtabs change
        self.main_tab_widget.currentChanged.connect(self._on_main_tab_changed)
        try:
            self.settings_tab.tab_widget.currentChanged.connect(self._on_settings_subtab_changed)
        except Exception:
            pass
        
        # Initialize
        self.load_animals_tab()
        self.showMaximized()
    
    def _apply_right_stretch(self):
        """Adjust right column stretches based on active tab and settings sub-tab."""
        current = self.main_tab_widget.currentWidget()
        if current is self.user_tab:
            # Profile has sparse content; give more height to Run/Stop
            self.right_layout.setStretch(0, 2)
            self.right_layout.setStretch(1, 2)
        elif current is self.settings_tab:
            # If Valve Calibration is selected, prioritize tab content
            try:
                idx = self.settings_tab.tab_widget.currentIndex()
                cal_idx = self.settings_tab.tab_widget.indexOf(self.settings_tab.calibration_tab)
                if idx == cal_idx:
                    self.right_layout.setStretch(0, 4)
                    self.right_layout.setStretch(1, 1)
                else:
                    self.right_layout.setStretch(0, 3)
                    self.right_layout.setStretch(1, 1)
            except Exception:
                self.right_layout.setStretch(0, 3)
                self.right_layout.setStretch(1, 1)
        else:
            # Help or others
            self.right_layout.setStretch(0, 3)
            self.right_layout.setStretch(1, 1)

    def _on_main_tab_changed(self, _index: int):
        self._apply_right_stretch()

    def _on_settings_subtab_changed(self, _index: int):
        self._apply_right_stretch()
    
    def toggle_mode(self):
        """Toggle between Normal and Super mode."""
        try:
            self.login_system.switch_mode()
            new_role = self.login_system.get_current_trainer()['role']
            self.print_to_terminal(f"Switched to {new_role.capitalize()} Mode.")
            # Refresh animals and schedules tabs
            self.projects_section.schedules_tab.load_animals()
            self.projects_section.animals_tab.load_animals()
            # Emit signal for SettingsTab to update button text
            return new_role
        except Exception as e:
            self.print_to_terminal(f"Error toggling mode: {e}")
            QMessageBox.critical(self, "Mode Toggle Error", f"An error occurred while toggling mode: {e}")
            return None
    
    def _on_terminal_tab_changed(self, index: int):
        """
        Dynamically adjust left pane layout when switching between Terminal and Execution Monitor.
        
        When Execution Monitor is active, we expand the terminal section to show cards properly.
        Also sets minimum height to ensure visibility during schedule execution.
        """
        if index == self.execution_monitor_index:
            # Execution Monitor selected - give it much more space for cards
            # Use 4:1 ratio to ensure monitor is clearly visible during execution
            self.left_layout.setStretch(0, 4)  # Terminal/Monitor area (expanded)
            self.left_layout.setStretch(1, 1)  # Projects section (compressed)
            # Set minimum height to ensure cards are visible
            self.terminal_tab_widget.setMinimumHeight(350)
        else:
            # Terminal selected - restore default proportions
            self.left_layout.setStretch(0, 1)  # Terminal area
            self.left_layout.setStretch(1, 3)  # Projects section
            # Reset minimum height for terminal mode
            self.terminal_tab_widget.setMinimumHeight(180)

    def print_to_terminal(self, message):
        """Print message to terminal output"""
        if hasattr(self, 'terminal_output'):
            self.terminal_output.appendPlainText(str(message))
    
    def show_execution_monitor(self, schedule_name: str, animals_data: dict):
        """
        Show the Execution Monitor tab when a schedule starts running.
        
        Called by run_stop_section when schedule execution begins.
        
        Args:
            schedule_name: Name of the running schedule
            animals_data: Dict of {animal_id: {'cage_id': int, 'target_volume': float}}
        """
        print(f"[GUI] show_execution_monitor called for: {schedule_name}")
        print(f"[GUI] animals_data: {animals_data}")
        print(f"[GUI] Progress tracker object: {id(self.progress_tracker)}")
        
        # Cancel any pending hide timer (prevents race condition)
        if hasattr(self, '_hide_timer') and self._hide_timer is not None:
            self._hide_timer.stop()
            self._hide_timer = None
            print("[GUI] Cancelled pending hide timer")
        
        # Mark that a schedule is running
        self._schedule_running = True
        
        # Make the Execution Monitor tab visible
        self.terminal_tab_widget.setTabVisible(self.execution_monitor_index, True)
        
        # Switch to the Execution Monitor tab
        self.terminal_tab_widget.setCurrentIndex(self.execution_monitor_index)
        
        # Explicitly trigger layout adjustment (in case signal wasn't connected)
        self._on_terminal_tab_changed(self.execution_monitor_index)
        
        # Ensure progress tracker widget is visible (may have been hidden by auto-dismiss)
        self.progress_tracker.show()
        
        # Start the progress tracker
        self.progress_tracker.start_schedule(schedule_name, animals_data)
        
        print(f"[GUI] Execution Monitor shown for: {schedule_name}")
    
    def hide_execution_monitor(self):
        """
        Hide the Execution Monitor tab when schedule stops/completes.
        
        Called by run_stop_section when schedule execution ends.
        """
        # Mark that no schedule is running
        self._schedule_running = False
        
        # Switch back to Terminal tab
        self.terminal_tab_widget.setCurrentIndex(0)
        
        # Explicitly restore normal layout proportions
        self._on_terminal_tab_changed(0)
        
        # Hide the Execution Monitor tab (with 10-second delay to show final state)
        from PyQt5.QtCore import QTimer
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_execution_monitor_tab)
        self._hide_timer.start(10000)
        
        print("[GUI] Execution Monitor will hide in 10 seconds")
    
    def _hide_execution_monitor_tab(self):
        """Actually hide the tab after delay."""
        # Only hide if no schedule is currently running
        if hasattr(self, '_schedule_running') and self._schedule_running:
            print("[GUI] Hide cancelled - new schedule is running")
            return
        
        self.terminal_tab_widget.setTabVisible(self.execution_monitor_index, False)
        self.progress_tracker.clear_cards()
        self._hide_timer = None
    
    def get_progress_tracker(self):
        """
        Provide access to progress tracker for signal connections.
        
        Used by main.py to connect worker signals to progress tracker.
        """
        return self.progress_tracker

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
            
            # Update tab access
            self._update_tab_access()
            
            # Update mode toggle button in settings
            if hasattr(self.settings_tab, '_update_mode_button_state'):
                self.settings_tab._update_mode_button_state()
            
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
            
            # Update tab access
            self._update_tab_access()
            
            # Update mode toggle button in settings
            if hasattr(self.settings_tab, '_update_mode_button_state'):
                self.settings_tab._update_mode_button_state()
            
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

    def _update_tab_access(self):
        """Update tab accessibility based on login status"""
        is_logged_in = self.login_system.is_logged_in()
        
        # Disable/enable tabs
        self.main_tab_widget.setTabEnabled(self.settings_tab_index, is_logged_in)
        self.main_tab_widget.setTabEnabled(self.help_tab_index, is_logged_in)
        
        # If on a restricted tab while logging out, switch to profile tab
        if not is_logged_in and self.main_tab_widget.currentIndex() in [self.settings_tab_index, self.help_tab_index]:
            self.main_tab_widget.setCurrentWidget(self.user_tab)