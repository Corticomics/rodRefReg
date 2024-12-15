# ui/relay_unit_widget.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QMessageBox, QLineEdit, QHBoxLayout, QPushButton, QDateTimeEdit,
    QScrollArea, QComboBox
)
from PyQt5.QtCore import Qt, QDataStream, QIODevice, QDateTime, pyqtSignal
from models.animal import Animal
from .available_animals_list import AvailableAnimalsList
from datetime import datetime

class WaterDeliverySlot(QWidget):
    # Signal emitted when the slot is about to be deleted
    slot_deleted = pyqtSignal(QWidget)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        
        # DateTime picker with calendar popup
        self.datetime_picker = QDateTimeEdit()
        self.datetime_picker.setCalendarPopup(True)
        self.datetime_picker.setDateTime(QDateTime.currentDateTime())
        self.datetime_picker.setMinimumDateTime(QDateTime.currentDateTime())
        self.datetime_picker.setDisplayFormat("yyyy-MM-dd hh:mm AP")
        
        # Volume input
        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("Water volume (mL)")
        self.volume_input.setFixedWidth(100)
        
        # Delete button
        self.delete_button = QPushButton("×")
        self.delete_button.setMaximumWidth(30)
        self.delete_button.clicked.connect(self.handle_delete)
        
        layout.addWidget(self.datetime_picker)
        layout.addWidget(self.volume_input)
        layout.addWidget(self.delete_button)
        self.setLayout(layout)

    def handle_delete(self):
        """Handle the deletion of the slot."""
        # Emit the signal before deletion
        self.slot_deleted.emit(self)
        self.deleteLater()

