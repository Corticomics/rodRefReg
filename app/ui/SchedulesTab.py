# app/ui/SchedulesTab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox, QHBoxLayout, QLabel, QGridLayout, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
from .RelayButton import RelayButton
from .SummaryDialog import SummaryDialog

class SchedulesTab(QWidget):
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

        # Relay Buttons Grid
        self.relay_grid = QGridLayout()
        layout.addLayout(self.relay_grid)

        # Initialize Relay Buttons
        relay_pairs = self.settings.get('relay_pairs', [])
        self.relay_buttons = {}
        for index, pair in enumerate(relay_pairs):
            relay_button = RelayButton(pair, parent=self)
            relay_button.setFixedSize(150, 50)
            self.relay_grid.addWidget(relay_button, index // 4, index % 4)
            self.relay_buttons[relay_button] = pair

        # Drag and Drop Area
        self.drag_drop_area = DragDropArea(self.db_manager, self.print_to_terminal)
        layout.addWidget(self.drag_drop_area)

        # Buttons for Project Management
        button_layout = QHBoxLayout()

        self.create_project_button = QPushButton("Create New Project")
        self.create_project_button.clicked.connect(self.create_new_project)
        button_layout.addWidget(self.create_project_button)

        self.view_projects_button = QPushButton("View Past Projects")
        self.view_projects_button.clicked.connect(self.view_past_projects)
        button_layout.addWidget(self.view_projects_button)

        layout.addLayout(button_layout)

    def handle_drop(self, animal_id, relay_pair):
        animal = self.db_manager.get_animal_by_id(animal_id)
        if animal:
            self.drag_drop_area.assign_relay(relay_pair, animal)
            self.print_to_terminal(f"Assigned Animal ID {animal_id} to Relay Pair {relay_pair}")
            self.show_summary()
        else:
            self.print_to_terminal(f"Animal ID {animal_id} not found.")
            QMessageBox.critical(self, "Error", f"Animal ID {animal_id} not found.")

    def create_new_project(self):
        assignments = self.drag_drop_area.get_assignments()
        if not assignments:
            QMessageBox.warning(self, "No Assignments", "Please assign animals to relays before creating a project.")
            return

        project_name, ok = QMessageBox.getText(self, "Create New Project", "Enter Project Name:")
        if ok and project_name:
            animals = [animal for relay, animal in assignments.items()]
            project = self.db_manager.create_project(project_name, animals, relay_volumes=assignments)
            if project:
                self.print_to_terminal(f"Project '{project.project_name}' created successfully.")
                QMessageBox.information(self, "Success", f"Project '{project.project_name}' created successfully.")
                self.drag_drop_area.clear_assignments()
                self.show_summary(assignments)
            else:
                self.print_to_terminal("Failed to create project.")
                QMessageBox.critical(self, "Error", "Failed to create project.")
        else:
            QMessageBox.warning(self, "Input Required", "Project name cannot be empty.")

    def view_past_projects(self):
        projects = self.db_manager.get_past_projects()
        if not projects:
            QMessageBox.information(self, "No Projects", "No past projects found.")
            return

        project_list = QListWidget()
        for project in projects:
            project_list.addItem(f"ID: {project.project_id} - Name: {project.project_name} - Date: {project.creation_date}")

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Past Projects")
        msg_box_layout = QVBoxLayout()
        msg_box_layout.addWidget(project_list)
        msg_box.setLayout(msg_box_layout)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def show_summary(self, assignments=None):
        if assignments is None:
            assignments = self.drag_drop_area.get_assignments()
        summary = ""
        for relay, animal in assignments.items():
            summary += f"Relay {relay} assigned to Animal ID: {animal.animal_id}\n"
        summary_dialog = SummaryDialog(summary, self)
        summary_dialog.exec_()