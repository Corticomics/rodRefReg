# app/ui/SchedulesTab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QMessageBox, QHBoxLayout, QInputDialog, QGridLayout
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag
from .drag_drop_area import DragDropArea  # Ensure this file exists

class SchedulesTab(QWidget):
    def __init__(self, db_manager, print_to_terminal, run_program_callback, stop_program_callback, settings):
        super().__init__()

        self.db_manager = db_manager
        self.print_to_terminal = print_to_terminal
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.settings = settings

        self.selected_animals = []

        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Title
        title_label = QLabel("Manage Watering Schedules")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(title_label)

        # Drag and Drop Area to Assign Animals to Relay Pairs
        self.drag_drop_area = DragDropArea(self)
        self.layout.addWidget(self.drag_drop_area)

        # Relay Pairs Grid
        self.relay_grid = QGridLayout()
        self.layout.addLayout(self.relay_grid)

        # Initialize Relay Buttons
        self.relay_buttons = {}
        relay_pairs = self.settings.get('relay_pairs', [])
        for index, pair in enumerate(relay_pairs):
            relay_label = f"Relays {pair[0]} & {pair[1]}"
            relay_button = QPushButton(relay_label)
            relay_button.setAcceptDrops(True)
            relay_button.setStyleSheet("background-color: #e0e0e0;")
            relay_button.setFixedSize(150, 50)
            relay_button.installEventFilter(self)
            self.relay_grid.addWidget(relay_button, index // 4, index % 4)
            self.relay_buttons[relay_button] = pair

        # Buttons for Project Management
        button_layout = QHBoxLayout()

        create_project_button = QPushButton("Create New Project")
        create_project_button.clicked.connect(self.create_new_project)
        button_layout.addWidget(create_project_button)

        view_projects_button = QPushButton("View Past Projects")
        view_projects_button.clicked.connect(self.view_past_projects)
        button_layout.addWidget(view_projects_button)

        manage_waterings_button = QPushButton("Manage Waterings")
        manage_waterings_button.clicked.connect(self.manage_waterings)
        button_layout.addWidget(manage_waterings_button)

        self.layout.addLayout(button_layout)

    def eventFilter(self, source, event):
        if event.type() == event.DragEnter:
            if event.mimeData().hasFormat('application/x-animal'):
                event.accept()
            else:
                event.ignore()
            return True
        elif event.type() == event.Drop:
            if event.mimeData().hasFormat('application/x-animal'):
                animal_id = event.mimeData().data('application/x-animal').data().decode('utf-8')
                animal = self.db_manager.get_animal_by_id(animal_id)
                if animal:
                    relay_pair = self.relay_buttons.get(source, None)
                    if relay_pair:
                        # Assign animal to relay pair
                        self.print_to_terminal(f"Assigned Animal ID {animal_id} to Relay Pair {relay_pair}")
                        # Here you can add logic to schedule the watering
                        QMessageBox.information(self, "Assignment Successful", f"Assigned Animal ID {animal_id} to Relay Pair {relay_pair}")
            else:
                event.ignore()
            return True
        return super().eventFilter(source, event)

    def create_new_project(self):
        # Gather selected animals from relay assignments
        assigned_animals = self.drag_drop_area.assigned_animals  # Assuming this attribute exists
        if not assigned_animals:
            QMessageBox.warning(self, "No Assignments", "Please assign at least one animal to a relay pair.")
            return

        # Prompt for project name
        project_name, ok = QInputDialog.getText(self, "Create New Project", "Enter Project Name:")
        if ok and project_name:
            # Create project in the database
            project = self.db_manager.create_project(project_name, assigned_animals)
            if project:
                self.print_to_terminal(f"New project '{project.project_id}' created successfully.")
                QMessageBox.information(self, "Success", f"Project '{project.project_id}' created successfully.")
                self.drag_drop_area.clear_assignments()
            else:
                self.print_to_terminal("Failed to create project.")
                QMessageBox.critical(self, "Error", "Failed to create project.")
        else:
            QMessageBox.warning(self, "Input Required", "Project name cannot be empty.")

    def view_past_projects(self):
        # Fetch past projects from the database
        projects = self.db_manager.get_past_projects()
        if not projects:
            QMessageBox.information(self, "No Projects", "No past projects found.")
            return

        # Display projects in a list
        project_list = QListWidget()
        for project in projects:
            project_list.addItem(f"Project ID: {project.project_id} - Created on: {project.creation_date}")

        # Show in a message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Past Projects")
        msg_box_layout = QVBoxLayout()
        msg_box_layout.addWidget(project_list)
        msg_box.setLayout(msg_box_layout)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def manage_waterings(self):
        # Placeholder for managing waterings
        QMessageBox.information(self, "Manage Waterings", "Manage Waterings functionality is under development.")