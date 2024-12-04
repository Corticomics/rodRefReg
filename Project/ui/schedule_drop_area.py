from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QTableWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal
from models.Schedule import Schedule
from .schedule_table import ScheduleTable

class ScheduleDropArea(QWidget):

    mode_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
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
        self.schedule_table.hide()
        
        self.layout.addWidget(self.drop_widget)
        self.layout.addWidget(self.schedule_table)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        self.current_schedule = None
        
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
                self.current_schedule.instant_deliveries = schedule_dict.get('instant_deliveries', [])
                
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
        
        if schedule.delivery_mode.lower() == 'staggered':
            for i, animal_id in enumerate(schedule.animals):
                self.schedule_table.insertRow(i)
                self.schedule_table.setItem(i, 0, QTableWidgetItem(str(animal_id)))
                self.schedule_table.setItem(i, 2, QTableWidgetItem(
                    str(schedule.desired_water_outputs.get(str(animal_id), schedule.water_volume))
                ))
                self.schedule_table.setItem(i, 3, QTableWidgetItem(schedule.start_time))
                self.schedule_table.setItem(i, 4, QTableWidgetItem(schedule.end_time))
        else:
            for i, delivery in enumerate(schedule.instant_deliveries):
                self.schedule_table.insertRow(i)
                self.schedule_table.setItem(i, 0, QTableWidgetItem(str(delivery['animal_id'])))
                self.schedule_table.setItem(i, 2, QTableWidgetItem(str(delivery['volume'])))
                self.schedule_table.setItem(i, 3, QTableWidgetItem(str(delivery['datetime'])))
    