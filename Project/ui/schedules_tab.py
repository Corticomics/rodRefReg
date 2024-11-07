from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
                             QLineEdit, QPushButton, QMessageBox, QDialog, QFormLayout, QListWidgetItem)
from PyQt5.QtCore import Qt

class SchedulesTab(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler):
        super().__init__()

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Animal List - displays animals from the database
        self.animal_list = QListWidget()
        self.animal_list.setDragEnabled(True)
        self.layout.addWidget(QLabel("Available Animals"))
        self.layout.addWidget(self.animal_list)

        # Load animals from the database
        self.load_animals()

        # Relay containers for animals
        self.relay_layout = QHBoxLayout()
        self.relay_containers = {}
        
        # Assume we have 4 relay pairs for demonstration
        for relay_id in range(1, 5):
            container = QListWidget()
            container.setAcceptDrops(True)
            container.setDragDropMode(QListWidget.InternalMove)
            container.setObjectName(f"Relay {relay_id}")
            self.relay_containers[relay_id] = container

            relay_layout = QVBoxLayout()
            relay_layout.addWidget(QLabel(f"Relay {relay_id}"))
            relay_layout.addWidget(container)
            self.relay_layout.addLayout(relay_layout)

        self.layout.addLayout(self.relay_layout)

        # Button to finalize schedule and enter water quantities
        self.finalize_button = QPushButton("Finalize Schedule")
        self.finalize_button.clicked.connect(self.finalize_schedule)
        self.layout.addWidget(self.finalize_button)

    def load_animals(self):
        """Load animals from the database and add them to the animal list."""
        animals = self.database_handler.get_all_animals()
        for animal in animals:
            item = QListWidgetItem(f"{animal['id']} - {animal['name']}")
            item.setData(Qt.UserRole, animal)
            self.animal_list.addItem(item)

    def finalize_schedule(self):
        """Finalize schedule by prompting for water quantities per relay."""
        relay_assignments = {}

        for relay_id, container in self.relay_containers.items():
            relay_assignments[relay_id] = []
            for i in range(container.count()):
                item = container.item(i)
                animal = item.data(Qt.UserRole)
                relay_assignments[relay_id].append(animal)

        # Open water quantity dialog for each relay
        self.enter_water_quantities(relay_assignments)

    def enter_water_quantities(self, relay_assignments):
        """Open a dialog to enter water quantity per relay."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Enter Water Quantities")
        form_layout = QFormLayout(dialog)

        water_inputs = {}

        # Recommended values for water quantity
        WATER_MIN = 5  # mL
        WATER_MAX = 10  # mL

        for relay_id, animals in relay_assignments.items():
            if animals:
                input_field = QLineEdit()
                input_field.setPlaceholderText(f"Recommended: {WATER_MIN}-{WATER_MAX} mL")
                water_inputs[relay_id] = input_field
                form_layout.addRow(f"Relay {relay_id}:", input_field)

        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(lambda: self.validate_water_inputs(water_inputs, WATER_MIN, WATER_MAX, dialog))
        form_layout.addWidget(submit_button)

        dialog.setLayout(form_layout)
        dialog.exec_()

    def validate_water_inputs(self, water_inputs, min_val, max_val, dialog):
        """Validate water inputs and display warnings if out of bounds."""
        for relay_id, input_field in water_inputs.items():
            try:
                water_amount = float(input_field.text())
                if not (min_val <= water_amount <= max_val):
                    QMessageBox.warning(self, "Water Amount Warning",
                                        f"Relay {relay_id} water amount is outside recommended range ({min_val}-{max_val} mL).")
            except ValueError:
                QMessageBox.critical(self, "Invalid Input", f"Please enter a valid number for Relay {relay_id}.")
                return  # Exit if any input is invalid

        QMessageBox.information(self, "Schedule Saved", "Schedule and water quantities have been saved.")
        dialog.accept()  # Close the dialog if inputs are valid