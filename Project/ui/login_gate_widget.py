from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

class LoginGateWidget(QStackedWidget):
    """
    A widget that shows either a login prompt or the projects section
    based on login status.
    """
    
    def __init__(self, projects_section, login_system):
        super().__init__()
        self.projects_section = projects_section
        self.login_system = login_system
        
        # Create the login prompt widget
        self.login_prompt = self._create_login_prompt()
        
        # Add both widgets to the stack
        self.addWidget(self.login_prompt)
        self.addWidget(self.projects_section)
        
        # Connect to login system signals
        self.login_system.login_status_changed.connect(self._handle_login_status)
        
        # Initial state
        self._handle_login_status()

    def _create_login_prompt(self):
        """Create the login prompt widget with a clean, minimal design."""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Message
        message = QLabel("Please log in to access projects")
        message.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        message.setFont(font)
        
        # Login button
        login_button = QPushButton("Login")
        login_button.setFixedWidth(200)
        login_button.setFixedHeight(40)
        login_button.clicked.connect(self._show_login_dialog)
        login_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        
        # Add widgets to layout with spacing
        layout.addStretch()
        layout.addWidget(message)
        layout.addSpacing(20)
        layout.addWidget(login_button, alignment=Qt.AlignCenter)
        layout.addStretch()
        
        container.setLayout(layout)
        return container

    def _show_login_dialog(self):
        """Show the login tab in the suggest settings section."""
        # Get the suggest settings section from the main window
        main_window = self.window()  # Get the top-level window
        if hasattr(main_window, 'suggest_settings_section'):
            # Switch to the user tab
            user_tab_index = main_window.suggest_settings_section.tab_widget.indexOf(
                main_window.suggest_settings_section.user_tab
            )
            main_window.suggest_settings_section.tab_widget.setCurrentIndex(user_tab_index)

    def _handle_login_status(self):
        """Update the visible widget based on login status."""
        if self.login_system.is_logged_in():
            self.setCurrentWidget(self.projects_section)
        else:
            self.setCurrentWidget(self.login_prompt) 