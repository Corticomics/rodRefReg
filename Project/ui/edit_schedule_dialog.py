from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QTableWidget, QTableWidgetItem, QPushButton,
                           QMessageBox, QDateTimeEdit, QFormLayout, QComboBox)
from PyQt5.QtCore import Qt, QDateTime
from datetime import datetime
from PyQt5.QtCore import pyqtSignal

class EditScheduleDialog(QDialog):
    schedule_updated = pyqtSignal(object)  # Signal to emit when schedule is updated
    
    def __init__(self, schedule, database_handler, parent=None):
        super().__init__(parent)
        self.schedule = schedule
        self.database_handler = database_handler
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"Edit Schedule: {self.schedule.name}")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout()
        
        # Schedule Details Form
        form_layout = QFormLayout()
        
        # Name field
        self.name_input = QLineEdit(self.schedule.name)
        form_layout.addRow("Schedule Name:", self.name_input)
        
        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Staggered", "Instant"])
        self.mode_combo.setCurrentText(self.schedule.delivery_mode.capitalize())
        form_layout.addRow("Delivery Mode:", self.mode_combo)
        
        # Time settings
        self.start_time = QDateTimeEdit()
        self.start_time.setDateTime(QDateTime.fromString(self.schedule.start_time, "yyyy-MM-dd HH:mm:ss"))
        self.start_time.setCalendarPopup(True)
        
        self.end_time = QDateTimeEdit()
        self.end_time.setDateTime(QDateTime.fromString(self.schedule.end_time, "yyyy-MM-dd HH:mm:ss"))
        self.end_time.setCalendarPopup(True)
        
        form_layout.addRow("Start Time:", self.start_time)
        form_layout.addRow("End Time:", self.end_time)
        
        layout.addLayout(form_layout)
        
        # Schedule Table
        self.schedule_table = ScheduleTable()
        self.populate_schedule_table()
        layout.addWidget(self.schedule_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.save_changes)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def populate_schedule_table(self):
        """Populate the schedule table with current schedule data"""
        self.schedule_table.setRowCount(0)
        schedule_details = self.database_handler.get_schedule_details(self.schedule.schedule_id)
        
        if not schedule_details:
            return
            
        for animal_id in schedule_details[0]['animal_ids']:
            animal = self.database_handler.get_animal_by_id(animal_id)
            if not animal:
                continue
                
            row = self.schedule_table.rowCount()
            self.schedule_table.insertRow(row)
            
            self.schedule_table.setItem(row, 0, QTableWidgetItem(animal.lab_animal_id))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(animal.name))
            
            volume = schedule_details[0]['desired_water_outputs'].get(str(animal_id), 0)
            self.schedule_table.setItem(row, 2, QTableWidgetItem(f"{volume:.1f}"))
            
            # Add start and end times
            self.schedule_table.setItem(row, 3, QTableWidgetItem(self.schedule.start_time))
            self.schedule_table.setItem(row, 4, QTableWidgetItem(self.schedule.end_time))
    
    def save_changes(self):
        """Save the modified schedule"""
        try:
            # Update schedule basic info
            self.schedule.name = self.name_input.text()
            self.schedule.delivery_mode = self.mode_combo.currentText().lower()
            self.schedule.start_time = self.start_time.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            self.schedule.end_time = self.end_time.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            
            # Update in database
            success = self.database_handler.update_schedule(self.schedule)
            
            if success:
                self.schedule_updated.emit(self.schedule)
                QMessageBox.information(self, "Success", "Schedule updated successfully!")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to update schedule")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}") 