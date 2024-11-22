# ui/schedules_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QInputDialog,
    QPushButton, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt
from datetime import datetime
from .relay_unit_widget import RelayUnitWidget
from models.Schedule import Schedule
from models.relay_unit import RelayUnit

class SchedulesTab(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler, login_system):
        super().__init__()

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system

        # Main layout: Horizontal box layout for three columns
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Left Column: Available Animals
        self.available_animals_widget = QWidget()
        self.available_animals_layout = QVBoxLayout()
        self.available_animals_widget.setLayout(self.available_animals_layout)

        self.animal_list = QListWidget()
        self.animal_list.setDragEnabled(True)
        self.animal_list.setSelectionMode(QListWidget.SingleSelection)
        self.animal_list.setDefaultDropAction(Qt.MoveAction)

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
        self.schedule_list.itemClicked.connect(self.load_selected_schedule)

        self.saved_schedules_layout.addWidget(QLabel("Saved Schedules"))
        self.saved_schedules_layout.addWidget(self.schedule_list)

        # Add columns to main layout
        self.layout.addWidget(self.available_animals_widget)
        self.layout.addWidget(self.relay_units_widget)
        self.layout.addWidget(self.saved_schedules_widget)

        # Load animals and schedules
        self.load_animals()
        self.load_schedules()

        # Save Schedule button
        self.save_schedule_button = QPushButton("Save Schedule")
        self.save_schedule_button.clicked.connect(self.save_current_schedule)
        self.layout.addWidget(self.save_schedule_button)

    def load_animals(self):
        """Load animals from the database and add them to the animal list."""
        current_trainer = self.login_system.get_current_trainer()
        if current_trainer:
            trainer_id = current_trainer['trainer_id']
            role = current_trainer['role']
            animals = self.database_handler.get_animals(trainer_id, role)
        else:
            animals = self.database_handler.get_all_animals()

        self.animal_list.clear()  # Clear existing items before loading
        for animal in animals:
            item = QListWidgetItem(f"{animal.name} ({animal.lab_animal_id})")
            item.setData(Qt.UserRole, animal)
            self.animal_list.addItem(item)

    def load_relay_units(self):
        """Load relay units and create RelayUnitWidgets."""
        self.relay_units_container_layout.addStretch()  # Add stretch to push items to the top
        self.relay_units_container_layout.setSpacing(10)

        # Load relay units from settings or database
        self.relay_units = self.database_handler.get_all_relay_units()
        if not self.relay_units:
            self.initialize_relay_units()

        for relay_unit in self.relay_units:
            relay_widget = RelayUnitWidget(relay_unit)
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
                    water_volume=relay_data['water_amount'],
                    start_time=datetime.now().isoformat(),
                    end_time=datetime.now().isoformat(),
                    created_by=current_trainer['trainer_id'],
                    is_super_user=(current_trainer['role'] == 'super')
                )
                schedule.animals = [animal.animal_id for animal in relay_data['animals']]
                schedule.desired_water_outputs = relay_data['desired_water_outputs']
                schedules.append(schedule)

        # Save schedules to the database
        for schedule in schedules:
            self.database_handler.add_schedule(schedule)

        QMessageBox.information(self, "Schedule Saved", "Schedule has been saved successfully.")
        self.load_schedules()

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
                # Fetch animal details
                animals = []
                for animal_id in schedule_detail['animal_ids']:
                    animal = self.database_handler.get_animal_by_id(animal_id)
                    if animal:
                        animals.append(animal)
                # Set data in relay widget
                relay_widget.set_data(animals, schedule_detail['water_volume'], schedule_detail['desired_water_outputs'])

    def refresh(self):
        """Refresh the UI components."""
        self.load_animals()
        self.load_schedules()
        for relay_widget in self.relay_unit_widgets.values():
            relay_widget.clear_assignments()