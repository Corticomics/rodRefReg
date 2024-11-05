# app/gui/project_builder.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox, QHBoxLayout, QInputDialog
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag
from shared.models.animal import Animal
from .drag_drop_area import DragDropArea

class ProjectBuilder(QWidget):
    def __init__(self, db_manager, relay_handler, notification_handler, settings, print_to_terminal_callback):
        super().__init__()

        self.db_manager = db_manager
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.settings = settings
        self.print_to_terminal = print_to_terminal_callback

        self.selected_animals = []

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Build Watering Project")
        self.layout = QVBoxLayout(self)

        # Label
        self.layout.addWidget(QLabel("Create a New Watering Project"))

        # Drag and Drop Area
        self.drag_drop_area = DragDropArea(self)
        self.layout.addWidget(self.drag_drop_area)

        # Button to create a new mouse
        create_mouse_button = QPushButton("Create New Mouse")
        create_mouse_button.clicked.connect(self.create_new_mouse)
        self.layout.addWidget(create_mouse_button)

        # Button to build project
        build_project_button = QPushButton("Build Project")
        build_project_button.clicked.connect(self.build_project)
        self.layout.addWidget(build_project_button)

    def create_new_mouse(self):
        text, ok = QInputDialog.getText(self, 'Create New Mouse', 'Enter Mouse ID and Species (e.g., ID - Species):')
        if ok and text:
            try:
                animal_id, species = text.split('-')
                animal_id = animal_id.strip()
                species = species.strip()
                # Prompt for body weight
                body_weight, ok_weight = QInputDialog.getDouble(self, 'Mouse Weight', 'Enter body weight in grams:', decimals=2, min=0.1)
                if ok_weight:
                    # Add to database
                    new_mouse = self.db_manager.add_animal(animal_id, species, body_weight)
                    self.drag_drop_area.add_animal(new_mouse)
                    QMessageBox.information(self, "Success", f"Mouse '{new_mouse.animal_id} - {new_mouse.species}' added successfully.")
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Please enter the Mouse ID and Species in the correct format (e.g., ID - Species).")

    def build_project(self):
        if not self.drag_drop_area.selected_animals:
            QMessageBox.warning(self, "No Selection", "Please add at least one mouse to the project.")
            return

        # Confirm project details
        for mouse in self.drag_drop_area.selected_animals:
            min_water = mouse.calculate_min_water()
            max_water = mouse.calculate_max_water()
            weight = mouse.body_weight
            self.print_to_terminal(f"Mouse ID: {mouse.animal_id}, Species: {mouse.species}, Weight: {weight}g")
            self.print_to_terminal(f" - Water Volume Range: {min_water:.2f}ml - {max_water:.2f}ml")

        # Save the project to the database
        project = self.db_manager.create_project(self.drag_drop_area.selected_animals)
        self.print_to_terminal(f"Project '{project.project_id}' created successfully.")

        QMessageBox.information(self, "Success", f"Project '{project.project_id}' created successfully.")
        self.drag_drop_area.clear()

    def load_project(self, project):
        # Implement loading the project into the UI
        self.drag_drop_area.clear()
        for mouse in project.animals:
            self.drag_drop_area.add_animal(mouse)