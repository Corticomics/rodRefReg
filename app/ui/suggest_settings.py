# app/ui/SuggestSettingsSection.py

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QLabel, QPushButton, QComboBox, QDateTimeEdit, QMessageBox, QCheckBox
)
from .SuggestSettingsTab import SuggestSettingsTab
class SuggestSettingsSection(QWidget):
    def __init__(
        self,
        settings,
        suggest_settings_callback,
        push_settings_callback,
        save_slack_credentials_callback,
        advanced_settings,
        run_stop_section,
        parent=None
    ):
        super().__init__(parent)

        self.settings = settings
        self.suggest_settings_callback = suggest_settings_callback
        self.push_settings_callback = push_settings_callback
        self.save_slack_credentials_callback = save_slack_credentials_callback
        self.advanced_settings = advanced_settings
        self.run_stop_section = run_stop_section

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Initialize the SuggestSettingsTab with necessary callbacks
        self.suggest_tab = SuggestSettingsTab(
            self.suggest_settings_callback,
            self.push_settings_callback,
            self.db_manager  # You may need to pass db_manager here if required
        )
        layout.addWidget(self.suggest_tab)
        form_layout = QFormLayout()

        # Mouse Selection or Manual Input
        self.mouse_selector = QComboBox()
        self.mouse_selector.addItem("Select a mouse")
        animals = self.db_manager.get_animals()
        for animal in animals:
            self.mouse_selector.addItem(f"{animal.animal_id} - {animal.species}")
        self.mouse_selector.addItem("Manual Input")
        self.mouse_selector.currentIndexChanged.connect(self.toggle_weight_input)
        form_layout.addRow(QLabel("Select Mouse:"), self.mouse_selector)

        # Current Weight Input
        self.weight_input = QLineEdit()
        self.weight_input.setPlaceholderText("Enter weight in grams")
        self.weight_input.setEnabled(False)
        self.weight_input.setValidator(QDoubleValidator(0.0, 1000.0, 2))
        form_layout.addRow(QLabel("Current Weight (g):"), self.weight_input)

        # Weight-Based Suggestions
        self.floor_volume = QLineEdit()
        self.floor_volume.setReadOnly(True)
        form_layout.addRow(QLabel("Floor Water Volume (mL):"), self.floor_volume)

        self.ceiling_volume = QLineEdit()
        self.ceiling_volume.setReadOnly(True)
        form_layout.addRow(QLabel("Ceiling Water Volume (mL):"), self.ceiling_volume)

        # Suggest and Push Buttons
        self.suggest_button = QPushButton("Suggest Settings")
        self.suggest_button.clicked.connect(self.suggest_settings)
        form_layout.addRow(self.suggest_button)

        self.push_button = QPushButton("Push Settings")
        self.push_button.clicked.connect(self.push_settings)
        self.push_button.setEnabled(False)
        form_layout.addRow(self.push_button)

        # Auto-Save Checkbox
        self.auto_save_checkbox = QCheckBox("Automatically Save Project After Pushing Settings")
        form_layout.addRow(self.auto_save_checkbox)

        layout.addLayout(form_layout)

    def toggle_weight_input(self):
        if self.mouse_selector.currentText() == "Manual Input":
            self.weight_input.setEnabled(True)
        else:
            self.weight_input.setEnabled(False)
            self.weight_input.clear()
            self.floor_volume.clear()
            self.ceiling_volume.clear()

    def suggest_settings(self):
        if self.mouse_selector.currentText() == "Select a mouse":
            QMessageBox.warning(self, "Selection Required", "Please select a mouse or choose 'Manual Input'.")
            return
        elif self.mouse_selector.currentText() == "Manual Input":
            weight_text = self.weight_input.text()
            if not weight_text:
                QMessageBox.warning(self, "Input Required", "Please enter the current weight.")
                return
            weight = float(weight_text)
        else:
            animal_id = self.mouse_selector.currentText().split(' - ')[0]
            animal = self.db_manager.get_animal_by_id(animal_id)
            if animal:
                weight = animal.body_weight
            else:
                QMessageBox.warning(self, "Error", "Selected animal not found.")
                return

        # Calculate suggestions based on weight
        floor = self.calculate_floor_volume(weight)
        ceiling = self.calculate_ceiling_volume(weight)

        self.floor_volume.setText(f"{floor:.2f}")
        self.ceiling_volume.setText(f"{ceiling:.2f}")

        self.push_button.setEnabled(True)
        self.print_to_terminal(f"Suggested settings based on weight {weight}g.")

    def push_settings(self):
        # Gather settings
        floor = self.floor_volume.text()
        ceiling = self.ceiling_volume.text()

        if not floor or not ceiling:
            QMessageBox.warning(self, "Incomplete Settings", "Please generate suggestions before pushing settings.")
            return

        # Implement pushing settings logic here
        # For example, updating hardware, saving to database, etc.
        self.print_to_terminal(f"Pushing settings: Floor={floor} mL, Ceiling={ceiling} mL")

        if self.auto_save_checkbox.isChecked():
            self.save_project()

        QMessageBox.information(self, "Settings Pushed", "Settings have been successfully pushed.")

    def save_project(self):
        project_name, ok = QMessageBox.getText(self, "Save Project", "Enter Project Name:")
        if ok and project_name:
            assigned_relays = {}  # Gather relay assignments as needed
            animals = []
            if self.mouse_selector.currentText() != "Manual Input":
                animal_id = self.mouse_selector.currentText().split(' - ')[0]
                animal = self.db_manager.get_animal_by_id(animal_id)
                if animal:
                    animals.append(animal)
            else:
                # Handle manual input assignment if applicable
                pass

            project = self.db_manager.create_project(project_name, animals, relay_volumes=assigned_relays)
            if project:
                self.print_to_terminal(f"Project '{project.project_name}' saved successfully.")
                QMessageBox.information(self, "Project Saved", f"Project '{project.project_name}' saved successfully.")
            else:
                self.print_to_terminal("Failed to save project.")
                QMessageBox.critical(self, "Error", "Failed to save project.")
        else:
            QMessageBox.warning(self, "Input Required", "Project name cannot be empty.")

    def calculate_floor_volume(self, weight):
        # Example calculation: 5% of body weight
        return weight * 0.05

    def calculate_ceiling_volume(self, weight):
        # Example calculation: 10% of body weight
        return weight * 0.10