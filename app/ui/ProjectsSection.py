# app/ui/ProjectsSection.py

from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from .SchedulesTab import SchedulesTab
from .AnimalsTab import AnimalsTab

class ProjectsSection(QWidget):
    def __init__(self, db_manager, print_to_terminal, run_program_callback, stop_program_callback, settings):
        super().__init__()

        self.db_manager = db_manager
        self.print_to_terminal = print_to_terminal
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.settings = settings

        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create Tab Widget
        self.tab_widget = QTabWidget()

        # Create Schedules Tab
        self.schedules_tab = SchedulesTab(
            self.db_manager,
            self.print_to_terminal,
            self.run_program_callback,
            self.stop_program_callback,
            self.settings
        )

        # Create Animals Tab
        self.animals_tab = AnimalsTab(
            self.db_manager,
            self.print_to_terminal
        )

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.schedules_tab, "Schedules")
        self.tab_widget.addTab(self.animals_tab, "Animals")

        self.layout.addWidget(self.tab_widget)