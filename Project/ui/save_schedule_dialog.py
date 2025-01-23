from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QDateTimeEdit, 
                           QComboBox, QMessageBox)
from PyQt5.QtCore import Qt, QDateTime
from datetime import datetime, timedelta

class SaveScheduleDialog(QDialog):
    def __init__(self, schedule_data, parent=None):
        super().__init__(parent)
        self.schedule_data = schedule_data
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Save Schedule")
        layout = QVBoxLayout()
        
        # Name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Schedule Name:")
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Time window selection
        time_layout = QVBoxLayout()
        time_label = QLabel("Time Window:")
        time_layout.addWidget(time_label)
        
        # Start time
        start_layout = QHBoxLayout()
        start_label = QLabel("Start:")
        self.start_time = QDateTimeEdit()
        self.start_time.setDateTime(QDateTime.currentDateTime())
        self.start_time.setCalendarPopup(True)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_time)
        time_layout.addLayout(start_layout)
        
        # End time
        end_layout = QHBoxLayout()
        end_label = QLabel("End:")
        self.end_time = QDateTimeEdit()
        self.end_time.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # +1 hour default
        self.end_time.setCalendarPopup(True)
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_time)
        time_layout.addLayout(end_layout)
        
        layout.addLayout(time_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.save_schedule)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def save_schedule(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a schedule name")
            return
            
        start_time = self.start_time.dateTime().toPyDateTime()
        end_time = self.end_time.dateTime().toPyDateTime()
        
        if end_time <= start_time:
            QMessageBox.warning(self, "Error", "End time must be after start time")
            return
            
        self.schedule_data.update({
            'name': name,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        })
        
        self.accept() 