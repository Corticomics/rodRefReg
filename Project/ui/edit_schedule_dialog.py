from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QTableWidget, QTableWidgetItem, QPushButton,
                           QMessageBox, QDateTimeEdit)
from PyQt5.QtCore import Qt, QDateTime
from datetime import datetime

class EditScheduleDialog(QDialog):
    def __init__(self, schedule, database_handler, parent=None):
        super().__init__(parent)
        self.schedule = schedule
        self.database_handler = database_handler
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Edit Schedule")
        self.setMinimumWidth(600)
        layout = QVBoxLayout()
        
        # Schedule Name
        name_layout = QHBoxLayout()
        name_label = QLabel("Schedule Name:")
        self.name_input = QLineEdit(self.schedule.name)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Animals Table
        self.animals_table = QTableWidget()
        self.animals_table.setColumnCount(4)
        self.animals_table.setHorizontalHeaderLabels(
            ["Lab ID", "Name", "Volume (mL)", "Remove"]
        )
        self.load_animals()
        layout.addWidget(self.animals_table)
        
        # Time Settings
        time_layout = QHBoxLayout()
        start_label = QLabel("Start Time:")
        self.start_time = QDateTimeEdit()
        self.start_time.setDateTime(
            QDateTime.fromString(self.schedule.start_time, "yyyy-MM-dd HH:mm:ss")
        )
        end_label = QLabel("End Time:")
        self.end_time = QDateTimeEdit()
        self.end_time.setDateTime(
            QDateTime.fromString(self.schedule.end_time, "yyyy-MM-dd HH:mm:ss")
        )
        time_layout.addWidget(start_label)
        time_layout.addWidget(self.start_time)
        time_layout.addWidget(end_label)
        time_layout.addWidget(self.end_time)
        layout.addLayout(time_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.save_changes)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout) 