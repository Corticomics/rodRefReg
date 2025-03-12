# ui/edit_animal_dialog.py

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDateTimeEdit, QDialogButtonBox, QMessageBox, QComboBox
from PyQt5.QtCore import QDateTime
from datetime import datetime

class EditAnimalDialog(QDialog):
    def __init__(self, animal_id, animal_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Animal")

        self.animal_id = animal_id
        self.animal_data = animal_data
        self.updated_info = {}

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Add gender selection
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Select Gender", "male", "female"])
        current_gender = animal_data.get('gender', "Select Gender")
        self.gender_combo.setCurrentText(current_gender if current_gender else "Select Gender")

        self.name_input = QLineEdit(animal_data['name'])
        self.initial_weight_input = QLineEdit(str(animal_data['initial_weight']))
        self.last_weight_input = QLineEdit(str(animal_data['last_weight']) if animal_data['last_weight'] is not None else "")
        self.last_weighted_input = QDateTimeEdit()
        self.last_weighted_input.setCalendarPopup(True)
        if animal_data['last_weighted']:
            try:
                dt = datetime.fromisoformat(animal_data['last_weighted'])
                self.last_weighted_input.setDateTime(QDateTime(dt))
            except ValueError:
                self.last_weighted_input.setDateTime(QDateTime.currentDateTime())
        else:
            self.last_weighted_input.setDateTime(QDateTime.currentDateTime())

        self.last_watering_input = QDateTimeEdit()
        self.last_watering_input.setCalendarPopup(True)
        if animal_data.get('last_watering'):
            try:
                dt = datetime.fromisoformat(animal_data['last_watering'])
                self.last_watering_input.setDateTime(QDateTime(dt))
            except ValueError:
                self.last_watering_input.setDateTime(QDateTime.currentDateTime())
        else:
            self.last_watering_input.setDateTime(QDateTime.currentDateTime())

        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Gender:", self.gender_combo)
        form_layout.addRow("Initial Weight (g):", self.initial_weight_input)
        form_layout.addRow("Last Weight (g):", self.last_weight_input)
        form_layout.addRow("Last Time Weighted:", self.last_weighted_input)
        form_layout.addRow("Last Watering:", self.last_watering_input)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def accept(self):
        try:
            gender = self.gender_combo.currentText()
            if gender == "Select Gender":
                gender = None

            self.updated_info = {
                'name': self.name_input.text().strip(),
                'gender': gender,
                'initial_weight': float(self.initial_weight_input.text().strip()),
                'last_weight': float(self.last_weight_input.text().strip()) if self.last_weight_input.text().strip() else None,
                'last_weighted': self.last_weighted_input.dateTime().toString("yyyy-MM-ddTHH:mm:ss.zzz"),
                'last_watering': self.last_watering_input.dateTime().toString("yyyy-MM-ddTHH:mm:ss.zzz")
            }
            super().accept()
        except ValueError as ve:
            QMessageBox.warning(self, "Input Error", f"Invalid input: {ve}")