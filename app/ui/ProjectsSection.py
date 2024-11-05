# app/ui/ProjectsSection.py

from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from SchedulesTab import SchedulesTab
from AnimalsTab import AnimalsTab

class ProjectsSection(QWidget):
    def __init__(self, db_manager, print_to_terminal):
        super().__init__()

        self.db_manager = db_manager
        self.print_to_terminal = print_to_terminal

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tabs = QTabWidget()
        self.schedules_tab = SchedulesTab(self.db_manager, self.print_to_terminal)
        self.animals_tab = AnimalsTab(self.db_manager, self.print_to_terminal)

        self.tabs.addTab(self.schedules_tab, "Schedules")
        self.tabs.addTab(self.animals_tab, "Animals")

        layout.addWidget(self.tabs)