# ui/schedules_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QInputDialog,
    QPushButton, QMessageBox, QScrollArea, QListWidget, QListWidgetItem, QComboBox, QDialog
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

        reset_button = QPushButton("Reset All")
        reset_button.clicked.connect(self.reset_all)
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 80px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        mode_layout.addWidget(reset_button)

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
        self.schedule_list.setDragEnabled(True)
        self.schedule_list.setDefaultDropAction(Qt.MoveAction)
        self.schedule_list.itemClicked.connect(self.load_selected_schedule)
        self.schedule_list.mousePressEvent = self.schedule_list_mouse_press

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

        # After creating mode_selector
        self.mode_selector.setStyleSheet("""
            QComboBox {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 120px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(:/icons/down-arrow.png);
            }
            QComboBox QAbstractItemView {
                background-color: #1a73e8;
                color: #202124;
                selection-background-color: #f8f9fa;
                selection-color: white;
            }
        """)

        # Refine table headers styling
        self.setStyleSheet("""
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #5f6368;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e0e4e8;
                font-weight: 500;
                font-size: 12px;
            }
            
            QTableWidget {
                gridline-color: #f0f0f0;
                border: 1px solid #e0e4e8;
                border-radius: 4px;
            }
            
            QTableWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #f0f0f0;
            }
        """)



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
            # Set initial mode from the mode selector
            relay_widget.set_mode(self.mode_selector.currentText())
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
        try:
            current_trainer = self.login_system.get_current_trainer()
            if not current_trainer:
                return
            
            trainer_id = current_trainer['trainer_id']
            role = current_trainer['role']
            is_super = role == 'super'
            
            # Get all animals if super user, otherwise get trainer's animals
            if is_super:
                animals = self.database_handler.get_all_animals()
            else:
                animals = self.database_handler.get_animals(trainer_id, role)
                self.print_to_terminal(f"Loaded {len(animals)} animals for trainer {trainer_id}")
            
            self.animal_list.clear()
            for animal in animals:
                item_text = f"{animal.lab_animal_id} - {animal.name}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, animal)
                self.animal_list.addItem(item)
                
        except Exception as e:
            self.print_to_terminal(f"Error loading animals: {e}")

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

        try:
            # Get delivery mode from mode selector
            delivery_mode = self.mode_selector.currentText().lower()
            
            # Initialize time variables
            min_time = None
            max_time = None
            total_volume = 0
            
            # Calculate schedule window based on delivery slots
            for unit_id, relay_widget in self.relay_unit_widgets.items():
                relay_data = relay_widget.get_data()
                if not relay_data['animals']:
                    continue
                    
                if delivery_mode == 'staggered':
                    for window in relay_data['delivery_schedule']:
                        start_time = window['start_time']
                        end_time = window['end_time']
                        total_volume += window['volume']
                        
                        if min_time is None or start_time < min_time:
                            min_time = start_time
                        if max_time is None or end_time > max_time:
                            max_time = end_time
                else:  # instant mode
                    for delivery in relay_data['delivery_schedule']:
                        total_volume += delivery['volume']
                        delivery_time = delivery['datetime']
                        
                        if min_time is None or delivery_time < min_time:
                            min_time = delivery_time
                        if max_time is None or delivery_time > max_time:
                            max_time = delivery_time

            if min_time is None:
                min_time = datetime.now()
            if max_time is None:
                max_time = datetime.now()

            # Create schedule object
            schedule = Schedule(
                schedule_id=None,
                name=schedule_name,
                water_volume=total_volume,
                start_time=min_time if isinstance(min_time, str) else min_time.isoformat(),
                end_time=max_time if isinstance(max_time, str) else max_time.isoformat(),
                created_by=current_trainer['trainer_id'],
                is_super_user=(current_trainer['role'] == 'super'),
                delivery_mode=delivery_mode
            )

            # Track all animals for both modes
            all_animals = set()

            # Add delivery data with correct relay unit assignments
            for unit_id, relay_widget in self.relay_unit_widgets.items():
                relay_data = relay_widget.get_data()
                if not relay_data['animals']:
                    continue

                if delivery_mode == 'instant':
                    print(f"save_current_schedule: adding instant deliveries for unit {unit_id}")
                    # Add animal to the set of all animals
                    animal_id = relay_data['animals'][0].animal_id
                    all_animals.add(animal_id)
                    
                    for delivery in relay_data['delivery_schedule']:
                        print(f"save_current_schedule: adding instant delivery for animal {animal_id} "
                              f"at {delivery['datetime']} with volume {delivery['volume']}")
                        schedule.add_instant_delivery(
                            animal_id,
                            delivery['datetime'],
                            delivery['volume'],
                            unit_id
                        )

                else:  # staggered mode
                    for animal in relay_data['animals']:
                        all_animals.add(animal.animal_id)
                        schedule.add_animal(
                            animal.animal_id,
                            unit_id,
                            relay_data['desired_water_output'].get(str(animal.animal_id))
                        )

            # Ensure animals are added to schedule for both modes
            schedule.animals = list(all_animals)

            # Save schedule to database using the appropriate method
            if delivery_mode == 'staggered':
                schedule_id = self.database_handler.add_staggered_schedule(schedule)
                print(f"save_current_schedule: added staggered schedule with details:" + str(schedule))
            else:
                print(f"save_current_schedule: adding instant schedule with details:" + str(schedule))
                schedule_id = self.database_handler.add_schedule(schedule)

            if schedule_id:
                QMessageBox.information(self, "Success", "Schedule saved successfully!")
                self.load_schedules()
            else:
                raise Exception("Failed to save schedule to database")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving schedule: {str(e)}")
            print(f"Error details: {traceback.format_exc()}")

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
                mode = schedule_detail.get('delivery_mode', 'staggered').capitalize()
                relay_widget.set_mode(mode)
                
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
        """Start the drag operation with proper selection handling"""
        item = self.schedule_list.currentItem()
        if not item:
            return
        
        try:
            schedule = item.data(Qt.UserRole)
            # Get fresh schedule details from database
            schedule_details = self.database_handler.get_schedule_details(schedule.schedule_id)
            if schedule_details:
                schedule_detail = schedule_details[0]
                
                mime_data = QMimeData()
                schedule_data = {
                    'schedule_id': schedule.schedule_id,
                    'name': schedule.name,
                    'water_volume': schedule.water_volume,
                    'start_time': schedule.start_time,
                    'end_time': schedule.end_time,
                    'created_by': schedule.created_by,
                    'is_super_user': schedule.is_super_user,
                    'delivery_mode': schedule_detail['delivery_mode'],
                    'animals': schedule_detail['animal_ids'],
                    'desired_water_outputs': schedule_detail.get('desired_water_outputs', {}),
                    'instant_deliveries': schedule_detail.get('delivery_schedule', [])
                }
                
                mime_data.setData('application/x-schedule', str(schedule_data).encode())
                
                drag = QDrag(self.schedule_list)
                drag.setMimeData(mime_data)
                
                # Clear selection after drag completes
                drag.finished.connect(lambda: self.schedule_list.clearSelection())
                
                drag.exec_(Qt.CopyAction)
                
        except Exception as e:
            self.print_to_terminal(f"Error starting drag: {e}")

    def handle_login_status_change(self):
        """Handle changes in login status"""
        self.refresh()

    def set_delivery_mode(self, mode):
        """Set the delivery mode for all relay units"""
        self.mode_selector.setCurrentText(mode)
        for widget in self.relay_unit_widgets.values():
            widget.set_mode(mode)

    def schedule_list_mouse_press(self, event):
        """Handle mouse press events on the schedule list"""
        if event.button() == Qt.LeftButton:
            item = self.schedule_list.itemAt(event.pos())
            if item:
                # Clear previous selection
                self.schedule_list.clearSelection()
                # Select the new item
                item.setSelected(True)
                # Only start drag if left button is pressed
                drag = QDrag(self.schedule_list)
                mime_data = QMimeData()
                
                schedule = item.data(Qt.UserRole)
                schedule_details = self.database_handler.get_schedule_details(schedule.schedule_id)
                
                if schedule_details:
                    schedule_detail = schedule_details[0]
                    schedule_data = {
                        'schedule_id': schedule.schedule_id,
                        'name': schedule.name,
                        'water_volume': schedule.water_volume,
                        'start_time': schedule.start_time,
                        'end_time': schedule.end_time,
                        'created_by': schedule.created_by,
                        'is_super_user': schedule.is_super_user,
                        'delivery_mode': schedule_detail['delivery_mode'],
                        'animals': schedule_detail['animal_ids'],
                        'desired_water_outputs': schedule_detail.get('desired_water_outputs', {}),
                        'instant_deliveries': schedule_detail.get('delivery_schedule', [])
                    }
                    
                    mime_data.setData('application/x-schedule', str(schedule_data).encode())
                    drag.setMimeData(mime_data)
                    drag.exec_(Qt.CopyAction)
        
        # Call the parent's mouse press event
        super(QListWidget, self.schedule_list).mousePressEvent(event)

    def get_relay_assignments(self):
        """Get current relay unit assignments for all animals"""
        assignments = {}
        for unit_id, relay_widget in self.relay_unit_widgets.items():
            if relay_widget.assigned_animal:
                assignments[str(relay_widget.assigned_animal.animal_id)] = unit_id
        return assignments

    def reset_all(self):
        """Reset all components to their default state"""
        try:
            # Reset mode selector to default
            self.mode_selector.setCurrentText("Staggered")
            
            # Clear animal list and reload
            self.animal_list.clear()
            self.load_animals()
            
            # Reset all relay units
            for relay_widget in self.relay_unit_widgets.values():
                relay_widget.clear_assignments()
            
            # Deselect any selected schedule
            self.schedule_list.clearSelection()
            
            # Reset the mode for all relay units
            self.set_delivery_mode("Staggered")
            
            # Notify user
            QMessageBox.information(
                self,
                "Reset Complete",
                "All settings have been reset to their default state."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Reset Error",
                f"An error occurred while resetting: {str(e)}"
            )
            self.print_to_terminal(f"Error during reset: {e}")
            traceback.print_exc()

    def update_time_window(self, start_time, end_time):
        """Update schedule time window"""
        self.start_time = start_time
        self.end_time = end_time