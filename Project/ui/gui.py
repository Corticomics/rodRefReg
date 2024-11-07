from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QSplitter, QSizePolicy, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal

# Import sections for the GUI
from .welcome_section import WelcomeSection
from .run_stop_section import RunStopSection
from .suggest_settings import SuggestSettingsSection
from .schedules_tab import SchedulesTab
from .animals_tab import AnimalsTab
from .projects_section import ProjectsSection

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)

    def __init__(self, run_program, stop_program, change_relay_hats, settings, database_handler, style='bitlearns'):
        super().__init__()

        self.run_program = run_program
        self.stop_program = stop_program
        self.change_relay_hats = change_relay_hats
        self.settings = settings
        self.database_handler = database_handler  # Pass database handler to be used in ProjectsSection

        # Connect the system message signal to the print_to_terminal method
        self.system_message_signal.connect(self.print_to_terminal)

        # Initialize the main UI layout
        self.init_ui(style)

    def init_ui(self, style):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        # Set stylesheet if a specific style is requested
        if style == 'bitlearns':
            self.setStyleSheet("""
                QWidget {
                    background-color: #f8f9fa;
                    font-size: 14px;
                }
                QGroupBox {
                    background-color: #ffffff;
                    border: 1px solid #ced4da;
                    border-radius: 5px;
                    padding: 15px;
                }
                QPushButton {
                    background-color: #007bff;
                    border: 1px solid #007bff;
                    border-radius: 5px;
                    color: #ffffff;
                    padding: 10px;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
                QLabel {
                    color: #343a40;
                    background-color: #ffffff;
                }
                QLineEdit, QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #ced4da;
                    padding: 5px;
                }
            """)

        # Main layout setup
        self.main_layout = QVBoxLayout(self)

        # Welcome section at the top
        self.welcome_section = WelcomeSection()
        self.welcome_scroll_area = QScrollArea()
        self.welcome_scroll_area.setWidgetResizable(True)
        self.welcome_scroll_area.setWidget(self.welcome_section)
        self.main_layout.addWidget(self.welcome_scroll_area)

        # Toggle button for the welcome message
        self.toggle_welcome_button = QPushButton("Hide Welcome Message")
        self.toggle_welcome_button.clicked.connect(self.toggle_welcome_message)
        self.main_layout.addWidget(self.toggle_welcome_button)

        # Horizontal layout for the middle content
        self.upper_layout = QHBoxLayout()

        # Left side layout (messages and projects)
        self.left_layout = QVBoxLayout()

        # System messages section
        self.terminal_output = QLabel("System Messages")  # Placeholder, replace with your TerminalOutput if needed
        self.terminal_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.left_layout.addWidget(self.terminal_output)

        # Projects section with tabs for schedules and animals
        self.projects_section = ProjectsSection(self.settings, self.print_to_terminal, self.database_handler)
        self.left_layout.addWidget(self.projects_section)

        # Left content with scroll
        self.left_content = QWidget()
        self.left_content.setLayout(self.left_layout)
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setWidget(self.left_content)
        self.upper_layout.addWidget(self.left_scroll)

        # Right side layout for suggested settings and run/stop
        self.right_layout = QVBoxLayout()

        # Run/Stop section (created first to be passed to SuggestSettingsSection)
        self.run_stop_section = RunStopSection(self.run_program, self.stop_program, self.change_relay_hats, self.settings)
        
        # Suggested settings section (now initialized after run_stop_section)
        self.suggest_settings_section = SuggestSettingsSection(
            self.settings,
            self.suggest_settings_callback,
            self.push_settings_callback,
            self.save_slack_credentials_callback,
            advanced_settings=None,  # Replace with actual advanced settings if available
            run_stop_section=self.run_stop_section
        )
        
        self.right_layout.addWidget(self.suggest_settings_section)
        self.right_layout.addWidget(self.run_stop_section)

        # Right content with scroll
        self.right_content = QWidget()
        self.right_content.setLayout(self.right_layout)
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setWidget(self.right_content)
        self.upper_layout.addWidget(self.right_scroll)

        # Add upper layout to main layout
        self.main_layout.addLayout(self.upper_layout)

    def print_to_terminal(self, message):
        """Display messages in the system message section."""
        self.terminal_output.setText(message)  # Replace with .append() if using QTextEdit

    def toggle_welcome_message(self):
        """Show or hide the welcome section."""
        visible = self.welcome_scroll_area.isVisible()
        self.welcome_scroll_area.setVisible(not visible)
        self.toggle_welcome_button.setText("Show Welcome Message" if visible else "Hide Welcome Message")

    def suggest_settings_callback(self):
        print("Suggested settings applied.")

    def push_settings_callback(self):
        print("Settings pushed.")

    def save_slack_credentials_callback(self):
        print("Slack credentials saved.")