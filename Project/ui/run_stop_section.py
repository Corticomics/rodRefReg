from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QDateTimeEdit, QTabWidget, QFormLayout, QSizePolicy, QHBoxLayout, QMessageBox, QComboBox)
from PyQt5.QtCore import QDateTime, QTimer, Qt
from .schedule_drop_area import ScheduleDropArea
from .edit_schedule_dialog import EditScheduleDialog

class RunStopSection(QWidget):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, settings=None, advanced_settings=None, parent=None):
        super().__init__(parent)
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback
        self.settings = settings
        self.advanced_settings = advanced_settings  # Pass advanced settings here

        # Track the state of the job
        self.job_in_progress = False

        self.init_ui()

        # Create a QTimer to keep updating the minimum date/time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_minimum_datetime)
        self.timer.start(1000)  # Update every second

        if settings:
            self.load_settings(settings)

        self.setAcceptDrops(True)  # Enable dropping

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)

        # Tab widget for Calendar and Offline modes
        self.tab_widget = QTabWidget()
        self.calendar_widget = QWidget()
        self.offline_widget = QWidget()

        # Calendar-Based Time Window Selection
        calendar_layout = QFormLayout()
        calendar_layout.setSpacing(12)
        calendar_layout.setContentsMargins(12, 12, 12, 12)
        
        self.start_time_label = QLabel("Start Time:")
        self.start_time_input = QDateTimeEdit(self.calendar_widget)
        self.start_time_input.setCalendarPopup(True)
        self.start_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_time_input.setDateTime(QDateTime.currentDateTime())  # Default to now
        self.start_time_input.setMinimumDateTime(QDateTime.currentDateTime())  # Set minimum to now
        self.start_time_input.setMinimumWidth(160)  # Set minimum width for the datetime input
        self.start_time_input.setFixedHeight(28)
        
        self.end_time_label = QLabel("End Time:")
        self.end_time_input = QDateTimeEdit(self.calendar_widget)
        self.end_time_input.setCalendarPopup(True)
        self.end_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_time_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # Default to 1 hour later
        self.end_time_input.setMinimumDateTime(QDateTime.currentDateTime())  # Set minimum to now
        self.end_time_input.setMinimumWidth(160)  # Set minimum width for the datetime input
        self.end_time_input.setFixedHeight(28)

        # Style the labels to be more visible
        label_style = "QLabel { font-size: 11pt; padding: 3px; }"
        self.start_time_label.setStyleSheet(label_style)
        self.end_time_label.setStyleSheet(label_style)

        # Style the datetime inputs to be more visible
        date_time_style = """
            QDateTimeEdit {
                padding: 5px;
                min-height: 25px;
                background-color: white;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
            }
            QCalendarWidget QAbstractItemView {
                background-color: #525251;
                selection-background-color: #607cff;
            }

            QCalendarWidget QWidget {
                alternate-background-color: #404040;
            }

            QCalendarWidget QToolButton {
                color: white;
                background-color: #525251;
            }

            QCalendarWidget QMenu {
                background-color: #525251;
            }
        """
        self.start_time_input.setStyleSheet(date_time_style)
        self.end_time_input.setStyleSheet(date_time_style)

        calendar_layout.addRow(self.start_time_label, self.start_time_input)
        calendar_layout.addRow(self.end_time_label, self.end_time_input)
        self.calendar_widget.setLayout(calendar_layout)

        # Offline Mode
        self.offline_label = QLabel("Offline Duration (minutes):")
        self.offline_input = QLineEdit(self.offline_widget)
        self.offline_input.setPlaceholderText("Enter minutes")

        offline_layout = QFormLayout()
        offline_layout.addRow(self.offline_label, self.offline_input)
        self.offline_widget.setLayout(offline_layout)

        self.tab_widget.addTab(self.calendar_widget, "Calendar Mode")
        self.tab_widget.addTab(self.offline_widget, "Offline Mode")

        # Schedule drop area
        self.schedule_drop_area = ScheduleDropArea()
        
        # Buttons
        self.run_button = QPushButton("Run", self)
        self.stop_button = QPushButton("Stop", self)
        self.relay_hats_button = QPushButton("Change Relay Hats", self)
        
        self.run_button.clicked.connect(self.run_program)
        self.stop_button.clicked.connect(self.stop_program)
        self.relay_hats_button.clicked.connect(self.change_relay_hats_callback)
        
        # Button layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(5)
        self.button_layout.addWidget(self.edit_button)
        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.relay_hats_button)
        
        # Create button container
        button_container = QHBoxLayout()
        
        # Initialize edit button
        self.edit_button = QPushButton("Edit Schedule")
        self.edit_button.setObjectName("edit_button")  # Important for findChild
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
        
        button_container.addWidget(self.edit_button)
        
        button_container.addWidget(self.run_button)
        button_container.addWidget(self.stop_button)
        button_container.addWidget(self.relay_hats_button)
        
        # Add button container to main layout
        self.layout.addLayout(button_container)
        
        self.layout.addWidget(self.tab_widget)
        
        # Add schedule drop area directly (without label)
        self.layout.addWidget(self.schedule_drop_area)
        
        self.layout.addLayout(self.button_layout)
        self.layout.addStretch()
        
        # Set size policies
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.run_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stop_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.relay_hats_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.setLayout(self.layout)
        self.update_button_states()

        # Add after line 112
        self.schedule_drop_area.mode_changed.connect(self._on_mode_changed)

    def load_settings(self, settings):
        self.start_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_start']))
        self.end_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_end']))
        self.offline_input.setText(str(settings.get('offline_duration', 60)))

    def update_minimum_datetime(self):
        """Update the minimum selectable datetime to 'right now'."""
        current_datetime = QDateTime.currentDateTime()
        self.start_time_input.setMinimumDateTime(current_datetime)
        self.end_time_input.setMinimumDateTime(current_datetime)

    # The rest of your methods remain unchanged...


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
                # For staggered mode, use the time window from UI
                if self.tab_widget.currentIndex() == 0:  # Calendar Mode
                    window_start = self.start_time_input.dateTime().toSecsSinceEpoch()
                    window_end = self.end_time_input.dateTime().toSecsSinceEpoch()
                else:  # Offline Mode
                    duration = int(self.offline_input.text()) * 60
                    window_start = int(QDateTime.currentSecsSinceEpoch())
                    window_end = window_start + duration
            else:  # Instant mode
                # Use the schedule's instant delivery times
                if not schedule.instant_deliveries:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "This schedule has no instant delivery times configured")
                    return
                
                # Get earliest and latest delivery times from schedule
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
        self.start_time_input.setDateTime(QDateTime.currentDateTime())
        self.end_time_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.offline_input.clear()


    def change_relay_hats(self):
        # Clear any old references in the advanced settings
        self.advanced_settings.clear_layout(self.advanced_settings.layout)
        self.advanced_settings.trigger_entries.clear()

        # Execute the callback to change the relay hats
        self.change_relay_hats_callback()

        # After changing the relay hats, reinitialize the advanced settings UI
        self.advanced_settings.create_settings_ui()

        # Update the internal settings with new relay pairs (optional but recommended)
        self.settings['relay_pairs'] = self.advanced_settings.settings['relay_pairs']

        # Reset the UI to ensure no lingering data or state
        self.reset_ui()

        # Update the button states to reflect the new configuration
        self.update_button_states()

    def _on_mode_changed(self, mode):
        """Handle mode changes from schedule drop area"""
        is_staggered = mode == "Staggered"
        self.tab_widget.setVisible(is_staggered)

    def edit_current_schedule(self):
        if not self.current_schedule:
            return
        
        dialog = EditScheduleDialog(self.current_schedule, self.database_handler, self)
        if dialog.exec_() == QDialog.Accepted:
            # Refresh the schedule display
            self.update_schedule_display()
            # Notify parent of changes
            if hasattr(self, 'schedule_updated'):
                self.schedule_updated.emit(self.current_schedule.schedule_id)


