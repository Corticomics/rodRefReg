from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, 
                           QTableWidgetItem, QTableWidget, QHBoxLayout, QPushButton, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
from models.Schedule import Schedule
from .schedule_table import ScheduleTable
import datetime
from models.database_handler import DatabaseHandler
import traceback

class ScheduleDropArea(QWidget):

    mode_changed = pyqtSignal(str)
    schedule_dropped = pyqtSignal(object)  # Signal for when schedule is dropped
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to maximize space
        self.setLayout(self.layout)
        
        # Initialize database handler
        self.database_handler = DatabaseHandler()
        
        # Drop area
        self.drop_widget = QWidget()
        self.drop_widget.setObjectName("DropArea")
        self.drop_widget.setProperty("state", "idle")
        self.drop_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Placeholder label
        self.placeholder = QLabel("Drop Schedule Here")
        self.placeholder.setAlignment(Qt.AlignCenter)
        
        drop_layout = QVBoxLayout()
        drop_layout.addWidget(self.placeholder)
        self.drop_widget.setLayout(drop_layout)
        
        # Schedule table (initially hidden)
        self.schedule_table = ScheduleTable()
        self.schedule_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Make read-only
        self.schedule_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.schedule_table.hide()
        
        # Scrollbars inherit from app QSS
        
        self.layout.addWidget(self.drop_widget)
        self.layout.addWidget(self.schedule_table)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        self.current_schedule = None
        
        # Enable double-click handling for both widgets
        self.drop_widget.mouseDoubleClickEvent = self.double_click_event
        self.schedule_table.mouseDoubleClickEvent = self.double_click_event
        
    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        formats = mime_data.formats()
        print(f"Drag enter event with formats: {formats}")
        
        if mime_data.hasFormat('application/x-schedule'):
            print(f"Accepting drag with schedule data")
            self.drop_widget.setProperty("state", "drag")
            self.drop_widget.style().unpolish(self.drop_widget)
            self.drop_widget.style().polish(self.drop_widget)
            event.acceptProposedAction()
        elif mime_data.hasText():
            print(f"Accepting drag with text: {mime_data.text()}")
            self.drop_widget.setProperty("state", "drag")
            self.drop_widget.style().unpolish(self.drop_widget)
            self.drop_widget.style().polish(self.drop_widget)
            event.acceptProposedAction()
        else:
            print(f"Rejecting drag - no recognized format")
            
    def dragLeaveEvent(self, event):
        """Reset appearance when drag leaves the area"""
        print("Drag left the drop area")
        self.drop_widget.setProperty("state", "idle")
        self.drop_widget.style().unpolish(self.drop_widget)
        self.drop_widget.style().polish(self.drop_widget)
            
    def dropEvent(self, event):
        print(f"Drop event received")
        data = event.mimeData()
        formats = data.formats()
        print(f"Available formats: {formats}")
        
        self.drop_widget.setProperty("state", "idle")
        self.drop_widget.style().unpolish(self.drop_widget)
        self.drop_widget.style().polish(self.drop_widget)
        
        if data.hasFormat('application/x-schedule'):
            try:
                print(f"Processing schedule data")
                schedule_data = data.data('application/x-schedule')
                schedule_dict = eval(bytes(schedule_data).decode())
                print(f"Schedule dict: {schedule_dict}")
                
                # Get schedule details from database
                schedule_details = self.database_handler.get_schedule_details(schedule_dict['schedule_id'])
                if not schedule_details:
                    raise Exception("Schedule details not found in database")
                
                schedule_detail = schedule_details[0]
                print(f"Retrieved schedule details: {schedule_detail}")
                
                # Create Schedule instance without relay_unit_id
                self.current_schedule = Schedule(
                    schedule_id=schedule_dict['schedule_id'],
                    name=schedule_dict['name'],
                    water_volume=schedule_detail['water_volume'],
                    start_time=schedule_detail['start_time'],
                    end_time=schedule_detail['end_time'],
                    created_by=schedule_dict['created_by'],
                    is_super_user=schedule_dict['is_super_user'],
                    delivery_mode=schedule_detail['delivery_mode']
                )
                
                # Load instant deliveries if in instant mode
                if self.current_schedule.delivery_mode.lower() == 'instant':
                    deliveries = self.database_handler.get_schedule_instant_deliveries(self.current_schedule.schedule_id)
                    for delivery in deliveries:
                        animal_id, _, _, datetime_str, volume, _, relay_unit_id = delivery
                        delivery_time = datetime.datetime.fromisoformat(datetime_str)
                        self.current_schedule.add_instant_delivery(
                            animal_id, 
                            delivery_time, 
                            volume,
                            relay_unit_id
                        )
                
                # Update UI
                self.placeholder.setText(f"Schedule: {self.current_schedule.name}")
                self.mode_changed.emit(self.current_schedule.delivery_mode.capitalize())
                
                # Show schedule details
                self.drop_widget.hide()
                self.schedule_table.show()
                self.update_table(self.current_schedule)
                
                # Emit the schedule_dropped signal
                print(f"Emitting schedule_dropped signal with schedule: {self.current_schedule.name}")
                self.schedule_dropped.emit(self.current_schedule)
                
                event.acceptProposedAction()
                print(f"Drop event processing completed successfully")
                
            except Exception as e:
                print(f"Error processing schedule data: {e}")
                traceback.print_exc()
                self.placeholder.setText("Error loading schedule")
        elif data.hasText():
            schedule_name = data.text()
            print(f"Processing text drop: {schedule_name}")
            self.placeholder.setText(f"Schedule: {schedule_name}")
            event.acceptProposedAction()
        else:
            print(f"No recognized format in drop event")
    
    def clear(self):
        self.current_schedule = None
        self.placeholder.setText("Drop Schedule Here")
        self.schedule_table.hide()
        self.schedule_table.setRowCount(0)
        self.drop_widget.show()
    
    def handle_schedule_drop(self, schedule):
        """Handle schedule drops from any source"""
        try:
            self.current_schedule = schedule
            self.placeholder.setText(f"Schedule: {schedule.name}")
            
            # Emit signal that schedule was dropped
            self.schedule_dropped.emit(schedule)
            
            # Update mode if needed
            if hasattr(self, 'mode_changed'):
                self.mode_changed.emit(schedule.delivery_mode.capitalize())
                
        except Exception as e:
            print(f"Error handling schedule drop: {e}")
            self.placeholder.setText("Error loading schedule")
    
    def update_table(self, schedule):
        """Update the table with schedule information"""
        self.schedule_table.setRowCount(0)  # Clear existing rows
        
        try:
            # First check if there's any data to display
            has_data = False
            
            if schedule.delivery_mode.lower() == 'instant':
                deliveries = self.database_handler.get_schedule_instant_deliveries(schedule.schedule_id)
                has_data = len(deliveries) > 0
                
                if not has_data:
                    self.schedule_table.setEmptyMessage(True)
                    return
                    
                self.schedule_table.setEmptyMessage(False)
                
                # Group deliveries by animal
                animal_deliveries = {}
                for delivery in deliveries:
                    # Unpack all 7 values from the delivery tuple
                    animal_id, lab_id, name, datetime_str, volume, completed, relay_unit_id = delivery
                    
                    if animal_id not in animal_deliveries:
                        animal_deliveries[animal_id] = {
                            'lab_id': lab_id,
                            'name': name,
                            'deliveries': [],
                            'total_volume': 0
                        }
                    delivery_time = datetime.datetime.fromisoformat(datetime_str)
                    animal_deliveries[animal_id]['deliveries'].append({
                        'datetime': delivery_time,
                        'volume': volume
                    })
                    animal_deliveries[animal_id]['total_volume'] += volume
                
                # Add rows for each animal
                for animal_id, data in animal_deliveries.items():
                    row = self.schedule_table.rowCount()
                    self.schedule_table.insertRow(row)
                    
                    lab_id_item = QTableWidgetItem(data['lab_id'])
                    name_item = QTableWidgetItem(data['name'])
                    vol_item = QTableWidgetItem(f"{data['total_volume']:.1f}")
                    
                    # Center-align items for better readability
                    lab_id_item.setTextAlignment(Qt.AlignCenter)
                    name_item.setTextAlignment(Qt.AlignCenter)
                    vol_item.setTextAlignment(Qt.AlignCenter)
                    
                    self.schedule_table.setItem(row, 0, lab_id_item)
                    self.schedule_table.setItem(row, 1, name_item)
                    self.schedule_table.setItem(row, 2, vol_item)
                    
                    if data['deliveries']:
                        first_time = min(d['datetime'] for d in data['deliveries'])
                        last_time = max(d['datetime'] for d in data['deliveries'])
                        
                        start_item = QTableWidgetItem(first_time.strftime("%Y-%m-%d %H:%M:%S"))
                        end_item = QTableWidgetItem(last_time.strftime("%Y-%m-%d %H:%M:%S"))
                        
                        start_item.setTextAlignment(Qt.AlignCenter)
                        end_item.setTextAlignment(Qt.AlignCenter)
                        
                        self.schedule_table.setItem(row, 3, start_item)
                        self.schedule_table.setItem(row, 4, end_item)
            
            else:
                # Handle staggered mode
                schedule_details = self.database_handler.get_schedule_details(schedule.schedule_id)[0]
                animal_ids = schedule_details.get('animal_ids', [])
                
                has_data = len(animal_ids) > 0
                
                if not has_data:
                    self.schedule_table.setEmptyMessage(True)
                    return
                    
                self.schedule_table.setEmptyMessage(False)
                
                for animal_id in animal_ids:
                    animal = self.database_handler.get_animal_by_id(animal_id)
                    if animal:
                        row = self.schedule_table.rowCount()
                        self.schedule_table.insertRow(row)
                        
                        lab_id_item = QTableWidgetItem(animal.lab_animal_id)
                        name_item = QTableWidgetItem(animal.name)
                        
                        desired_output = schedule_details['desired_water_outputs'].get(str(animal_id), 0)
                        vol_item = QTableWidgetItem(f"{desired_output:.1f}")
                        
                        # Center-align items
                        lab_id_item.setTextAlignment(Qt.AlignCenter)
                        name_item.setTextAlignment(Qt.AlignCenter)
                        vol_item.setTextAlignment(Qt.AlignCenter)
                        
                        self.schedule_table.setItem(row, 0, lab_id_item)
                        self.schedule_table.setItem(row, 1, name_item)
                        self.schedule_table.setItem(row, 2, vol_item)
                        
                        # Format start/end times (handle with or without microseconds)
                        try:
                            # Try parsing with microseconds first
                            start_dt = datetime.datetime.fromisoformat(schedule.start_time)
                            end_dt = datetime.datetime.fromisoformat(schedule.end_time)
                            start_time = start_dt.strftime("%Y-%m-%d %H:%M")
                            end_time = end_dt.strftime("%Y-%m-%d %H:%M")
                        except (ValueError, TypeError):
                            start_time = schedule.start_time or ""
                            end_time = schedule.end_time or ""
                            
                        start_item = QTableWidgetItem(start_time)
                        end_item = QTableWidgetItem(end_time)
                        
                        start_item.setTextAlignment(Qt.AlignCenter)
                        end_item.setTextAlignment(Qt.AlignCenter)
                        
                        self.schedule_table.setItem(row, 3, start_item)
                        self.schedule_table.setItem(row, 4, end_item)
            
            # Force layout update to ensure proper display
            self.schedule_table.resizeRowsToContents()
            self.schedule_table.updateGeometry()
        
        except Exception as e:
            print(f"Error updating table: {e}")
            traceback.print_exc()
    
    def get_mode(self):
        """Get the current schedule's delivery mode"""
        if self.current_schedule:
            return self.current_schedule.delivery_mode.capitalize()
        return "Staggered"  # Default mode
    
    def double_click_event(self, event):
        if self.current_schedule:
            self.clear()
    
    def resizeEvent(self, event):
        """Handle resize events to update table dimensions"""
        super().resizeEvent(event)
        if hasattr(self, 'schedule_table') and self.schedule_table.isVisible():
            # Ensure table uses full width
            self.schedule_table.setMinimumWidth(self.width() - 20)  # Account for margins
            self.schedule_table.updateGeometry()


