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
from .staggered_delivery_slot import StaggeredDeliverySlot

class WaterDeliverySlot(QWidget):
    # Signal emitted when the slot is about to be deleted
    slot_deleted = pyqtSignal(QWidget)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)  # Less aggressive margin reduction
        
        # DateTime picker with calendar popup - less aggressive size reduction
        self.datetime_picker = QDateTimeEdit()
        self.datetime_picker.setCalendarPopup(True)
        self.datetime_picker.setDateTime(QDateTime.currentDateTime())
        self.datetime_picker.setMinimumDateTime(QDateTime.currentDateTime())
        self.datetime_picker.setDisplayFormat("yyyy-MM-dd hh:mm AP")
        # Make calendar widget smaller but still usable
        self.datetime_picker.setStyleSheet("""
            QDateTimeEdit {
                min-width: 180px;
            }
            QCalendarWidget {
                min-width: 300px;
                min-height: 300px;
            }
        """)
        
        # Volume input
        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("Water volume (mL)")
        self.volume_input.setFixedWidth(120)  # Slightly wider than before
        
        # Delete button with refined styling
        self.delete_button = QPushButton("×")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px;
                max-width: 24px;
                max-height: 24px;
                font-size: 16px;
                font-weight: bold;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        self.delete_button.clicked.connect(self.handle_delete)
        
        layout.addWidget(self.datetime_picker)
        layout.addWidget(self.volume_input)
        layout.addWidget(self.delete_button)
        self.setLayout(layout)
        self.is_deleted = False

    def handle_delete(self):
        """Handle the deletion of the slot."""
        self.is_deleted = True
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
        self.assigned_animal = None
        self.pump_controller = pump_controller
        self.current_mode = "Staggered"

        # Main layout - less aggressive margin reduction
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(8, 8, 8, 8)  # Less aggressive
        self.layout.setSpacing(8)  # Less aggressive spacing
        self.setLayout(self.layout)

        # Title Label
        self.title_label = QLabel(f"Relay Unit {relay_unit.unit_id}")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold;")  # Make title visible
        self.layout.addWidget(self.title_label)

        # Drag-and-Drop Area - keep visible
        self.drag_area_label = QLabel("Drop Animal Here")
        self.drag_area_label.setAlignment(Qt.AlignCenter)
        self.drag_area_label.setStyleSheet("""
            background-color: #f8f9fa; 
            border: 2px dashed #e0e0e0; 
            font-size: 14px;
            min-height: 40px;
        """)
        self.layout.addWidget(self.drag_area_label)

        # Enable drag-and-drop
        self.setAcceptDrops(True)

        # Animal Information Table - improved sizing and formatting
        self.animal_table = QTableWidget()
        self.animal_table.setColumnCount(4)
        self.animal_table.setHorizontalHeaderLabels(["Lab ID", "Name", "Last Weight", "Last Watering"])
        
        # Set specific column widths for better visibility
        self.animal_table.setColumnWidth(0, 80)   # Lab ID
        self.animal_table.setColumnWidth(1, 100)  # Name
        self.animal_table.setColumnWidth(2, 90)   # Last Weight
        self.animal_table.setColumnWidth(3, 110)  # Last Watering
        
        self.animal_table.horizontalHeader().setStretchLastSection(True)
        self.animal_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.animal_table.setSelectionMode(QTableWidget.NoSelection)
        self.animal_table.verticalHeader().setVisible(False)
        self.animal_table.setMinimumHeight(60)  # Ensure it has minimum height
        self.animal_table.setMaximumHeight(80)  # Limit height but not too small
        self.animal_table.setStyleSheet("""
            QTableWidget {
                font-size: 12px;
                border: 1px solid #e0e4e8;
                border-radius: 4px;
            }
            QHeaderView::section {
                font-size: 12px;
                padding: 3px;
                background-color: #f8f9fa;
                border: none;
                border-bottom: 1px solid #e0e4e8;
            }
            QTableWidget::item {
                padding: 2px 4px;
            }
        """)
        self.layout.addWidget(self.animal_table)

        # Water Volume Display
        self.recommended_water_label = QLabel("Recommended water volume: N/A")
        self.recommended_water_label.setStyleSheet("font-size: 12px;")
        self.layout.addWidget(self.recommended_water_label)

        # Instant Delivery Components
        self.setup_instant_delivery_components()

        # Connect double-click to remove animal
        self.animal_table.cellDoubleClicked.connect(self.remove_animal)

        # Initialize UI state
        self.delivery_slots = []
        self.set_mode("Staggered")  # Default mode

    def setup_instant_delivery_components(self):
        """Setup components for instant delivery mode"""
        # Container for instant delivery slots
        self.instant_delivery_container = QWidget()
        self.instant_delivery_layout = QVBoxLayout(self.instant_delivery_container)
        self.instant_delivery_layout.setContentsMargins(3, 3, 3, 3)
        self.instant_delivery_layout.setSpacing(5)
        self.layout.addWidget(self.instant_delivery_container)
        
        # Add delivery slot button for instant mode
        self.add_instant_slot_button = QPushButton("+ Add Water Delivery Time")
        self.add_instant_slot_button.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1666d4;
            }
            QPushButton:pressed {
                background-color: #125bbf;
            }
        """)
        self.add_instant_slot_button.clicked.connect(self.add_delivery_slot)
        self.layout.addWidget(self.add_instant_slot_button)
        
        # Container for staggered delivery slots
        self.staggered_delivery_container = QWidget()
        self.staggered_delivery_layout = QVBoxLayout(self.staggered_delivery_container)
        self.staggered_delivery_layout.setContentsMargins(3, 3, 3, 3)
        self.staggered_delivery_layout.setSpacing(5)
        self.layout.addWidget(self.staggered_delivery_container)
        
        # Add delivery slot button for staggered mode
        self.add_staggered_slot_button = QPushButton("+ Add Time Window")
        self.add_staggered_slot_button.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1666d4;
            }
            QPushButton:pressed {
                background-color: #125bbf;
            }
        """)
        self.add_staggered_slot_button.clicked.connect(self.add_staggered_slot)
        self.layout.addWidget(self.add_staggered_slot_button)
        
        # Hide all delivery components by default
        self.instant_delivery_container.hide()
        self.add_instant_slot_button.hide()
        self.staggered_delivery_container.hide()
        self.add_staggered_slot_button.hide()

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

        # Update the animal information table
        self.animal_table.setRowCount(1)
        self.animal_table.setItem(0, 0, QTableWidgetItem(animal.lab_animal_id))
        self.animal_table.setItem(0, 1, QTableWidgetItem(animal.name))
        self.animal_table.setItem(0, 2, QTableWidgetItem(str(animal.last_weight)))
        self.animal_table.setItem(0, 3, QTableWidgetItem(str(animal.last_watering)))

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

    def get_data(self):
        """
        Retrieve the current data from the widget.
        """
        # Build desired water output dictionary
        desired_water_output = {}
        relay_unit_assignments = {}
        
        if self.assigned_animal:
            # Add relay unit assignment
            relay_unit_assignments[str(self.assigned_animal.animal_id)] = self.relay_unit.unit_id
            
            # Calculate recommended water volume for the animal
            recommended_volume = self.calculate_recommended_water(self.assigned_animal)
            desired_water_output[str(self.assigned_animal.animal_id)] = recommended_volume

        # Prepare base data structure
        data = {
            'animals': [self.assigned_animal] if self.assigned_animal else [],
            'desired_water_output': desired_water_output,
            'relay_unit_assignments': relay_unit_assignments,  # Add relay unit assignments
            'delivery_mode': self.current_mode.lower()
        }
        
        # Handle delivery schedule based on mode
        if data['delivery_mode'] == 'instant':
            schedule = []
            active_slots = [slot for slot in self.delivery_slots 
                           if slot.isVisible() and not slot.is_deleted]
            for slot in active_slots:
                try:
                    volume = float(slot.volume_input.text())
                    schedule.append({
                        'datetime': slot.datetime_picker.dateTime().toPyDateTime(),
                        'volume': volume,
                        'relay_unit_id': self.relay_unit.unit_id  # Add relay unit ID
                    })
                except (ValueError, AttributeError):
                    continue
            data['delivery_schedule'] = schedule
        else:  # staggered mode
            schedule = []
            active_slots = [slot for slot in self.delivery_slots 
                           if slot.isVisible() and not slot.is_deleted]
            total_volume = 0
            for slot in active_slots:
                try:
                    volume = float(slot.volume_input.text())
                    total_volume += volume
                    schedule.append({
                        'start_time': slot.start_datetime.dateTime().toPyDateTime(),
                        'end_time': slot.end_datetime.dateTime().toPyDateTime(),
                        'volume': volume,
                        'relay_unit_id': self.relay_unit.unit_id  # Add relay unit ID
                    })
                except (ValueError, AttributeError):
                    continue
            data['delivery_schedule'] = schedule
            
            # Update staggered-specific data with total volume
            if self.assigned_animal:
                data['staggered_settings'] = {
                    str(self.assigned_animal.animal_id): {
                        'total_volume': total_volume,
                        'windows': schedule,
                        'relay_unit_id': self.relay_unit.unit_id  # Add relay unit ID
                    }
                }
                # Update the desired water output with the total volume
                desired_water_output[str(self.assigned_animal.animal_id)] = total_volume
        
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

    def clear_assignments(self):
        """
        Clear all assigned animals and reset inputs.
        """
        self.assigned_animal = None
        self.animal_table.setRowCount(0)
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
        """Add a new water delivery time slot"""
        slot = WaterDeliverySlot()
        slot.slot_deleted.connect(self.remove_delivery_slot)
        self.delivery_slots.append(slot)
        self.instant_delivery_layout.addWidget(slot)

    def remove_delivery_slot(self, slot):
        """Remove a water delivery time slot"""
        if slot in self.delivery_slots:
            self.delivery_slots.remove(slot)

    def set_mode(self, mode):
        """Set the delivery mode and update UI accordingly"""
        self.current_mode = mode
        
        # Show/hide components based on mode
        if mode == "Instant":
            self.instant_delivery_container.show()
            self.add_instant_slot_button.show()
            self.staggered_delivery_container.hide()
            self.add_staggered_slot_button.hide()
            # Clear staggered slots
            self.clear_staggered_slots()
        else:  # Staggered mode
            self.instant_delivery_container.hide()
            self.add_instant_slot_button.hide()
            self.staggered_delivery_container.show()
            self.add_staggered_slot_button.show()
            # Clear instant slots
            self.clear_instant_slots()

    def add_staggered_slot(self):
        """Add a new staggered delivery time window slot"""
        slot = StaggeredDeliverySlot()
        slot.slot_deleted.connect(self.remove_staggered_slot)
        self.delivery_slots.append(slot)
        self.staggered_delivery_layout.addWidget(slot)

    def remove_staggered_slot(self, slot):
        """Remove a staggered delivery time window slot"""
        if slot in self.delivery_slots:
            self.delivery_slots.remove(slot)

    def clear_instant_slots(self):
        """Clear instant delivery slots"""
        for slot in self.delivery_slots[:]:
            if isinstance(slot, WaterDeliverySlot):
                slot.deleteLater()
                self.delivery_slots.remove(slot)

    def clear_staggered_slots(self):
        """Clear staggered delivery slots"""
        for slot in self.delivery_slots[:]:
            if isinstance(slot, StaggeredDeliverySlot):
                slot.deleteLater()
                self.delivery_slots.remove(slot)

    def update_animal_info(self, animal):
        """Update the animal information display"""
        self.animal_table.setRowCount(1)
        self.animal_table.setItem(0, 0, QTableWidgetItem(animal.lab_animal_id))
        self.animal_table.setItem(0, 1, QTableWidgetItem(animal.name))
        self.animal_table.setItem(0, 2, QTableWidgetItem(str(animal.last_weight)))
        self.animal_table.setItem(0, 3, QTableWidgetItem(str(animal.last_watering)))
        
        # Update recommended water label if weight is available
        if animal.last_weight:
            recommended = self.calculate_recommended_water(animal.last_weight)
            self.recommended_water_label.setText(f"Recommended water volume: {recommended:.2f} mL")
        else:
            self.recommended_water_label.setText("Recommended water volume: N/A")

    def clear_animal_info(self):
        """Clear all animal information from the display"""
        self.animal_table.setRowCount(0)
        self.recommended_water_label.setText("Recommended water volume: N/A")
        self.assigned_animal = None
        
        # Clear any instant delivery slots
        for slot in self.delivery_slots:
            slot.deleteLater()
        self.delivery_slots.clear()