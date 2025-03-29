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
