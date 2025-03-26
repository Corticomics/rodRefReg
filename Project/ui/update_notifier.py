"""UI Update Notifier Module

This module handles checking for UI updates and displaying notifications to users.
"""

import os
import json
from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from PyQt5.QtCore import Qt

class UpdateNotifier:
    """Class to handle UI update notifications."""
    
    @staticmethod
    def check_for_updates():
        """Checks if UI has been updated and shows notification if needed."""
        update_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui_updated.json')
        
        if not os.path.exists(update_file):
            return False
            
        try:
            with open(update_file, 'r') as f:
                update_data = json.load(f)
                
            if update_data.get('updated', False):
                # Show notification
                UpdateNotifier.show_update_notification(update_data)
                
                # Reset the update flag so notification shows only once
                update_data['updated'] = False
                with open(update_file, 'w') as f:
                    json.dump(update_data, f, indent=4)
                    
                return True
        except Exception as e:
            print(f"Error checking for UI updates: {e}")
            
        return False
        
    @staticmethod
    def show_update_notification(update_data):
        """Shows a nicely formatted dialog with update information."""
        dialog = QDialog()
        dialog.setWindowTitle("UI Improvements Applied")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("UI Improvements Applied")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1a73e8;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # Date
        date_label = QLabel(f"Updated on: {update_data.get('date', 'Unknown')}")
        date_label.setStyleSheet("font-style: italic; color: #5f6368;")
        layout.addWidget(date_label)
        
        # Create scrollable area for changes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Add change list
        changes_label = QLabel("Changes:")
        changes_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        scroll_layout.addWidget(changes_label)
        
        for change in update_data.get('changes', []):
            change_item = QLabel(f"• {change}")
            change_item.setWordWrap(True)
            scroll_layout.addWidget(change_item)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # OK button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1658c5;
            }
        """)
        layout.addWidget(ok_button)
        
        dialog.setLayout(layout)
        dialog.exec_() 