# ui/AddPumpDialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QLabel, QPushButton,
    QFormLayout, QMessageBox, QHBoxLayout
)
import logging

class AddPumpDialog(QDialog):
    def __init__(self, pumps):
        super().__init__()
        self.pumps = pumps
        self.pump = None  # Initialize pump to None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Add Custom Pump")
        layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.volume_input = QLineEdit()

        form_layout.addRow("Pump Name:", self.name_input)
        form_layout.addRow("Volume per Trigger (μL):", self.volume_input)
        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.save_pump)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def save_pump(self):
        try:
            name = self.name_input.text().strip()
            volume_str = self.volume_input.text().strip()
            if not name:
                raise ValueError("Pump name cannot be empty.")

            try:
                volume = float(volume_str)
                if volume <= 0:
                    raise ValueError("Volume per trigger must be positive.")
            except ValueError:
                raise ValueError("Volume per trigger must be a valid number.")

            # Check for duplicate names
            if any(pump['name'] == name for pump in self.pumps):
                raise ValueError("A pump with this name already exists.")

            self.pump = {'name': name, 'volume_per_trigger': volume}
            self.accept()
        except ValueError as ve:
            logging.error(f"Input Error: {ve}")
            QMessageBox.critical(self, "Input Error", str(ve))
        except Exception as e:
            logging.error(f"Unexpected Error: {e}")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def get_pump(self):
        return self.pump
