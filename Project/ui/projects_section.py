from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from .schedules_tab import SchedulesTab
from .animals_tab import AnimalsTab

class ProjectsSection(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler  # Pass database handler here

        self.layout = QVBoxLayout(self)
        
        # Initialize the tabs with the database handler
        self.schedules_tab = SchedulesTab(self.settings, self.database_handler)
        self.animals_tab = AnimalsTab(self.settings, self.print_to_terminal)

        # Create a tab widget and add both tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.schedules_tab, "Schedules")
        self.tabs.addTab(self.animals_tab, "Animals")

        self.layout.addWidget(self.tabs)