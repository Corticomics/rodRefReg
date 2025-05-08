# ui/schedules_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QInputDialog,
    QPushButton, QMessageBox, QScrollArea, QListWidget, QListWidgetItem, QComboBox, QDialog, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QRect, QPoint, QSize
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QLinearGradient, QPen, QColor, QFont
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
        self.relay_units = {}  # Dictionary to store relay unit widgets by ID

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)  # Restore reasonable margins
        
        # Common GroupBox style for all columns
        groupbox_style = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e4e8;
                border-radius: 8px;
                margin-top: 1.5ex;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                background-color: white;
            }
        """
        
        # Available animals section (left column)
        self.available_animals_list = AvailableAnimalsList(self.database_handler, self)
        available_animals_group = QGroupBox("Available Animals")
        available_animals_group.setStyleSheet(groupbox_style)
        available_animals_layout = QVBoxLayout()
        
        # Add mode selector at the top
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Delivery Mode:")
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Staggered", "Instant"])
        self.mode_selector.currentTextChanged.connect(self.on_mode_changed)
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
        """)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_selector)
        available_animals_layout.addLayout(mode_layout)
        
        available_animals_layout.addWidget(self.available_animals_list)
        available_animals_group.setLayout(available_animals_layout)
        
        # Relay units section (middle column)
        self.relay_units_container = QScrollArea()
        self.relay_units_container.setWidgetResizable(True)
        relay_units_widget = QWidget()
        self.relay_units_layout = QVBoxLayout(relay_units_widget)
        self.relay_units_layout.setAlignment(Qt.AlignTop)
        self.relay_units_layout.setSpacing(15)  # More spacing between relay units
        self.relay_units_container.setWidget(relay_units_widget)
        
        relay_units_group = QGroupBox("Relay Units")
        relay_units_group.setStyleSheet(groupbox_style)
        relay_units_group_layout = QVBoxLayout()
        
        # Add Clear All Assignments button at the top
        self.clear_assignments_button = QPushButton("Clear All Assignments")
        self.clear_assignments_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        self.clear_assignments_button.clicked.connect(self.clear_all)
        relay_units_group_layout.addWidget(self.clear_assignments_button)
        relay_units_group_layout.addWidget(self.relay_units_container)
        relay_units_group.setLayout(relay_units_group_layout)
        
        # Saved schedules section (right column)
        schedules_group = QGroupBox("Saved Schedules")
        schedules_group.setStyleSheet(groupbox_style)
        schedules_layout = QVBoxLayout()
        
        # Schedule list widget with improved styling
        self.schedule_list = QListWidget()
        self.schedule_list.setSelectionMode(QListWidget.SingleSelection)
        self.schedule_list.itemClicked.connect(self.load_selected_schedule)
        # Connect mousePressEvent to handle dragging schedules
        self.schedule_list.mousePressEvent = self.schedule_list_mouse_press
        self.schedule_list.setDragEnabled(True)  # Enable dragging from the list
        self.schedule_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e4e8;
                border-radius: 4px;
                padding: 5px;
                margin-bottom: 10px;
                background-color: #f8f9fa;
            }
            QListWidget::item {
                border-bottom: 1px solid #f0f0f0;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
        """)
        schedules_layout.addWidget(self.schedule_list)
        
        # Save Schedule button - the only button we'll keep
        self.save_button = QPushButton("Save Schedule")
        self.save_button.setMinimumHeight(40)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1666d4;
            }
            QPushButton:pressed {
                background-color: #125bbf;
            }
        """)
        self.save_button.clicked.connect(self.save_current_schedule)
        schedules_layout.addWidget(self.save_button)
        
        schedules_layout.addStretch()
        schedules_group.setLayout(schedules_layout)
        
        # Set column proportions (1:2:1 ratio)
        main_layout.addWidget(available_animals_group, 1)  # Left column - 25%
        main_layout.addWidget(relay_units_group, 2)        # Middle column - 50% 
        main_layout.addWidget(schedules_group, 1)          # Right column - 25%
        
        self.setLayout(main_layout)
        
        # Initialize relay units
        self.initialize_relay_units()

        # Load animals and schedules
        self.load_animals()
        self.load_schedules()

        # Connect the mode selector to emit the mode_changed signal
        self.mode_selector.currentTextChanged.connect(self.mode_changed.emit)

        # Connect refresh to login system changes
        self.login_system.login_status_changed.connect(self.refresh)

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
            QScrollArea:hover QScrollBar::handle:horizontal, 
            QScrollArea:hover QScrollBar::handle:vertical,
            QListWidget:hover QScrollBar::handle:horizontal,
            QListWidget:hover QScrollBar::handle:vertical,
            QTableWidget:hover QScrollBar::handle:horizontal, 
            QTableWidget:hover QScrollBar::handle:vertical {
                background: rgba(26, 115, 232, 0.5);  /* Show on hover */
            }
        """)

    def initialize_relay_units(self):
        """Initialize the relay unit widgets based on the database configuration."""
        # Clear existing relay units
        self.clear_relay_units_layout()
        
        # Get relay units from database or use defaults if not configured
        try:
            # Try to use get_relay_units first
            relay_units = self.database_handler.get_relay_units()
        except AttributeError:
            try:
                # Fall back to get_all_relay_units if available
                print("Falling back to get_all_relay_units")
                relay_units = self.database_handler.get_all_relay_units()
            except AttributeError:
                # No relay unit retrieval method available, use defaults
                print("No relay unit retrieval method available, using defaults")
                relay_units = []
        
        if not relay_units or len(relay_units) == 0:
            # Default setup: 6 relay units with 2 relays each
            relay_units = []
            for i in range(1, 7):
                relay_ids = (i * 2 - 1, i * 2)
                relay_unit = RelayUnit(i, relay_ids)
                relay_units.append(relay_unit)
        
        # Create widgets for each relay unit
        for relay_unit in relay_units:
            widget = RelayUnitWidget(
                relay_unit,
                self.database_handler,
                self.available_animals_list,
                self.pump_controller
            )
            # Set initial mode from mode selector
            widget.set_mode(self.mode_selector.currentText())
            self.relay_units[relay_unit.unit_id] = widget
            self.relay_units_layout.addWidget(widget)
        
    def clear_relay_units_layout(self):
        """Clear all relay unit widgets from the layout."""
        # Remove all widgets from the layout
        for i in reversed(range(self.relay_units_layout.count())):
            item = self.relay_units_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        # Clear the relay units dictionary
        self.relay_units.clear()
        
    def apply_schedule(self):
        """Apply the current water delivery schedule."""
        # Gather schedule data from all relay units
        schedule_data = {}
        
        for unit_id, relay_widget in self.relay_units.items():
            # Skip relay units with no animal assigned
            if not relay_widget.assigned_animal:
                continue
            
            animal_id = relay_widget.assigned_animal.id
            delivery_slots = []
            
            # Get all water delivery slots for this relay unit
            if relay_widget.current_mode == "Instant":
                # For instant mode, gather individual delivery slots
                for slot_widget in relay_widget.delivery_slots:
                    if not slot_widget.is_deleted:
                        delivery_time = slot_widget.datetime_picker.dateTime().toPython()
                        volume = float(slot_widget.volume_input.text() or 0)
                        delivery_slots.append({
                            "time": delivery_time,
                            "volume": volume
                        })
            elif relay_widget.current_mode == "Staggered":
                # For staggered mode, gather start and end time ranges
                # Implementation depends on your UI design
                # This is a placeholder - adjust according to your UI
                pass
            
            # Add to schedule data
            if delivery_slots:
                schedule_data[animal_id] = {
                    "relay_unit_id": unit_id,
                    "relay_ids": relay_widget.relay_unit.relay_ids,
                    "delivery_slots": delivery_slots,
                    "mode": relay_widget.current_mode
                }
        
        # Save schedule to database
        if schedule_data:
            success = self.database_handler.save_water_schedule(schedule_data)
            if success:
                QMessageBox.information(self, "Schedule Applied", 
                                       "The water delivery schedule has been successfully applied.")
            else:
                QMessageBox.warning(self, "Schedule Error", 
                                  "There was an error applying the water delivery schedule.")
        else:
            QMessageBox.information(self, "No Schedule", 
                                   "No water delivery schedule to apply. Please assign animals and set delivery times.")
    
    def clear_all(self):
        """Clear all assignments and schedules."""
        reply = QMessageBox.question(self, "Clear All", 
                                   "Are you sure you want to clear all animal assignments and schedules?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Reinitialize all relay unit widgets
            self.initialize_relay_units()
            
            QMessageBox.information(self, "Cleared", 
                                   "All animal assignments and schedules have been cleared.")
    
    def export_schedule(self):
        """Export the current schedule to a file."""
        # Implement export functionality
        # This is a placeholder
        QMessageBox.information(self, "Export Schedule", 
                               "Schedule export functionality will be implemented here.")
    
    def import_schedule(self):
        """Import a schedule from a file."""
        # Implement import functionality
        # This is a placeholder
        QMessageBox.information(self, "Import Schedule", 
                               "Schedule import functionality will be implemented here.")

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
            
            self.available_animals_list.clear()
            for animal in animals:
                item_text = f"{animal.lab_animal_id} - {animal.name}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, animal)
                self.available_animals_list.addItem(item)
                
        except Exception as e:
            self.print_to_terminal(f"Error loading animals: {e}")

    def load_schedules(self):
        """Load saved schedules and display them in the schedule list."""
        # Safety check in case schedule_list hasn't been initialized yet
        if not hasattr(self, 'schedule_list'):
            self.print_to_terminal("Warning: schedule_list not initialized. Skipping schedule loading.")
            return
            
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
        for widget in self.relay_units.values():
            widget.set_mode(mode)
        # Emit signal to inform other components
        self.mode_changed.emit(mode)

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
            for unit_id, relay_widget in self.relay_units.items():
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
            for unit_id, relay_widget in self.relay_units.items():
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

                        # --- Add this section to populate schedule.window_data ---
                        animal_id_str = str(animal.animal_id)
                        if animal_id_str not in schedule.window_data:
                            schedule.window_data[animal_id_str] = {}
                        
                        # Assuming only one window per animal in this widget for now
                        # If multiple StaggeredDeliverySlots are added, this needs adjustment
                        if relay_data['delivery_schedule']:
                            window = relay_data['delivery_schedule'][0] # Get the first window
                            schedule.window_data[animal_id_str]['start_time'] = window['start_time'].isoformat()
                            schedule.window_data[animal_id_str]['end_time'] = window['end_time'].isoformat()
                        # --- End of added section ---

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
        for relay_widget in self.relay_units.values():
            relay_widget.clear_assignments()

        # Load schedule data
        schedule_details = self.database_handler.get_schedule_details(schedule.schedule_id)

        for schedule_detail in schedule_details:
            relay_unit_id = schedule_detail['relay_unit_id']
            if relay_unit_id in self.relay_units:
                relay_widget = self.relay_units[relay_unit_id]
                
                # Set delivery mode
                mode = schedule_detail.get('delivery_mode', 'staggered').capitalize()
                relay_widget.set_mode(mode)
                
                # Load animals
                animals = []
                for animal_id in schedule_detail['animal_ids']:
                    animal = self.database_handler.get_animal_by_id(animal_id)
                    if animal:
                        animals.append(animal)
                
                # Set data based on mode - update to use new parameter names
                if schedule_detail.get('delivery_mode') == 'instant':
                    relay_widget.set_data(
                        animals=animals,
                        desired_water_output=schedule_detail.get('desired_water_outputs', {}),
                        delivery_schedule=schedule_detail.get('delivery_schedule', [])
                    )
                else:
                    relay_widget.set_data(
                        animals=animals,
                        desired_water_output=schedule_detail.get('desired_water_outputs', {})
                    )

    def refresh(self):
        """Refresh the UI components."""
        self.available_animals_list.clear()  # Clear the list first
        self.load_animals()  # Reload animals
        
        # Only try to load schedules if schedule_list exists
        if hasattr(self, 'schedule_list'):
            self.load_schedules()
            
        # Clear relay unit assignments
        for relay_widget in self.relay_units.values():
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
                
                # Create a visual representation for dragging
                pixmap = QPixmap(320, 80)  # Fixed size for the drag image
                pixmap.fill(Qt.transparent)  # Start with transparent background
                
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Draw rounded rectangle background with gradient
                gradient = QLinearGradient(0, 0, 0, 80)
                gradient.setColorAt(0, QColor("#e8f0fe"))
                gradient.setColorAt(1, QColor("#c2d9fc"))
                
                painter.setBrush(gradient)
                painter.setPen(QPen(QColor("#1a73e8"), 2))  # Blue border
                painter.drawRoundedRect(0, 0, pixmap.width(), pixmap.height(), 10, 10)
                
                # Draw schedule information
                painter.setFont(QFont("Arial", 12, QFont.Bold))
                painter.setPen(QColor("#1a73e8"))  # Blue text
                painter.drawText(QRect(15, 10, pixmap.width() - 30, 25), 
                                 Qt.AlignLeft | Qt.AlignVCenter, 
                                 f"Schedule: {schedule.name}")
                
                # Draw additional schedule details
                painter.setFont(QFont("Arial", 9))
                painter.setPen(QColor("#5f6368"))  # Gray text
                
                # Get count of animals in this schedule
                animal_count = len(schedule_detail['animal_ids'])
                delivery_mode = schedule_detail['delivery_mode'].capitalize()
                
                painter.drawText(QRect(15, 35, pixmap.width() - 30, 20), 
                                 Qt.AlignLeft | Qt.AlignVCenter, 
                                 f"Mode: {delivery_mode} • Animals: {animal_count}")
                
                painter.drawText(QRect(15, 55, pixmap.width() - 30, 20), 
                                 Qt.AlignLeft | Qt.AlignVCenter, 
                                 f"Drag to Run/Stop section to execute...")
                
                painter.end()
                
                # Apply the pixmap to the drag object
                drag.setPixmap(pixmap)
                drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))  # Center the pixmap
                
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
        for widget in self.relay_units.values():
            widget.set_mode(mode)

    def schedule_list_mouse_press(self, event):
        """Handle mouse press events on the schedule list"""
        if event.button() == Qt.LeftButton:
            item = self.schedule_list.itemAt(event.pos())
            if item:
                print(f"Starting drag for schedule: {item.text()}")
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
                    
                    # Create a visual representation for dragging
                    pixmap = QPixmap(320, 80)  # Fixed size for the drag image
                    pixmap.fill(Qt.transparent)  # Start with transparent background
                    
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    
                    # Draw rounded rectangle background with gradient
                    gradient = QLinearGradient(0, 0, 0, 80)
                    gradient.setColorAt(0, QColor("#e8f0fe"))
                    gradient.setColorAt(1, QColor("#c2d9fc"))
                    
                    painter.setBrush(gradient)
                    painter.setPen(QPen(QColor("#1a73e8"), 2))  # Blue border
                    painter.drawRoundedRect(0, 0, pixmap.width(), pixmap.height(), 10, 10)
                    
                    # Draw schedule information
                    painter.setFont(QFont("Arial", 12, QFont.Bold))
                    painter.setPen(QColor("#1a73e8"))  # Blue text
                    painter.drawText(QRect(15, 10, pixmap.width() - 30, 25), 
                                     Qt.AlignLeft | Qt.AlignVCenter, 
                                     f"Schedule: {schedule.name}")
                    
                    # Draw additional schedule details
                    painter.setFont(QFont("Arial", 9))
                    painter.setPen(QColor("#5f6368"))  # Gray text
                    
                    # Get count of animals in this schedule
                    animal_count = len(schedule_detail['animal_ids'])
                    delivery_mode = schedule_detail['delivery_mode'].capitalize()
                    
                    painter.drawText(QRect(15, 35, pixmap.width() - 30, 20), 
                                     Qt.AlignLeft | Qt.AlignVCenter, 
                                     f"Mode: {delivery_mode} • Animals: {animal_count}")
                    
                    painter.drawText(QRect(15, 55, pixmap.width() - 30, 20), 
                                     Qt.AlignLeft | Qt.AlignVCenter, 
                                     f"Drag to Run/Stop section to execute...")
                    
                    painter.end()
                    
                    # Apply the pixmap to the drag object
                    drag.setPixmap(pixmap)
                    drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))  # Center the pixmap
                    
                    print(f"Starting drag operation with mime type: application/x-schedule")
                    drag.exec_(Qt.CopyAction)
                    print(f"Drag operation completed")
                else:
                    print(f"Could not find schedule details for ID: {schedule.schedule_id}")
            else:
                print(f"No item found at position: {event.pos()}")
        
        # Call the parent's mouse press event
        super(QListWidget, self.schedule_list).mousePressEvent(event)

    def get_relay_assignments(self):
        """Get current relay unit assignments for all animals"""
        assignments = {}
        for unit_id, relay_widget in self.relay_units.items():
            if relay_widget.assigned_animal:
                assignments[str(relay_widget.assigned_animal.animal_id)] = unit_id
        return assignments

    def reset_all(self):
        """Reset all components to their default state"""
        try:
            # Reset mode selector to default
            self.mode_selector.setCurrentText("Staggered")
            
            # Clear animal list and reload
            self.available_animals_list.clear()
            self.load_animals()
            
            # Reset all relay units
            for relay_widget in self.relay_units.values():
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