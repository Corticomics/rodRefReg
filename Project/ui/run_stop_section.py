from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QDateTimeEdit, QTabWidget, QFormLayout, QSizePolicy, 
                             QHBoxLayout, QMessageBox, QComboBox, QDialog, QListWidget,
                             QStackedWidget, QGroupBox)
from PyQt5.QtCore import QDateTime, QTimer, Qt, pyqtSignal, pyqtSlot
from .schedule_drop_area import ScheduleDropArea
from .edit_schedule_dialog import EditScheduleDialog
from gpio.relay_worker import RelayWorker
from datetime import datetime
from PyQt5.QtWidgets import QApplication

class RunStopSection(QWidget):
    """
    Run/Stop control section with login-gated access.
    
    Security Model (per PyQt5 best practices):
    - Controls are disabled when user is not logged in
    - Visual feedback indicates disabled state
    - All operations verify login status before execution
    
    Reference: https://doc.qt.io/qt-5/qwidget.html#enabled-prop
    """
    schedule_updated = pyqtSignal(int)

    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, 
                 system_controller=None, database_handler=None, relay_handler=None, 
                 notification_handler=None, login_system=None, parent=None):
        super().__init__(parent)
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback
        self.system_controller = system_controller
        
        if database_handler is None:
            raise ValueError("database_handler cannot be None")
        self.database_handler = database_handler
        
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.login_system = login_system
        self.current_schedule = None

        self.job_in_progress = False

        self.init_ui()

        if system_controller:
            self.load_settings(system_controller.settings)

        self.setAcceptDrops(True)
        
        # Connect to login system for permission updates
        if self.login_system:
            self.login_system.login_status_changed.connect(self._update_controls_access)
            # Set initial state
            self._update_controls_access()
        
        print("RunStopSection initialized")

    def init_ui(self):
        """
        Initialize UI with split-pane layout following lab software best practices.
        
        Architecture:
        - Left pane: Schedule queue and controls (persistent)
        - Right pane: Real-time execution monitoring (persistent)
        
        Benefits:
        - Persistent visibility of both queue and execution
        - Follows industry standards (LabVIEW, CellProfiler patterns)
        - Reduces cognitive load (no context switching)
        """
        self.layout = QHBoxLayout()  # Horizontal split instead of vertical
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)

        # === LEFT PANE: Schedule Queue & Controls ===
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        self.run_button = QPushButton("Run", self)
        self.run_button.setProperty("variant", "primary")
        self.stop_button = QPushButton("Stop", self)
        self.relay_hats_button = QPushButton("Change Relay Hats", self)
        self.edit_button = QPushButton("Edit Schedule")
        
        self.edit_button.setObjectName("edit_button")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_current_schedule)

        self.run_button.clicked.connect(self.run_program)
        self.stop_button.clicked.connect(self.stop_program)
        self.relay_hats_button.clicked.connect(self.change_relay_hats)

        # Controls group
        controls_group = QGroupBox("Controls")
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(8)
        self.button_layout.setContentsMargins(12, 8, 12, 8)
        self.button_layout.addWidget(self.edit_button)
        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.relay_hats_button)
        controls_group.setLayout(self.button_layout)
        
        # Schedule drop area (always visible)
        schedule_group = QGroupBox("Schedule Queue")
        schedule_layout = QVBoxLayout()
        schedule_layout.setContentsMargins(12, 12, 12, 12)
        self.schedule_drop_area = ScheduleDropArea()
        self.schedule_drop_area.schedule_dropped.connect(self.on_schedule_dropped)
        print("Connected schedule_dropped signal to on_schedule_dropped slot")
        schedule_layout.addWidget(self.schedule_drop_area)
        schedule_group.setLayout(schedule_layout)
        
        left_layout.addWidget(controls_group)
        left_layout.addWidget(schedule_group)
        
        # Execution Monitor moved to gui.py (Terminal/Monitor tab interface)
        # This section now contains only controls and schedule queue
        
        # Add left pane to main layout (full width now)
        self.layout.addWidget(left_pane)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.run_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stop_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.relay_hats_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.setLayout(self.layout)
        self.update_button_states()
        
        self.schedule_drop_area.mode_changed.connect(self._on_mode_changed)

    def load_settings(self, settings):
        # No calendar settings needed anymore
        pass
    
    def _update_controls_access(self):
        """
        Update control button accessibility based on login status.
        
        Security Pattern: Disable controls at the widget level when user is not
        authenticated. This follows Qt best practices for access control.
        
        Reference: https://doc.qt.io/qt-5/qwidget.html#enabled-prop
        """
        is_logged_in = self.login_system.is_logged_in() if self.login_system else False
        
        # Update button states based on login
        self.run_button.setEnabled(is_logged_in and not self.job_in_progress)
        self.stop_button.setEnabled(is_logged_in and self.job_in_progress)
        self.relay_hats_button.setEnabled(is_logged_in and not self.job_in_progress)
        self.edit_button.setEnabled(is_logged_in and self.current_schedule is not None and not self.job_in_progress)
        
        # Update schedule drop area
        self.schedule_drop_area.setEnabled(is_logged_in)
        
        # Visual feedback: update tooltip for disabled state
        if not is_logged_in:
            disabled_tooltip = "Please log in to use this control"
            self.run_button.setToolTip(disabled_tooltip)
            self.stop_button.setToolTip(disabled_tooltip)
            self.relay_hats_button.setToolTip(disabled_tooltip)
            self.edit_button.setToolTip(disabled_tooltip)
            self.schedule_drop_area.setToolTip("Please log in to drop schedules")
        else:
            # Restore normal tooltips
            self.run_button.setToolTip("Start the loaded schedule")
            self.stop_button.setToolTip("Stop the running schedule")
            self.relay_hats_button.setToolTip("Configure relay HAT hardware")
            self.edit_button.setToolTip("Edit the current schedule")
            self.schedule_drop_area.setToolTip("Drag and drop a schedule here to load it")

    def update_button_states(self):
        """
        Update button enabled states based on job status AND login status.
        
        Security: Always check login status in addition to job state.
        Reference: Qt documentation on widget state management
        """
        is_logged_in = self.login_system.is_logged_in() if self.login_system else False
        
        # Debug logging for security diagnosis
        print(f"[SEC] update_button_states: login_system={self.login_system is not None}, is_logged_in={is_logged_in}, job_in_progress={self.job_in_progress}")
        
        # Buttons require both: logged in AND appropriate job state
        run_enabled = is_logged_in and not self.job_in_progress
        stop_enabled = is_logged_in and self.job_in_progress
        relay_enabled = is_logged_in and not self.job_in_progress
        edit_enabled = is_logged_in and self.current_schedule is not None and not self.job_in_progress
        
        print(f"[SEC] Button states: run={run_enabled}, stop={stop_enabled}, relay={relay_enabled}, edit={edit_enabled}")
        
        self.run_button.setEnabled(run_enabled)
        self.stop_button.setEnabled(stop_enabled)
        self.relay_hats_button.setEnabled(relay_enabled)
        self.edit_button.setEnabled(edit_enabled)
        self.schedule_drop_area.setEnabled(is_logged_in)
        
        # Set appropriate tooltips
        if not is_logged_in:
            disabled_tooltip = "Please log in to use this control"
            self.run_button.setToolTip(disabled_tooltip)
            self.stop_button.setToolTip(disabled_tooltip)
            self.relay_hats_button.setToolTip(disabled_tooltip)
        elif self.job_in_progress:
            self.run_button.setToolTip("Job in progress")
            self.relay_hats_button.setToolTip("Cannot change relay hats during a job")
            self.stop_button.setToolTip("Click to stop the current job")
        else:
            self.run_button.setToolTip("Start the loaded schedule")
            self.relay_hats_button.setToolTip("Configure relay HAT hardware")
            self.stop_button.setToolTip("No job in progress to stop")

    def run_program(self):
        """
        Execute the loaded schedule with optimized UI responsiveness.
        
        Optimization Strategy:
        1. Update UI immediately to show "Starting..." state
        2. Defer database queries using QTimer.singleShot(0)
        3. Reduce verbose debug output
        
        Security: Verifies login status before execution (defense in depth).
        Reference: 
        - OWASP Access Control guidelines
        - Qt Event Loop: https://doc.qt.io/qt-5/qcoreapplication.html#processEvents
        """
        # Security check: verify login status (defense in depth)
        if self.login_system and not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", 
                "You must be logged in to run schedules.")
            return
        
        if self.job_in_progress:
            return
        
        if not self.schedule_drop_area.current_schedule:
            QMessageBox.warning(self, "No Schedule", "Please drop a schedule to run")
            return
        
        # OPTIMIZATION: Update UI immediately before any database work
        self.job_in_progress = True
        self.run_button.setEnabled(False)
        self.run_button.setText("Starting...")
        self.stop_button.setEnabled(True)
        QApplication.processEvents()  # Force UI update
        
        # Defer heavy work to next event loop iteration
        # This ensures UI updates are painted before blocking operations
        QTimer.singleShot(0, self._prepare_and_execute_schedule)
    
    def _prepare_and_execute_schedule(self):
        """
        Prepare schedule data and execute (runs after UI update).
        
        This is called via QTimer.singleShot(0) to ensure the UI
        has updated before we do any blocking database queries.
        """
        try:
            schedule = self.schedule_drop_area.current_schedule
            mode = self.schedule_drop_area.get_mode()
            
            print(f"[RUN] Starting schedule: {schedule.name}, mode: {mode}")
            
            # Database queries (now happen after UI is updated)
            schedule_details = self.database_handler.get_schedule_details(schedule.schedule_id)[0]
            schedule.animals = schedule_details['animal_ids']
            schedule.relay_unit_assignments = schedule_details.get('relay_unit_assignments', {})
            schedule.desired_water_outputs = schedule_details.get('desired_water_outputs', {})
            
            if not schedule.animals:
                self._reset_run_button()
                QMessageBox.warning(self, "Invalid Schedule", "No animals assigned to this schedule")
                return
            
            if mode == "Staggered":
                if not schedule.start_time or not schedule.end_time:
                    self._reset_run_button()
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "Schedule must have start and end times for staggered mode")
                    return
                
                if not schedule.desired_water_outputs:
                    self._reset_run_button()
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "No water outputs configured for staggered mode")
                    return
                
                windows = self.database_handler.get_schedule_staggered_windows(schedule.schedule_id)
                if not windows:
                    self._reset_run_button()
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "No delivery windows configured for staggered mode")
                    return
                
                schedule.window_data = windows
                
                # Time window validation
                now = datetime.now()
                scheduled_start = datetime.fromisoformat(schedule.start_time)
                scheduled_end = datetime.fromisoformat(schedule.end_time)
                
                # Scenario 1: Schedule entirely in the past
                if now > scheduled_end:
                    self._reset_run_button()
                    QMessageBox.warning(self, "Expired Schedule", 
                        f"This schedule ended on {scheduled_end.strftime('%Y-%m-%d %H:%M')}.\n\n"
                        "Please create a new schedule with future times.")
                    return
                
                # Scenario 2: Start time has passed but end is in future
                if now > scheduled_start:
                    remaining_minutes = (scheduled_end - now).total_seconds() / 60
                    reply = QMessageBox.question(
                        self, "Schedule Start Time Passed",
                        f"The scheduled start time ({scheduled_start.strftime('%Y-%m-%d %H:%M')}) "
                        f"has already passed.\n\n"
                        f"Remaining window: {remaining_minutes:.0f} minutes until "
                        f"{scheduled_end.strftime('%H:%M')}.\n\n"
                        "Do you want to start the schedule now with the remaining time?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    if reply != QMessageBox.Yes:
                        self._reset_run_button()
                        return
                    
                    # Adjust window_start to now
                    print(f"[RUN] Adjusting window start from {scheduled_start} to {now}")
                    window_start = now.timestamp()
                else:
                    # Future schedule - use original start time
                    window_start = scheduled_start.timestamp()
                
                window_end = scheduled_end.timestamp()
                
            else:  # Instant mode
                deliveries = self.database_handler.get_schedule_instant_deliveries(schedule.schedule_id)
                if not deliveries:
                    self._reset_run_button()
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "This schedule has no instant delivery times configured")
                    return
                
                now = datetime.now()
                schedule.instant_deliveries = []
                past_count = 0
                
                for delivery in deliveries:
                    animal_id, _, _, datetime_str, volume, _, relay_unit_id = delivery
                    delivery_time = datetime.fromisoformat(datetime_str)
                    
                    # Track past deliveries but still add them for reference
                    if delivery_time < now:
                        past_count += 1
                    
                    schedule.add_instant_delivery(animal_id, delivery_time, volume, relay_unit_id)
                
                # Filter to only future deliveries for execution
                future_deliveries = [d for d in schedule.instant_deliveries if d['datetime'] >= now]
                
                # Scenario 1: All deliveries are in the past
                if len(future_deliveries) == 0:
                    self._reset_run_button()
                    QMessageBox.warning(self, "Expired Schedule", 
                        f"All {len(schedule.instant_deliveries)} scheduled deliveries have already passed.\n\n"
                        "Please create a new schedule with future delivery times.")
                    return
                
                # Scenario 2: Some deliveries are in the past
                if past_count > 0:
                    reply = QMessageBox.question(
                        self, "Some Deliveries Passed",
                        f"{past_count} of {len(schedule.instant_deliveries)} scheduled deliveries "
                        f"have already passed.\n\n"
                        f"{len(future_deliveries)} deliveries will still be executed.\n\n"
                        "Do you want to continue with the remaining deliveries?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    if reply != QMessageBox.Yes:
                        self._reset_run_button()
                        return
                    
                    print(f"[RUN] Skipping {past_count} past deliveries, executing {len(future_deliveries)}")
                
                delivery_times = [d['datetime'] for d in future_deliveries]
                window_start = min(delivery_times).timestamp()
                window_end = max(delivery_times).timestamp()
            
            if not schedule.relay_unit_assignments:
                self._reset_run_button()
                QMessageBox.warning(self, "Invalid Schedule", 
                    "No relay unit assignments configured")
                return
            
            # Update button states (already set job_in_progress in run_program)
            self.update_button_states()
            
            # Show progress tracker with Material Design cards
            self.show_progress_tracker(schedule)
            
            # Transition: "Starting..." → "Running" after prep completes
            self.run_button.setText("Running")
            QApplication.processEvents()
            
            # Execute in next event loop iteration
            print(f"[RUN] Launching execution for {schedule.name}")
            QTimer.singleShot(0, lambda: self._execute_program(
                schedule, mode, window_start, window_end
            ))
            
        except Exception as e:
            self._reset_run_button()
            QMessageBox.critical(self, "Error", f"Failed to run program: {str(e)}")
    
    def _reset_run_button(self):
        """Reset run button to initial state after error or cancellation."""
        self.job_in_progress = False
        self.run_button.setText("Run")
        self.update_button_states()

    def _execute_program(self, schedule, mode, window_start, window_end):
        """
        Execute the schedule program via callback.
        
        On success: Button stays "Running" until stopped
        On error: Reset to initial state with error message
        """
        try:
            self.run_program_callback(schedule, mode, window_start, window_end)
        except Exception as e:
            # Reset to initial state on error
            self.job_in_progress = False
            self.run_button.setText("Run")
            self.update_button_states()
            QMessageBox.critical(self, "Error", f"Failed to run program: {str(e)}")

    def stop_program(self):
        try:
            if not self.job_in_progress:
                return
            
            self.progress_dialog = QMessageBox(self)
            self.progress_dialog.setIcon(QMessageBox.Information)
            self.progress_dialog.setText("Stopping schedule...")
            self.progress_dialog.setStandardButtons(QMessageBox.NoButton)
            
            self.stop_button.setEnabled(False)
            self.stop_button.setText("Stopping...")
            
            self._execute_stop()
            
        except Exception as e:
            self.job_in_progress = False
            self.update_button_states()
            QMessageBox.critical(self, "Error", f"Failed to stop schedule: {str(e)}")

    def _execute_stop(self):
        try:
            self.progress_dialog.show()
            QApplication.processEvents()
            
            success = self.stop_program_callback()
            
            QApplication.processEvents()
            
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog.deleteLater()
                self.progress_dialog = None
            
            self.job_in_progress = False
            self.update_button_states()
            self.reset_ui()
            
            if not success:
                QMessageBox.warning(self, "Warning", "Failed to stop schedule completely")
                
        except Exception as e:
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog.deleteLater()
                self.progress_dialog = None
            QMessageBox.critical(self, "Error", f"Failed to stop schedule: {str(e)}")
            self.job_in_progress = False
            self.update_button_states()

    def reset_ui(self):
        """
        Reset UI state after schedule completion or stop.
        
        Best Practice: Reset ALL button states to initial values.
        Reference: Qt State Management - https://doc.qt.io/qt-5/qabstractbutton.html
        """
        self.job_in_progress = False
        # Reset both button texts to initial state
        self.run_button.setText("Run")
        self.stop_button.setText("Stop")
        self.update_button_states()
        # No need to switch views - both panes persist

    def change_relay_hats(self):
        try:
            self.change_relay_hats_callback()
            self.reset_ui()
            self.update_button_states()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change relay hats: {str(e)}")

    def _on_mode_changed(self, mode):
        pass

    def edit_current_schedule(self):
        if not self.current_schedule:
            return
        
        try:
            dialog = EditScheduleDialog(self.current_schedule, self.database_handler, self)
            if dialog.exec_() == QDialog.Accepted:
                self.schedule_drop_area.update_table(self.current_schedule)
                self.schedule_updated.emit(self.current_schedule.schedule_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit schedule: {str(e)}")

    @pyqtSlot(object)
    def on_schedule_dropped(self, schedule):
        print(f"Schedule dropped: {schedule.name if schedule else 'None'}")
        self.current_schedule = schedule
        # Update button states with login check instead of directly enabling
        self.update_button_states()

    def on_schedule_updated(self, updated_schedule):
        self.current_schedule = updated_schedule
        self.schedule_drop_area.update_table(updated_schedule)
        self.schedule_updated.emit(updated_schedule.schedule_id)
    
    def show_progress_tracker(self, schedule):
        """
        Initialize progress tracker with schedule data.
        
        Architecture:
        - Progress tracker now lives in gui.py (Terminal/Monitor tab interface)
        - This method prepares data and delegates to parent GUI
        
        Best Practices:
        - Separation of concerns: RunStopSection handles controls, GUI handles display
        - Execution Monitor appears as tab alongside Terminal when running
        """
        print(f"\n[RunStopSection] show_progress_tracker called for: {getattr(schedule, 'name', 'Unknown')}")
        
        # Prepare schedule data
        animal_ids = schedule.animals if hasattr(schedule, 'animals') else []
        relay_assignments = schedule.relay_unit_assignments if hasattr(schedule, 'relay_unit_assignments') else {}
        desired_outputs = schedule.desired_water_outputs if hasattr(schedule, 'desired_water_outputs') else {}
        
        print(f"[RunStopSection] animal_ids: {animal_ids}")
        print(f"[RunStopSection] relay_assignments: {relay_assignments}")
        print(f"[RunStopSection] desired_outputs: {desired_outputs}")
        
        # Build animals_data: {animal_id: {'cage_id': int, 'target_volume': float}}
        animals_data = {}
        for animal_id in animal_ids:
            key_str = str(animal_id)
            relay_unit_id = relay_assignments.get(key_str) or relay_assignments.get(animal_id)
            if relay_unit_id is None:
                print(f"[RunStopSection] WARNING: No relay assignment for animal {animal_id}")
                continue
            # In solenoid mode relay_unit_id maps to cage_id 1:1
            cage_id = int(relay_unit_id)
            target_volume = desired_outputs.get(key_str, schedule.water_volume)
            animals_data[animal_id] = {
                'cage_id': cage_id,
                'target_volume': float(target_volume) if target_volume is not None else 0.0
            }
            print(f"[RunStopSection] Mapped animal {animal_id} → cage {cage_id}, target {target_volume}ml")
        
        print(f"[RunStopSection] Final animals_data: {animals_data}")
        
        # Delegate to parent GUI to show Execution Monitor tab
        schedule_name = getattr(schedule, 'name', 'Untitled Schedule')
        parent_gui = self._get_parent_gui()
        if parent_gui and hasattr(parent_gui, 'show_execution_monitor'):
            parent_gui.show_execution_monitor(schedule_name, animals_data)
            print(f"[RunStopSection] Delegated to GUI show_execution_monitor")
        else:
            print(f"[RunStopSection] WARNING: Parent GUI not found, progress tracker skipped")
    
    def hide_progress_tracker(self):
        """
        Hide the Execution Monitor tab after schedule completion.
        
        Delegates to parent GUI which handles the tab visibility.
        """
        parent_gui = self._get_parent_gui()
        if parent_gui and hasattr(parent_gui, 'hide_execution_monitor'):
            parent_gui.hide_execution_monitor()
    
    def _get_parent_gui(self):
        """
        Find the parent RodentRefreshmentGUI widget.
        
        Traverses widget hierarchy to find the main GUI.
        """
        widget = self.parent()
        while widget is not None:
            if widget.__class__.__name__ == 'RodentRefreshmentGUI':
                return widget
            widget = widget.parent()
        return None
    
    def get_progress_tracker(self):
        """
        Provide access to progress tracker for signal connections.
        
        Returns:
            ScheduleProgressTracker: The progress tracker instance from parent GUI
        """
        parent_gui = self._get_parent_gui()
        if parent_gui and hasattr(parent_gui, 'get_progress_tracker'):
            return parent_gui.get_progress_tracker()
        return None