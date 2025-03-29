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
        
        # Improved style and behavior
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)  # Show grid for better readability
        self.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f5f5f5;
                border: 1px solid #c0c0c0;
                border-radius: 6px;
                gridline-color: #e0e4e8;
            }
            QHeaderView::section {
                background-color: #f0f2f5;
                color: #333;
                padding: 8px;
                border: 1px solid #c0c0c0;
                border-bottom: 2px solid #a0a0a0;
                font-weight: bold;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #e0e4e8;
            }
            QTableWidget::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
        """)
        
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