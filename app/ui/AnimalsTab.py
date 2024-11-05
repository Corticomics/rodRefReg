# app/ui/AnimalsTab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox, QHBoxLayout, QInputDialog
)
from PyQt5.QtCore import Qt
from .drag_drop_area import DragDropArea
from .SummaryDialog import SummaryDialog

class AnimalsTab(QWidget):
    def __init__(self, db_manager, print_to_terminal):
        super().__init__()

        self.db_manager = db_manager
        self.print_to_terminal = print_to_terminal

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Table to Display Animals
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Species", "Initial Weight (g)", "Current Weight (g)", "Last Watering"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Buttons for Editing
        button_layout = QHBoxLayout()

        self.edit_button = QPushButton("Edit Selected Animal")
        self.edit_button.clicked.connect(self.edit_selected_animal)
        button_layout.addWidget(self.edit_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_animals)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

        # Drag and Drop Area for Assigning to Relays
        self.drag_drop_area = DragDropArea(self.db_manager, self.print_to_terminal)
        layout.addWidget(self.drag_drop_area)

        self.load_animals()

    def load_animals(self):
        animals = self.db_manager.get_animals()
        self.table.setRowCount(len(animals))
        for row, animal in enumerate(animals):
            self.table.setItem(row, 0, QTableWidgetItem(animal.animal_id))
            self.table.setItem(row, 1, QTableWidgetItem(animal.species))
            self.table.setItem(row, 2, QTableWidgetItem(f"{animal.initial_weight:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{animal.body_weight:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(animal.last_watering if animal.last_watering else "Never"))
        self.table.resizeColumnsToContents()

    def edit_selected_animal(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select an animal to edit.")
            return

        row = self.table.currentRow()
        animal_id = self.table.item(row, 0).text()
        species = self.table.item(row, 1).text()
        initial_weight = float(self.table.item(row, 2).text())
        current_weight = float(self.table.item(row, 3).text())
        last_watering = self.table.item(row, 4).text()

        new_weight, ok = QInputDialog.getDouble(self, "Edit Weight", f"Enter new weight for Animal ID {animal_id}:", value=current_weight, decimals=2, min=0.1)
        if ok:
            success = self.db_manager.update_animal_weight(animal_id, new_weight)
            if success:
                self.print_to_terminal(f"Updated weight for Animal ID {animal_id} to {new_weight}g.")
                QMessageBox.information(self, "Success", f"Animal ID {animal_id} weight updated to {new_weight}g.")
                self.load_animals()
            else:
                self.print_to_terminal(f"Failed to update weight for Animal ID {animal_id}.")
                QMessageBox.critical(self, "Error", f"Failed to update weight for Animal ID {animal_id}.")