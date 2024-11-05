# app/gui/main_window.py

from PyQt5.QtWidgets import (
    QMainWindow, QAction, QStackedWidget, QMessageBox, QApplication
)
from gui.welcome_section import WelcomeSection
from gui.terminal_output import TerminalOutput
from gui.animal_profile_manager import AnimalProfileManager
from gui.project_builder import ProjectBuilder
from gui.dashboard import Dashboard  # Newly added
from gui.developer_mode_launcher import DeveloperModeLauncher  # Adjusted
from shared.models.database import DatabaseManager

class MainWindow(QMainWindow):
    def __init__(self, relay_handler, notification_handler, db_manager, settings):
        super().__init__()
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.db_manager = db_manager
        self.settings = settings

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        # Create menu bar
        self.create_menu()

        # Create stacked widget
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Initialize views
        self.init_views()

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('Menu')

        home_action = QAction('Home', self)
        home_action.triggered.connect(lambda: self.switch_view('home'))
        file_menu.addAction(home_action)

        dashboard_action = QAction('Dashboard', self)
        dashboard_action.triggered.connect(lambda: self.switch_view('dashboard'))
        file_menu.addAction(dashboard_action)

        animal_profiles_action = QAction('Animal Profiles', self)
        animal_profiles_action.triggered.connect(lambda: self.switch_view('animal_profiles'))
        file_menu.addAction(animal_profiles_action)

        build_project_action = QAction('Build Watering Project', self)
        build_project_action.triggered.connect(lambda: self.switch_view('project_builder'))
        file_menu.addAction(build_project_action)

        developer_mode_action = QAction('Developer Mode', self)
        developer_mode_action.triggered.connect(self.launch_developer_mode)
        file_menu.addAction(developer_mode_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def init_views(self):
        # Home view
        self.welcome_section = WelcomeSection()
        self.terminal_output = TerminalOutput()
        home_widget = self.create_home_widget()

        # Dashboard view
        self.dashboard = Dashboard(self.db_manager, self.open_project)

        # Animal Profile Manager
        self.animal_profile_manager = AnimalProfileManager(self.db_manager)

        # Project Builder
        self.project_builder = ProjectBuilder(
            self.db_manager,
            self.relay_handler,
            self.notification_handler,
            self.settings,
            self.terminal_output.print_to_terminal
        )

        # Add views to stacked widget
        self.stacked_widget.addWidget(home_widget)                  # Index 0
        self.stacked_widget.addWidget(self.dashboard)               # Index 1
        self.stacked_widget.addWidget(self.animal_profile_manager)  # Index 2
        self.stacked_widget.addWidget(self.project_builder)         # Index 3

        # Set initial view
        self.stacked_widget.setCurrentIndex(0)

    def create_home_widget(self):
        from PyQt5.QtWidgets import QWidget, QVBoxLayout

        home_widget = QWidget()
        home_layout = QVBoxLayout(home_widget)
        home_layout.addWidget(self.welcome_section)
        home_layout.addWidget(self.terminal_output)
        return home_widget

    def switch_view(self, view_name):
        if view_name == 'home':
            self.stacked_widget.setCurrentIndex(0)
        elif view_name == 'dashboard':
            self.stacked_widget.setCurrentIndex(1)
        elif view_name == 'animal_profiles':
            self.stacked_widget.setCurrentIndex(2)
        elif view_name == 'project_builder':
            self.stacked_widget.setCurrentIndex(3)
        else:
            QMessageBox.warning(self, "Error", f"Unknown view: {view_name}")

    def launch_developer_mode(self):
        try:
            # Launch Developer Mode as a separate QApplication
            launcher = DeveloperModeLauncher()
            launcher.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch Developer Mode: {e}")

    def open_project(self, project_id):
        # Implement functionality to open a selected project
        # For example, load the project details into the ProjectBuilder
        project = self.db_manager.get_project_by_id(project_id)
        if project:
            self.project_builder.load_project(project)
            self.switch_view('project_builder')
        else:
            QMessageBox.warning(self, "Error", f"Project ID: {project_id} not found.")