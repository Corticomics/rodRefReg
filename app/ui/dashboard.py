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
        title_label = QLabel("Previous Watering Projects")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(title_label)

        # List of projects
        self.project_list = QListWidget()
        self.load_projects()
        self.layout.addWidget(self.project_list)

        # Buttons
        button_layout = QHBoxLayout()

        open_button = QPushButton("Open Project")
        open_button.clicked.connect(self.open_project)
        button_layout.addWidget(open_button)

        delete_button = QPushButton("Delete Project")
        delete_button.clicked.connect(self.delete_project)
        button_layout.addWidget(delete_button)

        self.layout.addLayout(button_layout)

    def load_projects(self):
        self.project_list.clear()
        projects = self.db_manager.get_projects()
        for project in projects:
            self.project_list.addItem(f"Project ID: {project.project_id} - Created on: {project.creation_date}")

    def open_project(self):
        selected_item = self.project_list.currentItem()
        if selected_item:
            project_id = selected_item.text().split(" - ")[0].split(": ")[1]
            self.open_project_callback(project_id)
        else:
            QMessageBox.warning(self, "No Selection", "Please select a project to open.")

    def delete_project(self):
        selected_item = self.project_list.currentItem()
        if selected_item:
            project_id = selected_item.text().split(" - ")[0].split(": ")[1]
            confirm = QMessageBox.question(
                self, "Confirm Deletion",
                f"Are you sure you want to delete Project ID: {project_id}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                self.db_manager.delete_project(project_id)
                self.load_projects()
                QMessageBox.information(self, "Deleted", f"Project ID: {project_id} has been deleted.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a project to delete.")