from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, 
    QPushButton, QDateTimeEdit
)
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QTimer
from datetime import datetime

class StaggeredDeliverySlot(QWidget):
    slot_deleted = pyqtSignal(QWidget)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Time window row
        time_window_layout = QHBoxLayout()
        
        # Start time picker
        start_time_layout = QVBoxLayout()
        start_label = QLabel("Start Time:")
        self.start_datetime = QDateTimeEdit()
        self.start_datetime.setCalendarPopup(True)
        self.start_datetime.setDateTime(QDateTime.currentDateTime())
        self.start_datetime.setDisplayFormat("yyyy-MM-dd hh:mm AP")
        start_time_layout.addWidget(start_label)
        start_time_layout.addWidget(self.start_datetime)
        
        # End time picker
        end_time_layout = QVBoxLayout()
        end_label = QLabel("End Time:")
        self.end_datetime = QDateTimeEdit()
        self.end_datetime.setCalendarPopup(True)
        self.end_datetime.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # Default 1 hour window
        self.end_datetime.setDisplayFormat("yyyy-MM-dd hh:mm AP")
        end_time_layout.addWidget(end_label)
        end_time_layout.addWidget(self.end_datetime)
        
        # Connect datetime changes to validation
        self.start_datetime.dateTimeChanged.connect(self.validate_times)
        self.end_datetime.dateTimeChanged.connect(self.validate_times)
        
        # Volume input
        volume_layout = QVBoxLayout()
        volume_label = QLabel("Volume (mL):")
        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("Water volume")
        self.volume_input.setFixedWidth(100)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_input)
        
        # Delete button
        self.delete_button = QPushButton("×")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px;
                max-width: 20px;
                max-height: 20px;
                font-size: 16px;
                font-weight: bold;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        self.delete_button.clicked.connect(self.handle_delete)
        
        # Add widgets to layouts
        time_window_layout.addLayout(start_time_layout)
        time_window_layout.addLayout(end_time_layout)
        time_window_layout.addLayout(volume_layout)
        time_window_layout.addWidget(self.delete_button)
        time_window_layout.addStretch()
        
        self.layout.addLayout(time_window_layout)
        self.is_deleted = False

    def validate_times(self):
        """Ensure end time is after start time with minimum 5-minute window"""
        start_time = self.start_datetime.dateTime()
        end_time = self.end_datetime.dateTime()
        
        if end_time <= start_time:
            # Add 5 minutes to ensure minimum window
            new_end_time = start_time.addSecs(300)  # 5 minutes = 300 seconds
            self.end_datetime.setDateTime(new_end_time)
            return
            
        # Ensure minimum 5-minute window
        if end_time < start_time.addSecs(300):
            self.end_datetime.setDateTime(start_time.addSecs(300))

    def handle_delete(self):
        """Handle the deletion of the slot."""
        self.is_deleted = True
        self.slot_deleted.emit(self)
        self.deleteLater()

    def get_data(self):
        """Get the slot's data"""
        try:
            return {
                'start_time': self.start_datetime.dateTime().toPyDateTime(),
                'end_time': self.end_datetime.dateTime().toPyDateTime(),
                'volume': float(self.volume_input.text()) if self.volume_input.text() else 0.0
            }
        except ValueError:
            return None 