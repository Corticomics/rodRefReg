# app/ui/AnimalsTab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox, QHBoxLayout, QInputDialog, QLabel
)
from PyQt5.QtCore import Qt

class AnimalsTab(QWidget):
    def __init__(self, db_manager, print_to_terminal):
        super().__init__()

        self.db_manager = db_manager
        self.print_to_terminal = print_to_terminal

        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Title
        title_label = QLabel("Manage Animals")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(title_label)

        # Table to Display Animals
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Species", "Initial Weight (g)", "Last Updated Weight (g)", "Last Watering"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.layout.addWidget(self.table)

        # Buttons for Editing
        button_layout = QHBoxLayout()

        edit_button = QPushButton("Edit Selected Animal")
        edit_button.clicked.connect(self.edit_selected_animal)
        button_layout.addWidget(edit_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_animals)
        button_layout.addWidget(refresh_button)

        add_button = QPushButton("Add New Animal")
        add_button.clicked.connect(self.add_new_animal)
        button_layout.addWidget(add_button)

        self.layout.addLayout(button_layout)

        # Load animals into the table
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

        # Prompt user to edit weight
        new_weight, ok = QInputDialog.getDouble(self, "Edit Weight", f"Enter new weight for Animal ID {animal_id}:", value=current_weight, decimals=2, min=0.1)
        if ok:
            # Update in database
            success = self.db_manager.update_animal_weight(animal_id, new_weight)
            if success:
                self.print_to_terminal(f"Updated weight for Animal ID {animal_id} to {new_weight}g.")
                QMessageBox.information(self, "Success", f"Animal ID {animal_id} weight updated to {new_weight}g.")
                self.load_animals()
            else:
                self.print_to_terminal(f"Failed to update weight for Animal ID {animal_id}.")
                QMessageBox.critical(self, "Error", f"Failed to update weight for Animal ID {animal_id}.")

    def add_new_animal(self):
        # Prompt user to enter new animal details
        dialog_layout = QVBoxLayout()

        animal_id, ok_id = QInputDialog.getText(self, "Add New Animal", "Enter Animal ID:")
        if not ok_id or not animal_id.strip():
            QMessageBox.warning(self, "Input Required", "Animal ID cannot be empty.")
            return

        species, ok_species = QInputDialog.getText(self, "Add New Animal", "Enter Species:")
        if not ok_species or not species.strip():
            QMessageBox.warning(self, "Input Required", "Species cannot be empty.")
            return

        body_weight, ok_weight = QInputDialog.getDouble(self, "Add New Animal", "Enter Initial Weight (g):", decimals=2, min=0.1)
        if not ok_weight:
            QMessageBox.warning(self, "Input Required", "Initial Weight is required.")
            return

        # Add to database
        new_animal = self.db_manager.add_animal(animal_id.strip(), species.strip(), body_weight)
        if new_animal:
            self.print_to_terminal(f"Added new animal '{new_animal.animal_id} - {new_animal.species}'.")
            QMessageBox.information(self, "Success", f"Animal '{new_animal.animal_id} - {new_animal.species}' added successfully.")
            self.load_animals()
        else:
            self.print_to_terminal(f"Failed to add animal. Animal ID '{animal_id}' may already exist.")
            QMessageBox.critical(self, "Error", f"Failed to add animal. Animal ID '{animal_id}' may already exist.")