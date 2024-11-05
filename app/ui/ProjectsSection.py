# app/ui/ProjectsSection.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView, QPushButton, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt

class ProjectsSection(QWidget):
    def __init__(self, db_manager, print_to_terminal, settings):
        super().__init__()

        self.db_manager = db_manager
        self.print_to_terminal = print_to_terminal
        self.settings = settings

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create tabs
        self.tabs = QTabWidget()

        # Add "Schedules" tab
        self.schedules_tab = QWidget()
        self.init_schedules_tab()
        self.tabs.addTab(self.schedules_tab, "Schedules")

        # Add "Animals" tab
        self.animals_tab = QWidget()
        self.init_animals_tab()
        self.tabs.addTab(self.animals_tab, "Animals")

        layout.addWidget(self.tabs)

    def init_schedules_tab(self):
        schedules_layout = QVBoxLayout()

        # Label for schedules management
        schedules_label = QLabel("Manage Watering Schedules and Create New Projects")
        schedules_label.setAlignment(Qt.AlignCenter)
        schedules_layout.addWidget(schedules_label)

        # Table to view past projects
        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(3)
        self.projects_table.setHorizontalHeaderLabels(["Project ID", "Project Name", "Creation Date"])
        self.projects_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        schedules_layout.addWidget(self.projects_table)

        # Load projects from database
        self.load_projects()

        # Add buttons
        button_layout = QHBoxLayout()
        create_project_btn = QPushButton("Create New Project")
        create_project_btn.clicked.connect(self.create_new_project)
        button_layout.addWidget(create_project_btn)

        schedules_layout.addLayout(button_layout)
        self.schedules_tab.setLayout(schedules_layout)

    def init_animals_tab(self):
        animals_layout = QVBoxLayout()

        # Label for animals management
        animals_label = QLabel("Animals Information and Assignments")
        animals_label.setAlignment(Qt.AlignCenter)
        animals_layout.addWidget(animals_label)

        # Table to display animals
        self.animals_table = QTableWidget()
        self.animals_table.setColumnCount(4)
        self.animals_table.setHorizontalHeaderLabels(["Animal ID", "Initial Weight", "Last Updated Weight", "Last Watering"])
        self.animals_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        animals_layout.addWidget(self.animals_table)

        # Load animals from database
        self.load_animals()

        self.animals_tab.setLayout(animals_layout)

    def load_projects(self):
        """Load past projects from the database."""
        projects = self.db_manager.get_past_projects()
        self.projects_table.setRowCount(len(projects))
        for row, project in enumerate(projects):
            self.projects_table.setItem(row, 0, QTableWidgetItem(str(project.project_id)))
            self.projects_table.setItem(row, 1, QTableWidgetItem(project.project_name))
            self.projects_table.setItem(row, 2, QTableWidgetItem(project.creation_date))

    def load_animals(self):
        """Load animals data from the database."""
        animals = self.db_manager.get_animals()
        self.animals_table.setRowCount(len(animals))
        for row, animal in enumerate(animals):
            self.animals_table.setItem(row, 0, QTableWidgetItem(animal.animal_id))
            self.animals_table.setItem(row, 1, QTableWidgetItem(str(animal.initial_weight)))
            self.animals_table.setItem(row, 2, QTableWidgetItem(str(animal.body_weight)))
            self.animals_table.setItem(row, 3, QTableWidgetItem(animal.last_watering if animal.last_watering else "N/A"))

    def create_new_project(self):
        """Logic to create a new project."""
        # Placeholder for project creation logic
        self.print_to_terminal("Creating a new project (Functionality to be implemented).")