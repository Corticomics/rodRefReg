# ui/schedules_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QInputDialog,
    QPushButton, QMessageBox, QScrollArea, QListWidget, QListWidgetItem, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtGui import QDrag
from datetime import datetime
from .relay_unit_widget import RelayUnitWidget, WaterDeliverySlot
from models.Schedule import Schedule
from models.relay_unit import RelayUnit
from .available_animals_list import AvailableAnimalsList  # Import the custom list
import traceback

class SchedulesTab(QWidget):
    mode_changed = pyqtSignal(str)  # Signal to emit mode changes

    def __init__(self, settings, print_to_terminal, database_handler, login_system):
        super().__init__()

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system
        self.pump_controller = settings.get('pump_controller')

        # Main layout: Horizontal box layout for three columns
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Left Column: Available Animals
        self.available_animals_widget = QWidget()
        self.available_animals_layout = QVBoxLayout()
        self.available_animals_widget.setLayout(self.available_animals_layout)

        # Add delivery mode selector at the top
        mode_layout = QHBoxLayout()
        self.mode_label = QLabel("Delivery Mode:")
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Staggered", "Instant"])
        self.mode_selector.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_label)
        mode_layout.addWidget(self.mode_selector)
        mode_layout.addStretch()
        self.available_animals_layout.insertLayout(0, mode_layout)

        self.animal_list = AvailableAnimalsList()
        self.animal_list.setMinimumWidth(200)

        self.available_animals_layout.addWidget(QLabel("Available Animals"))
        self.available_animals_layout.addWidget(self.animal_list)

        # Center Column: Relay Units
        self.relay_units_widget = QWidget()
        self.relay_units_layout = QVBoxLayout()
        self.relay_units_widget.setLayout(self.relay_units_layout)

        # Scroll area for relay units to handle scalability
        self.relay_units_scroll = QScrollArea()
        self.relay_units_scroll.setWidgetResizable(True)
        self.relay_units_container = QWidget()
        self.relay_units_container_layout = QVBoxLayout()
        self.relay_units_container.setLayout(self.relay_units_container_layout)
        self.relay_units_scroll.setWidget(self.relay_units_container)

        self.relay_units_layout.addWidget(QLabel("Relay Units"))
        self.relay_units_layout.addWidget(self.relay_units_scroll)

        # Dictionary to hold RelayUnitWidgets
        self.relay_unit_widgets = {}
        self.load_relay_units()

        # Right Column: Saved Schedules
        self.saved_schedules_widget = QWidget()
        self.saved_schedules_layout = QVBoxLayout()
        self.saved_schedules_widget.setLayout(self.saved_schedules_layout)

        self.schedule_list = QListWidget()
        self.schedule_list.setDragEnabled(True)  # Enable dragging
        self.schedule_list.itemClicked.connect(self.load_selected_schedule)

        self.saved_schedules_layout.addWidget(QLabel("Saved Schedules"))
        self.saved_schedules_layout.addWidget(self.schedule_list)

        # Add columns to main layout with stretch factors
        self.layout.addWidget(self.available_animals_widget, stretch=1)
        self.layout.addWidget(self.relay_units_widget, stretch=2)  # Increase stretch for Relay Units
        self.layout.addWidget(self.saved_schedules_widget, stretch=1)

        # Load animals and schedules
        self.load_animals()
        self.load_schedules()

        # Connect the mode selector to emit the mode_changed signal
        self.mode_selector.currentTextChanged.connect(self.mode_changed.emit)

        # Connect refresh to login system changes
        self.login_system.login_status_changed.connect(self.refresh)

    def load_relay_units(self):
        """Load relay units and create RelayUnitWidgets."""
        self.relay_units_container_layout.addStretch()
        self.relay_units_container_layout.setSpacing(10)

        self.relay_units = self.database_handler.get_all_relay_units()
        if not self.relay_units:
            self.initialize_relay_units()

        for relay_unit in self.relay_units:
            relay_widget = RelayUnitWidget(
                relay_unit, 
                self.database_handler, 
                self.animal_list,
                self.pump_controller
            )
            self.relay_unit_widgets[relay_unit.unit_id] = relay_widget
            self.relay_units_container_layout.addWidget(relay_widget)

    def initialize_relay_units(self):
        """Create relay units based on settings."""
        relay_pairs = self.settings.get('relay_pairs', [])
        unit_id = 1
        for pair in relay_pairs:
            relay_unit = RelayUnit(unit_id=unit_id, relay_ids=pair)
            self.database_handler.add_relay_unit(relay_unit)
            self.relay_units.append(relay_unit)
            unit_id += 1

    def load_animals(self):
        """Load animals into the available animals list."""
        try:
            current_trainer = self.login_system.get_current_trainer()
            if current_trainer:
                trainer_id = current_trainer['trainer_id']
                role = current_trainer['role']
                animals = self.database_handler.get_animals(trainer_id, role)
                self.print_to_terminal(f"Loading {len(animals)} animals for trainer ID {trainer_id} in SchedulesTab")
            else:
                animals = self.database_handler.get_all_animals()
                self.print_to_terminal(f"Loading {len(animals)} animals in guest mode for SchedulesTab")

            # Clear existing items
            self.animal_list.clear()
            
            # Add new items
            for animal in animals:
                item = self.animal_list.create_available_animal_item(animal)
                self.animal_list.addItem(item)
                
            # Force update
            self.animal_list.update()

        except Exception as e:
            print(f"Exception in SchedulesTab.load_animals: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Load Animals Error", f"An error occurred while loading animals:\n{e}")

    def load_schedules(self):
        """Load saved schedules and display them in the schedule list."""
        self.schedule_list.clear()
        current_trainer = self.login_system.get_current_trainer()
        if current_trainer:
            trainer_id = current_trainer['trainer_id']
            role = current_trainer['role']
            schedules = self.database_handler.get_schedules_by_trainer(trainer_id)
        else:
            schedules = self.database_handler.get_all_schedules()

        for schedule in schedules:
            item = QListWidgetItem(schedule.name)
            item.setData(Qt.UserRole, schedule)
            self.schedule_list.addItem(item)

    def on_mode_changed(self, mode):
        """Update all relay units to use the selected mode"""
        for widget in self.relay_unit_widgets.values():
            widget.set_mode(mode)

    def save_current_schedule(self):
        """Save the current assignments and settings as a new schedule."""
        schedule_name, ok = QInputDialog.getText(self, "Save Schedule", "Enter a name for the schedule:")
        if not ok or not schedule_name.strip():
            QMessageBox.warning(self, "Invalid Name", "Schedule name cannot be empty.")
            return

        current_trainer = self.login_system.get_current_trainer()
        if not current_trainer:
            QMessageBox.warning(self, "Not Logged In", "Please log in to save schedules.")
            return

        schedules = []
        for unit_id, relay_widget in self.relay_unit_widgets.items():
            relay_data = relay_widget.get_data()
            if relay_data['animals']:
                schedule = Schedule(
                    schedule_id=None,
                    name=schedule_name,
                    relay_unit_id=unit_id,
                    delivery_mode=relay_data['delivery_mode'],
                    created_by=current_trainer['trainer_id'],
                    is_super_user=(current_trainer['role'] == 'super')
                )
                
                if relay_data['delivery_mode'] == 'instant':
                    schedule.delivery_schedule = relay_data['delivery_schedule']
                else:
                    schedule.water_volume = relay_data['desired_water_output']
                    schedule.start_time = datetime.now().isoformat()
                    schedule.end_time = datetime.now().isoformat()
                
                schedule.animals = [animal.animal_id for animal in relay_data['animals']]
                schedules.append(schedule)

        # Save schedules to database
        try:
            for schedule in schedules:
                self.database_handler.add_schedule(schedule)
            QMessageBox.information(self, "Success", "Schedule saved successfully!")
            self.load_schedules()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save schedule: {str(e)}")

    def load_selected_schedule(self, item):
        """Load the selected schedule and populate the relay units."""
        schedule = item.data(Qt.UserRole)
        if not schedule:
            return

        # Clear current assignments
        for relay_widget in self.relay_unit_widgets.values():
            relay_widget.clear_assignments()

        # Load schedule data
        schedule_details = self.database_handler.get_schedule_details(schedule.schedule_id)

        for schedule_detail in schedule_details:
            relay_unit_id = schedule_detail['relay_unit_id']
            if relay_unit_id in self.relay_unit_widgets:
                relay_widget = self.relay_unit_widgets[relay_unit_id]
                
                # Set delivery mode
                relay_widget.mode_selector.setCurrentText(
                    schedule_detail.get('delivery_mode', 'staggered').capitalize()
                )
                
                # Load animals
                animals = []
                for animal_id in schedule_detail['animal_ids']:
                    animal = self.database_handler.get_animal_by_id(animal_id)
                    if animal:
                        animals.append(animal)
                
                # Set data based on mode
                if schedule_detail.get('delivery_mode') == 'instant':
                    relay_widget.set_data(
                        animals=animals,
                        delivery_schedule=schedule_detail.get('delivery_schedule', [])
                    )
                else:
                    relay_widget.set_data(
                        animals=animals,
                        desired_water_output=schedule_detail.get('desired_water_outputs', {})
                    )

    def refresh(self):
        """Refresh the UI components."""
        self.animal_list.clear()  # Clear the list first
        self.load_animals()  # Reload animals
        self.load_schedules()
        # Clear relay unit assignments
        for relay_widget in self.relay_unit_widgets.values():
            relay_widget.clear_assignments()

    def startDrag(self, event):
        """Start the drag operation."""
        item = self.schedule_list.currentItem()
        if item:
            mime_data = QMimeData()
            mime_data.setText(item.text())  # You can customize this to include more data

            drag = QDrag(self)
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)

    def handle_login_status_change(self):
        """Handle changes in login status"""
        self.refresh()