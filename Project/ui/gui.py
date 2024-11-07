from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QPlainTextEdit, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal

# Import sections for the GUI
from .welcome_section import WelcomeSection
from .run_stop_section import RunStopSection
from .suggest_settings import SuggestSettingsSection
from .projects_section import ProjectsSection
from .user_icon import UserIcon  # Import UserIcon for login functionality

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)

    def __init__(self, run_program, stop_program, change_relay_hats, settings, database_handler, login_system, style='bitlearns'):
        super().__init__()

        self.run_program = run_program
        self.stop_program = stop_program
        self.change_relay_hats = change_relay_hats
        self.settings = settings
        self.database_handler = database_handler
        self.login_system = login_system  # Add login system for managing user sessions

        # Default to guest mode
        self.current_user = None  

        # Connect the system message signal to the print_to_terminal method
        self.system_message_signal.connect(self.print_to_terminal)

        # Initialize the main UI layout
        self.init_ui(style)

    def init_ui(self, style):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        # Main layout setup
        self.main_layout = QVBoxLayout(self)

        # User icon for login and profile actions
        self.user_icon = UserIcon(self, self.database_handler, self.login_system)
        self.user_icon.login_signal.connect(self.on_login)    # Connect login signal
        self.user_icon.logout_signal.connect(self.on_logout)  # Connect logout signal
        self.main_layout.addWidget(self.user_icon, alignment=Qt.AlignRight)

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

        # System messages section - Updated to use QPlainTextEdit
        self.terminal_output = QPlainTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setPlainText("System Messages")
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
        
        # Suggested settings section
        self.suggest_settings_section = SuggestSettingsSection(
            self.settings,
            self.suggest_settings_callback,
            self.push_settings_callback,
            self.save_slack_credentials_callback,
            advanced_settings=None,
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

        # Load initial data (guest view)
        self.load_animals_tab()

    def print_to_terminal(self, message):
        """Display messages in the system message section."""
        self.terminal_output.appendPlainText(message)

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
    
    def on_login(self, user):
        """Callback for handling user login."""
        self.current_user = user
        self.print_to_terminal(f"Logged in as: {user.name}")
        self.load_animals_tab(trainer_id=user.id)  # Load animals for the logged-in trainer

    def on_logout(self):
        """Callback for handling user logout, reverting to guest mode."""
        self.current_user = None
        self.print_to_terminal("Logged out. Displaying all animals (guest mode).")
        self.load_animals_tab()  # Load all animals in guest mode

    def load_animals_tab(self, trainer_id=None):
        """
        Load the AnimalsTab for the specific trainer.
        If trainer_id is None, display all animals (guest mode).
        """
        if trainer_id:
            self.projects_section.animals_tab.trainer_id = trainer_id
            self.print_to_terminal(f"Displaying animals for trainer ID {trainer_id}")
        else:
            self.projects_section.animals_tab.trainer_id = None
            self.print_to_terminal("Displaying all animals (guest mode)")
        self.projects_section.animals_tab.load_animals()