# ui/user_tab.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QDialog, QInputDialog, QMessageBox
from PyQt5.QtCore import pyqtSignal

class UserTab(QWidget):
    login_signal = pyqtSignal(object)   # Emitted when login is successful, passing user info
    logout_signal = pyqtSignal()        # Emitted when user logs out

    def __init__(self, login_system):
        super().__init__()
        self.login_system = login_system
        self.current_user = None  # Holds the logged-in user info

        # Set up layout and initial UI state
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.info_label = QLabel("You are currently in Guest mode.")
        self.layout.addWidget(self.info_label)

        self.login_button = QPushButton("Log In")
        self.login_button.clicked.connect(self.prompt_login)
        self.layout.addWidget(self.login_button)

        self.logout_button = QPushButton("Log Out")
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setVisible(False)  # Hidden in guest mode
        self.layout.addWidget(self.logout_button)

    def prompt_login(self):
        """Prompts the user to log in."""
        dialog = QDialog(self)
        username, ok = QInputDialog.getText(self, "Login", "Enter username:")
        password, ok = QInputDialog.getText(self, "Login", "Enter password:", QInputDialog.Password)

        if ok and username and password:
            user_info = self.login_system.authenticate(username, password)
            if user_info:
                self.set_user(user_info)
                self.login_signal.emit(user_info)  # Emit login signal
            else:
                QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")

    def set_user(self, user_info):
        """Sets the user information after a successful login."""
        self.current_user = user_info
        self.info_label.setText(f"Logged in as: {user_info['username']}")
        self.login_button.setVisible(False)
        self.logout_button.setVisible(True)

    def logout(self):
        """Logs out the user."""
        self.current_user = None
        self.info_label.setText("You are currently in Guest mode.")
        self.login_button.setVisible(True)
        self.logout_button.setVisible(False)
        self.logout_signal.emit()  # Emit logout signal