# app/ui/SuggestSettingsTab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QLabel, QPushButton, QComboBox, QDateTimeEdit, QMessageBox, QCheckBox
)
from PyQt5.QtCore import QDateTime, Qt

class SuggestSettingsTab(QWidget):
    def __init__(self, suggest_settings_callback, push_settings_callback, db_manager):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        form_layout = QFormLayout()
        self.entries = {}

        self.db_manager = db_manager  # Store db_manager for later use

        # Dropdown to select existing mice or choose 'Manual Input'
        self.mouse_selector = QComboBox()
        self.mouse_selector.addItem("Select a mouse")
        mice = self.db_manager.get_animals()
        for mouse in mice:
            self.mouse_selector.addItem(f"{mouse.animal_id} - {mouse.species}")
        self.mouse_selector.addItem("Manual Input")
        self.mouse_selector.currentIndexChanged.connect(self.toggle_weight_input)
        form_layout.addRow(QLabel("Select Mouse:"), self.mouse_selector)
        self.entries["selected_mouse"] = self.mouse_selector

        # Current Weight input (optional)
        self.current_weight_label = QLabel("Current Weight (g):")
        self.current_weight_input = QLineEdit()
        self.current_weight_input.setPlaceholderText("Enter current weight in grams")
        self.current_weight_input.setEnabled(False)  # Initially disabled
        form_layout.addRow(self.current_weight_label, self.current_weight_input)
        self.entries["current_weight"] = self.current_weight_input

        # Floor and Ceiling Water Volume based on Body Weight
        floor_volume_label = QLabel("Floor Water Volume (mL):")
        self.floor_volume_input = QLineEdit()
        self.floor_volume_input.setPlaceholderText("Calculated based on body weight")
        self.floor_volume_input.setReadOnly(True)
        form_layout.addRow(floor_volume_label, self.floor_volume_input)
        self.entries["floor_volume"] = self.floor_volume_input

        ceiling_volume_label = QLabel("Ceiling Water Volume (mL):")
        self.ceiling_volume_input = QLineEdit()
        self.ceiling_volume_input.setPlaceholderText("Calculated based on body weight")
        self.ceiling_volume_input.setReadOnly(True)
        form_layout.addRow(ceiling_volume_label, self.ceiling_volume_input)
        self.entries["ceiling_volume"] = self.ceiling_volume_input

        # Volume input per relay pair (optional, no validation required for button enable/disable)
        relay_pairs = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]
        for relay_pair in relay_pairs:
            volume_label = QLabel(f"Water Volume for Cage Pair (Relays {relay_pair[0]} & {relay_pair[1]}) (mL):")
            volume_input = QLineEdit()
            volume_input.setPlaceholderText(f"Volume for {relay_pair[0]} & {relay_pair[1]}")
            form_layout.addRow(volume_label, volume_input)
            self.entries[f"relay_{relay_pair[0]}_{relay_pair[1]}"] = volume_input

        # Frequency (required field)
        frequency_label = QLabel("Dispensing Frequency (times per day):")
        self.frequency_input = QLineEdit()
        self.frequency_input.setPlaceholderText("Enter number of times per day")
        form_layout.addRow(frequency_label, self.frequency_input)
        self.entries["frequency"] = self.frequency_input

        # Duration (required field)
        duration_label = QLabel("Duration (days):")
        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("Enter duration in days")
        form_layout.addRow(duration_label, self.duration_input)
        self.entries["duration"] = self.duration_input

        # Start Date and Time (required field)
        start_datetime_label = QLabel("Start Date and Time:")
        self.start_datetime_input = QDateTimeEdit()
        self.start_datetime_input.setCalendarPopup(True)
        self.start_datetime_input.setDateTime(QDateTime.currentDateTime())
        form_layout.addRow(start_datetime_label, self.start_datetime_input)
        self.entries["start_datetime"] = self.start_datetime_input

        self.layout.addLayout(form_layout)

        # Auto-Save Project Checkbox
        self.auto_save_checkbox = QCheckBox("Automatically Save Project After Pushing Settings")
        self.layout.addWidget(self.auto_save_checkbox)

        # Buttons
        button_layout = QVBoxLayout()

        suggest_button = QPushButton("Suggest Settings")
        suggest_button.clicked.connect(suggest_settings_callback)
        button_layout.addWidget(suggest_button)

        self.push_button = QPushButton("Push Settings")
        self.push_button.clicked.connect(self.push_settings_callback_wrapper)
        self.push_button.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.push_button)

        self.layout.addLayout(button_layout)

        # Connect signals to enable/disable the push button based on form validation
        self.frequency_input.textChanged.connect(self.validate_form)
        self.duration_input.textChanged.connect(self.validate_form)
        self.start_datetime_input.dateTimeChanged.connect(self.validate_form)
        self.current_weight_input.textChanged.connect(self.update_water_volumes)
        self.mouse_selector.currentIndexChanged.connect(self.update_selected_mouse)

        self.update_button_states()

    def toggle_weight_input(self):
        selected_text = self.mouse_selector.currentText()
        if selected_text == "Manual Input":
            self.current_weight_input.setEnabled(True)
        else:
            self.current_weight_input.setEnabled(False)
            self.update_selected_mouse()

    def update_selected_mouse(self):
        """Update the current weight based on selected mouse."""
        selected_text = self.mouse_selector.currentText()
        if selected_text and selected_text != "Select a mouse" and selected_text != "Manual Input":
            animal_id = selected_text.split(' - ')[0]
            mouse = self.db_manager.get_animal_by_id(animal_id)
            if mouse:
                self.current_weight_input.setText(str(mouse.body_weight))
                self.update_water_volumes()
        else:
            self.current_weight_input.clear()
            self.floor_volume_input.clear()
            self.ceiling_volume_input.clear()

    def update_water_volumes(self):
        """Update the floor and ceiling water volumes based on the current weight."""
        try:
            weight_text = self.current_weight_input.text().strip()
            if weight_text:
                body_weight = float(weight_text)
                floor_volume = self.calculate_floor_volume(body_weight)
                ceiling_volume = self.calculate_ceiling_volume(body_weight)
                self.floor_volume_input.setText(f"{floor_volume:.2f}")
                self.ceiling_volume_input.setText(f"{ceiling_volume:.2f}")
            else:
                self.floor_volume_input.clear()
                self.ceiling_volume_input.clear()
        except ValueError:
            self.floor_volume_input.setText("Invalid weight")
            self.ceiling_volume_input.setText("Invalid weight")

    def calculate_floor_volume(self, body_weight):
        # Example calculation: 5% of body weight
        return body_weight * 0.05

    def calculate_ceiling_volume(self, body_weight):
        # Example calculation: 10% of body weight
        return body_weight * 0.10

    def validate_form(self):
        """Validate if all required fields are filled."""
        frequency_valid = bool(self.frequency_input.text().strip())
        duration_valid = bool(self.duration_input.text().strip())
        start_datetime_valid = bool(self.start_datetime_input.dateTime().isValid())
        
        # Weight is required only if 'Manual Input' is selected
        if self.mouse_selector.currentText() == "Manual Input":
            current_weight_valid = bool(self.current_weight_input.text().strip())
        else:
            current_weight_valid = True  # Already filled based on selection

        # If all required fields are valid, enable the Push button
        if frequency_valid and duration_valid and start_datetime_valid and current_weight_valid:
            self.push_button.setEnabled(True)
            self.push_button.setStyleSheet("")
            self.push_button.setToolTip("")
        else:
            self.push_button.setEnabled(False)
            self.push_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)

    def update_button_states(self):
        """Initial setup of the Push button state."""
        self.validate_form()  # Initial validation on creation

    def push_settings_callback_wrapper(self):
        """Wrapper to handle auto-save functionality."""
        try:
            # Push settings as usual
            self.push_settings_callback()

            # Check if auto-save is enabled
            if self.auto_save_checkbox.isChecked():
                self.save_project()
        except Exception as e:
            self.print_to_terminal(f"Error pushing settings: {e}")

    def save_project(self):
        """Automatically save the project after pushing settings."""
        try:
            # Gather all necessary data to create a project
            selected_mouse_text = self.mouse_selector.currentText()
            if selected_mouse_text == "Manual Input":
                weight_text = self.current_weight_input.text().strip()
                if not weight_text:
                    QMessageBox.warning(self, "Input Required", "Please enter the current weight.")
                    return
                body_weight = float(weight_text)
                mouse_id = "Manual"
            else:
                mouse_id = selected_mouse_text.split(' - ')[0]
                mouse = self.db_manager.get_animal_by_id(mouse_id)
                body_weight = mouse.body_weight if mouse else 0.0

            # Gather relay pair assignments and volumes
            relay_volumes = {}
            relay_pairs = self.settings.get('relay_pairs', [])
            for pair in relay_pairs:
                volume = self.entries.get(f"relay_{pair[0]}_{pair[1]}", QLineEdit()).text().strip()
                relay_volumes[pair] = float(volume) if volume else 0.0

            # Create project name based on timestamp
            import datetime
            project_name = f"AutoProject_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Create project in the database
            project = self.db_manager.create_project(project_name, [self.db_manager.get_animal_by_id(mouse_id)], relay_volumes)
            if project:
                self.print_to_terminal(f"Auto-saved project '{project.project_id}' successfully.")
                QMessageBox.information(self, "Auto-Save Success", f"Project '{project.project_id}' saved successfully.")
            else:
                self.print_to_terminal("Failed to auto-save project.")
                QMessageBox.critical(self, "Auto-Save Error", "Failed to auto-save project.")
        except Exception as e:
            self.print_to_terminal(f"Error auto-saving project: {e}")
            QMessageBox.critical(self, "Auto-Save Error", f"Error auto-saving project: {e}")