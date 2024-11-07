# ui/edit_animal_dialog.py
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
