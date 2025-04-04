# ui/animals_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QMessageBox, QHBoxLayout, QDialog, QDialogButtonBox, QDateTimeEdit, QHeaderView, QComboBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QDateTime
from models.animal import Animal
from .edit_animal_dialog import EditAnimalDialog
import traceback
from datetime import datetime

class AnimalsTab(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler, login_system):
        super().__init__()
        self.settings = settings
        self.print_to_terminal = print_to_terminal or (lambda x: None)  # Fallback if not provided
        self.database_handler = database_handler
        self.login_system = login_system  # Store login_system for permission checks
        self.trainer_id = None  # Add this line back

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Modern styling for the instruction label
        instruction_label = QLabel("Manage Animal Data")
        instruction_label.setStyleSheet("""
            QLabel {
                color: #202124;
                font-size: 18px;
                font-weight: 600;
                padding: 16px 0;
            }
        """)
        self.layout.addWidget(instruction_label)

        # Setup filter section with modern styling
        filter_container = QWidget()
        filter_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        filter_layout = QHBoxLayout(filter_container)
        
        filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search animals...")
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        self.layout.addWidget(filter_container)

        # Setup the table with modern styling
        self.animals_table = QTableWidget()
        self.animals_table.setColumnCount(7)
        
        # Set headers with proper styling
        headers = ["Lab Animal ID", "Name", "Sex", "Initial Weight (g)", "Last Weight", "Last Weighted", "Last Watering"]
        self.animals_table.setHorizontalHeaderLabels(headers)
        
        # Configure table properties with improved sizing
        # Use Fixed mode for all columns except the last one
        for i in range(7):
            self.animals_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
        
        # Set specific column widths to ensure all information is visible
        self.animals_table.setColumnWidth(0, 120)  # Lab Animal ID
        self.animals_table.setColumnWidth(1, 120)  # Name
        self.animals_table.setColumnWidth(2, 80)   # Sex
        self.animals_table.setColumnWidth(3, 130)  # Initial Weight
        self.animals_table.setColumnWidth(4, 110)  # Last Weight
        self.animals_table.setColumnWidth(5, 160)  # Last Weighted
        self.animals_table.setColumnWidth(6, 160)  # Last Watering
        
        # Make the last column stretch to fill available space
        self.animals_table.horizontalHeader().setStretchLastSection(True)
        
        # Set size policy to expand horizontally
        self.animals_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Set row height and hide vertical headers for cleaner look
        self.animals_table.verticalHeader().setDefaultSectionSize(40) # Taller rows
        self.animals_table.verticalHeader().setVisible(False)  # Hide row numbers
        
        # Dynamic height based on content
        self.animals_table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.animals_table.setMinimumHeight(150)  # More conservative minimum height
        self.animals_table.setMaximumHeight(400)  # Add maximum height to prevent excessive space
        
        # Enable horizontal scrolling if needed but make it fill container width
        self.animals_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.animals_table.setMinimumWidth(self.width())  # Make table full width of container
        
        # Improve table appearance with alternating colors and grid
        self.animals_table.setAlternatingRowColors(True)
        self.animals_table.setShowGrid(True)  # Show grid lines for better visibility
        self.animals_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #1a73e8;      /* Blue border to match theme */
                border-radius: 8px;
                padding: 4px;
                gridline-color: #d0d0d0;        /* Darker grid lines */
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e4e8;
                color: #333333;                  /* Darker text for readability */
                font-weight: 500;                /* Semi-bold text */
            }
            QTableWidget::item:selected {
                background-color: #e8f0fe;       /* Light blue selection */
                color: #1a73e8;                  /* Blue text on selection */
            }
            QHeaderView::section {
                background-color: #e8f0fe;       /* Light blue headers */
                color: #1a73e8;                  /* Blue text for headers */
                padding: 10px 8px;               /* More vertical padding */
                border: 1px solid #1a73e8;       /* Blue border */
                border-bottom: 2px solid #1a73e8;/* Emphasize bottom border */
                font-weight: 600;                /* Bolder headers */
                font-size: 13px;                 /* Larger font size */
            }
            /* When table is empty, show a nicer message */
            QTableWidget[empty="true"]::item {
                border: none;
                padding: 20px;
                text-align: center;
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
            QTableWidget:hover QScrollBar::handle:horizontal, 
            QTableWidget:hover QScrollBar::handle:vertical {
                background: rgba(26, 115, 232, 0.5);  /* Show on table hover */
            }
        """)

        # Add table to layout with a title
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)  # Reduce container margins
        table_label = QLabel("Animals")
        table_label.setStyleSheet("""
            QLabel {
                color: #5f6368;
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 8px;
            }
        """)
        table_layout.addWidget(table_label)
        table_layout.addWidget(self.animals_table)
        self.layout.addWidget(table_container)

        # Action buttons with modern styling
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        
        add_button = QPushButton("Add Animal")
        edit_button = QPushButton("Edit")
        remove_button = QPushButton("Remove")
        
        for button in [add_button, edit_button, remove_button]:
            button.setMinimumWidth(100)
            button_layout.addWidget(button)
        
        button_layout.addStretch()
        self.layout.addWidget(button_container)

        # Connect signals
        add_button.clicked.connect(self.add_animal)
        edit_button.clicked.connect(self.edit_animal)
        remove_button.clicked.connect(self.remove_animal)
        self.filter_input.textChanged.connect(self.apply_filter)

        # Initial load
        self.load_animals()

    def calculate_days_ago(self, timestamp_str):
        """Convert timestamp to 'X days ago' format"""
        if not timestamp_str:
            return "Never"
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            delta = now - timestamp
            
            if delta.days == 0:
                if delta.seconds < 3600:  # Less than an hour
                    minutes = delta.seconds // 60
                    return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
                else:
                    hours = delta.seconds // 3600
                    return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif delta.days == 1:
                return "Yesterday"
            else:
                return f"{delta.days} days ago"
        except (ValueError, TypeError):
            return "Invalid date"

    def populate_animal_table(self, animals):
        """Populate the animals_table widget with the given animals."""
        self.animals_table.setRowCount(0)  # Clear existing rows

        for animal in animals:
            row_position = self.animals_table.rowCount()
            self.animals_table.insertRow(row_position)

            # Convert timestamps to "X days ago" format
            last_weighted_text = self.calculate_days_ago(animal.last_weighted)
            last_watering_text = self.calculate_days_ago(animal.last_watering)

            lab_animal_id_item = QTableWidgetItem(animal.lab_animal_id)
            name_item = QTableWidgetItem(animal.name)
            sex_item = QTableWidgetItem(animal.sex if animal.sex else "N/A")
            initial_weight_item = QTableWidgetItem(f"{animal.initial_weight:.1f}" if animal.initial_weight else "N/A")
            last_weight_item = QTableWidgetItem(f"{animal.last_weight:.1f}" if animal.last_weight else "N/A")
            last_weighted_item = QTableWidgetItem(last_weighted_text)
            last_watering_item = QTableWidgetItem(last_watering_text)
            
            # Set items in table
            self.animals_table.setItem(row_position, 0, lab_animal_id_item)
            self.animals_table.setItem(row_position, 1, name_item)
            self.animals_table.setItem(row_position, 2, sex_item)
            self.animals_table.setItem(row_position, 3, initial_weight_item)
            self.animals_table.setItem(row_position, 4, last_weight_item)
            self.animals_table.setItem(row_position, 5, last_weighted_item)
            self.animals_table.setItem(row_position, 6, last_watering_item)

            # Center-align text for better readability
            for col in range(7):
                item = self.animals_table.item(row_position, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

            # Store the original timestamp in the item's data for sorting
            last_weighted_item.setData(Qt.UserRole, animal.last_weighted or "")
            last_watering_item.setData(Qt.UserRole, animal.last_watering or "")

            lab_animal_id_item.setData(Qt.UserRole, animal)

            # Set fixed row height for better appearance
            self.animals_table.setRowHeight(row_position, 40)

        # Resize rows and make sure all data is visible after populating
        self.animals_table.resizeColumnsToContents()  # Ensure columns fit content

    def load_animals(self):
        """Load animals from the database, filtered by trainer_id if available."""
        try:
            current_trainer = self.login_system.get_current_trainer()
            if current_trainer:
                trainer_id = current_trainer['trainer_id']
                role = current_trainer['role']
                animals = self.database_handler.get_animals(trainer_id, role)
                if self.print_to_terminal:
                    self.print_to_terminal(f"Loaded {len(animals)} animals for trainer ID {trainer_id}")
            else:
                animals = self.database_handler.get_all_animals()
                if self.print_to_terminal:
                    self.print_to_terminal(f"Loaded {len(animals)} animals for all trainers (guest mode)")
            # Populate the UI with the animals table
            self.populate_animal_table(animals)
        except Exception as e:
            if self.print_to_terminal:
                self.print_to_terminal(f"Error loading animals: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "Load Animals Error", f"An error occurred while loading animals:\n{e}")

    def apply_filter(self, text):
        """Filter the animals in the table based on the input text."""
        for row in range(self.animals_table.rowCount()):
            match = False
            for column in range(self.animals_table.columnCount()):
                item = self.animals_table.item(row, column)
                if text.lower() in item.text().lower():
                    match = True
                    break
            self.animals_table.setRowHidden(row, not match)

    def add_animal(self):
        """Open dialog to add a new animal with error handling."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Animal")
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        lab_animal_id_input = QLineEdit()
        name_input = QLineEdit()
        initial_weight_input = QLineEdit()
        last_weight_input = QLineEdit()
        last_weighted_input = QDateTimeEdit()
        last_weighted_input.setCalendarPopup(True)
        last_weighted_input.setDateTime(QDateTime.currentDateTime())
        last_watering_input = QDateTimeEdit()
        last_watering_input.setCalendarPopup(True)
        last_watering_input.setDateTime(QDateTime.currentDateTime())

        # Add sex selection combo box
        sex_combo = QComboBox()
        sex_combo.addItems(["Select Sex", "male", "female"])
        sex_combo.setCurrentText("Select Sex")

        form_layout.addRow("Lab Animal ID:", lab_animal_id_input)
        form_layout.addRow("Name:", name_input)
        form_layout.addRow("Initial Weight (g):", initial_weight_input)
        form_layout.addRow("Last Weight (g):", last_weight_input)
        form_layout.addRow("Last Time Weighted:", last_weighted_input)
        form_layout.addRow("Last Watering:", last_watering_input)
        form_layout.addRow("Sex:", sex_combo)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            try:
                lab_animal_id = lab_animal_id_input.text().strip()
                name = name_input.text().strip()
                initial_weight_text = initial_weight_input.text().strip()
                last_weight_text = last_weight_input.text().strip()
                last_weighted = last_weighted_input.dateTime().toString("yyyy-MM-dd HH:mm")
                last_watering = last_watering_input.dateTime().toString("yyyy-MM-dd HH:mm")
                sex = sex_combo.currentText()
                if sex == "Select Sex":
                    sex = None

                # Validate inputs
                if not lab_animal_id or not name:
                    raise ValueError("Animal ID and name cannot be empty.")
                if not initial_weight_text:
                    raise ValueError("Initial weight cannot be empty.")
                initial_weight = float(initial_weight_text)
                last_weight = float(last_weight_text) if last_weight_text else None

                new_animal = Animal(
                    None,
                    lab_animal_id,
                    name,
                    initial_weight,
                    last_weight,
                    last_weighted,
                    last_watering,
                    sex
                )
                current_trainer = self.login_system.get_current_trainer()
                trainer_id = current_trainer['trainer_id'] if current_trainer else None

                animal_id = self.database_handler.add_animal(new_animal, trainer_id=trainer_id)

                if animal_id:
                    self.print_to_terminal(f"Animal '{name}' added with ID: {lab_animal_id}.")
                    self.load_animals()
                    self.notify_schedules_tab()  # Notify schedules tab of the change
                else:
                    QMessageBox.warning(self, "Add Error", "Failed to add animal. ID might already exist.")

            except ValueError as ve:
                QMessageBox.warning(self, "Input Error", f"Invalid input: {ve}")
                self.print_to_terminal(f"Input Error: {ve}")
            except Exception as e:
                QMessageBox.critical(self, "Add Error", f"Unexpected error: {e}")
                self.print_to_terminal(f"Unexpected error during add operation: {e}")

    def remove_animal(self):
        """Remove selected animal from the database with error handling."""
        selected_row = self.animals_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an animal to remove.")
            return

        # Retrieve the Animal object from the selected row
        lab_animal_id_item = self.animals_table.item(selected_row, 0)
        animal = lab_animal_id_item.data(Qt.UserRole)

        confirm = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove '{animal.name}' (Lab ID: {animal.lab_animal_id})?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                self.database_handler.remove_animal(animal.lab_animal_id)
                self.print_to_terminal(f"Removed animal '{animal.name}' with Lab ID {animal.lab_animal_id}.")
                self.load_animals()
            except Exception as e:
                QMessageBox.critical(self, "Remove Error", f"Error removing animal: {e}")
                self.print_to_terminal(f"Error removing animal '{animal.lab_animal_id}': {e}")

    def edit_animal(self):
        """Open dialog to edit the selected animal's information with error handling."""
        selected_row = self.animals_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an animal to edit.")
            return

        # Retrieve the Animal object from the selected row
        lab_animal_id_item = self.animals_table.item(selected_row, 0)
        animal = lab_animal_id_item.data(Qt.UserRole)

        # Pass `lab_animal_id` and other details to the EditAnimalDialog
        dialog = EditAnimalDialog(animal.animal_id, animal.to_dict(), self)

        try:
            if dialog.exec_() == QDialog.Accepted:
                updated_info = dialog.updated_info
                updated_animal = Animal(
                    animal_id=animal.animal_id,
                    lab_animal_id=animal.lab_animal_id,
                    name=updated_info['name'],
                    initial_weight=updated_info['initial_weight'],
                    last_weight=updated_info['last_weight'],
                    last_weighted=updated_info['last_weighted'],
                    last_watering=updated_info['last_watering'],
                    sex=updated_info['sex']
                )

                # Update the animal in the database
                self.database_handler.update_animal(updated_animal)

                # Notify and refresh
                self.print_to_terminal(f"Updated animal '{updated_animal.name}' (Lab ID: {updated_animal.lab_animal_id}).")
                self.load_animals()
                self.notify_schedules_tab()  # Notify schedules tab of the change
        except Exception as e:
            QMessageBox.critical(self, "Edit Error", f"Error updating animal: {e}")
            self.print_to_terminal(f"Unhandled exception in edit_animal: {e}")

    def notify_schedules_tab(self):
        """Notify the schedules tab that animals have been updated"""
        try:
            # Find the parent widget and access the schedules_tab
            parent = self.parent()
            while parent and not hasattr(parent, 'schedules_tab'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'schedules_tab'):
                parent.schedules_tab.refresh()
                self.print_to_terminal("Refreshed schedules tab after animal update")
        except Exception as e:
            self.print_to_terminal(f"Error refreshing schedules tab: {e}")
            traceback.print_exc()

    def resizeEvent(self, event):
        """Handle resize events to adjust table width to match container"""
        super().resizeEvent(event)
        # Update table width to match container width
        if hasattr(self, 'animals_table'):
            available_width = self.width() - 20  # Account for layout margins
            self.animals_table.setMinimumWidth(available_width)
            
            # Redistribute column widths based on available space
            if available_width > 800:  # For wide screens, give more space to timestamps
                self.animals_table.setColumnWidth(5, 180)  # Last Weighted
                self.animals_table.setColumnWidth(6, 180)  # Last Watering
            
            # Force update
            self.animals_table.updateGeometry()