# ui/projects_section.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPushButton, QMessageBox
from .schedules_tab import SchedulesTab
from .animals_tab import AnimalsTab
from .wizard_tab import WizardTab
from .cages_visualization_tab import CagesVisualizationTab

class ProjectsSection(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler, login_system,
                 system_controller=None):
        super().__init__()

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system  # Store the login_system
        self.system_controller = system_controller  # For hardware limits

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create a tab widget for schedules and animals
        self.tab_widget = QTabWidget()

        # Schedules tab (legacy method)
        self.schedules_tab = SchedulesTab(
            settings, 
            self.print_to_terminal,
            database_handler, 
            login_system,
            system_controller=system_controller
        )
        self.tab_widget.addTab(self.schedules_tab, "Schedules")

        # Animals tab
        self.animals_tab = AnimalsTab(
            settings, 
            self.print_to_terminal,
            database_handler, 
            login_system
        )
        self.tab_widget.addTab(self.animals_tab, "Animals")
        
        # Wizard tab (new step-by-step method)
        self.wizard_tab = WizardTab(
            database_handler=database_handler,
            login_system=login_system,
            print_to_terminal=print_to_terminal,
            system_controller=system_controller
        )
        self.tab_widget.addTab(self.wizard_tab, "Wizard")
        
        # Cages visualization tab
        self.cages_tab = CagesVisualizationTab(
            database_handler=database_handler,
            system_controller=system_controller,
            print_to_terminal=print_to_terminal
        )
        self.tab_widget.addTab(self.cages_tab, "Cages")
        
        # Refresh schedules tab when wizard creates a schedule
        self.wizard_tab.schedule_created.connect(self._on_wizard_schedule_created)

        self.layout.addWidget(self.tab_widget)
    
    def _on_wizard_schedule_created(self, config: dict):
        """Handle schedule created via wizard - refresh schedules list."""
        # Refresh the schedules tab to show the new schedule
        if hasattr(self.schedules_tab, 'load_schedules'):
            self.schedules_tab.load_schedules()
        elif hasattr(self.schedules_tab, 'refresh'):
            self.schedules_tab.refresh()
