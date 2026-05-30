from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget


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
        # objectName drives the card-coloured background defined in the theme
        # QSS (white in light, dark-card in dark) so the prompt reads as an
        # intentional surface rather than the bare grey app background.
        container = QWidget()
        container.setObjectName("LoginGatePrompt")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Message. The login form itself lives in the always-visible Profile
        # tab, so this prompt is informational only — no button (the old
        # "Login" button just re-selected the already-current Profile tab and
        # appeared to do nothing).
        message = QLabel("Please log in to access projects")
        message.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        message.setFont(font)

        layout.addStretch()
        layout.addWidget(message)
        layout.addStretch()

        container.setLayout(layout)
        return container

    def _handle_login_status(self):
        """Update the visible widget based on login status."""
        if self.login_system.is_logged_in():
            self.setCurrentWidget(self.projects_section)
        else:
            self.setCurrentWidget(self.login_prompt)
