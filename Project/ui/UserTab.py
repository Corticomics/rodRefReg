# ui/user_tab.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, QMessageBox, QHBoxLayout
from PyQt5.QtCore import pyqtSignal, Qt
import traceback

class UserTab(QWidget):
    login_signal = pyqtSignal(dict)
    logout_signal = pyqtSignal()
    size_changed_signal = pyqtSignal()  

    def __init__(self, login_system):
        super().__init__()
        self.login_system = login_system
        self.current_user = None

        # Main layout with centered alignment
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)

        # Info label
        self.info_label = QLabel("You are running the application in Guest mode.")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.info_label)

        # Username Label and Input
        self.username_label = QLabel("Username:")
        self.username_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.username_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setFixedWidth(200)
        self.username_input.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.username_input)

        # Password Label and Input
        self.password_label = QLabel("Password:")
        self.password_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedWidth(200)
        self.password_input.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.password_input)

        # Button Layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(10)  # Consistent spacing between buttons

        self.login_button = QPushButton("Log In")
        self.login_button.setFixedWidth(100)
        self.login_button.clicked.connect(self.handle_login)
        self.button_layout.addWidget(self.login_button)

        self.create_profile_button = QPushButton("Create New Profile")
        self.create_profile_button.setFixedWidth(150)
        self.create_profile_button.clicked.connect(self.handle_create_profile)
        self.button_layout.addWidget(self.create_profile_button)

        self.logout_button = QPushButton("Log Out")
        self.logout_button.setFixedWidth(100)
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setVisible(False)
        self.button_layout.addWidget(self.logout_button)

        self.layout.addLayout(self.button_layout)

    def handle_login(self):
        try:
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()

            if not username or not password:
                QMessageBox.warning(self, "Input Required", "Please enter both username and password.")
                return

            user_info = self.login_system.authenticate(username, password)
            if not user_info:
                QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")
                return

            self.set_user(user_info)
            self.login_signal.emit(user_info)

        except Exception as e:
            print(f"Exception during handle_login: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Login Error", f"An unexpected error occurred during login:\n{str(e)}")

    def set_user(self, user_info):
        try:
            self.current_user = user_info
            self.info_label.setText(f"Logged in as: {user_info.get('username', 'Unknown')}")
            self.username_input.clear()
            self.password_input.clear()

            # Hide login and create profile inputs/buttons
            self.username_label.hide()
            self.username_input.hide()
            self.password_label.hide()
            self.password_input.hide()
            self.login_button.hide()
            self.create_profile_button.hide()

            # Show logout button
            self.logout_button.show()

            # Adjust size and emit signal
            self.adjustSize()
            self.size_changed_signal.emit()

        except Exception as e:
            print(f"Error in set_user: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Profile Error", f"An unexpected error occurred:\n{str(e)}")

    def logout(self):
        try:
            self.current_user = None
            self.login_system.logout()
            self.info_label.setText("You are running the application in Guest mode.")

            # Show login and create profile inputs/buttons
            self.username_label.show()
            self.username_input.show()
            self.password_label.show()
            self.password_input.show()
            self.login_button.show()
            self.create_profile_button.show()

            # Hide logout button
            self.logout_button.hide()

            # Adjust size and emit signal
            self.adjustSize()
            self.size_changed_signal.emit()

        except Exception as e:
            print(f"Error during logout: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Logout Error", f"An unexpected error occurred during logout:\n{str(e)}")

    def handle_create_profile(self):
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
        try:
            if not username:
                raise ValueError("Username is required to set the minimal profile view.")
            
            self.info_label.setText(f"Logged in as: {username}")
            self.username_input.hide()
            self.password_input.hide()
            self.username_label.hide()
            self.password_label.hide()
            self.login_button.hide()
            self.create_profile_button.hide()
            self.logout_button.show()
            
            # Adjust the size and emit the signal
            self.adjustSize()
            self.size_changed_signal.emit()
        
        except ValueError as ve:
            QMessageBox.critical(self, "Profile View Error", str(ve))
            print(f"Profile View Error: {ve}")
        
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {str(e)}")
            print(f"Unexpected error in set_minimal_profile_view: {e}")

    def set_guest_view(self):
        try:
            self.info_label.setText("You are running the application in Guest mode.")
            self.username_input.show()
            self.password_input.show()
            self.username_label.show()
            self.password_label.show()
            self.login_button.show()
            self.create_profile_button.show()
            self.logout_button.hide()
            
            # Adjust the size and emit the signal
            self.adjustSize()
            self.size_changed_signal.emit()
        
        except Exception as e:
            QMessageBox.critical(self, "View Error", f"An unexpected error occurred while resetting to guest view: {str(e)}")
            print(f"Unexpected error in set_guest_view: {e}")