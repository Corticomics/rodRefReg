# ui/relay_unit_widget.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt
from .animal_entry_widget import AnimalEntryWidget

class RelayUnitWidget(QWidget):
    def __init__(self, relay_unit):
        super().__init__()
        self.relay_unit = relay_unit
        self.assigned_animals = []
        self.desired_water_outputs = {}

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.title_label = QLabel(f"Relay Unit {relay_unit.unit_id}")
        self.layout.addWidget(self.title_label)

        self.animal_list_widget = QListWidget()
        self.animal_list_widget.setAcceptDrops(True)
        self.animal_list_widget.setDragEnabled(False)
        self.animal_list_widget.setDragDropMode(QListWidget.DropOnly)
        self.animal_list_widget.setDefaultDropAction(Qt.MoveAction)
        self.animal_list_widget.dragEnterEvent = self.drag_enter_event
        self.animal_list_widget.dropEvent = self.drop_event
        self.layout.addWidget(self.animal_list_widget)

        # Water amount input
        self.water_amount_input = QLineEdit()
        self.water_amount_input.setPlaceholderText("Total Water Amount (mL)")
        self.layout.addWidget(self.water_amount_input)

    def drag_enter_event(self, event):
        if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.acceptProposedAction()

    def drop_event(self, event):
        data = event.mimeData()
        item_data = data.data('application/x-qabstractitemmodeldatalist')
        # Process item_data to extract the animal object
        source_widget = event.source()
        if isinstance(source_widget, QListWidget):
            selected_items = source_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
                animal = item.data(Qt.UserRole)
                self.add_animal(animal)
                source_widget.takeItem(source_widget.row(item))
                event.acceptProposedAction()

    def add_animal(self, animal):
        if any(a.animal_id == animal.animal_id for a in self.assigned_animals):
            QMessageBox.warning(self, "Duplicate Animal", "This animal is already assigned to this relay unit.")
            return
        self.assigned_animals.append(animal)
        animal_entry = AnimalEntryWidget(animal)
        item = QListWidgetItem()
        item.setSizeHint(animal_entry.sizeHint())
        self.animal_list_widget.addItem(item)
        self.animal_list_widget.setItemWidget(item, animal_entry)

    def get_data(self):
        """Retrieve the current data from the widget."""
        water_amount_text = self.water_amount_input.text().strip()
        try:
            water_amount = float(water_amount_text)
        except ValueError:
            water_amount = 0.0

        desired_water_outputs = {}
        for index in range(self.animal_list_widget.count()):
            item = self.animal_list_widget.item(index)
            animal_entry = self.animal_list_widget.itemWidget(item)
            desired_output = animal_entry.get_desired_water_output()
            animal_id = animal_entry.animal.animal_id
            desired_water_outputs[animal_id] = desired_output

        return {
            'animals': self.assigned_animals,
            'water_amount': water_amount,
            'desired_water_outputs': desired_water_outputs
        }

    def set_data(self, animals, water_amount, desired_water_outputs):
        """Set the data for the relay unit."""
        self.clear_assignments()
        self.water_amount_input.setText(str(water_amount))
        for animal in animals:
            self.add_animal(animal)
        for index in range(self.animal_list_widget.count()):
            item = self.animal_list_widget.item(index)
            animal_entry = self.animal_list_widget.itemWidget(item)
            animal_id = animal_entry.animal.animal_id
            if animal_id in desired_water_outputs:
                animal_entry.set_desired_water_output(desired_water_outputs[animal_id])

    def clear_assignments(self):
        """Clear all assigned animals and reset inputs."""
        self.assigned_animals = []
        self.desired_water_outputs = {}
        self.animal_list_widget.clear()
        self.water_amount_input.clear()