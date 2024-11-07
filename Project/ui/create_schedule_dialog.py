# ui/create_schedule_dialog.py

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from .schedule_creation_widget import ScheduleCreationWidget

class CreateScheduleDialog(QDialog):
    def __init__(self, settings, print_to_terminal, database_handler, trainer_id):
        super().__init__()
        self.setWindowTitle("Create Schedule")
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.trainer_id = trainer_id

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Add schedule creation form or widgets
        self.schedule_form = ScheduleCreationWidget(self.database_handler, self.trainer_id)
        layout.addWidget(self.schedule_form)

        # Connect signals (e.g., when the schedule is created)
        self.schedule_form.schedule_created_signal.connect(self.on_schedule_created)

    def on_schedule_created(self):
        QMessageBox.information(self, "Success", "Schedule created successfully.")
        self.accept()  # Close the dialog