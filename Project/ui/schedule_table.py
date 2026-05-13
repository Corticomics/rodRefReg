from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
from PyQt5.QtCore import Qt

class ScheduleTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels([
            "Lab ID",
            "Name",
            "Volume (mL)",
            "Start Time",
            "End Time"
        ])
        
        # Set specific column widths for better visibility
        self.setColumnWidth(0, 120)  # Lab ID
        self.setColumnWidth(1, 120)  # Name
        self.setColumnWidth(2, 110)  # Volume
        self.setColumnWidth(3, 160)  # Start Time
        self.setColumnWidth(4, 160)  # End Time
        
        # Turn off stretch mode initially to allow setting specific widths
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        
        # Set row height and hide vertical headers for cleaner look
        self.verticalHeader().setDefaultSectionSize(40)  # Taller rows
        self.verticalHeader().setVisible(False)  # Hide row numbers
        
        # Table appearance - uses global QSS styles (app-light.qss / app-dark.qss)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        
        # Set minimum height for better visibility
        self.setMinimumHeight(200)
        
        # After setting specific widths, make last column stretch
        self.horizontalHeader().setStretchLastSection(True)
    
    def resizeEvent(self, event):
        """Override resize event to adjust column widths on resize"""
        super().resizeEvent(event)
        # Adjust column widths when table is resized
        width = self.width()
        self.setColumnWidth(0, int(width * 0.15))  # Lab ID: 15%
        self.setColumnWidth(1, int(width * 0.15))  # Name: 15%
        self.setColumnWidth(2, int(width * 0.15))  # Volume: 15%
        self.setColumnWidth(3, int(width * 0.25))  # Start Time: 25% 
        # Last column will stretch automatically
        
    def setEmptyMessage(self, is_empty=True):
        """Set empty state styling and message"""
        if is_empty:
            self.setProperty("empty", True)
            self.setRowCount(1)
            self.setSpan(0, 0, 1, 5)  # Merge all cells in first row
            no_data_item = QTableWidgetItem("No schedule data available")
            no_data_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(0, 0, no_data_item)
        else:
            self.setProperty("empty", False)
            # Style update to force the table to refresh
            self.style().unpolish(self)
            self.style().polish(self) 