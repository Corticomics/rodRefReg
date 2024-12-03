from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import Qt, pyqtSignal
from models.Schedule import Schedule

class ScheduleDropArea(QWidget):

    
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
        self.layout.addWidget(self.drop_widget)
        
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
            schedule_data = data.data('application/x-schedule')
            try:
                # Convert QByteArray to Schedule object
                schedule_dict = eval(bytes(schedule_data).decode())
                self.current_schedule = Schedule(**schedule_dict)
                self.placeholder.setText(f"Schedule: {self.current_schedule.name}")
                event.acceptProposedAction()
            except Exception as e:
                print(f"Error processing schedule data: {e}")
        elif data.hasText():
            schedule_name = data.text()
            self.placeholder.setText(f"Schedule: {schedule_name}")
            event.acceptProposedAction()
    
    def clear(self):
        self.current_schedule = None
        self.placeholder.setText("Drop Schedule Here")
    