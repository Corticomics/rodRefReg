from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QLabel, QPushButton, QHBoxLayout,
    QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt

class SchedulesTab(QWidget):
    def __init__(self, settings, print_to_terminal):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Instruction Label
        instruction_label = QLabel("Drag and drop animals to relays to create watering schedules:")
        self.layout.addWidget(instruction_label)

        # Horizontal layout for Relay List and Animal List
        self.drag_drop_layout = QHBoxLayout()

        # Relay List
        self.relay_list = QListWidget()
        self.relay_list.setFixedWidth(200)
        self.relay_list.setSelectionMode(QListWidget.SingleSelection)
        self.relay_list.setDragEnabled(False)
        self.relay_list.setAcceptDrops(True)
        self.relay_list.setDefaultDropAction(Qt.MoveAction)
        self.relay_list.setDragDropMode(QListWidget.DropOnly)
        self.relay_list.setAlternatingRowColors(True)
        self.relay_list.setSortingEnabled(True)
        self.relay_list.setDragDropOverwriteMode(False)
        self.relay_list.setSpacing(2)
        self.populate_relays()
        self.drag_drop_layout.addWidget(self.relay_list)

        # Animal List
        self.animal_list = QListWidget()
        self.animal_list.setFixedWidth(200)
        self.animal_list.setSelectionMode(QListWidget.MultiSelection)
        self.animal_list.setDragEnabled(True)
        self.animal_list.setAcceptDrops(False)
        self.animal_list.setDragDropMode(QListWidget.DragOnly)
        self.animal_list.setDefaultDropAction(Qt.MoveAction)
        self.animal_list.setAlternatingRowColors(True)
        self.animal_list.setSortingEnabled(True)
        self.animal_list.setDragDropOverwriteMode(False)
        self.animal_list.setSpacing(2)
        self.populate_animals()
        self.drag_drop_layout.addWidget(self.animal_list)

        self.layout.addLayout(self.drag_drop_layout)

        # Buttons
        buttons_layout = QHBoxLayout()
        add_schedule_button = QPushButton("Add Schedule")
        remove_schedule_button = QPushButton("Remove Selected Schedule")
        buttons_layout.addWidget(add_schedule_button)
        buttons_layout.addWidget(remove_schedule_button)
        self.layout.addLayout(buttons_layout)

        # Connect Buttons
        add_schedule_button.clicked.connect(self.add_schedule)
        remove_schedule_button.clicked.connect(self.remove_schedule)

        # Schedule List
        self.schedule_list = QListWidget()
        self.schedule_list.setSelectionMode(QListWidget.SingleSelection)
        self.layout.addWidget(QLabel("Existing Watering Schedules:"))
        self.layout.addWidget(self.schedule_list)
        self.load_schedules()

    def populate_relays(self):
        """Populate the relay list based on the relay_pairs in settings."""
        self.relay_list.clear()
        relay_pairs = self.settings.get('relay_pairs', [])
        for relay in relay_pairs:
            relay_str = f"Relay {relay[0]} & Relay {relay[1]}"
            self.relay_list.addItem(relay_str)

    def populate_animals(self):
        """Populate the animal list from the database."""
        self.animal_list.clear()
        animals = self.settings.get('animals', {})
        for animal_id, animal_info in animals.items():
            animal_name = animal_info.get('name', f"Animal {animal_id}")
            self.animal_list.addItem(animal_name)

    def add_schedule(self):
        """Add a new watering schedule by dragging and dropping animals to a relay."""
        selected_relays = self.relay_list.selectedItems()
        selected_animals = self.animal_list.selectedItems()

        if not selected_relays:
            QMessageBox.warning(self, "No Relay Selected", "Please select a relay to assign the schedule.")
            return

        if not selected_animals:
            QMessageBox.warning(self, "No Animals Selected", "Please select at least one animal for the schedule.")
            return

        relay = selected_relays[0].text()
        animals = [animal.text() for animal in selected_animals]

        schedule_name, ok = QInputDialog.getText(self, "Schedule Name", "Enter a name for the schedule:")
        if not ok or not schedule_name:
            return

        # Save the schedule to settings
        if 'schedules' not in self.settings:
            self.settings['schedules'] = []

        # Check for duplicate schedule names
        for sched in self.settings['schedules']:
            if sched['name'] == schedule_name:
                QMessageBox.warning(self, "Duplicate Schedule", "A schedule with this name already exists.")
                return

        schedule = {
            'name': schedule_name,
            'relay': relay,
            'animals': animals
        }
        self.settings['schedules'].append(schedule)
        self.print_to_terminal(f"Added schedule '{schedule_name}' for {relay} with animals {', '.join(animals)}.")
        self.save_schedules()
        self.load_schedules()

    def remove_schedule(self):
        """Remove the selected watering schedule."""
        selected_item = self.schedule_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Schedule Selected", "Please select a schedule to remove.")
            return

        schedule_name = selected_item.text()
        confirm = QMessageBox.question(
            self, "Confirm Removal",
            f"Are you sure you want to remove the schedule '{schedule_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # Remove the schedule from settings
            self.settings['schedules'] = [sched for sched in self.settings['schedules'] if sched['name'] != schedule_name]
            self.print_to_terminal(f"Removed schedule '{schedule_name}'.")
            self.save_schedules()
            self.load_schedules()

    def load_schedules(self):
        """Load schedules from settings into the schedule list."""
        self.schedule_list.clear()
        schedules = self.settings.get('schedules', [])
        for sched in schedules:
            relay = sched.get('relay', 'Unknown Relay')
            animals = ', '.join(sched.get('animals', []))
            schedule_str = f"{sched.get('name', 'Unnamed')} - {relay} - Animals: {animals}"
            self.schedule_list.addItem(schedule_str)

    def save_schedules(self):
        """Save schedules to the settings.json file."""
        try:
            from settings.config import save_settings
            save_settings(self.settings)
            self.print_to_terminal("Schedules saved successfully.")
        except Exception as e:
            self.print_to_terminal(f"Error saving schedules: {e}")