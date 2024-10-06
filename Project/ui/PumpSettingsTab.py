from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton,
    QMessageBox
)
import logging

class PumpSettingsTab(QWidget):
    def __init__(self, pumps, pump_selected_callback, add_pump_callback):
        super().__init__()
        self.pumps = pumps
        self.pump_selected_callback = pump_selected_callback
        self.add_pump_callback = add_pump_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Pump Selection
        self.pump_combo = QComboBox()
        layout.addWidget(QLabel("Select Pump Type:"))
        layout.addWidget(self.pump_combo)

        # Pump Specifications Display
        self.specs_label = QLabel()
        layout.addWidget(self.specs_label)

        # Add Custom Pump Button
        self.add_pump_button = QPushButton("Add Custom Pump")
        self.add_pump_button.clicked.connect(self.add_pump_callback)
        layout.addWidget(self.add_pump_button)

        self.setLayout(layout)

        # Populate pump list
        self.update_pump_list()

        # Connect selection change
        self.pump_combo.currentIndexChanged.connect(self.on_pump_selected)

        # Display specs of the initially selected pump
        self.display_pump_specs()

    def update_pump_list(self):
        try:
            self.pump_combo.blockSignals(True)  # Prevent signals during update
            self.pump_combo.clear()
            for pump in self.pumps:
                self.pump_combo.addItem(pump['name'])
            self.pump_combo.blockSignals(False)
            self.display_pump_specs()
        except Exception as e:
            logging.error(f"Error updating pump list: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update pump list: {e}")

    def on_pump_selected(self, index):
        try:
            self.display_pump_specs()
            if index >= 0 and index < len(self.pumps):
                self.pump_selected_callback(self.pumps[index])
            else:
                raise IndexError("Selected pump index out of range.")
        except Exception as e:
            logging.error(f"Error selecting pump: {e}")
            QMessageBox.critical(self, "Error", f"Failed to select pump: {e}")

    def display_pump_specs(self):
        try:
            index = self.pump_combo.currentIndex()
            if index >= 0 and index < len(self.pumps):
                pump = self.pumps[index]
                specs_text = f"Volume per Trigger: {pump['volume_per_trigger']} μL"
                self.specs_label.setText(specs_text)
            else:
                self.specs_label.setText("No pump selected.")
        except Exception as e:
            logging.error(f"Error displaying pump specs: {e}")
            self.specs_label.setText("Error displaying pump specs.")
