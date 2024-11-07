from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QListWidget, QMessageBox, QHBoxLayout, QInputDialog, QDialog, QDialogButtonBox, QDateTimeEdit, QListWidgetItem
)
from PyQt5.QtCore import Qt, QDateTime
from models.animal import Animal
from .edit_animal_dialog import EditAnimalDialog

class AnimalsTab(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        instruction_label = QLabel("Manage animal bodyweight data:")
        self.layout.addWidget(instruction_label)

        self.animals_list = QListWidget()
        self.layout.addWidget(QLabel("Animals:"))
        self.layout.addWidget(self.animals_list)

        buttons_layout = QHBoxLayout()
        add_animal_button = QPushButton("Add Animal")
        remove_animal_button = QPushButton("Remove Selected Animal")
        edit_animal_button = QPushButton("Edit Selected Animal")
        buttons_layout.addWidget(add_animal_button)
        buttons_layout.addWidget(remove_animal_button)
        buttons_layout.addWidget(edit_animal_button)
        self.layout.addLayout(buttons_layout)

        add_animal_button.clicked.connect(self.add_animal)
        remove_animal_button.clicked.connect(self.remove_animal)
        edit_animal_button.clicked.connect(self.edit_animal)

        self.load_animals()

    def load_animals(self):
        """Load animals from the database into the list widget."""
        self.animals_list.clear()
        animals = self.database_handler.get_all_animals()
        for animal in animals:
            item_text = f"Lab ID: {animal.lab_animal_id} | Name: {animal.name} | Last Weight: {animal.last_weight}g"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, animal)
            self.animals_list.addItem(item)

    def add_animal(self):
        """Open dialog to add a new animal, including lab_animal_id."""
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

        form_layout.addRow("Lab Animal ID:", lab_animal_id_input)
        form_layout.addRow("Name:", name_input)
        form_layout.addRow("Initial Weight (g):", initial_weight_input)
        form_layout.addRow("Last Weight (g):", last_weight_input)
        form_layout.addRow("Last Time Weighted:", last_weighted_input)
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

                if not lab_animal_id or not name:
                    raise ValueError("Animal ID and name cannot be empty.")
                
                new_animal = Animal(None, lab_animal_id, name, initial_weight, last_weight, last_weighted)
                animal_id = self.database_handler.add_animal(new_animal)
                
                if animal_id:
                    self.print_to_terminal(f"Animal '{name}' added with ID: {lab_animal_id}.")
                    self.load_animals()
                else:
                    QMessageBox.warning(self, "Error", "Failed to add animal. ID might already exist.")

            except ValueError as ve:
                QMessageBox.warning(self, "Input Error", f"Invalid input: {ve}")

    def remove_animal(self):
        """Remove selected animal from the database."""
        selected_item = self.animals_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select an animal to remove.")
            return

        animal = selected_item.data(Qt.UserRole)
        confirm = QMessageBox.question(self, "Confirm Removal", f"Are you sure you want to remove '{animal.name}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.database_handler.remove_animal(animal.lab_animal_id)
            self.print_to_terminal(f"Removed animal '{animal.name}' with Lab ID {animal.lab_animal_id}.")
            self.load_animals()


    def edit_animal(self):
        """Open dialog to edit the selected animal's information"""
        selected_item = self.animals_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select an animal to edit.")
            return
        
        # Retrieve the animal instance from the selected item
        animal = selected_item.data(Qt.UserRole)
        
        # Pass `lab_animal_id` and other details to the EditAnimalDialog
        dialog = EditAnimalDialog(animal.lab_animal_id, animal.to_dict(), self)
        
        try:
            if dialog.exec_() == QDialog.Accepted:
                updated_info = dialog.updated_info
                updated_animal = Animal(
                    lab_animal_id=animal.lab_animal_id,  # Use the user-defined lab animal ID
                    name=updated_info['name'],
                    initial_weight=updated_info['initial_weight'],
                    last_weight=updated_info['last_weight'],
                    last_weighted=updated_info['last_weighted']
                )
                
                # Update the animal in the database using the new lab_animal_id-based structure
                self.database_handler.update_animal(updated_animal)
                
                # Notify the terminal and refresh the animal list
                self.print_to_terminal(f"Updated animal '{updated_animal.name}' (Lab ID: {updated_animal.lab_animal_id}).")
                self.load_animals()
        except Exception as e:
            print(f"Unhandled exception in edit_animal: {e}")
