# ui/projects_section.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPushButton, QMessageBox
from .schedules_tab import SchedulesTab
from .animals_tab import AnimalsTab

class ProjectsSection(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler, login_system):
        super().__init__()

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system  # Store the login_system

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create a tab widget for schedules and animals
        self.tab_widget = QTabWidget()

        # Schedules tab
        self.schedules_tab = SchedulesTab(
            settings, 
            self.print_to_terminal,
            database_handler, 
            login_system
        )
        self.tab_widget.addTab(self.schedules_tab, "Schedules")

        # Animals tab
        self.animals_tab = AnimalsTab(
            settings, 
            self.print_to_terminal,
            database_handler, 
            login_system
        )
        self.tab_widget.addTab(self.animals_tab, "Animals")

        self.layout.addWidget(self.tab_widget)

        # Add the "Save Current Schedule" button back
        self.save_schedule_button = QPushButton("Save Current Schedule")
        self.save_schedule_button.clicked.connect(self.save_current_schedule)
        self.layout.addWidget(self.save_schedule_button)

    def save_current_schedule(self):
        # Call the save_current_schedule method of the schedules_tab
        try:
            self.schedules_tab.save_current_schedule()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving the schedule: {e}")
            self.print_to_terminal(f"Error saving schedule: {e}")
