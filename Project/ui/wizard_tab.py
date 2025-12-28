# ui/wizard_tab.py
"""
Wizard Tab - Embedded schedule creation wizard for comparison with legacy method.

This tab provides the new step-by-step wizard interface for creating schedules,
allowing side-by-side comparison with the traditional Schedules tab method.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QMessageBox, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from .schedule_wizard import ScheduleCreationWizard


class WizardTab(QWidget):
    """
    Tab wrapper for the Schedule Creation Wizard.
    
    Provides the wizard UI embedded as a tab rather than a dialog,
    with a reset button to start fresh.
    
    Signals:
        schedule_created(dict): Emitted when a schedule is successfully created
    """
    
    schedule_created = pyqtSignal(dict)
    
    def __init__(self, database_handler, login_system, print_to_terminal, parent=None):
        super().__init__(parent)
        
        self._database_handler = database_handler
        self._login_system = login_system
        self._print_to_terminal = print_to_terminal
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with reset button
        header = QWidget()
        header.setObjectName("WizardTabHeader")
        header.setStyleSheet("""
            #WizardTabHeader {
                background-color: #F8FAFB;
                border-bottom: 1px solid #E5E7EB;
                padding: 8px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        # Title
        title = QLabel("✨ New Schedule Wizard")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #0D9488;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Reset button
        reset_btn = QPushButton("🔄 Start Over")
        reset_btn.setToolTip("Reset wizard to create a new schedule")
        reset_btn.clicked.connect(self._reset_wizard)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #F3F4F6;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
        """)
        header_layout.addWidget(reset_btn)
        
        layout.addWidget(header)
        
        # Wizard container (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create the wizard
        self._wizard = ScheduleCreationWizard(
            database_handler=self._database_handler,
            login_system=self._login_system
        )
        
        # Connect wizard signals
        self._wizard.schedule_created.connect(self._on_schedule_created)
        self._wizard.cancelled.connect(self._on_cancelled)
        
        scroll.setWidget(self._wizard)
        layout.addWidget(scroll, 1)
    
    def _on_schedule_created(self, config: dict):
        """Handle schedule creation from wizard."""
        schedule_name = config.get('parameters', {}).get('name', 'Unnamed')
        self._print_to_terminal(f"[Wizard Tab] Schedule '{schedule_name}' created successfully!")
        
        # Emit for parent to handle
        self.schedule_created.emit(config)
        
        # Show success message
        QMessageBox.information(
            self,
            "Schedule Created",
            f"Schedule '{schedule_name}' has been created and saved.\n\n"
            "You can now drag it from the Schedules tab to run it."
        )
        
        # Reset wizard for next creation
        self._reset_wizard()
    
    def _on_cancelled(self):
        """Handle wizard cancellation."""
        self._print_to_terminal("[Wizard Tab] Schedule creation cancelled")
        self._reset_wizard()
    
    def _reset_wizard(self):
        """Reset the wizard to initial state for new schedule creation."""
        # Remove old wizard
        if hasattr(self, '_wizard') and self._wizard:
            self._wizard.deleteLater()
        
        # Find the scroll area
        scroll = self.findChild(QScrollArea)
        if scroll:
            # Create new wizard
            self._wizard = ScheduleCreationWizard(
                database_handler=self._database_handler,
                login_system=self._login_system
            )
            self._wizard.schedule_created.connect(self._on_schedule_created)
            self._wizard.cancelled.connect(self._on_cancelled)
            scroll.setWidget(self._wizard)
        
        self._print_to_terminal("[Wizard Tab] Wizard reset - ready for new schedule")
    
    def refresh(self):
        """Refresh the wizard (reload animals etc.)."""
        # Reset to ensure fresh data
        self._reset_wizard()

