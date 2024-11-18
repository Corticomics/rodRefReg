# ui/schedules_tab.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QHBoxLayout, QDialog, QFormLayout, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt
from models.relay_unit import RelayUnit
from models.Schedule import Schedule
from datetime import datetime

# In schedules_tab.py
class SchedulesTab(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler, login_system):
        super().__init__()
        
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system

        # Change main layout to QHBoxLayout
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Left side: Animal List
        self.left_layout = QVBoxLayout()
        self.left_widget = QWidget()
        self.left_widget.setLayout(self.left_layout)

        self.animal_list = QListWidget()
        self.animal_list.setDragEnabled(True)
        self.animal_list.setSelectionMode(QListWidget.SingleSelection)
        self.animal_list.setDefaultDropAction(Qt.MoveAction)

        self.left_layout.addWidget(QLabel("Available Animals"))
        self.left_layout.addWidget(self.animal_list)

        # Right side: Relay Units
        self.right_layout = QVBoxLayout()
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.right_layout)

        # Relay containers will be added to right_layout
        self.relay_containers = {}
        self.load_relay_units()

        # Add left and right widgets to the main layout
        self.layout.addWidget(self.left_widget)
        self.layout.addWidget(self.right_widget)

        # Load animals from the database
        self.load_animals()

        # Finalize Schedule button
        self.finalize_button = QPushButton("Finalize Schedule")
        self.finalize_button.clicked.connect(self.finalize_schedule)
        self.layout.addWidget(self.finalize_button)
        self.relay_containers = {}

    def load_relay_units(self):
        """Load relay units and create containers."""
        # Load relay units
        self.relay_units = self.database_handler.get_all_relay_units()
        if not self.relay_units:
            # If no relay units exist, create them based on settings
            self.initialize_relay_units()

        for relay_unit in self.relay_units:
            container = QListWidget()
            container.setAcceptDrops(True)
            container.setDragDropMode(QListWidget.InternalMove)
            container.setDefaultDropAction(Qt.MoveAction)
            container.setFixedSize(200, 60)  # Adjust size to fit one animal
            container.setMaximumHeight(60)
            container.setStyleSheet("QListWidget { background-color: #f0f0f0; }")
            container.objectName = f"Relay Unit {relay_unit.unit_id}"
            self.relay_containers[relay_unit.unit_id] = container

            relay_layout = QVBoxLayout()
            relay_label = QLabel(f"Relay Unit {relay_unit.unit_id}")
            relay_label.setAlignment(Qt.AlignCenter)
            relay_layout.addWidget(relay_label)
            relay_layout.addWidget(container)

            # Add relay_layout to the right_layout
            self.right_layout.addLayout(relay_layout)

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

    def initialize_relay_units(self):
        """Create relay units based on settings."""
        relay_pairs = self.settings.get('relay_pairs', [])
        unit_id = 1
        for pair in relay_pairs:
            relay_unit = RelayUnit(unit_id=unit_id, relay_ids=pair)
            self.database_handler.add_relay_unit(relay_unit)
            self.relay_units.append(relay_unit)
            unit_id += 1

    def finalize_schedule(self):
        """Finalize schedule by prompting for water quantities per relay."""
        relay_assignments = {}

        for unit_id, container in self.relay_containers.items():
            relay_assignments[unit_id] = []
            for i in range(container.count()):
                item = container.item(i)
                animal = item.data(Qt.UserRole)
                relay_assignments[unit_id].append(animal)

        # Open water quantity dialog for each relay
        self.enter_water_quantities(relay_assignments)

    def enter_water_quantities(self, relay_assignments):
        """Open a dialog to enter water quantity per relay."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Enter Water Quantities")
        form_layout = QFormLayout(dialog)

        water_inputs = {}

        # Recommended values for water quantity
        WATER_MIN = 5  # mL
        WATER_MAX = 10  # mL

        for unit_id, animals in relay_assignments.items():
            if animals:
                input_field = QLineEdit()
                input_field.setPlaceholderText(f"Recommended: {WATER_MIN}-{WATER_MAX} mL")
                water_inputs[unit_id] = input_field
                form_layout.addRow(f"Relay Unit {unit_id}:", input_field)

        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(lambda: self.validate_water_inputs(water_inputs, relay_assignments, WATER_MIN, WATER_MAX, dialog))
        form_layout.addWidget(submit_button)

        dialog.setLayout(form_layout)
        dialog.exec_()

    def validate_water_inputs(self, water_inputs, relay_assignments, min_val, max_val, dialog):
        """Validate water inputs and save schedules."""
        schedules = []
        for unit_id, input_field in water_inputs.items():
            try:
                water_amount = float(input_field.text())
                if not (min_val <= water_amount <= max_val):
                    QMessageBox.warning(self, "Water Amount Warning",
                                        f"Relay Unit {unit_id} water amount is outside recommended range ({min_val}-{max_val} mL).")
                # Create schedule object
                schedule = Schedule(
                    schedule_id=None,
                    name=f"Schedule for Relay Unit {unit_id}",
                    relay_unit_id=unit_id,
                    water_volume=water_amount,
                    start_time=datetime.now().isoformat(),
                    end_time=datetime.now().isoformat(),
                    created_by=self.login_system.get_current_trainer()['trainer_id'],
                    is_super_user=self.login_system.get_current_trainer()['role'] == 'super'
                )
                # Add animal IDs
                schedule.animals = [animal.animal_id for animal in relay_assignments[unit_id]]
                schedules.append(schedule)
            except ValueError:
                QMessageBox.critical(self, "Invalid Input", f"Please enter a valid number for Relay Unit {unit_id}.")
                return  # Exit if any input is invalid

        # Save schedules to the database
        for schedule in schedules:
            self.database_handler.add_schedule(schedule)

        # Log action if super user
        if self.login_system.get_current_trainer()['role'] == 'super':
            self.log_super_user_action(schedules)

        QMessageBox.information(self, "Schedule Saved", "Schedule and water quantities have been saved.")
        dialog.accept()  # Close the dialog if inputs are valid

    def log_super_user_action(self, schedules):
        """Log actions performed by super user."""
        super_user_id = self.login_system.get_current_trainer()['trainer_id']
        action = "created schedule"
        details = "\n".join([str(schedule.to_dict()) for schedule in schedules])
        self.database_handler.log_action(super_user_id, action, details)

    def load_schedules(self):
        """Load schedules from the database and display them."""
        # Implement this method based on your application's requirements
        pass