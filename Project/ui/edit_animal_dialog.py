from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDateTimeEdit, QDialogButtonBox, QMessageBox
from PyQt5.QtCore import QDateTime

class EditAnimalDialog(QDialog):
    def __init__(self, animal_id, animal_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Animal")

        self.animal_id = animal_id
        self.animal_data = animal_data
        self.updated_info = {}

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.name_input = QLineEdit(animal_data['name'])
        self.initial_weight_input = QLineEdit(str(animal_data['initial_weight']))
        self.last_weight_input = QLineEdit(str(animal_data['last_weight']))
        self.last_weighted_input = QDateTimeEdit()
        self.last_weighted_input.setCalendarPopup(True)
        self.last_weighted_input.setDateTime(
            QDateTime.fromString(animal_data['last_weighted'], "yyyy-MM-dd HH:mm")
        )

        self.last_watering_input = QDateTimeEdit()
        self.last_watering_input.setCalendarPopup(True)
        if animal_data.get('last_watering'):
            self.last_watering_input.setDateTime(
                QDateTime.fromString(animal_data['last_watering'], "yyyy-MM-dd HH:mm")
            )
        else:
            self.last_watering_input.setDateTime(QDateTime.currentDateTime())

        form_layout.addRow("Name:", self.name_input)
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
            self.updated_info = {
                'name': self.name_input.text().strip(),
                'initial_weight': float(self.initial_weight_input.text().strip()),
                'last_weight': float(self.last_weight_input.text().strip()),
                'last_weighted': self.last_weighted_input.dateTime().toString("yyyy-MM-dd HH:mm"),
                'last_watering': self.last_watering_input.dateTime().toString("yyyy-MM-dd HH:mm")
            }
            super().accept()
        except ValueError as ve:
            QMessageBox.warning(self, "Input Error", f"Invalid input: {ve}")