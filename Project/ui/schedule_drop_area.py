from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, 
                           QTableWidgetItem, QTableWidget, QHBoxLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from models.Schedule import Schedule
from .schedule_table import ScheduleTable
import datetime
from models.database_handler import DatabaseHandler

class ScheduleDropArea(QWidget):

    mode_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Initialize database handler
        self.database_handler = DatabaseHandler()
        
        # Drop area
        self.drop_widget = QWidget()
        self.drop_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa; 
                border: 2px dashed #e0e0e0;
                border-radius: 4px;
                min-height: 80px;
            }
        """)
        
        # Placeholder label
        self.placeholder = QLabel("Drop Schedule Here")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet("border: none; background: none;")
        
        drop_layout = QVBoxLayout()
        drop_layout.addWidget(self.placeholder)
        self.drop_widget.setLayout(drop_layout)
        
        # Schedule table (initially hidden)
        self.schedule_table = ScheduleTable()
        self.schedule_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Make read-only
        self.schedule_table.hide()
        
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
        if mime_data.hasFormat('application/x-schedule') or mime_data.hasText():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        data = event.mimeData()
        if data.hasFormat('application/x-schedule'):
            try:
                schedule_data = data.data('application/x-schedule')
                schedule_dict = eval(bytes(schedule_data).decode())
                
                # Create a new Schedule instance
                self.current_schedule = Schedule(
                    schedule_id=schedule_dict['schedule_id'],
                    name=schedule_dict['name'],
                    relay_unit_id=schedule_dict['relay_unit_id'],
                    water_volume=schedule_dict['water_volume'],
                    start_time=schedule_dict['start_time'],
                    end_time=schedule_dict['end_time'],
                    created_by=schedule_dict['created_by'],
                    is_super_user=schedule_dict['is_super_user'],
                    delivery_mode=schedule_dict['delivery_mode']
                )
                
                # Set additional properties
                self.current_schedule.animals = schedule_dict.get('animals', [])
                self.current_schedule.desired_water_outputs = schedule_dict.get('desired_water_outputs', {})
                
                # Convert instant deliveries datetime strings to datetime objects
                instant_deliveries = schedule_dict.get('instant_deliveries', [])
                for delivery in instant_deliveries:
                    if isinstance(delivery['datetime'], str):
                        delivery['datetime'] = datetime.datetime.fromisoformat(delivery['datetime'])
                self.current_schedule.instant_deliveries = instant_deliveries
                
                self.placeholder.setText(f"Schedule: {self.current_schedule.name}")
                event.acceptProposedAction()
                
                self.mode_changed.emit(self.current_schedule.delivery_mode.capitalize())
                
                self.drop_widget.hide()
                self.schedule_table.show()
                self.update_table(self.current_schedule)
                
            except Exception as e:
                print(f"Error processing schedule data: {e}")
                self.placeholder.setText("Error loading schedule")
        elif data.hasText():
            schedule_name = data.text()
            self.placeholder.setText(f"Schedule: {schedule_name}")
            event.acceptProposedAction()
    
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
            
            # Update mode if needed
            if hasattr(self, 'mode_changed'):
                self.mode_changed.emit(schedule.delivery_mode.capitalize())
            
        except Exception as e:
            print(f"Error handling schedule drop: {e}")
            self.placeholder.setText("Error loading schedule")
    
    def update_table(self, schedule):
        """Update the table with schedule information"""
        self.schedule_table.setRowCount(0)  # Clear existing rows
        
        if schedule.delivery_mode.lower() == 'instant':
            # Group deliveries by animal
            animal_deliveries = {}
            latest_time = None
            
            deliveries = self.database_handler.get_schedule_instant_deliveries(schedule.schedule_id)
            for delivery in deliveries:
                animal_id, lab_id, name, datetime_str, volume, completed = delivery
                if animal_id not in animal_deliveries:
                    animal_deliveries[animal_id] = {
                        'lab_id': lab_id,
                        'name': name,
                        'deliveries': [],
                        'total_volume': 0
                    }
                animal_deliveries[animal_id]['deliveries'].append({
                    'datetime': datetime.datetime.fromisoformat(datetime_str),
                    'volume': volume
                })
                animal_deliveries[animal_id]['total_volume'] += volume
            
            # Add rows for each animal
            for animal_id, data in animal_deliveries.items():
                row = self.schedule_table.rowCount()
                self.schedule_table.insertRow(row)
                
                # Animal Lab ID and Name
                self.schedule_table.setItem(row, 0, QTableWidgetItem(data['lab_id']))
                self.schedule_table.setItem(row, 1, QTableWidgetItem(data['name']))
                
                # Total Volume
                self.schedule_table.setItem(row, 2, QTableWidgetItem(f"{data['total_volume']:.1f}"))
                
                # First and Last Delivery Times
                first_time = min(d['datetime'] for d in data['deliveries'])
                last_time = max(d['datetime'] for d in data['deliveries'])
                
                self.schedule_table.setItem(row, 3, QTableWidgetItem(first_time.strftime("%Y-%m-%d %H:%M:%S")))
                self.schedule_table.setItem(row, 4, QTableWidgetItem(last_time.strftime("%Y-%m-%d %H:%M:%S")))
    
    def get_mode(self):
        """Get the current schedule's delivery mode"""
        if self.current_schedule:
            return self.current_schedule.delivery_mode.capitalize()
        return "Staggered"  # Default mode
    
    def double_click_event(self, event):
        if self.current_schedule:
            self.clear()
    