# ui/projects_section.py
"""
Projects Section - Tab container for schedule and animal management.

Tabs:
- Schedules: Hub for viewing and managing schedules (drag to Run/Stop to execute)
- Animals: Manage animal records
- Wizard: Step-by-step schedule creation
- Cages: Visual relay board layout with cage naming

Architecture:
- Each tab is responsible for its own data loading and UI
- Communication between tabs via signals
- Wizard tab creates schedules, Schedules tab displays/manages them
"""

from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .animals_tab import AnimalsTab
from .cages_visualization_tab import CagesVisualizationTab
from .schedules_hub import SchedulesHub
from .wizard_tab import WizardTab


class ProjectsSection(QWidget):
    """
    Container widget for project-related tabs.

    Design:
    - Uses QTabWidget for tab navigation
    - Schedules Hub: View, manage, and drag schedules to execute
    - Wizard: Create new schedules step-by-step
    - Seamless integration: clicking "+ New Schedule" in Hub switches to Wizard
    """

    def __init__(
        self, settings, print_to_terminal, database_handler, login_system, system_controller=None
    ):
        super().__init__()

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system
        self.system_controller = system_controller

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # Create a tab widget for schedules and animals
        self.tab_widget = QTabWidget()

        # ═══════════════════════════════════════════════════════════════
        # SCHEDULES TAB (Hub - view, manage, drag to run)
        # ═══════════════════════════════════════════════════════════════
        self.schedules_tab = SchedulesHub(
            settings,
            self.print_to_terminal,
            database_handler,
            login_system,
            system_controller=system_controller,
        )
        self.schedules_tab_index = self.tab_widget.addTab(self.schedules_tab, "Schedules")

        # Connect "New Schedule" button to switch to Wizard tab
        self.schedules_tab.create_requested.connect(self._switch_to_wizard)

        # ═══════════════════════════════════════════════════════════════
        # ANIMALS TAB
        # ═══════════════════════════════════════════════════════════════
        self.animals_tab = AnimalsTab(
            settings, self.print_to_terminal, database_handler, login_system
        )
        self.animals_tab_index = self.tab_widget.addTab(self.animals_tab, "Animals")

        # ═══════════════════════════════════════════════════════════════
        # WIZARD TAB (Step-by-step schedule creation)
        # ═══════════════════════════════════════════════════════════════
        self.wizard_tab = WizardTab(
            database_handler=database_handler,
            login_system=login_system,
            print_to_terminal=print_to_terminal,
            system_controller=system_controller,
        )
        self.wizard_tab_index = self.tab_widget.addTab(self.wizard_tab, "Wizard")

        # ═══════════════════════════════════════════════════════════════
        # CAGES TAB (Visual relay board layout)
        # ═══════════════════════════════════════════════════════════════
        self.cages_tab = CagesVisualizationTab(
            database_handler=database_handler,
            system_controller=system_controller,
            print_to_terminal=print_to_terminal,
        )
        self.cages_tab_index = self.tab_widget.addTab(self.cages_tab, "Cages")

        # ═══════════════════════════════════════════════════════════════
        # SIGNAL CONNECTIONS
        # ═══════════════════════════════════════════════════════════════

        # Refresh schedules tab when wizard creates a schedule
        self.wizard_tab.schedule_created.connect(self._on_wizard_schedule_created)

        self.layout.addWidget(self.tab_widget)

    def _switch_to_wizard(self) -> None:
        """
        Switch to the Wizard tab.

        Called when user clicks "+ New Schedule" in the Schedules Hub.
        Also resets the wizard to ensure fresh state.
        """
        # Switch to Wizard tab
        self.tab_widget.setCurrentIndex(self.wizard_tab_index)

        # Reset wizard to fresh state
        if hasattr(self.wizard_tab, 'refresh'):
            self.wizard_tab.refresh()

        self.print_to_terminal("[ProjectsSection] Switched to Schedule Wizard")

    def _on_wizard_schedule_created(self, config: dict):
        """
        Handle schedule created via wizard.

        - Refresh the schedules hub to show the new schedule
        - Optionally switch back to Schedules tab
        """
        # Refresh the schedules hub to show the new schedule
        if hasattr(self.schedules_tab, 'load_schedules'):
            self.schedules_tab.load_schedules()
        elif hasattr(self.schedules_tab, 'refresh'):
            self.schedules_tab.refresh()

        # Switch back to Schedules tab to show the new schedule
        self.tab_widget.setCurrentIndex(self.schedules_tab_index)

        schedule_name = config.get('parameters', {}).get('name', 'New Schedule')
        self.print_to_terminal(
            f"[ProjectsSection] Schedule '{schedule_name}' created, returning to hub"
        )
