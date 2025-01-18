# ui/schedule_creation_widget.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import pyqtSignal

class ScheduleCreationWidget(QWidget):
    schedule_created_signal = pyqtSignal()

    def __init__(self, database_handler, trainer_id):
        super().__init__()
        self.database_handler = database_handler
        self.trainer_id = trainer_id

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
            # Save the schedule to the database
            success = self.database_handler.add_schedule(schedule_name, self.trainer_id)

            if success:
                self.schedule_created_signal.emit()
            else:
                QMessageBox.warning(self, "Error", "Failed to create schedule.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while creating the schedule: {e}")