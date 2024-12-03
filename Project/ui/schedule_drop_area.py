from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import Qt, pyqtSignal

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
        if event.mimeData().hasFormat('application/x-schedule'):
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        data = event.mimeData()
        if data.hasFormat('application/x-schedule'):
            self.current_schedule = data.data('application/x-schedule').data()
            self.placeholder.setText(f"Schedule: {self.current_schedule.name}")
            event.acceptProposedAction()
            
    def clear(self):
        self.current_schedule = None
        self.placeholder.setText("Drop Schedule Here")
    