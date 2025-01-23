from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QTabWidget, QFormLayout, QSizePolicy, QHBoxLayout, 
                            QMessageBox, QComboBox)
from PyQt5.QtCore import Qt, QDateTime, QTimer, pyqtSignal
from .schedule_drop_area import ScheduleDropArea
from .edit_schedule_dialog import EditScheduleDialog

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
        self.job_in_progress = False
        self.init_ui()

        if settings:
            self.load_settings(settings)

        self.setAcceptDrops(True)

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create buttons
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_current_schedule)
        self.edit_button.setEnabled(False)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_program)
        self.run_button.setEnabled(False)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_program)
        self.stop_button.setEnabled(False)

        self.relay_hats_button = QPushButton("Change Relay Hats")
        self.relay_hats_button.clicked.connect(self.change_relay_hats)

        # Create and populate button layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(5)
        self.button_layout.addWidget(self.edit_button)
        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.relay_hats_button)

        # Offline Mode
        self.offline_widget = QWidget()
        self.offline_label = QLabel("Offline Duration (minutes):")
        self.offline_input = QLineEdit(self.offline_widget)
        self.offline_input.setPlaceholderText("Enter minutes")

        offline_layout = QFormLayout()
        offline_layout.addRow(self.offline_label, self.offline_input)
        self.offline_widget.setLayout(offline_layout)

        # Schedule drop area
        self.schedule_drop_area = ScheduleDropArea()
        self.schedule_drop_area.schedule_dropped.connect(self.on_schedule_dropped)
        
        # Add components to main layout
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.offline_widget)
        self.layout.addWidget(self.schedule_drop_area)
        self.layout.addStretch()

    def load_settings(self, settings):
        self.offline_input.setText(str(settings.get('offline_duration', 60)))

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
        try:
            if not self.schedule_drop_area.current_schedule:
                QMessageBox.warning(self, "No Schedule", "Please drop a schedule to run")
                return
            
            schedule = self.schedule_drop_area.current_schedule
            mode = self.schedule_drop_area.get_mode()
            
            if mode == "Staggered":
                # For staggered mode, use the schedule's saved time window
                window_start = int(QDateTime.fromString(schedule.start_time, 
                                                      "yyyy-MM-ddTHH:mm:ss").toSecsSinceEpoch())
                window_end = int(QDateTime.fromString(schedule.end_time, 
                                                    "yyyy-MM-ddTHH:mm:ss").toSecsSinceEpoch())
            else:  # Instant mode
                # Use the schedule's instant delivery times
                if not schedule.instant_deliveries:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "This schedule has no instant delivery times configured")
                    return
                
                delivery_times = [QDateTime.fromString(d['datetime'].strftime("%Y-%m-%d %H:%M:%S"), 
                                                     "yyyy-MM-dd HH:mm:ss") 
                                for d in schedule.instant_deliveries]
                window_start = min(delivery_times).toSecsSinceEpoch()
                window_end = max(delivery_times).toSecsSinceEpoch()
            
            self.run_program_callback(schedule, mode, window_start, window_end)
            self.job_in_progress = True
            self.update_button_states()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run program: {e}")

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
        self.offline_input.clear()

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


