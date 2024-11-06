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

        self.name_input = QLineEdit()
        self.name_input.setText(animal_info.get('name', ''))
        form_layout.addRow("Name:", self.name_input)

        self.initial_weight_input = QLineEdit()
        self.initial_weight_input.setText(str(animal_info.get('initial_weight', '')))
        self.initial_weight_input.setPlaceholderText("Enter initial weight in grams (e.g., 25.5)")
        form_layout.addRow("Initial Weight (g):", self.initial_weight_input)

        self.last_weight_input = QLineEdit()
        self.last_weight_input.setText(str(animal_info.get('last_weight', '')))
        self.last_weight_input.setPlaceholderText("Enter last weight in grams (e.g., 30.2)")
        form_layout.addRow("Last Weight (g):", self.last_weight_input)

        self.last_weighted_input = QDateTimeEdit()
        self.last_weighted_input.setCalendarPopup(True)
        if animal_info.get('last_weighted'):
            dt = QDateTime.fromString(animal_info.get('last_weighted'), "yyyy-MM-dd HH:mm")
            self.last_weighted_input.setDateTime(dt)
        else:
            self.last_weighted_input.setDateTime(QDateTime.currentDateTime())
        self.last_weighted_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        form_layout.addRow("Last Time Weighted:", self.last_weighted_input)

        self.layout.addLayout(form_layout)

        # Dialog Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.save_changes)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def save_changes(self):
        name = self.name_input.text().strip()
        initial_weight = self.initial_weight_input.text().strip()
        last_weight = self.last_weight_input.text().strip()
        last_weighted = self.last_weighted_input.dateTime().toString("yyyy-MM-dd HH:mm")

        if not name:
            QMessageBox.warning(self, "Input Error", "Name cannot be empty.")
            return
        try:
            initial_weight = float(initial_weight)
            last_weight = float(last_weight)
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Weights must be numeric (e.g., 25.5).")
            return
        if not last_weighted:
            QMessageBox.warning(self, "Input Error", "Last Time Weighted cannot be empty.")
            return

        self.updated_info = {
            'name': name,
            'initial_weight': initial_weight,
            'last_weight': last_weight,
            'last_weighted': last_weighted
        }
        self.accept()

class AnimalsTab(QWidget):
    def __init__(self, settings, print_to_terminal):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Instruction Label
        instruction_label = QLabel("Manage animal bodyweight data:")
        self.layout.addWidget(instruction_label)

        # Animal List
        self.animals_list = QListWidget()
        self.animals_list.setSelectionMode(QListWidget.SingleSelection)
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

        # Load existing animals
        self.load_animals()

    def add_animal(self):
        """Add a new animal to the database."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Add New Animal")
            layout = QVBoxLayout()
            form_layout = QFormLayout()

            name_input = QLineEdit()
            initial_weight_input = QLineEdit()
            initial_weight_input.setPlaceholderText("Enter initial weight in grams (e.g., 25.5)")
            last_weight_input = QLineEdit()
            last_weight_input.setPlaceholderText("Enter last weight in grams (e.g., 30.2)")
            last_weighted_input = QDateTimeEdit()
            last_weighted_input.setCalendarPopup(True)
            last_weighted_input.setDateTime(QDateTime.currentDateTime())
            last_weighted_input.setDisplayFormat("yyyy-MM-dd HH:mm")

            form_layout.addRow("Name:", name_input)
            form_layout.addRow("Initial Weight (g):", initial_weight_input)
            form_layout.addRow("Last Weight (g):", last_weight_input)
            form_layout.addRow("Last Time Weighted:", last_weighted_input)

            layout.addLayout(form_layout)

            # Dialog Buttons
            buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            dialog.setLayout(layout)

            if dialog.exec_() == QDialog.Accepted:
                name = name_input.text().strip()
                initial_weight = initial_weight_input.text().strip()
                last_weight = last_weight_input.text().strip()
                last_weighted = last_weighted_input.dateTime().toString("yyyy-MM-dd HH:mm")

                if not name:
                    QMessageBox.warning(self, "Input Error", "Name cannot be empty.")
                    return
                try:
                    initial_weight = float(initial_weight)
                    last_weight = float(last_weight)
                except ValueError:
                    QMessageBox.warning(self, "Input Error", "Weights must be numeric (e.g., 25.5).")
                    return
                if not last_weighted:
                    QMessageBox.warning(self, "Input Error", "Last Time Weighted cannot be empty.")
                    return

                # Generate a unique animal ID
                animal_id = max([int(k) for k in self.settings.get('animals', {}).keys()], default=0) + 1

                # Add to settings
                if 'animals' not in self.settings:
                    self.settings['animals'] = {}
                self.settings['animals'][str(animal_id)] = {
                    'name': name,
                    'initial_weight': initial_weight,
                    'last_weight': last_weight,
                    'last_weighted': last_weighted
                }
                self.print_to_terminal(f"Added animal '{name}' with ID {animal_id}.")
                self.save_animals()
                self.load_animals()
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
        animal_name = selected_item.text().split('|')[1].strip()

        confirm = QMessageBox.question(
            self, "Confirm Removal",
            f"Are you sure you want to remove animal '{animal_name}' (ID: {animal_id})?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            del self.settings['animals'][str(animal_id)]
            self.print_to_terminal(f"Removed animal '{animal_name}' (ID: {animal_id}).")
            self.save_animals()
            self.load_animals()

    def edit_animal(self):
        """Edit the selected animal's information."""
        selected_item = self.animals_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select an animal to edit.")
            return

        animal_id = selected_item.data(Qt.UserRole)
        animal_info = self.settings['animals'][str(animal_id)]

        dialog = EditAnimalDialog(animal_id, animal_info, self)
        if dialog.exec_() == QDialog.Accepted:
            updated_info = dialog.updated_info
            self.settings['animals'][str(animal_id)] = updated_info
            self.print_to_terminal(f"Updated animal '{updated_info['name']}' (ID: {animal_id}).")
            self.save_animals()
            self.load_animals()

    def load_animals(self):
        """Load animals from the settings into the list widget."""
        self.animals_list.clear()
        animals = self.settings.get('animals', {})
        for animal_id, info in animals.items():
            display_text = f"ID: {animal_id} | Name: {info.get('name', '')} | Last Watered: {info.get('last_weighted', '')} | Last Weight: {info.get('last_weight', '')}g"
            item = QListWidgetItem(display_text)  # Corrected line
            item.setData(Qt.UserRole, animal_id)
            self.animals_list.addItem(item)

    def save_animals(self):
        """Save the animal data to the settings.json file."""
        try:
            from settings.config import save_settings
            save_settings(self.settings)
            self.print_to_terminal("Animal data saved successfully.")
        except Exception as e:
            self.print_to_terminal(f"Error saving animal data: {e}")