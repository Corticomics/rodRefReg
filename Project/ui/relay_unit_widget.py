# ui/relay_unit_widget.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QMessageBox, QLineEdit, QHBoxLayout, QPushButton, QDateTimeEdit,
    QScrollArea, QComboBox, QHeaderView, QSizePolicy, QGridLayout
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
        
        # Main layout with proper margins
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(6)
        self.setLayout(self.layout)
        
        # Create a grid layout for better alignment
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)
        
        # DateTime label and picker
        datetime_label = QLabel("Delivery Time:")
        self.datetime_picker = QDateTimeEdit()
        self.datetime_picker.setCalendarPopup(True)
        self.datetime_picker.setDateTime(QDateTime.currentDateTime())
        self.datetime_picker.setMinimumDateTime(QDateTime.currentDateTime())
        self.datetime_picker.setDisplayFormat("yyyy-MM-dd hh:mm AP")
        self.datetime_picker.setMinimumWidth(180)
        self.datetime_picker.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # Volume label and input
        volume_label = QLabel("Volume (mL):")
        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("Water volume")
        self.volume_input.setFixedWidth(100)
        self.volume_input.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Delete button with refined styling
        self.delete_button = QPushButton("×")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px;
                min-width: 24px;
                min-height: 24px;
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
        self.delete_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Add widgets to the grid layout with proper alignment
        # First row - labels
        grid_layout.addWidget(datetime_label, 0, 0, Qt.AlignBottom)
        grid_layout.addWidget(volume_label, 0, 1, Qt.AlignBottom)
        
        # Second row - inputs and delete button
        grid_layout.addWidget(self.datetime_picker, 1, 0)
        grid_layout.addWidget(self.volume_input, 1, 1)
        grid_layout.addWidget(self.delete_button, 1, 2, Qt.AlignCenter)
        
        # Set column stretch factors
        grid_layout.setColumnStretch(0, 4)  # Datetime picker - more space
        grid_layout.setColumnStretch(1, 1)  # Volume input - less space
        grid_layout.setColumnStretch(2, 0)  # Delete button - fixed width
        
        # Add the grid to the main layout
        self.layout.addLayout(grid_layout)
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
        self.title_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #333;
            padding: 4px;
        """)
        self.layout.addWidget(self.title_label)

        # Drag-and-Drop Area - keep visible
        self.drag_area_label = QLabel("Drop Animal Here")
        self.drag_area_label.setAlignment(Qt.AlignCenter)
        self.drag_area_label.setStyleSheet("""
            background-color: #f8f9fa; 
            border: 2px dashed #1a73e8; 
            font-size: 14px;
            color: #5f6368;
            min-height: 50px;
            border-radius: 4px;
            padding: 8px;
        """)
        self.layout.addWidget(self.drag_area_label)

        # Enable drag-and-drop
        self.setAcceptDrops(True)

        # Animal Information Table - improved sizing and formatting
        self.animal_table = QTableWidget()
        self.animal_table.setColumnCount(4)
        self.animal_table.setHorizontalHeaderLabels(["Lab ID", "Name", "Last Weight", "Last Watering"])
        
        # Set fixed row height and improved visual appearance
        self.animal_table.verticalHeader().setDefaultSectionSize(50)  # Taller rows for better text display
        self.animal_table.verticalHeader().setVisible(False)  # Hide row numbers
        
        # Set absolute minimum column widths to ensure data visibility
        self.animal_table.setColumnWidth(0, 90)   # Lab ID: minimum 90px
        self.animal_table.setColumnWidth(1, 110)  # Name: minimum 110px
        self.animal_table.setColumnWidth(2, 110)  # Last Weight: minimum 110px
        self.animal_table.setColumnWidth(3, 140)  # Last Watering: minimum 140px
        
        # Set size policy to expand and fill available space
        self.animal_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Fix table size and appearance
        # Make the last column stretch to fill remaining space
        self.animal_table.horizontalHeader().setStretchLastSection(True)
        
        # Allow word wrap for better text display
        self.animal_table.setWordWrap(True)
        
        # Fix specific settings for better appearance
        self.animal_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.animal_table.setSelectionMode(QTableWidget.NoSelection)
        self.animal_table.setMinimumHeight(100)   # Increase minimum height for better text display
        self.animal_table.setMaximumHeight(120)   # Increase maximum height
        self.animal_table.setShowGrid(True)       # Show grid for better visibility
        self.animal_table.setAlternatingRowColors(True)  # Alternate row colors
        
        # Enhanced table styling with better contrast and readability
        self.animal_table.setStyleSheet("""
            QTableWidget {
                font-size: 13px;              /* Larger font size for readability */
                border: 1px solid #1a73e8;    /* Blue border to match application theme */
                border-radius: 4px;
                gridline-color: #d0d0d0;      /* Darker grid lines for visibility */
                background-color: white;
            }
            QHeaderView::section {
                font-size: 13px;              /* Larger font */
                font-weight: bold;
                padding: 8px;                 /* More padding */
                background-color: #e8f0fe;    /* Light blue header background */
                border: 1px solid #1a73e8;    /* Blue border to match theme */
                border-bottom: 2px solid #1a73e8;
                color: #1a73e8;               /* Blue text for headers */
            }
            QTableWidget::item {
                padding: 8px;                 /* More padding in cells */
                border-bottom: 1px solid #e0e4e8;
                color: #333333;               /* Darker text for better readability */
                font-weight: 500;             /* Slightly bolder text */
            }
            QTableWidget::item:selected {
                background-color: #e8f0fe;    /* Light blue selection */
                color: #1a73e8;               /* Blue text on selection */
            }
            /* Scrollbar styling - appear only on hover */
            QScrollBar:horizontal {
                height: 8px;
                background: transparent;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
                background: rgba(26, 115, 232, 0.2);  /* Transparent blue matching theme */
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover {
                background: rgba(26, 115, 232, 0.5);  /* More visible on handle hover */
            }
            /* Hide scrollbar when not needed */
            QScrollBar::add-line, QScrollBar::sub-line {
                width: 0px;
                height: 0px;
            }
            QScrollBar::add-page, QScrollBar::sub-page {
                background: transparent;
            }
            /* Hide scrollbar until hover */
            QTableWidget {
                /* Start with transparent scrollbars */
                scrollbar-width: thin;
            }
            QTableWidget:hover QScrollBar::handle:horizontal, 
            QTableWidget:hover QScrollBar::handle:vertical {
                background: rgba(26, 115, 232, 0.5);  /* Show on table hover */
            }
        """)
        self.layout.addWidget(self.animal_table)

        # Water Volume Display - improved styling
        self.recommended_water_label = QLabel("Recommended water volume: N/A")
        self.recommended_water_label.setStyleSheet("""
            font-size: 13px;
            padding: 8px;
            background-color: #e8f0fe;         /* Light blue background */
            border: 1px solid #1a73e8;         /* Blue border */
            border-radius: 4px;
            color: #1a73e8;                    /* Blue text to match theme */
            font-weight: 500;
            margin-top: 4px;
        """)
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
            # Change the appearance to indicate a valid drop target
            self.drag_area_label.setStyleSheet("""
                background-color: #e8f0fe; 
                border: 3px solid #1a73e8; 
                font-size: 14px;
                color: #1a73e8;
                font-weight: bold;
                min-height: 50px;
                border-radius: 4px;
                padding: 8px;
            """)
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dragLeaveEvent(self, event):
        """
        Handle the drag leave event.
        
        Args:
            event (QDragLeaveEvent): The drag leave event.
        """
        # Reset the appearance
        self.drag_area_label.setStyleSheet("""
            background-color: #f8f9fa; 
            border: 2px dashed #1a73e8; 
            font-size: 14px;
            color: #5f6368;
            min-height: 50px;
            border-radius: 4px;
            padding: 8px;
        """)

    def dropEvent(self, event):
        """
        Handle the drop event.

        Args:
            event (QDropEvent): The drop event.
        """
        # Reset the appearance
        self.drag_area_label.setStyleSheet("""
            background-color: #f8f9fa; 
            border: 2px dashed #1a73e8; 
            font-size: 14px;
            color: #5f6368;
            min-height: 50px;
            border-radius: 4px;
            padding: 8px;
        """)
        
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
        
        # Format the weight and last watering data properly with clear formatting
        last_weight_text = f"{animal.last_weight:.1f} g" if animal.last_weight else "N/A"
        
        # Format last watering with better readability
        if animal.last_watering:
            try:
                # Parse the datetime string
                watering_date = datetime.fromisoformat(animal.last_watering)
                # Format it in a readable way
                last_watering_text = watering_date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                # Fallback if parsing fails
                last_watering_text = str(animal.last_watering).split()[0] if animal.last_watering else "Never"
        else:
            last_watering_text = "Never"
        
        # Create table items with formatted data
        lab_id_item = QTableWidgetItem(animal.lab_animal_id)
        name_item = QTableWidgetItem(animal.name)
        weight_item = QTableWidgetItem(last_weight_text)
        watering_item = QTableWidgetItem(last_watering_text)
        
        # Set items in table
        self.animal_table.setItem(0, 0, lab_id_item)
        self.animal_table.setItem(0, 1, name_item)
        self.animal_table.setItem(0, 2, weight_item)
        self.animal_table.setItem(0, 3, watering_item)

        # Align text to center for better readability
        for column in range(4):
            item = self.animal_table.item(0, column)
            if item:
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                # Set a light background color for better readability
                item.setBackground(Qt.white)

        # Calculate and display recommended water volume
        recommended_volume = self.calculate_recommended_water(animal)
        self.recommended_water_label.setText(f"Recommended water volume: {recommended_volume} mL")

        # Hide the drag area since an animal is now assigned
        self.drag_area_label.hide()
        
        # Force table to resize rows based on content
        self.animal_table.resizeRowsToContents()
        
        # Update minimum width to ensure all content is visible
        self.ensure_table_width()
        
        # Force layout update
        self.update()

    def calculate_recommended_water(self, animal):
        """
        Calculate recommended water volume based on the animal's weight.

        Args:
            animal (Animal): The animal for which to calculate water volume.

        Returns:
            float: Recommended water volume in milliliters.
        """
        weight = animal.last_weight if animal.last_weight is not None else animal.initial_weight
        if weight is None:
            return 0.0
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

    def set_data(self, animals, desired_water_output=None, delivery_schedule=None):
        """
        Set the data for the relay unit.

        Args:
            animals (list): A list of Animal instances to assign.
            desired_water_output (dict, optional): Desired water output per animal_id.
            delivery_schedule (list, optional): Schedule for instant delivery mode.
        """
        self.clear_assignments()
        if animals:
            animal = animals[0]  # Assuming only one animal per relay unit
            self.assigned_animal = animal  # Set the assigned animal
            
            # Update the animal table with proper formatting
            self.animal_table.setRowCount(1)
            
            # Format the weight and last watering data properly with clear formatting
            last_weight_text = f"{animal.last_weight:.1f} g" if animal.last_weight else "N/A"
            
            # Format last watering with better readability
            if animal.last_watering:
                try:
                    # Parse the datetime string
                    watering_date = datetime.fromisoformat(animal.last_watering)
                    # Format it in a readable way
                    last_watering_text = watering_date.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    # Fallback if parsing fails
                    last_watering_text = str(animal.last_watering).split()[0] if animal.last_watering else "Never"
            else:
                last_watering_text = "Never"
            
            # Create table items with formatted data
            lab_id_item = QTableWidgetItem(animal.lab_animal_id)
            name_item = QTableWidgetItem(animal.name)
            weight_item = QTableWidgetItem(last_weight_text)
            watering_item = QTableWidgetItem(last_watering_text)
            
            # Set items in table with center alignment
            for i, item in enumerate([lab_id_item, name_item, weight_item, watering_item]):
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                self.animal_table.setItem(0, i, item)
            
            # Calculate and display recommended water volume
            recommended_volume = self.calculate_recommended_water(animal)
            self.recommended_water_label.setText(f"Recommended water volume: {recommended_volume:.2f} mL")
            
            # Hide the drag area since an animal is now assigned
            self.drag_area_label.hide()
            
            # Force table to resize rows based on content
            self.animal_table.resizeRowsToContents()
            
            # Update minimum width to ensure all content is visible
            self.ensure_table_width()
            
            # If delivery schedule is provided (for instant mode)
            if delivery_schedule and isinstance(delivery_schedule, list):
                try:
                    self.set_mode("Instant")
                    # Clear any existing slots
                    self.clear_instant_slots()
                    
                    # Add delivery slots
                    for delivery in delivery_schedule:
                        self.add_instant_slot_button.click()  # Create new slot
                        # Find the last added slot
                        if self.delivery_slots:
                            slot = self.delivery_slots[-1]
                            # Set slot data if possible
                            if hasattr(slot, 'volume_input') and hasattr(slot, 'datetime_picker'):
                                try:
                                    slot.volume_input.setText(str(delivery.get('volume', 0)))
                                    # Handle datetime if present
                                    if 'datetime' in delivery:
                                        dt = delivery['datetime']
                                        if hasattr(slot.datetime_picker, 'setDateTime'):
                                            slot.datetime_picker.setDateTime(dt)
                                except (AttributeError, TypeError) as e:
                                    print(f"Error setting delivery slot data: {e}")
                except Exception as e:
                    print(f"Error setting delivery schedule: {e}")
                    QMessageBox.warning(self, "Schedule Error", 
                                      f"There was an error setting the delivery schedule: {str(e)}")
            
            # Force update to ensure proper display
            self.update()

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
        
        # Format the data properly with clear formatting
        last_weight_text = f"{animal.last_weight:.1f} g" if animal.last_weight else "N/A"
        
        # Format last watering with better readability
        if animal.last_watering:
            try:
                # Parse the datetime string
                watering_date = datetime.fromisoformat(animal.last_watering)
                # Format it in a readable way
                last_watering_text = watering_date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                # Fallback if parsing fails
                last_watering_text = str(animal.last_watering).split()[0] if animal.last_watering else "Never"
        else:
            last_watering_text = "Never"
            
        # Create table items with formatted data
        lab_id_item = QTableWidgetItem(animal.lab_animal_id)
        name_item = QTableWidgetItem(animal.name)
        weight_item = QTableWidgetItem(last_weight_text)
        watering_item = QTableWidgetItem(last_watering_text)
        
        # Set items in table with center alignment
        for i, item in enumerate([lab_id_item, name_item, weight_item, watering_item]):
            item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.animal_table.setItem(0, i, item)
        
        # Update recommended water label if weight is available
        if animal.last_weight:
            recommended = self.calculate_recommended_water(animal)
            self.recommended_water_label.setText(f"Recommended water volume: {recommended:.2f} mL")
        else:
            self.recommended_water_label.setText("Recommended water volume: N/A")
            
        # Force table to resize rows based on content
        self.animal_table.resizeRowsToContents()
        
        # Update minimum width
        self.ensure_table_width()

    def clear_animal_info(self):
        """Clear all animal information from the display"""
        self.animal_table.setRowCount(0)
        self.recommended_water_label.setText("Recommended water volume: N/A")
        self.assigned_animal = None
        
        # Clear any instant delivery slots
        for slot in self.delivery_slots:
            slot.deleteLater()
        self.delivery_slots.clear()

    def resizeEvent(self, event):
        """Handle resize events to adjust table to fit container"""
        super().resizeEvent(event)
        self.ensure_table_width()
    
    def ensure_table_width(self):
        """Make sure table width is sufficient to display all content"""
        if hasattr(self, 'animal_table') and self.animal_table.isVisible():
            # Get available width (accounting for layout margins)
            available_width = self.width() - 20
            
            # Set minimum table width to available width
            self.animal_table.setMinimumWidth(available_width)
            
            # Set column widths proportionally
            col_widths = [0.20, 0.25, 0.25, 0.30]  # Proportions for each column
            
            for i, proportion in enumerate(col_widths):
                min_width = [90, 110, 110, 140][i]  # Minimum widths by column
                width = max(min_width, int(available_width * proportion))
                
                # Don't set width for the last column if stretch is enabled
                if i < len(col_widths) - 1 or not self.animal_table.horizontalHeader().stretchLastSection():
                    self.animal_table.setColumnWidth(i, width)
            
            # Force table to update its layout
            self.animal_table.updateGeometry()

    def update_animal_table_display(self, animal):
        """
        Update the animal information table with formatted data.
        
        Args:
            animal (Animal): The animal object containing data to display.
        """
        self.animal_table.setRowCount(1)
        
        # Format the weight and last watering data properly
        last_weight_text = f"{animal.last_weight:.1f} g" if animal.last_weight else "N/A"
        
        # Format last watering with better readability
        if animal.last_watering:
            try:
                # Parse the datetime string
                watering_date = datetime.fromisoformat(animal.last_watering)
                # Format it in a readable way
                last_watering_text = watering_date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                # Fallback if parsing fails
                last_watering_text = str(animal.last_watering).split()[0] if animal.last_watering else "Never"
        else:
            last_watering_text = "Never"
        
        # Create table items with formatted data
        lab_id_item = QTableWidgetItem(animal.lab_animal_id)
        name_item = QTableWidgetItem(animal.name)
        weight_item = QTableWidgetItem(last_weight_text)
        watering_item = QTableWidgetItem(last_watering_text)
        
        # Set items in table with center alignment
        for i, item in enumerate([lab_id_item, name_item, weight_item, watering_item]):
            item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.animal_table.setItem(0, i, item)
        
        # Force table to resize rows based on content
        self.animal_table.resizeRowsToContents()
        
        # Update minimum width to ensure all content is visible
        self.ensure_table_width()