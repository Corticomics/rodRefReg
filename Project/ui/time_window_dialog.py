from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, QDateTimeEdit
from PyQt5.QtCore import QDateTime

class TimeWindowDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Schedule Time Window")
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Initialize with current datetime
        current_dt = QDateTime.currentDateTime()
        
        self.start_time = QDateTimeEdit(current_dt)
        self.start_time.setCalendarPopup(True)
        self.end_time = QDateTimeEdit(current_dt.addDays(1))
        self.end_time.setCalendarPopup(True)
        
        form_layout.addRow("Start Time:", self.start_time)
        form_layout.addRow("End Time:", self.end_time)
        
        layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_times(self):
        return (
            self.start_time.dateTime().toString("yyyy-MM-ddTHH:mm:ss"),
            self.end_time.dateTime().toString("yyyy-MM-ddTHH:mm:ss")
        ) 