# ui/user_tab.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, QMessageBox, QInputDialog
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

        # Display current mode (guest/user)
        self.info_label = QLabel("You are running the application in Guest mode.")
        self.layout.addWidget(self.info_label)

        # Username and password input fields for login
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.layout.addWidget(QLabel("Username:"))
        self.layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(QLabel("Password:"))
        self.layout.addWidget(self.password_input)

        # Login button
        self.login_button = QPushButton("Log In")
        self.login_button.clicked.connect(self.handle_login)
        self.layout.addWidget(self.login_button)

        # Create New Profile button for registration
        self.create_profile_button = QPushButton("Create New Profile")
        self.create_profile_button.clicked.connect(self.handle_create_profile)
        self.layout.addWidget(self.create_profile_button)

        # Logout button (initially hidden in guest mode)
        self.logout_button = QPushButton("Log Out")
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setVisible(False)
        self.layout.addWidget(self.logout_button)

    def handle_login(self):
        """Handle the login process with error handling."""
        try:
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()

            if not username or not password:
                QMessageBox.warning(self, "Input Required", "Please enter both username and password.")
                return

            user_info = self.login_system.authenticate(username, password)
            if user_info:
                self.set_user(user_info)
                self.login_signal.emit(user_info)  # Emit login signal
            else:
                QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")
        except Exception as e:
            QMessageBox.critical(self, "Login Error", f"An unexpected error occurred during login: {str(e)}")

    def handle_create_profile(self):
        """Handle the profile creation process with error handling."""
        try:
            username, ok = QInputDialog.getText(self, "Create Profile", "Choose a username:")
            if not ok or not username:
                QMessageBox.warning(self, "Invalid Username", "Username cannot be empty.")
                return

            password, ok = QInputDialog.getText(self, "Create Profile", "Choose a password:", QLineEdit.Password)
            if not ok or not password:
                QMessageBox.warning(self, "Invalid Password", "Password cannot be empty.")
                return

            success = self.login_system.create_user(username, password)
            if success:
                QMessageBox.information(self, "Profile Created", f"Profile for '{username}' created successfully.")
            else:
                QMessageBox.warning(self, "Creation Failed", f"Username '{username}' is already taken.")
        except Exception as e:
            QMessageBox.critical(self, "Profile Creation Error", f"An unexpected error occurred during profile creation: {str(e)}")

    def set_user(self, user_info):
        """Sets the user information after a successful login with error handling."""
        try:
            self.current_user = user_info
            self.info_label.setText(f"Logged in as: {user_info['username']}")
            self.username_input.clear()
            self.password_input.clear()
            self.username_input.setVisible(False)
            self.password_input.setVisible(False)
            self.login_button.setVisible(False)
            self.create_profile_button.setVisible(False)
            self.logout_button.setVisible(True)
        except KeyError as e:
            QMessageBox.critical(self, "Data Error", f"Missing user information: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {str(e)}")

    def logout(self):
        """Logs out the user with error handling."""
        try:
            self.current_user = None
            self.info_label.setText("You are running the application in Guest mode.")
            self.username_input.setVisible(True)
            self.password_input.setVisible(True)
            self.login_button.setVisible(True)
            self.create_profile_button.setVisible(True)
            self.logout_button.setVisible(False)
            self.logout_signal.emit()  # Emit logout signal
        except Exception as e:
            QMessageBox.critical(self, "Logout Error", f"An unexpected error occurred during logout: {str(e)}")