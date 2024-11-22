# ui/animal_entry_widget.py

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit
from PyQt5.QtCore import Qt

class AnimalEntryWidget(QWidget):
    def __init__(self, animal):
        super().__init__()
        self.animal = animal
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.name_label = QLabel(f"{animal.name} ({animal.lab_animal_id})")
        self.weight_label = QLabel(f"Weight: {animal.last_weight} g")
        self.recommended_water_label = QLabel(f"Recommended: {self.calculate_recommended_water()} mL")

        self.desired_water_input = QLineEdit()
        self.desired_water_input.setPlaceholderText("Desired Water (mL)")
        self.desired_water_input.setFixedWidth(100)

        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.weight_label)
        self.layout.addWidget(self.recommended_water_label)
        self.layout.addWidget(self.desired_water_input)

    def calculate_recommended_water(self):
        """Calculate recommended water amount based on animal weight."""
        weight = self.animal.last_weight or self.animal.initial_weight or 0
        # Example formula: 10% of body weight in mL
        recommended_water = round(weight * 0.1, 2)
        return recommended_water

    def get_desired_water_output(self):
        """Get the desired water output entered by the user."""
        text = self.desired_water_input.text().strip()
        try:
            value = float(text)
        except ValueError:
            value = 0.0
        return value

    def set_desired_water_output(self, value):
        """Set the desired water output value."""
        self.desired_water_input.setText(str(value))