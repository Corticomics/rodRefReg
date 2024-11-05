# app/gui/dashboard.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt

class Dashboard(QWidget):
    def __init__(self, db_manager, open_project_callback):
        super().__init__()

        self.db_manager = db_manager
        self.open_project_callback = open_project_callback

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Title
        title_label = QLabel("Dashboard")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(title_label)

        # List of system messages or other dashboard elements can be added here
        # Previously, if there was a 'Projects' tab, it's now removed

        # Example: Add any other dashboard elements you need
        # For now, keeping it minimal
        self.info_label = QLabel("System Status: All systems operational.")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.info_label)