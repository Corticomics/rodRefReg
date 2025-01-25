from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QDateTimeEdit, QTabWidget, QFormLayout, QSizePolicy, QHBoxLayout, QMessageBox, QComboBox, QDialog)
from PyQt5.QtCore import QDateTime, QTimer, Qt
from .schedule_drop_area import ScheduleDropArea
from .edit_schedule_dialog import EditScheduleDialog
from PyQt5.QtCore import pyqtSignal

from datetime import datetime

class RunStopSection(QWidget):
    schedule_updated = pyqtSignal(int)

    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, settings=None, database_handler=None, parent=None):
        super().__init__(parent)
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback
        self.settings = settings
        self.database_handler = database_handler
        self.current_schedule = None

        # Track the state of the job
        self.job_in_progress = False

        self.init_ui()

        if settings:
            self.load_settings(settings)

        self.setAcceptDrops(True)  # Enable dropping

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)

        # Initialize all buttons
        self.run_button = QPushButton("Run", self)
        self.stop_button = QPushButton("Stop", self)
        self.relay_hats_button = QPushButton("Change Relay Hats", self)
        self.edit_button = QPushButton("Edit Schedule")
        
        # Set up edit button properties
        self.edit_button.setObjectName("edit_button")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_current_schedule)
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 80px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:disabled {
                background-color: #87c4cb;
            }
        """)

        # Connect button signals
        self.run_button.clicked.connect(self.run_program)
        self.stop_button.clicked.connect(self.stop_program)
        self.relay_hats_button.clicked.connect(self.change_relay_hats)

        # Create and populate button layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(5)
        self.button_layout.addWidget(self.edit_button)
        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.relay_hats_button)

        # Schedule drop area
        self.schedule_drop_area = ScheduleDropArea()
        self.schedule_drop_area.schedule_dropped.connect(self.on_schedule_dropped)
        
        # Add widgets to main layout
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.schedule_drop_area)
        self.layout.addStretch()
        
        # Set size policies
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.run_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stop_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.relay_hats_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.setLayout(self.layout)
        self.update_button_states()
        
        # Connect mode changed signal
        self.schedule_drop_area.mode_changed.connect(self._on_mode_changed)

    def load_settings(self, settings):
        """Load settings without calendar-related inputs"""
        pass  # We no longer need to load calendar settings

    def update_minimum_datetime(self):
        """Update minimum datetime is no longer needed"""
        pass

    def update_button_states(self):
        """Enable or disable the Run, Stop, and Change Relay Hats buttons based on the job's state."""
        self.run_button.setEnabled(not self.job_in_progress)
        self.stop_button.setEnabled(self.job_in_progress)
        self.relay_hats_button.setEnabled(not self.job_in_progress)  # Disable when job in progress

        # Apply styles for disabled buttons
        if self.job_in_progress:
            self.run_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)
            self.run_button.setToolTip("Job in progress")
            self.relay_hats_button.setToolTip("Cannot change relay hats during a job")
        else:
            self.run_button.setStyleSheet("")
            self.run_button.setToolTip("")
            self.relay_hats_button.setToolTip("")

        if not self.job_in_progress:
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)
            self.stop_button.setToolTip("No job in progress to stop")
        else:
            self.stop_button.setStyleSheet("")
            self.stop_button.setToolTip("")

    def run_program(self):
        """Start executing the current schedule"""
        try:
            if not self.schedule_drop_area.current_schedule:
                QMessageBox.warning(self, "No Schedule", "Please drop a schedule to run")
                return
            
            schedule = self.schedule_drop_area.current_schedule
            mode = self.schedule_drop_area.get_mode()
            
            print("\nDEBUG INFO:")
            print(f"Schedule: {schedule.__dict__}")
            print(f"Mode: {mode}")
            
            # Get schedule window from delivery slots
            if mode == "Staggered":
                if not schedule.start_time or not schedule.end_time:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "Schedule must have start and end times for staggered mode")
                    return
                    
                # Convert ISO format strings to datetime objects
                start_dt = datetime.fromisoformat(schedule.start_time)
                end_dt = datetime.fromisoformat(schedule.end_time)
                
                window_start = start_dt.timestamp()
                window_end = end_dt.timestamp()
                
            else:  # Instant mode
                if not schedule.instant_deliveries:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "This schedule has no instant delivery times configured")
                    return
                
                # Use the earliest and latest delivery times
                delivery_times = [d['datetime'] for d in schedule.instant_deliveries]
                window_start = min(delivery_times).timestamp()
                window_end = max(delivery_times).timestamp()
            
            # Update settings with mode before passing to run_program_callback
            settings = {
                'window_start': window_start,
                'window_end': window_end,
                'mode': mode,  # Add mode to settings
                'schedule_id': schedule.schedule_id,
                'target_volumes': schedule.desired_water_outputs,
                'relay_unit_assignments': schedule.relay_unit_assignments
            }
            
            # Start the schedule execution with updated settings
            print(f"Starting schedule execution with settings: {settings}")
            self.run_program_callback(schedule, settings)
            self.job_in_progress = True
            self.update_button_states()
            
        except Exception as e:
            print(f"Error details: {str(e)}")  # Add detailed error logging
            QMessageBox.critical(self, "Error", f"Failed to run program in RunStopSection: {e}")

    def stop_program(self):
        """Pause the current schedule and display dispensed volumes"""
        try:
            self.stop_program_callback()
            self.job_in_progress = False
            self.update_button_states()
            
            # Display paused message with volumes
            volumes_text = "\n".join([
                f"Relay unit {unit}: {volume}mL" 
                for unit, volume in self.schedule_manager.dispensed_volumes.items()
            ])
            QMessageBox.information(
                self,
                "Schedule Paused",
                f"Schedule paused. Volumes dispensed:\n{volumes_text}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to pause schedule: {str(e)}")

    def reset_ui(self):
        """Reset the UI to the initial state after a job is completed."""
        self.job_in_progress = False
        self.update_button_states()

    def change_relay_hats(self):
        """Change relay hats configuration"""
        try:
            # Execute the callback to change the relay hats
            self.change_relay_hats_callback()
            
            # Reset the UI
            self.reset_ui()
            
            # Update the button states
            self.update_button_states()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change relay hats: {str(e)}")

    def _on_mode_changed(self, mode):
        """Handle mode changes from schedule drop area"""
        pass  # No need to handle visibility of removed tab widget

    def edit_current_schedule(self):
        """Open the edit dialog for the current schedule"""
        if not self.current_schedule:
            return
        
        try:
            dialog = EditScheduleDialog(self.current_schedule, self.database_handler, self)
            if dialog.exec_() == QDialog.Accepted:
                # Refresh the schedule display
                self.schedule_drop_area.update_table(self.current_schedule)
                # Notify any listeners that the schedule was updated
                self.schedule_updated.emit(self.current_schedule.schedule_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit schedule: {str(e)}")

    def on_schedule_dropped(self, schedule):
        """Handle when a schedule is dropped"""
        self.current_schedule = schedule
        self.edit_button.setEnabled(True)
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 80px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        # Connect the schedule drop area's signal
        self.schedule_drop_area.schedule_dropped.connect(self.on_schedule_dropped)

    def on_schedule_updated(self, updated_schedule):
        """Handle when a schedule is updated"""
        self.current_schedule = updated_schedule
        self.update_table(updated_schedule)
        self.schedule_updated.emit(updated_schedule.schedule_id)


