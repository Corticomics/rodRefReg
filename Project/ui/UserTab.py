# ui/user_tab.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import pyqtSignal
import traceback

class UserTab(QWidget):
    login_signal = pyqtSignal(object)
    logout_signal = pyqtSignal()

    def __init__(self, login_system):
        super().__init__()
        self.login_system = login_system
        self.current_user = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.info_label = QLabel("You are running the application in Guest mode.")
        self.layout.addWidget(self.info_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.layout.addWidget(QLabel("Username:"))
        self.layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(QLabel("Password:"))
        self.layout.addWidget(self.password_input)

        self.login_button = QPushButton("Log In")
        self.login_button.clicked.connect(self.handle_login)
        self.layout.addWidget(self.login_button)

        self.create_profile_button = QPushButton("Create New Profile")
        self.create_profile_button.clicked.connect(self.handle_create_profile)
        self.layout.addWidget(self.create_profile_button)

        self.logout_button = QPushButton("Log Out")
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setVisible(False)
        self.layout.addWidget(self.logout_button)

    def handle_login(self):
        try:
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()

            if not username or not password:
                QMessageBox.warning(self, "Input Required", "Please enter both username and password.")
                return

            print(f"Initiating authentication for username: {username}")
            user_info = self.login_system.authenticate(username, password)
            if not user_info:
                QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")
                return

            print(f"Login successful: {user_info}")
            self.set_user(user_info)
            self.login_signal.emit(user_info)

        except Exception as e:
            print(f"Exception during handle_login: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Login Error", f"An unexpected error occurred during login:\n{str(e)}")

    def set_user(self, user_info):
        """Sets the user information after a successful login."""
        try:
            self.current_user = user_info
            self.info_label.setText(f"Logged in as: {user_info.get('username', 'Unknown')}")
            self.username_input.clear()
            self.password_input.clear()
            self.username_input.setVisible(False)
            self.password_input.setVisible(False)
            self.login_button.setVisible(False)
            self.create_profile_button.setVisible(False)
            self.logout_button.setVisible(True)
        except Exception as e:
            print(f"Error in set_user: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Profile Error", f"An unexpected error occurred:\n{str(e)}")

    def logout(self):
        try:
            self.current_user = None
            self.login_system.logout()
            self.info_label.setText("You are running the application in Guest mode.")
            self.username_input.setVisible(True)
            self.password_input.setVisible(True)
            self.login_button.setVisible(True)
            self.create_profile_button.setVisible(True)
            self.logout_button.setVisible(False)
            self.logout_signal.emit()
        except Exception as e:
            print(f"Error during logout: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Logout Error", f"An unexpected error occurred during logout:\n{str(e)}")
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

    
    def set_minimal_profile_view(self, username):
        """Sets a minimal view for logged-in users with error handling."""
        try:
            if not username:
                raise ValueError("Username is required to set the minimal profile view.")
            
            self.info_label.setText(f"Logged in as: {username}")
            self.username_input.hide()
            self.password_input.hide()
            self.login_button.hide()
            self.create_profile_button.hide()
            self.logout_button.show()
            self.setFixedSize(self.sizeHint())
        
        except ValueError as ve:
            QMessageBox.critical(self, "Profile View Error", str(ve))
            print(f"Profile View Error: {ve}")
        
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {str(e)}")
            print(f"Unexpected error in set_minimal_profile_view: {e}")

    def set_guest_view(self):
        """Resets the view for guest mode with error handling."""
        try:
            self.info_label.setText("You are running the application in Guest mode.")
            self.username_input.show()
            self.password_input.show()
            self.login_button.show()
            self.create_profile_button.show()
            self.logout_button.hide()
            self.setFixedSize(self.sizeHint())
        
        except Exception as e:
            QMessageBox.critical(self, "View Error", f"An unexpected error occurred while resetting to guest view: {str(e)}")
            print(f"Unexpected error in set_guest_view: {e}")