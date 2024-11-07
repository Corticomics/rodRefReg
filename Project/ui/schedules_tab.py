from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QDialog
from .drag_drop_container import DragDropContainer

class SchedulesTab(QWidget):
    def __init__(self, settings, database_handler):
        super().__init__()
        self.settings = settings
        self.database_handler = database_handler  # Set database_handler here

        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        # Available schedules list and buttons
        self.schedules_list = QListWidget()
        self.layout.addWidget(QLabel("Available Schedules"))
        self.layout.addWidget(self.schedules_list)

        # Load existing schedules
        self.load_schedules()

        # Open and create schedule buttons
        button_layout = QHBoxLayout()
        open_button = QPushButton("Open Schedule")
        open_button.clicked.connect(self.open_schedule)
        create_button = QPushButton("Create Schedule")
        create_button.clicked.connect(self.create_schedule)
        button_layout.addWidget(open_button)
        button_layout.addWidget(create_button)
        self.layout.addLayout(button_layout)

    def load_schedules(self):
        # Use database_handler to get schedules
        self.schedules_list.clear()
        schedules = self.database_handler.get_all_schedules()
        for schedule in schedules:
            self.schedules_list.addItem(f"Schedule ID: {schedule['schedule_id']} - {schedule['name']}")

    def open_schedule(self):
        selected_item = self.schedules_list.currentItem()
        if selected_item:
            schedule_id = int(selected_item.text().split(":")[1].strip().split(" - ")[0])
            schedule = self.database_handler.get_schedule(schedule_id)
            self.show_schedule_dialog(schedule, edit_mode=True)

    def create_schedule(self):
        self.show_schedule_dialog(edit_mode=False)

    def show_schedule_dialog(self, schedule=None, edit_mode=False):
        dialog = ScheduleDialog(self.database_handler, schedule, edit_mode)
        if dialog.exec_() == QDialog.Accepted:
            self.load_schedules()  # Reload schedules if changes were made


class ScheduleDialog(QDialog):
    def __init__(self, database_handler, schedule=None, edit_mode=False):
        super().__init__()
        self.database_handler = database_handler
        self.schedule = schedule or {}
        self.edit_mode = edit_mode
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Edit Schedule" if self.edit_mode else "Create Schedule")
        layout = QVBoxLayout(self)

        # Display relay containers as bins
        relays_layout = QHBoxLayout()
        relay_pairs = [(1, 2), (3, 4), (5, 6), (7, 8)]
        self.relay_containers = {}

        for pair in relay_pairs:
            container = DragDropContainer(pair)
            container.setTitle(f"Relay {pair[0]} & {pair[1]}")
            self.relay_containers[pair] = container
            relays_layout.addWidget(container)

        layout.addLayout(relays_layout)

        # Add Save/Cancel buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save" if self.edit_mode else "Create")
        save_button.clicked.connect(self.save_schedule)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # If editing, load animals into containers
        if self.edit_mode and self.schedule:
            self.load_animals_into_containers(self.schedule)

    def load_animals_into_containers(self, schedule):
        for relay, animals in schedule.get("relay_assignments", {}).items():
            for animal_id in animals:
                animal_name = f"Animal {animal_id}"  # Placeholder; fetch the real name if available
                self.relay_containers[relay].add_animal(animal_name, animal_id)

    def save_schedule(self):
        # Collect relay assignments
        relay_assignments = {}
        for relay_pair, container in self.relay_containers.items():
            relay_assignments[relay_pair] = container.get_animal_ids()

        # Save schedule
        new_schedule = {
            "name": self.schedule.get("name", "Unnamed Schedule"),
            "relay_assignments": relay_assignments
        }
        if self.edit_mode:
            self.database_handler.update_schedule(self.schedule['schedule_id'], new_schedule)
        else:
            self.database_handler.add_schedule(new_schedule)
        self.accept()