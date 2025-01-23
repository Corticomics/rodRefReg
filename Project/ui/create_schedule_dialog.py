# ui/create_schedule_dialog.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                           QPushButton, QMessageBox, QDateTimeEdit)
from PyQt5.QtCore import Qt, QDateTime
from datetime import datetime
from models.Schedule import Schedule

class CreateScheduleDialog(QDialog):
    def __init__(self, settings, print_to_terminal, database_handler, login_system, mode='instant'):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system
        self.mode = mode.lower()

        self.setWindowTitle(f"Save {mode.capitalize()} Schedule")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Common fields
        self.name_label = QLabel("Schedule Name:")
        self.name_input = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)

        # Staggered mode specific fields
        if self.mode == 'staggered':
            # Start time
            self.start_time_label = QLabel("Start Time:")
            self.start_time_input = QDateTimeEdit()
            self.start_time_input.setCalendarPopup(True)
            self.start_time_input.setDateTime(QDateTime.currentDateTime())
            layout.addWidget(self.start_time_label)
            layout.addWidget(self.start_time_input)

            # End time
            self.end_time_label = QLabel("End Time:")
            self.end_time_input = QDateTimeEdit()
            self.end_time_input.setCalendarPopup(True)
            self.end_time_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
            layout.addWidget(self.end_time_label)
            layout.addWidget(self.end_time_input)

            # Interval
            self.interval_label = QLabel("Interval (minutes):")
            self.interval_input = QLineEdit()
            self.interval_input.setText("60")  # Default 60 minutes
            layout.addWidget(self.interval_label)
            layout.addWidget(self.interval_input)

        # Save button
        self.save_button = QPushButton("Save Schedule")
        self.save_button.clicked.connect(self.create_schedule)
        layout.addWidget(self.save_button)

    def create_schedule(self):
        schedule_name = self.name_input.text().strip()

        if not schedule_name:
            QMessageBox.warning(self, "Input Error", "Please enter a schedule name.")
            return

        try:
            current_trainer = self.login_system.get_current_trainer()
            if not current_trainer:
                QMessageBox.warning(self, "Authentication Error", "You must be logged in to create a schedule.")
                return

            trainer_id = current_trainer['trainer_id']
            role = current_trainer['role']

            if self.mode == 'staggered':
                start_time = self.start_time_input.dateTime().toPyDateTime()
                end_time = self.end_time_input.dateTime().toPyDateTime()
                
                if start_time >= end_time:
                    QMessageBox.warning(self, "Time Error", "End time must be after start time.")
                    return

                try:
                    interval = int(self.interval_input.text())
                    if interval <= 0:
                        raise ValueError
                except ValueError:
                    QMessageBox.warning(self, "Input Error", "Please enter a valid interval (positive number).")
                    return

            # Create base schedule object
            schedule = Schedule(
                schedule_id=None,
                name=schedule_name,
                water_volume=0.0,  # Will be updated when adding deliveries
                start_time=start_time.isoformat() if self.mode == 'staggered' else datetime.now().isoformat(),
                end_time=end_time.isoformat() if self.mode == 'staggered' else datetime.now().isoformat(),
                created_by=trainer_id,
                is_super_user=(role == 'super'),
                delivery_mode=self.mode
            )

            # Save schedule to database
            schedule_id = self.database_handler.add_schedule(schedule)

            if schedule_id:
                self.print_to_terminal(f"Schedule '{schedule_name}' created with ID: {schedule_id}")
                QMessageBox.information(self, "Success", f"Schedule '{schedule_name}' created successfully.")
                self.accept()
            else:
                QMessageBox.warning(self, "Create Error", "Failed to create schedule. Please try again.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")