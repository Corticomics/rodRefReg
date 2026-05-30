# ui/wizard_tab.py
"""
Wizard Tab - Embedded schedule creation wizard for comparison with legacy method.

This tab provides the new step-by-step wizard interface for creating schedules,
allowing side-by-side comparison with the traditional Schedules tab method.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from .schedule_wizard import ScheduleCreationWizard


class WizardTab(QWidget):
    """
    Tab wrapper for the Schedule Creation Wizard.

    Provides the wizard UI embedded as a tab rather than a dialog,
    with a reset button to start fresh.

    Args:
        database_handler: Database access for animals, schedules
        login_system: Login system for trainer info
        print_to_terminal: Terminal output function
        system_controller: System controller for hardware settings (optional)

    Signals:
        schedule_created(dict): Emitted when a schedule is successfully created
    """

    schedule_created = pyqtSignal(dict)

    def __init__(
        self,
        database_handler,
        login_system,
        print_to_terminal,
        system_controller=None,
        parent=None,
    ):
        super().__init__(parent)

        self._database_handler = database_handler
        self._login_system = login_system
        self._print_to_terminal = print_to_terminal
        self._system_controller = system_controller

        self._init_ui()

    def _init_ui(self):
        """
        Initialize the tab UI.

        Design Decision:
        - The wizard container is NOT wrapped in a scroll area
        - Scrolling happens WITHIN individual wizard steps (e.g., Step 3 animal config)
        - This keeps the progress bar, navigation buttons, and step headers fixed
        - Only content that needs scrolling (many animals) will scroll

        Reference: Material Design Steppers - Fixed navigation pattern
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Wizard container (STATIC - no outer scroll). The old "New Schedule
        # Wizard" header band was removed to reclaim vertical space for the
        # Select Animals step; the persistent "Start Over" control now lives in
        # the wizard's own progress band. Scrolling is handled internally by
        # each step that needs it (Step 3).
        self._wizard = ScheduleCreationWizard(
            database_handler=self._database_handler,
            login_system=self._login_system,
            system_controller=self._system_controller,
        )

        # Connect wizard signals
        self._wizard.schedule_created.connect(self._on_schedule_created)
        self._wizard.cancelled.connect(self._on_cancelled)
        self._wizard.restart_requested.connect(self._reset_wizard)

        layout.addWidget(self._wizard, 1)

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
            "You can now drag it from the Schedules tab to run it.",
        )

        # Reset wizard for next creation
        self._reset_wizard()

    def _on_cancelled(self):
        """Handle wizard cancellation."""
        self._print_to_terminal("[Wizard Tab] Schedule creation cancelled")
        self._reset_wizard()

    def _reset_wizard(self):
        """
        Reset the wizard to initial state for new schedule creation.

        Design: Replaces the wizard widget in the layout with a fresh instance.
        """
        # Store layout reference
        layout = self.layout()

        # Remove old wizard from layout
        if hasattr(self, '_wizard') and self._wizard:
            layout.removeWidget(self._wizard)
            self._wizard.deleteLater()

        # Create new wizard (with hardware limits from system_controller)
        self._wizard = ScheduleCreationWizard(
            database_handler=self._database_handler,
            login_system=self._login_system,
            system_controller=self._system_controller,
        )
        self._wizard.schedule_created.connect(self._on_schedule_created)
        self._wizard.cancelled.connect(self._on_cancelled)
        self._wizard.restart_requested.connect(self._reset_wizard)

        # Add to layout (fills the tab, with stretch)
        layout.addWidget(self._wizard, 1)

        self._print_to_terminal("[Wizard Tab] Wizard reset - ready for new schedule")

    def refresh(self):
        """Refresh the wizard (reload animals etc.)."""
        # Reset to ensure fresh data
        self._reset_wizard()
