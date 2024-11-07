from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QDialog
from .schedules_tab import SchedulesTab

class ProjectsSection(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler):
        super().__init__()

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Button to create a new schedule
        self.create_schedule_button = QPushButton("Create Schedule")
        self.create_schedule_button.clicked.connect(self.open_create_schedule)
        self.layout.addWidget(self.create_schedule_button)

    def open_create_schedule(self):
        # Open the Create Schedule window
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Schedule")
        layout = QVBoxLayout(dialog)

        # Add SchedulesTab inside the dialog
        self.schedules_tab = SchedulesTab(self.settings, self.print_to_terminal, self.database_handler)
        layout.addWidget(self.schedules_tab)

        dialog.setLayout(layout)
        dialog.exec_()