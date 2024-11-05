# app/ui/gui.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSplitter, QSizePolicy, QScrollArea, QLabel, QLineEdit, QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal
from .ProjectsSection import ProjectsSection
from .suggest_settings import SuggestSettingsSection
from .run_stop_section import RunStopSection  # Ensure this file exists and is correctly implemented
from shared.models.database import DatabaseManager

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)

    def __init__(self, run_program, stop_program, change_relay_hats, settings, db_manager, style='bitlearns'):
        super().__init__()

        self.run_program = run_program
        self.stop_program = stop_program
        self.change_relay_hats = change_relay_hats

        self.settings = settings  # Ensure settings are stored as self.settings
        self.db_manager = db_manager  # Assign db_manager
        self.selected_relays = self.settings.get('selected_relays', [])
        self.num_triggers = self.settings.get('num_triggers', {})

        # Connect the system message signal to the print_to_terminal method
        self.system_message_signal.connect(self.print_to_terminal)

        self.init_ui(style)

    def init_ui(self, style):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

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
                QPushButton:hover:!disabled {
                    background-color: #0056b3;
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
                QScrollArea {
                    background-color: #f1f1f1;
                    border: none;
                }
            """)

        self.main_layout = QVBoxLayout()

        # Run/Stop Section
        self.run_stop_section = RunStopSection(
            self.run_program,
            self.stop_program,
            self.change_relay_hats_callback,
            settings=self.settings,
            advanced_settings=None  # Pass if applicable
        )
        self.main_layout.addWidget(self.run_stop_section)

        # Upper Layout containing Projects and Suggest Settings
        self.upper_layout = QHBoxLayout()

        # Projects Section
        self.projects_section = ProjectsSection(
            self.db_manager,
            self.print_to_terminal,
            self.run_program,
            self.stop_program,
            self.settings
        )
        self.projects_scroll = QScrollArea()
        self.projects_scroll.setWidgetResizable(True)
        self.projects_scroll.setWidget(self.projects_section)
        self.upper_layout.addWidget(self.projects_scroll)

        # Suggest Settings Section
        self.suggest_settings_section = SuggestSettingsSection(
            self.db_manager,
            self.print_to_terminal
        )
        self.suggest_scroll = QScrollArea()
        self.suggest_scroll.setWidgetResizable(True)
        self.suggest_scroll.setWidget(self.suggest_settings_section)
        self.upper_layout.addWidget(self.suggest_scroll)

        self.main_layout.addLayout(self.upper_layout)
        self.setLayout(self.main_layout)

    def print_to_terminal(self, message):
        """Safely print messages to the terminal."""
        self.run_stop_section.terminal_output.print_to_terminal(message)