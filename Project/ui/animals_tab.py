#ui/animals_tab.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QListWidget, QMessageBox, QHBoxLayout, QDateTimeEdit, QListWidgetItem, QDialog
)
from PyQt5.QtCore import Qt, QDateTime
from models.animal import Animal
from edit_animal_dialog import EditAnimalDialog

class AnimalsTab(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Instruction Label
        instruction_label = QLabel("Manage animal bodyweight data:")
        self.layout.addWidget(instruction_label)

        # Animal List
        self.animals_list = QListWidget()
        self.layout.addWidget(QLabel("Animals:"))
        self.layout.addWidget(self.animals_list)

        # Buttons
        buttons_layout = QHBoxLayout()
        add_animal_button = QPushButton("Add Animal")
        remove_animal_button = QPushButton("Remove Selected Animal")
        edit_animal_button = QPushButton("Edit Selected Animal")
        buttons_layout.addWidget(add_animal_button)
        buttons_layout.addWidget(remove_animal_button)
        buttons_layout.addWidget(edit_animal_button)
        self.layout.addLayout(buttons_layout)

        # Connect Buttons
        add_animal_button.clicked.connect(self.add_animal)
        remove_animal_button.clicked.connect(self.remove_animal)
        edit_animal_button.clicked.connect(self.edit_animal)

        # Load existing animals from the database
        self.load_animals()

    def load_animals(self):
        """Load animals from the database into the list widget."""
        self.animals_list.clear()
        animals = self.database_handler.get_all_animals()
        for animal in animals:
            display_text = f"ID: {animal.animal_id} | Name: {animal.name} | Last Weight: {animal.last_weight}g"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, animal.animal_id)
            self.animals_list.addItem(item)

    def add_animal(self):
        """Add a new animal to the database."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Animal")
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        name_input = QLineEdit()
        initial_weight_input = QLineEdit()
        last_weight_input = QLineEdit()
        last_weighted_input = QDateTimeEdit()
        last_weighted_input.setCalendarPopup(True)
        last_weighted_input.setDateTime(QDateTime.currentDateTime())

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
                name = name_input.text().strip()
                initial_weight = float(initial_weight_input.text().strip())
                last_weight = float(last_weight_input.text().strip())
                last_weighted = last_weighted_input.dateTime().toString("yyyy-MM-dd HH:mm")

                new_animal = Animal(None, name, initial_weight, last_weight, last_weighted)
                animal_id = self.database_handler.add_animal(new_animal)
                
                if animal_id:
                    self.print_to_terminal(f"Added animal '{name}' with ID {animal_id}.")
                    self.load_animals()
                else:
                    QMessageBox.critical(self, "Database Error", "Failed to add animal to the database.")

            except ValueError:
                QMessageBox.warning(self, "Input Error", "Please enter valid numeric values for weights.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
                self.print_to_terminal(f"Unhandled exception in add_animal: {e}")

    def remove_animal(self):
        """Remove the selected animal from the database."""
        selected_item = self.animals_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select an animal to remove.")
            return

        animal_id = selected_item.data(Qt.UserRole)
        confirm = QMessageBox.question(
            self, "Confirm Removal",
            f"Are you sure you want to remove animal ID {animal_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.database_handler.remove_animal(animal_id)
            self.print_to_terminal(f"Removed animal ID {animal_id}.")
            self.load_animals()


    def edit_animal(self):
        """Open dialogg to edit the selected animal's information"""
        selected_item = self.animals_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select an animal to edit.")
            return
        
        animal = selected_item.data(Qt.UserRole)
        dialog = EditAnimalDialog(animal.animal_id, animal.to_dict(), self)
        try:
            if dialog.exec_() == QDialog.Accepted:
                updated_info = dialog.updated_info
                updated_animal = Animal(
                    animal_id=animal.animal_id,
                    name=updated_info['name'],
                    initial_weight=updated_info['initial_weight'],
                    last_weight=updated_info['last_weight'],
                    last_weighted=updated_info['last_weighted']
                )
                self.database_handler.update_animal(updated_animal)
                self.print_to_terminal(f"Updated animal '{updated_animal.name}' (ID: {updated_animal.animal_id}).")
                self.load_animals()
        except Exception as e:
            print(f"Unhandled exception in edit_animal: {e}")

