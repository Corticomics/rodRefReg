# app/ui/ProjectsSection.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView, QPushButton, QHBoxLayout, QMessageBox, QListWidget, QScrollArea
from PyQt5.QtCore import Qt
from .SchedulesTab import SchedulesTab
from .AnimalsTab import AnimalsTab
from .SummaryDialog import SummaryDialog

class ProjectsSection(QWidget):
    def __init__(self, db_manager, print_to_terminal, run_program, stop_program, settings):
        super().__init__()

        self.db_manager = db_manager
        self.print_to_terminal = print_to_terminal
        self.run_program = run_program
        self.stop_program = stop_program
        self.settings = settings

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create tabs
        self.tabs = QTabWidget()

        # Add "Schedules" tab
        self.schedules_tab = SchedulesTab(self.db_manager, self.print_to_terminal, self.run_program, self.stop_program, self.settings)
        self.tabs.addTab(self.schedules_tab, "Schedules")

        # Add "Animals" tab
        self.animals_tab = AnimalsTab(self.db_manager, self.print_to_terminal, self.run_program, self.stop_program, self.settings)
        self.tabs.addTab(self.animals_tab, "Animals")

        layout.addWidget(self.tabs)