# ui/animals_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QListWidget, QMessageBox, QHBoxLayout, QDialog, QDialogButtonBox, QDateTimeEdit, QListWidgetItem
)
from PyQt5.QtCore import Qt, QDateTime
from models.animal import Animal
from .edit_animal_dialog import EditAnimalDialog
import traceback

class AnimalsTab(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler, login_system):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system  # Store login_system for permission checks

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Instruction label
        instruction_label = QLabel("Manage animal bodyweight data:")
        self.layout.addWidget(instruction_label)

        # List widget for displaying animals
        self.animals_list = QListWidget()
        self.layout.addWidget(QLabel("Animals:"))
        self.layout.addWidget(self.animals_list)

        # Button layout
        buttons_layout = QHBoxLayout()
        add_animal_button = QPushButton("Add Animal")
        remove_animal_button = QPushButton("Remove Selected Animal")
        edit_animal_button = QPushButton("Edit Selected Animal")
        buttons_layout.addWidget(add_animal_button)
        buttons_layout.addWidget(remove_animal_button)
        buttons_layout.addWidget(edit_animal_button)
        self.layout.addLayout(buttons_layout)

        # Connect button actions
        add_animal_button.clicked.connect(self.add_animal)
        remove_animal_button.clicked.connect(self.remove_animal)
        edit_animal_button.clicked.connect(self.edit_animal)

        # Load existing animals into the list
        self.load_animals()

    def load_animals(self):
        """Load animals from the database, filtered by trainer_id if available."""
        try:
            current_trainer = self.login_system.get_current_trainer()
            if current_trainer:
                trainer_id = current_trainer['trainer_id']
                role = current_trainer['role']
                animals = self.database_handler.get_animals(trainer_id, role)
                self.print_to_terminal(f"Loaded {len(animals)} animals for trainer ID {trainer_id}")
            else:
                animals = self.database_handler.get_all_animals()
                self.print_to_terminal(f"Loaded {len(animals)} animals for all trainers (guest mode)")
            # Populate the UI with the animals list
            self.populate_animal_list(animals)
        except Exception as e:
            print(f"Exception in AnimalsTab.load_animals: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Load Animals Error", f"An error occurred while loading animals:\n{e}")

    def populate_animal_list(self, animals):
        """Populate the animals_list widget with the given animals."""
        self.animals_list.clear()
        for animal in animals:
            display_text = f"{animal.lab_animal_id} - {animal.name} - Last Watering: {animal.last_watering or 'N/A'}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, animal)
            self.animals_list.addItem(item)

    def add_animal(self):
        """Open dialog to add a new animal with error handling."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Animal")
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        lab_animal_id_input = QLineEdit()
        name_input = QLineEdit()
        initial_weight_input = QLineEdit()
        last_weight_input = QLineEdit()
        last_weighted_input = QDateTimeEdit()
        last_weighted_input.setCalendarPopup(True)
        last_weighted_input.setDateTime(QDateTime.currentDateTime())
        last_watering_input = QDateTimeEdit()
        last_watering_input.setCalendarPopup(True)
        last_watering_input.setDateTime(QDateTime.currentDateTime())

        form_layout.addRow("Lab Animal ID:", lab_animal_id_input)
        form_layout.addRow("Name:", name_input)
        form_layout.addRow("Initial Weight (g):", initial_weight_input)
        form_layout.addRow("Last Weight (g):", last_weight_input)
        form_layout.addRow("Last Time Weighted:", last_weighted_input)
        form_layout.addRow("Last Watering:", last_watering_input)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            try:
                lab_animal_id = lab_animal_id_input.text().strip()
                name = name_input.text().strip()
                initial_weight = float(initial_weight_input.text().strip())
                last_weight = float(last_weight_input.text().strip())
                last_weighted = last_weighted_input.dateTime().toString("yyyy-MM-dd HH:mm")
                last_watering = last_watering_input.dateTime().toString("yyyy-MM-dd HH:mm")

                if not lab_animal_id or not name:
                    raise ValueError("Animal ID and name cannot be empty.")

                new_animal = Animal(
                    None,
                    lab_animal_id,
                    name,
                    initial_weight,
                    last_weight,
                    last_weighted,
                    last_watering
                )
                current_trainer = self.login_system.get_current_trainer()
                trainer_id = current_trainer['trainer_id'] if current_trainer else None

                animal_id = self.database_handler.add_animal(new_animal, trainer_id=trainer_id)

                if animal_id:
                    self.print_to_terminal(f"Animal '{name}' added with ID: {lab_animal_id}.")
                    self.load_animals()
                else:
                    QMessageBox.warning(self, "Add Error", "Failed to add animal. ID might already exist.")

            except ValueError as ve:
                QMessageBox.warning(self, "Input Error", f"Invalid input: {ve}")
                self.print_to_terminal(f"Input Error: {ve}")
            except Exception as e:
                QMessageBox.critical(self, "Add Error", f"Unexpected error: {e}")
                self.print_to_terminal(f"Unexpected error during add operation: {e}")

        if dialog.exec_() == QDialog.Accepted:
            try:
                lab_animal_id = lab_animal_id_input.text().strip()
                name = name_input.text().strip()
                initial_weight = float(initial_weight_input.text().strip())
                last_weight = float(last_weight_input.text().strip())
                last_weighted = last_weighted_input.dateTime().toString("yyyy-MM-dd HH:mm")

                if not lab_animal_id or not name:
                    raise ValueError("Animal ID and name cannot be empty.")
                
                new_animal = Animal(None, lab_animal_id, name, initial_weight, last_weight, last_weighted)
                animal_id = self.database_handler.add_animal(new_animal, trainer_id=self.trainer_id)  # Assuming `trainer_id` can be None for now
                
                if animal_id:
                    self.print_to_terminal(f"Animal '{name}' added with ID: {lab_animal_id}.")
                    self.load_animals()
                else:
                    QMessageBox.warning(self, "Add Error", "Failed to add animal. ID might already exist.")

            except ValueError as ve:
                QMessageBox.warning(self, "Input Error", f"Invalid input: {ve}")
                self.print_to_terminal(f"Input Error: {ve}")
            except Exception as e:
                QMessageBox.critical(self, "Add Error", f"Unexpected error: {e}")
                self.print_to_terminal(f"Unexpected error during add operation: {e}")

    def remove_animal(self):
        """Remove selected animal from the database with error handling."""
        selected_item = self.animals_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select an animal to remove.")
            return

        animal = selected_item.data(Qt.UserRole)
        confirm = QMessageBox.question(self, "Confirm Removal", f"Are you sure you want to remove '{animal.name}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                self.database_handler.remove_animal(animal.lab_animal_id)
                self.print_to_terminal(f"Removed animal '{animal.name}' with Lab ID {animal.lab_animal_id}.")
                self.load_animals()
            except Exception as e:
                QMessageBox.critical(self, "Remove Error", f"Error removing animal: {e}")
                self.print_to_terminal(f"Error removing animal '{animal.lab_animal_id}': {e}")

    def edit_animal(self):
        """Open dialog to edit the selected animal's information with error handling."""
        selected_item = self.animals_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select an animal to edit.")
            return

        # Retrieve the animal instance from the selected item
        animal = selected_item.data(Qt.UserRole)

        # Pass `lab_animal_id` and other details to the EditAnimalDialog
        dialog = EditAnimalDialog(animal.animal_id, animal.to_dict(), self)

        try:
            if dialog.exec_() == QDialog.Accepted:
                updated_info = dialog.updated_info
                updated_animal = Animal(
                    animal_id=animal.animal_id,
                    lab_animal_id=animal.lab_animal_id,
                    name=updated_info['name'],
                    initial_weight=updated_info['initial_weight'],
                    last_weight=updated_info['last_weight'],
                    last_weighted=updated_info['last_weighted'],
                    last_watering=updated_info['last_watering']
                )

                # Update the animal in the database
                self.database_handler.update_animal(updated_animal)

                # Notify and refresh
                self.print_to_terminal(f"Updated animal '{updated_animal.name}' (Lab ID: {updated_animal.lab_animal_id}).")
                self.load_animals()
        except Exception as e:
            QMessageBox.critical(self, "Edit Error", f"Error updating animal: {e}")
            self.print_to_terminal(f"Unhandled exception in edit_animal: {e}")