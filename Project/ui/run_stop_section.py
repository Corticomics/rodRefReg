from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QDateTimeEdit, QTabWidget, QFormLayout, QSizePolicy, QSpacerItem)
from PyQt5.QtCore import QDateTime, QTimer

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

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(100)

        # Tab widget for Calendar and Offline modes
        self.tab_widget = QTabWidget()
        self.calendar_widget = QWidget()
        self.offline_widget = QWidget()

        # Calendar-Based Time Window Selection
        self.start_time_label = QLabel("Start Time:")
        self.start_time_input = QDateTimeEdit(self.calendar_widget)
        self.start_time_input.setCalendarPopup(True)
        self.start_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_time_input.setDateTime(QDateTime.currentDateTime())  # Default to now
        self.start_time_input.setMinimumDateTime(QDateTime.currentDateTime())  # Set minimum to now

        self.end_time_label = QLabel("End Time:")
        self.end_time_input = QDateTimeEdit(self.calendar_widget)
        self.end_time_input.setCalendarPopup(True)
        self.end_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_time_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # Default to 1 hour later
        self.end_time_input.setMinimumDateTime(QDateTime.currentDateTime())  # Set minimum to now

        calendar_layout = QFormLayout()
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

        # Interval and Stagger Inputs
        self.interval_label = QLabel("Interval (seconds):")
        self.interval_input = QLineEdit(self)
        self.interval_input.setPlaceholderText("Enter seconds")

        self.stagger_label = QLabel("Stagger (seconds):")
        self.stagger_input = QLineEdit(self)
        self.stagger_input.setPlaceholderText("Enter seconds")

        buttonsspace  = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(buttonsspace)
        self.run_button = QPushButton("Run", self)
        self.stop_button = QPushButton("Stop", self)
        self.relay_hats_button = QPushButton("Change Relay Hats", self)
        self.layout.addItem(buttonsspace)

        self.run_button.clicked.connect(self.run_program)
        self.stop_button.clicked.connect(self.stop_program)
        self.relay_hats_button.clicked.connect(self.change_relay_hats_callback)

        # Layout
        form_layout = QFormLayout()
        form_layout.addRow(self.interval_label, self.interval_input)
        form_layout.addRow(self.stagger_label, self.stagger_input)

        self.layout.addWidget(self.tab_widget)
        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.run_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.relay_hats_button)

        self.setLayout(self.layout)

        # Initialize button states
        self.update_button_states()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.run_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stop_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.relay_hats_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Add stretch to push buttons to the bottom
        self.layout.addStretch()

        self.setLayout(self.layout)

    def load_settings(self, settings):
        self.start_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_start']))
        self.end_time_input.setDateTime(QDateTime.fromSecsSinceEpoch(settings['window_end']))
        self.offline_input.setText(str(settings.get('offline_duration', 60)))  # Use default if not found
        self.interval_input.setText(str(settings['interval']))
        self.stagger_input.setText(str(settings['stagger']))

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
            interval = int(self.interval_input.text())
            stagger = int(self.stagger_input.text())
            if self.tab_widget.currentIndex() == 0:  # Calendar Mode
                window_start = self.start_time_input.dateTime().toSecsSinceEpoch()
                window_end = self.end_time_input.dateTime().toSecsSinceEpoch()
                
            else:  # Offline Mode
                duration = int(self.offline_input.text()) * 60  # Convert minutes to seconds
                window_start = int(QDateTime.currentSecsSinceEpoch())
                window_end = window_start + duration
                

            self.settings['interval'] = interval
            self.settings['stagger'] = stagger
            self.settings['window_start'] = window_start
            self.settings['window_end'] = window_end

            # Get updated relay settings
            
            if self.advanced_settings:
                advanced_settings = self.advanced_settings.get_settings()
                
                # Ensure all keys are strings for consistency
                advanced_settings['num_triggers'] = {str(k): v for k, v in advanced_settings['num_triggers'].items()}
                self.settings.update(advanced_settings)
                

            # Call the callback with settings that have string keys
            self.run_program_callback(interval, stagger, window_start, window_end)

            # Mark job as in progress and update buttons
            self.job_in_progress = True
            
            self.update_button_states()

        except Exception as e:
            print(f"g program: {e}")

    def stop_program(self):
        self.stop_program_callback()

        # Mark job as not in progress and update buttons
        self.job_in_progress = False
        self.update_button_states()

    def reset_ui(self):
        """Reset the UI to the initial state after a job is completed."""
        self.job_in_progress = False
        self.update_button_states()
        self.interval_input.clear()
        self.stagger_input.clear()
        self.start_time_input.setDateTime(QDateTime.currentDateTime())
        self.end_time_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # Default 1 hour later
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


