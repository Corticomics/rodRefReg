from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QListWidget, QMessageBox, QHBoxLayout, QInputDialog, QDialog, QDialogButtonBox, QDateTimeEdit, QListWidgetItem
)
from PyQt5.QtCore import Qt, QDateTime

class EditAnimalDialog(QDialog):
    def __init__(self, animal_id, animal_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Animal: {animal_info.get('name', '')}")
        self.animal_id = animal_id
        self.animal_info = animal_info

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        form_layout = QFormLayout()

        self.name_input = QLineEdit(animal_info.get('name', ''))
        form_layout.addRow("Name:", self.name_input)

        self.initial_weight_input = QLineEdit(str(animal_info.get('initial_weight', '')))
        form_layout.addRow("Initial Weight (g):", self.initial_weight_input)

        self.last_weight_input = QLineEdit(str(animal_info.get('last_weight', '')))
        form_layout.addRow("Last Weight (g):", self.last_weight_input)

        self.last_weighted_input = QDateTimeEdit()
        self.last_weighted_input.setCalendarPopup(True)
        if animal_info.get('last_weighted'):
            dt = QDateTime.fromString(animal_info['last_weighted'], "yyyy-MM-dd HH:mm")
            self.last_weighted_input.setDateTime(dt)
        else:
            self.last_weighted_input.setDateTime(QDateTime.currentDateTime())
        form_layout.addRow("Last Time Weighted:", self.last_weighted_input)

        self.layout.addLayout(form_layout)
        
        # Save and Cancel buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.save_changes)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def save_changes(self):
        name = self.name_input.text().strip()
        try:
            initial_weight = float(self.initial_weight_input.text().strip())
            last_weight = float(self.last_weight_input.text().strip())
            last_weighted = self.last_weighted_input.dateTime().toString("yyyy-MM-dd HH:mm")

            if not name:
                raise ValueError("Name cannot be empty.")
            
            self.updated_info = {
                'name': name,
                'initial_weight': initial_weight,
                'last_weight': last_weight,
                'last_weighted': last_weighted
            }
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))


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
            display_text = f"ID: {animal['id']} | Name: {animal.get('name', '')} | Last Watered: {animal.get('last_weighted', '')} | Last Weight: {animal.get('last_weight', '')}g"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, animal['id'])
            self.animals_list.addItem(item)

    def add_animal(self):
        """Add a new animal to the database."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Animal")
        layout = QVBoxLayout()
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

                animal_data = {
                    'name': name,
                    'initial_weight': initial_weight,
                    'last_weight': last_weight,
                    'last_weighted': last_weighted
                }
                self.database_handler.add_animal(animal_data)
                self.print_to_terminal(f"Added animal '{name}'.")
                self.load_animals()
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Please enter valid numeric values for weights.")

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
        """Edit the selected animal's information."""
        selected_item = self.animals_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select an animal to edit.")
            return

        animal_id = selected_item.data(Qt.UserRole)
        animal_info = self.database_handler.get_animal(animal_id)

        dialog = EditAnimalDialog(animal_id, animal_info, self)
        if dialog.exec_() == QDialog.Accepted:
            updated_info = dialog.updated_info
            self.database_handler.update_animal(animal_id, updated_info)
            self.print_to_terminal(f"Updated animal ID {animal_id}.")
            self.load_animals()