# ui/relay_unit_widget.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QLineEdit,
    QMessageBox, QListWidget
)
from PyQt5.QtCore import Qt, QDataStream, QIODevice
from models.animal import Animal
from .available_animals_list import AvailableAnimalsList

class RelayUnitWidget(QWidget):
    def __init__(self, relay_unit):
        super().__init__()
        self.relay_unit = relay_unit
        self.assigned_animals = []
        self.desired_water_output = {}  # {animal_id: desired_output}

        # Main layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Title Label
        self.title_label = QLabel(f"Relay Unit {relay_unit.unit_id}")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

        # Minimalistic Drag-and-Drop Area
        self.drag_area_label = QLabel("Drop Animal Here")
        self.drag_area_label.setAlignment(Qt.AlignCenter)
        self.drag_area_label.setStyleSheet("background-color: #e0e0e0; border: 1px dashed #000;")
        self.drag_area_label.setFixedHeight(30)
        self.layout.addWidget(self.drag_area_label)

        # Set up drag-and-drop
        self.setAcceptDrops(True)

        # Animal Information Table
        self.animal_table = QTableWidget()
        self.animal_table.setColumnCount(4)
        self.animal_table.setHorizontalHeaderLabels(["Lab ID", "Name", "Last Weight", "Last Watering"])
        self.animal_table.horizontalHeader().setStretchLastSection(True)
        self.animal_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.animal_table.setSelectionMode(QTableWidget.NoSelection)
        self.animal_table.verticalHeader().setVisible(False)
        self.animal_table.setFixedHeight(60)
        self.layout.addWidget(self.animal_table)

        # Water Volume Display
        self.recommended_water_label = QLabel("Recommended water volume: N/A")
        self.layout.addWidget(self.recommended_water_label)

        self.desired_output_label = QLabel("Desired output by trainer:")
        self.desired_output_input = QLineEdit()
        self.layout.addWidget(self.desired_output_label)
        self.layout.addWidget(self.desired_output_input)

        # Connect the cellClicked signal
        self.animal_table.cellClicked.connect(self.remove_animal)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        source_widget = event.source()
        if isinstance(source_widget, AvailableAnimalsList):  # Ensure source is the custom list
            mime = event.mimeData()
            if mime.hasFormat('application/x-animal-id'):
                data = mime.data('application/x-animal-id')
                stream = QDataStream(data, QIODevice.ReadOnly)
                animal_id = stream.readInt32()

                # Retrieve the animal from the database
                animal = self.database_handler.get_animal_by_id(animal_id)
                if animal:
                    self.add_animal(animal)

                    # Remove the animal from the source widget
                    for i in range(source_widget.count()):
                        item = source_widget.item(i)
                        if item.data(Qt.UserRole).animal_id == animal_id:
                            source_widget.takeItem(i)
                            break
                else:
                    QMessageBox.warning(self, "Drag Error", "Failed to retrieve animal data.")
        event.acceptProposedAction()

    def add_animal(self, animal):
        # Prevent multiple animals if only one is allowed
        if len(self.assigned_animals) >= 1:
            QMessageBox.warning(self, "Limit Reached", "Only one animal can be assigned to this relay unit.")
            return

        self.assigned_animals.append(animal)
        # Update the table
        self.animal_table.setRowCount(1)
        self.animal_table.setItem(0, 0, QTableWidgetItem(animal.lab_animal_id))
        self.animal_table.setItem(0, 1, QTableWidgetItem(animal.name))
        last_weight = str(animal.last_weight or animal.initial_weight or 'N/A')
        self.animal_table.setItem(0, 2, QTableWidgetItem(last_weight))

        # Retrieve last_watering information
        last_watering = animal.last_watering or 'N/A'
        self.animal_table.setItem(0, 3, QTableWidgetItem(last_watering))

        info = f"Weight: {animal.last_weight or animal.initial_weight} g"
        self.animal_table.setItem(0, 1, QTableWidgetItem(info))

        # Update recommended water volume
        recommended_volume = self.calculate_recommended_water(animal)
        self.recommended_water_label.setText(f"Recommended water volume: {recommended_volume} mL")
        # Hide Placeholder
        self.drag_area_label.hide()

    def calculate_recommended_water(self, animal):
        weight = animal.last_weight or animal.initial_weight or 0
        recommended_water = round(weight * 0.1, 2)  # Example: 10% of body weight
        return recommended_water

    def get_data(self):
        """Retrieve the current data from the widget."""
        desired_output_text = self.desired_output_input.text().strip()
        try:
            desired_output = float(desired_output_text)
        except ValueError:
            desired_output = 0.0

        desired_water_output = {}
        if self.assigned_animals:
            animal = self.assigned_animals[0]
            desired_water_output[animal.animal_id] = desired_output

        return {
            'animals': self.assigned_animals,
            'desired_water_output': desired_water_output
        }

    def set_data(self, animals, desired_water_output):
        """Set the data for the relay unit."""
        self.clear_assignments()
        if animals:
            self.add_animal(animals[0])  # Assuming only one animal per relay unit
            animal_id = animals[0].animal_id
            if animal_id in desired_water_output:
                self.desired_output_input.setText(str(desired_water_output[animal_id]))

    def clear_assignments(self):
        """Clear all assigned animals and reset inputs."""
        self.assigned_animals = []
        self.desired_water_output = {}
        self.animal_table.setRowCount(0)
        self.desired_output_input.clear()
        self.recommended_water_label.setText("Recommended water volume: N/A")
        self.drag_area_label.show()
                                             
    def remove_animal(self, row, column):
        reply = QMessageBox.question(
            self,
            'Remove Animal',
            'Are you sure you want to remove this animal?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.clear_assignments()
            # Show the placeholder again
            self.drag_area_label.show()