class RelayUnitWidget(QWidget):
    def __init__(self, relay_unit, database_handler, available_animals_list, pump_controller):
        """
        Initialize the RelayUnitWidget.

        Args:
            relay_unit (RelayUnit): The relay unit instance.
            database_handler (DatabaseHandler): Handler for database interactions.
            available_animals_list (AvailableAnimalsList): Reference to the AvailableAnimalsList widget.
            pump_controller (PumpController): Reference to the PumpController instance.
        """
        super().__init__()
        self.relay_unit = relay_unit
        self.database_handler = database_handler
        self.available_animals_list = available_animals_list
        self.assigned_animal = None  # Only one animal per relay unit
        self.desired_water_output = 0.0  # Desired water output for the animal
        self.pump_controller = pump_controller
        self.current_mode = "Staggered"  # Track mode internally

        # Main layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Title Label
        self.title_label = QLabel(f"Relay Unit {relay_unit.unit_id}")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

        # Drag-and-Drop Area
        self.drag_area_label = QLabel("Drop Animal Here")
        self.drag_area_label.setAlignment(Qt.AlignCenter)
        self.drag_area_label.setStyleSheet("""
            background-color: #f8f9fa; 
            border: 2px dashed #e0e0e0; 
            font-size: 14px;
        """)
        self.drag_area_label.setFixedHeight(50)
        self.layout.addWidget(self.drag_area_label)

        # Enable drag-and-drop
        self.setAcceptDrops(True)

        # Animal Information Table
        self.animal_table = QTableWidget()
        self.animal_table.setColumnCount(4)
        self.animal_table.setHorizontalHeaderLabels(["Lab ID", "Name", "Last Weight", "Last Watering"])
        self.animal_table.horizontalHeader().setStretchLastSection(True)
        self.animal_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.animal_table.setSelectionMode(QTableWidget.NoSelection)
        self.animal_table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.animal_table)

        # Water Volume Display
        self.recommended_water_label = QLabel("Recommended water volume: N/A")
        self.layout.addWidget(self.recommended_water_label)

        # **Desired Water Output Input**
        # Create a horizontal layout for the label and input box
        desired_output_layout = QHBoxLayout()

        # Label for Desired Water Output
        self.desired_output_label = QLabel("Water Output (mL):")
        self.desired_output_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.desired_output_label.setFixedWidth(150)  # Optional: Set a fixed width for better alignment

        # Input box for Desired Water Output
        self.desired_output_input = QLineEdit()
        self.desired_output_input.setPlaceholderText("Enter desired water volume")
        self.desired_output_input.setFixedWidth(200)  # Set a fixed width as desired

        # Add widgets to the horizontal layout
        desired_output_layout.addWidget(self.desired_output_label)
        desired_output_layout.addWidget(self.desired_output_input)
        desired_output_layout.addStretch()  # Pushes the widgets to the left

        # Add the horizontal layout to the main vertical layout
        self.layout.addLayout(desired_output_layout)

        # Connect input change to update desired water output
        self.desired_output_input.textChanged.connect(self.update_desired_water_output)

        # Connect double-click to remove animal
        self.animal_table.cellDoubleClicked.connect(self.remove_animal)

        # Container for instant delivery slots
        self.instant_delivery_container = QWidget()
        self.instant_delivery_layout = QVBoxLayout()
        self.instant_delivery_container.setLayout(self.instant_delivery_layout)
        
        # Add delivery slot button with icon or clear text
        self.add_slot_button = QPushButton("+ Add Water Delivery Time")
        self.add_slot_button.clicked.connect(self.add_delivery_slot)
        
        # Add widgets to layout
        self.layout.addWidget(self.instant_delivery_container)
        self.layout.addWidget(self.add_slot_button)
        
        # Add spacing between relay units
        self.layout.addSpacing(20)
        
        # Initialize UI state
        self.delivery_slots = []
        
        # Hide instant delivery components by default
        self.instant_delivery_container.hide()
        self.add_slot_button.hide()

        # Initialize UI state
        self.delivery_slots = []
        self.set_mode("Staggered")  # Default mode

    def dragEnterEvent(self, event):
        """
        Handle the drag enter event.

        Args:
            event (QDragEnterEvent): The drag enter event.
        """
        if event.mimeData().hasFormat('application/x-animal-id'):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """
        Handle the drop event.

        Args:
            event (QDropEvent): The drop event.
        """
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
                    # Check if relay unit already has an animal
                    if self.assigned_animal is not None:
                        QMessageBox.warning(
                            self, 
                            "Assignment Error", 
                            f"Relay Unit {self.relay_unit.unit_id} already has an animal assigned."
                        )
                        event.ignore()
                        return

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
        """
        Assign an animal to the relay unit and update the UI.

        Args:
            animal (Animal): The animal to assign.
        """
        self.assigned_animal = animal
        self.desired_water_output = 0.0  # Reset desired water output

        # Update the animal information table
        self.animal_table.setRowCount(1)
        self.animal_table.setItem(0, 0, QTableWidgetItem(animal.lab_animal_id))
        self.animal_table.setItem(0, 1, QTableWidgetItem(animal.name))
        last_weight = str(animal.last_weight) if animal.last_weight is not None else "N/A"
        self.animal_table.setItem(0, 2, QTableWidgetItem(last_weight))
        last_watering = animal.last_watering if animal.last_watering else "N/A"
        self.animal_table.setItem(0, 3, QTableWidgetItem(last_watering))

        # Align text to center for better readability
        for column in range(4):
            self.animal_table.item(0, column).setTextAlignment(Qt.AlignCenter)

        # Calculate and display recommended water volume
        recommended_volume = self.calculate_recommended_water(animal)
        self.recommended_water_label.setText(f"Recommended water volume: {recommended_volume} mL")

        # Hide the drag area since an animal is now assigned
        self.drag_area_label.hide()

    def calculate_recommended_water(self, animal):
        """
        Calculate recommended water volume based on the animal's weight.

        Args:
            animal (Animal): The animal for which to calculate water volume.

        Returns:
            float: Recommended water volume in milliliters.
        """
        weight = animal.last_weight if animal.last_weight is not None else animal.initial_weight
        recommended_water = round(weight * 0.1, 2)  # Example: 10% of body weight
        return recommended_water

    def update_desired_water_output(self, text):
        """
        Update the desired water output based on user input.

        Args:
            text (str): The text input from the user.
        """
        try:
            if text.strip() == "":
                self.desired_water_output = 0.0
            else:
                self.desired_water_output = float(text)
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter a valid number for water volume.")
            self.desired_output_input.setText("")

    def get_data(self):
        """
        Retrieve the current data from the widget.
        """
        desired_output_text = self.desired_output_input.text().strip()
        try:
            desired_output = float(desired_output_text) if desired_output_text else 0.0
        except ValueError:
            desired_output = 0.0
            QMessageBox.warning(self, "Input Error", "Invalid desired water output. Resetting to 0.0 mL.")

        desired_water_output = {}
        if self.assigned_animal:
            desired_water_output[str(self.assigned_animal.animal_id)] = desired_output

        data = {
            'animals': [self.assigned_animal] if self.assigned_animal else [],
            'desired_water_output': desired_water_output,
            'delivery_mode': self.current_mode.lower()
        }
        
        if data['delivery_mode'] == 'instant':
            schedule = []
            # Create a list to store references to slots while iterating
            active_slots = [slot for slot in self.delivery_slots if slot.isVisible()]
            for slot in active_slots:
                try:
                    volume = float(slot.volume_input.text())
                    schedule.append({
                        'datetime': slot.datetime_picker.dateTime().toPyDateTime(),
                        'volume': volume
                    })
                except (ValueError, AttributeError):
                    continue
            data['delivery_schedule'] = schedule
        
        return data

    def set_data(self, animals, desired_water_output):
        """
        Set the data for the relay unit.

        Args:
            animals (list): A list of Animal instances to assign.
            desired_water_output (dict): Desired water output per animal_id.
        """
        self.clear_assignments()
        if animals:
            animal = animals[0]  # Assuming only one animal per relay unit
            self.add_animal(animal)
            if animal.animal_id in desired_water_output:
                self.desired_output_input.setText(str(desired_water_output[animal.animal_id]))
            else:
                self.desired_output_input.setText("0.0")

    def clear_assignments(self):
        """
        Clear all assigned animals and reset inputs.
        """
        self.assigned_animal = None
        self.desired_water_output = 0.0
        self.animal_table.setRowCount(0)
        self.desired_output_input.clear()
        self.recommended_water_label.setText("Recommended water volume: N/A")
        self.drag_area_label.show()

    def remove_animal(self, row, column):
        """
        Remove the assigned animal from the relay unit.

        Args:
            row (int): The row of the clicked cell.
            column (int): The column of the clicked cell.
        """
        if self.assigned_animal is None:
            QMessageBox.warning(self, "Removal Error", "No animal is assigned to this relay unit.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove '{self.assigned_animal.name}' from Relay Unit {self.relay_unit.unit_id}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                # Re-add the animal to the Available Animals list
                new_item = self.available_animals_list.create_available_animal_item(self.assigned_animal)
                self.available_animals_list.addItem(new_item)

                # Clear the assignment
                self.clear_assignments()
            except AttributeError as e:
                QMessageBox.critical(self, "Removal Error", f"Failed to re-add animal to available list: {e}")
            except Exception as e:
                QMessageBox.critical(self, "Removal Error", f"An unexpected error occurred: {e}")

    def update_volume_display(self):
        if self.assigned_animal:
            recommended = self.assigned_animal.calculate_recommended_water()
            self.volume_display.setText(f"Recommended: {recommended}mL")
            
    def validate_and_dispense(self):
        if not self.assigned_animal:
            return
            
        try:
            volume = float(self.volume_input.text())
            if self.assigned_animal.validate_water_volume(volume):
                self.pump_controller.dispense_water(self.relay_unit, volume)
            else:
                QMessageBox.warning(self, "Invalid Volume", 
                    "Volume outside recommended range")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", 
                "Please enter a valid number")

    def add_delivery_slot(self):
        """Add a new instant delivery time slot"""
        slot = WaterDeliverySlot()
        self.delivery_slots.append(slot)
        self.instant_delivery_layout.addWidget(slot)

    def set_mode(self, mode):
        """Set the delivery mode from parent widget"""
        self.current_mode = mode
        is_instant = mode == "Instant"
        
        # Update visibility
        self.instant_delivery_container.setVisible(is_instant)
        self.add_slot_button.setVisible(is_instant)
        self.desired_output_label.setVisible(not is_instant)
        self.desired_output_input.setVisible(not is_instant)
        
        # Clear existing slots when switching modes
        if not is_instant:
            while self.delivery_slots:
                slot = self.delivery_slots.pop()
                slot.setParent(None)  # Remove parent reference
                slot.deleteLater()  # Schedule for deletion

    def on_slot_deleted(self, slot):
        """Handle the deletion of a WaterDeliverySlot."""
        if slot in self.delivery_slots:
            self.delivery_slots.remove(slot)
        else:
            print("Attempted to remove a slot that was not in the delivery_slots list.")