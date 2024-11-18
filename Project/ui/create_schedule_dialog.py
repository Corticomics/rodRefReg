# ui/create_schedule_dialog.py

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from datetime import datetime
from models.Schedule import Schedule

class CreateScheduleDialog(QDialog):
    def __init__(self, settings, print_to_terminal, database_handler, login_system):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system

        self.setWindowTitle("Create Schedule")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Example form fields
        self.name_label = QLabel("Schedule Name:")
        self.name_input = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)

        # Add more fields as needed...

        # Create Schedule button
        self.create_button = QPushButton("Create Schedule")
        self.create_button.clicked.connect(self.create_schedule)
        layout.addWidget(self.create_button)

    def create_schedule(self):
        # Implement the logic to create a schedule
        schedule_name = self.name_input.text().strip()

        if not schedule_name:
            QMessageBox.warning(self, "Input Error", "Please enter a schedule name.")
            return

        try:
            # Example: Assign to current trainer or handle super user logic
            current_trainer = self.login_system.get_current_trainer()
            if not current_trainer:
                QMessageBox.warning(self, "Authentication Error", "You must be logged in to create a schedule.")
                return

            trainer_id = current_trainer['trainer_id']
            role = current_trainer['role']

            # Create a Schedule object (you may need to gather more data)
            schedule = Schedule(
                schedule_id=None,
                name=schedule_name,
                relay_unit_id=1,  # Example relay_unit_id
                water_volume=10.0,  # Example water_volume
                start_time=datetime.datetime.now().isoformat(),
                end_time=datetime.datetime.now().isoformat(),
                created_by=trainer_id,
                is_super_user=(role == 'super')
            )

            # Save the schedule to the database
            schedule_id = self.database_handler.add_schedule(schedule)

            if schedule_id:
                self.print_to_terminal(f"Schedule '{schedule_name}' created with ID: {schedule_id}.")
                QMessageBox.information(self, "Success", f"Schedule '{schedule_name}' created successfully.")
                self.accept()
            else:
                QMessageBox.warning(self, "Create Error", "Failed to create schedule. Please try again.")

        except Exception as e:
            QMessageBox.critical(self, "Create Error", f"An unexpected error occurred: {e}")
            self.print_to_terminal(f"Unexpected error during schedule creation: {e}")