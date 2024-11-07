# ui/projects_section.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPushButton, QMessageBox
from .schedules_tab import SchedulesTab
from .animals_tab import AnimalsTab
from .create_schedule_dialog import CreateScheduleDialog  # Import the new dialog class

class ProjectsSection(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler, trainer_id=None):
        super().__init__()

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.trainer_id = trainer_id  # Store the trainer_id

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create a tab widget for schedules and animals
        self.tab_widget = QTabWidget()

        # Schedules tab
        self.schedules_tab = SchedulesTab(settings, print_to_terminal, database_handler, trainer_id=self.trainer_id)
        self.tab_widget.addTab(self.schedules_tab, "Schedules")

        # Animals tab
        self.animals_tab = AnimalsTab(settings, print_to_terminal, database_handler, trainer_id=self.trainer_id)
        self.tab_widget.addTab(self.animals_tab, "Animals")

        self.layout.addWidget(self.tab_widget)

        # Add a create schedule button that opens the create schedule dialog
        self.create_schedule_button = QPushButton("Create Schedule")
        self.create_schedule_button.clicked.connect(self.open_create_schedule)
        self.layout.addWidget(self.create_schedule_button)

    def open_create_schedule(self):
        # Open the Create Schedule dialog
        try:
            dialog = CreateScheduleDialog(self.settings, self.print_to_terminal, self.database_handler, trainer_id=self.trainer_id)
            dialog.exec_()
            # After dialog is closed, refresh the schedules tab to show new schedules
            self.schedules_tab.load_schedules()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while creating a schedule: {e}")
            self.print_to_terminal(f"Error opening Create Schedule dialog: {e}")