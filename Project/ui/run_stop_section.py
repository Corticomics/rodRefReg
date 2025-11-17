from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QDateTimeEdit, QTabWidget, QFormLayout, QSizePolicy, 
                             QHBoxLayout, QMessageBox, QComboBox, QDialog, QListWidget,
                             QStackedWidget, QGroupBox)
from PyQt5.QtCore import QDateTime, QTimer, Qt, pyqtSignal, pyqtSlot
from .schedule_drop_area import ScheduleDropArea
from .edit_schedule_dialog import EditScheduleDialog
from .ScheduleProgressTracker import ScheduleProgressTracker
from gpio.relay_worker import RelayWorker
from datetime import datetime
from PyQt5.QtWidgets import QApplication

class RunStopSection(QWidget):
    schedule_updated = pyqtSignal(int)

    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, 
                 system_controller=None, database_handler=None, relay_handler=None, notification_handler=None, parent=None):
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
        self.current_schedule = None

        self.job_in_progress = False

        self.init_ui()

        if system_controller:
            self.load_settings(system_controller.settings)

        self.setAcceptDrops(True)
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
        
        # === RIGHT PANE: Real-Time Monitoring ===
        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress tracker (always visible, starts empty)
        monitor_group = QGroupBox("Execution Monitor")
        monitor_layout = QVBoxLayout()
        monitor_layout.setContentsMargins(12, 12, 12, 12)
        self.progress_tracker = ScheduleProgressTracker()
        self.progress_tracker.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        monitor_layout.addWidget(self.progress_tracker)
        monitor_group.setLayout(monitor_layout)
        
        right_layout.addWidget(monitor_group)
        
        # Add panes to main layout (60/40 split)
        self.layout.addWidget(left_pane, 60)   # 60% for queue
        self.layout.addWidget(right_pane, 40)  # 40% for monitoring
        
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

    def update_button_states(self):
        self.run_button.setEnabled(not self.job_in_progress)
        self.stop_button.setEnabled(self.job_in_progress)
        self.relay_hats_button.setEnabled(not self.job_in_progress)
        if self.job_in_progress:
            self.run_button.setToolTip("Job in progress")
            self.relay_hats_button.setToolTip("Cannot change relay hats during a job")
        else:
            self.run_button.setToolTip("")
            self.relay_hats_button.setToolTip("")

        if not self.job_in_progress:
            self.stop_button.setToolTip("No job in progress to stop")
        else:
            self.stop_button.setToolTip("")

    def run_program(self):
        try:
            print("\nDEBUG - RunStopSection run_program:")
            print(f"self.system_controller type: {type(self.system_controller)}")
            if self.job_in_progress:
                return
            
            if not self.schedule_drop_area.current_schedule:
                QMessageBox.warning(self, "No Schedule", "Please drop a schedule to run")
                return
            
            schedule = self.schedule_drop_area.current_schedule
            mode = self.schedule_drop_area.get_mode()
            
            # Get settings from system_controller; note we do not alter system_controller.settings here
            worker_settings = self.system_controller.settings.copy()
            worker_settings.update({
                'schedule_id': schedule.schedule_id,
                'mode': mode,
                'window_start': schedule.start_time,
                'window_end': schedule.end_time,
                'water_volume': schedule.water_volume,
                'relay_unit_assignments': schedule.relay_unit_assignments,
                'desired_water_outputs': schedule.desired_water_outputs
            })
            
            schedule_details = self.database_handler.get_schedule_details(schedule.schedule_id)[0]
            schedule.animals = schedule_details['animal_ids']
            schedule.relay_unit_assignments = schedule_details.get('relay_unit_assignments', {})
            schedule.desired_water_outputs = schedule_details.get('desired_water_outputs', {})
            
            if not schedule.animals:
                QMessageBox.warning(self, "Invalid Schedule", "No animals assigned to this schedule")
                return
            
            print("\nDEBUG INFO:")
            print(f"Schedule: {schedule.__dict__}")
            print(f"Mode: {mode}")
            
            print("\nSchedule Debug Info:")
            print(f"Desired water outputs: {schedule.desired_water_outputs}")
            print(f"Relay assignments: {schedule.relay_unit_assignments}")
            
            if mode == "Staggered":
                if not schedule.start_time or not schedule.end_time:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "Schedule must have start and end times for staggered mode")
                    return
                
                if not schedule.desired_water_outputs:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "No water outputs configured for staggered mode")
                    return
                
                windows = self.database_handler.get_schedule_staggered_windows(schedule.schedule_id)
                if not windows:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "No delivery windows configured for staggered mode")
                    return
                
                schedule.window_data = windows
                window_start = datetime.fromisoformat(schedule.start_time).timestamp()
                window_end = datetime.fromisoformat(schedule.end_time).timestamp()
                
            else:  # Instant mode
                deliveries = self.database_handler.get_schedule_instant_deliveries(schedule.schedule_id)
                if not deliveries:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "This schedule has no instant delivery times configured")
                    return
                
                schedule.instant_deliveries = []
                for delivery in deliveries:
                    animal_id, _, _, datetime_str, volume, _, relay_unit_id = delivery
                    delivery_time = datetime.fromisoformat(datetime_str)
                    schedule.add_instant_delivery(animal_id, delivery_time, volume, relay_unit_id)
                
                delivery_times = [d['datetime'] for d in schedule.instant_deliveries]
                window_start = min(delivery_times).timestamp()
                window_end = max(delivery_times).timestamp()
            
            if not schedule.relay_unit_assignments:
                QMessageBox.warning(self, "Invalid Schedule", 
                    "No relay unit assignments configured")
                return
            
            self.job_in_progress = True
            self.update_button_states()
            
            # Show progress tracker with Material Design cards
            self.show_progress_tracker(schedule)
            
            QTimer.singleShot(0, lambda: self._execute_program(
                schedule, mode, window_start, window_end
            ))
            
        except Exception as e:
            self.job_in_progress = False
            self.update_button_states()
            QMessageBox.critical(self, "Error", f"Failed to run program: {str(e)}")

    def _execute_program(self, schedule, mode, window_start, window_end):
        try:
            self.run_program_callback(schedule, mode, window_start, window_end)
        except Exception as e:
            self.job_in_progress = False
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
        """Reset UI state after schedule completion."""
        self.job_in_progress = False
        self.update_button_states()
        self.stop_button.setText("Stop")
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
        self.edit_button.setEnabled(True)
        # Use theme defaults (no inline styles)

    def on_schedule_updated(self, updated_schedule):
        self.current_schedule = updated_schedule
        self.schedule_drop_area.update_table(updated_schedule)
        self.schedule_updated.emit(updated_schedule.schedule_id)
    
    def show_progress_tracker(self, schedule):
        """
        Initialize progress tracker with schedule data.
        
        Best Practices (Lab Software Pattern):
        - No view switching - both queue and monitor visible
        - Real-time updates in persistent right pane
        - Follows LabVIEW/CellProfiler monitoring patterns
        """
        # Initialize progress tracker with schedule animals
        animal_ids = schedule.animals if hasattr(schedule, 'animals') else []
        relay_assignments = schedule.relay_unit_assignments if hasattr(schedule, 'relay_unit_assignments') else {}
        desired_outputs = schedule.desired_water_outputs if hasattr(schedule, 'desired_water_outputs') else {}
        
        # Build animals_data: {animal_id: {'cage_id': int, 'target_volume': float}}
        animals_data = {}
        for animal_id in animal_ids:
            key_str = str(animal_id)
            relay_unit_id = relay_assignments.get(key_str) or relay_assignments.get(animal_id)
            if relay_unit_id is None:
                continue
            # In solenoid mode relay_unit_id maps to cage_id 1:1
            cage_id = int(relay_unit_id)
            target_volume = desired_outputs.get(key_str, schedule.water_volume)
            animals_data[animal_id] = {
                'cage_id': cage_id,
                'target_volume': float(target_volume) if target_volume is not None else 0.0
            }
        
        # Start the tracker (no view switching - it's already visible in right pane)
        schedule_name = getattr(schedule, 'name', 'Untitled Schedule')
        self.progress_tracker.start_schedule(schedule_name, animals_data)
    
    def hide_progress_tracker(self):
        """
        Clear progress tracker after schedule completion.
        
        Note: No view switching - progress cards fade out in-place.
        """
        # Schedule cleanup of progress cards (10-second auto-dismiss)
        QTimer.singleShot(10000, self.progress_tracker.clear_cards)
    
    def get_progress_tracker(self):
        """
        Provide access to progress tracker for signal connections.
        
        Returns:
            ScheduleProgressTracker: The progress tracker instance
        """
        return self.progress_tracker