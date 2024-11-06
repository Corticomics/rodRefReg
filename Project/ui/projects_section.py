from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from .schedules_tab import SchedulesTab
from .animals_tab import AnimalsTab

class ProjectsSection(QWidget):
    def __init__(self, settings, print_to_terminal):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create Tab Widget
        self.tab_widget = QTabWidget()

        # Create Schedules Tab
        self.schedules_tab = SchedulesTab(settings, print_to_terminal)
        self.tab_widget.addTab(self.schedules_tab, "Schedules")

        # Create Animals Tab
        self.animals_tab = AnimalsTab(settings, print_to_terminal)
        self.tab_widget.addTab(self.animals_tab, "Animals")

        self.layout.addWidget(self.tab_widget)