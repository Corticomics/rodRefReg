from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, 
    QPushButton, QDateTimeEdit, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QTimer
from datetime import datetime

class StaggeredDeliverySlot(QWidget):
    slot_deleted = pyqtSignal(QWidget)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Use a single main layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(6)
        self.setLayout(self.layout)
        
        # Create a grid layout for better alignment
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)  # Consistent spacing
        
        # Start time picker
        start_label = QLabel("Start Time:")
        self.start_datetime = QDateTimeEdit()
        self.start_datetime.setCalendarPopup(True)
        self.start_datetime.setDateTime(QDateTime.currentDateTime())
        self.start_datetime.setDisplayFormat("yyyy-MM-dd hh:mm AP")
        self.start_datetime.setMinimumWidth(180)
        self.start_datetime.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # End time picker
        end_label = QLabel("End Time:")
        self.end_datetime = QDateTimeEdit()
        self.end_datetime.setCalendarPopup(True)
        self.end_datetime.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # Default 1 hour window
        self.end_datetime.setDisplayFormat("yyyy-MM-dd hh:mm AP")
        self.end_datetime.setMinimumWidth(180)
        self.end_datetime.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # Volume input
        volume_label = QLabel("Volume (mL):")
        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("Water volume")
        self.volume_input.setFixedWidth(100)
        self.volume_input.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Delete button
        self.delete_button = QPushButton("×")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px;
                min-width: 24px;
                min-height: 24px;
                max-width: 24px;
                max-height: 24px;
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
        self.delete_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Add all widgets to the grid layout with proper alignment
        # First row - labels
        grid_layout.addWidget(start_label, 0, 0, Qt.AlignBottom)
        grid_layout.addWidget(end_label, 0, 1, Qt.AlignBottom)
        grid_layout.addWidget(volume_label, 0, 2, Qt.AlignBottom)
        
        # Second row - inputs and delete button
        grid_layout.addWidget(self.start_datetime, 1, 0)
        grid_layout.addWidget(self.end_datetime, 1, 1)
        grid_layout.addWidget(self.volume_input, 1, 2)
        grid_layout.addWidget(self.delete_button, 1, 3, Qt.AlignCenter)
        
        # Set column stretch factors to control relative widths
        grid_layout.setColumnStretch(0, 3)  # Start time - 3 parts
        grid_layout.setColumnStretch(1, 3)  # End time - 3 parts
        grid_layout.setColumnStretch(2, 1)  # Volume - 1 part
        grid_layout.setColumnStretch(3, 0)  # Delete button - fixed width
        
        # Connect datetime changes to validation
        self.start_datetime.dateTimeChanged.connect(self.validate_times)
        self.end_datetime.dateTimeChanged.connect(self.validate_times)
        
        # Add the grid to the main layout
        self.layout.addLayout(grid_layout)
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