# ui/user_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, 
    QMessageBox, QFrame, QGridLayout, QSizePolicy, QInputDialog, QFormLayout, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal, Qt, QDateTime
from PyQt5.QtGui import QFont, QIcon
import traceback

class UserTab(QWidget):
    login_signal = pyqtSignal(dict)
    logout_signal = pyqtSignal()
    size_changed_signal = pyqtSignal()

    def __init__(self, login_system, database_handler=None):
        super().__init__()
        self.login_system = login_system
        self.database_handler = database_handler
        self.current_user = None
        self.init_ui()

    def init_ui(self):
        # Main layout with reduced spacing
        self.layout = QVBoxLayout()
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.layout)

        # Info label with smaller font
        self.info_label = QLabel("You are running the application in Guest mode.")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setFont(QFont("Segoe UI", 12))
        self.info_label.setStyleSheet("""
            QLabel {
                color: #1a73e8;
                padding: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f8f9fa, stop:1 #ffffff);
                border-radius: 6px;
            }
        """)
        self.layout.addWidget(self.info_label)

        # Login form container
        self.login_container = QFrame()
        self.login_container.setFrameStyle(QFrame.NoFrame)
        self.login_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 6px;
                padding: 16px;
                margin: 8px;
                border: 1px solid #e0e4e8;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            }
        """)

        # Form layout for login inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(8, 8, 8, 8)

        # Create and style input fields
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setStyleSheet(self._get_input_style())
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self._get_input_style())

        # Add fields to form layout
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        
        # Set form layout to login container
        self.login_container.setLayout(form_layout)
        self.layout.addWidget(self.login_container)

        # Setup buttons
        self._setup_buttons()
        self.layout.addStretch()

    def _get_input_style(self):
        return """
            QLineEdit {
                border: 1px solid #e0e4e8;
                border-radius: 4px;
                padding: 6px 12px;
                background: white;
                font-size: 11px;
                min-height: 24px;
            }
            QLineEdit:hover {
                border-color: #1a73e8;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
                background: white;
                box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.1);
            }
        """

    def _setup_buttons(self):
        # Create buttons container
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        # Create and style buttons
        self.login_button = QPushButton("Log In")
        self.create_profile_button = QPushButton("Create New Profile")
        self.logout_button = QPushButton("Log Out")
        
        # Style each button
        for button in [self.login_button, self.create_profile_button, self.logout_button]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #1a73e8;
                    border: 1px solid #1a73e8;
                    border-radius: 4px;
                    padding: 6px 12px;
                    min-width: 80px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #1a73e8;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #1557b0;
                }
            """)
        
        # Connect button signals
        self.login_button.clicked.connect(self.handle_login)
        self.create_profile_button.clicked.connect(self.handle_create_profile)
        self.logout_button.clicked.connect(self.logout)
        
        # Add buttons to layout
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.create_profile_button)
        buttons_layout.addWidget(self.logout_button)
        
        # Hide logout button initially
        self.logout_button.hide()
        
        # Add buttons layout to main layout
        self.layout.addLayout(buttons_layout)

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

            if 'trainer_id' not in user_info:
                QMessageBox.warning(self, "Login Failed", "Invalid user data: missing trainer ID.")
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
            
            # Clear and hide login form elements
            self.login_container.hide()
            self.info_label.hide()  # Hide the info label
            
            # Create profile container
            self.profile_container = QWidget()
            profile_layout = QVBoxLayout(self.profile_container)
            profile_layout.setSpacing(16)
            profile_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
            
            # Welcome message
            welcome_label = QLabel(f"Welcome, {user_info['username']}")
            welcome_label.setStyleSheet("""
                QLabel {
                    color: #202124;
                    font-size: 18px;
                    font-weight: 600;
                }
            """)
            welcome_label.setAlignment(Qt.AlignCenter)
            profile_layout.addWidget(welcome_label)
            
            # Stats container
            stats_container = QFrame()
            stats_layout = QGridLayout(stats_container)
            stats_layout.setSpacing(8)
            stats_container.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #e0e4e8;
                    border-radius: 8px;
                    padding: 16px;
                }
            """)
            
            # Simplified stats
            stats = [
                ("Trainer ID", str(user_info.get('trainer_id', 'N/A'))),
                ("Last Login", QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm"))
            ]
            
            for i, (label, value) in enumerate(stats):
                stat_label = QLabel(label + ":")
                stat_value = QLabel(value)
                stats_layout.addWidget(stat_label, i, 0)
                stats_layout.addWidget(stat_value, i, 1)
            
            profile_layout.addWidget(stats_container)
            
            # Logout button
            self.logout_button = self._create_button("Log Out", "#dc3545")
            self.logout_button.clicked.connect(self.logout)
            profile_layout.addWidget(self.logout_button)
            
            self.layout.addWidget(self.profile_container)
            self.adjustSize()
            self.size_changed_signal.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {str(e)}")
            print(f"Unexpected error in set_user: {e}")

    def logout(self):
        try:
            self.current_user = None
            self.login_system.logout()
            
            # Remove the profile container if it exists
            if hasattr(self, 'profile_container'):
                self.profile_container.deleteLater()
                delattr(self, 'profile_container')
            
            # Show login container
            self.login_container.show()
            
            # Reset the info label
            self.info_label.setText("You are running the application in Guest mode.")
            
            # Reset input fields
            self.username_input.clear()
            self.password_input.clear()
            self.username_input.setVisible(True)
            self.password_input.setVisible(True)
            
            # Reset buttons
            self.login_button.setVisible(True)
            self.create_profile_button.setVisible(True)
            self.logout_button.setVisible(False)
            
            # Emit logout signal
            self.logout_signal.emit()
            
            # Adjust size
            self.adjustSize()
            self.size_changed_signal.emit()
            
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


    def set_guest_view(self):
        """Resets the view for guest mode with error handling."""
        try:
            self.info_label.setText("You are running the application in Guest mode.")
            self.username_input.show()
            self.password_input.show()
            self.login_button.show()
            self.create_profile_button.show()
            self.logout_button.hide()
            self.adjustSize()
            self.size_changed_signal.emit()
        
        except Exception as e:
            QMessageBox.critical(self, "View Error", f"An unexpected error occurred while resetting to guest view: {str(e)}")
            print(f"Unexpected error in set_guest_view: {e}")

    def _create_button(self, text, color):
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setFont(QFont("Segoe UI", 11, QFont.Medium))
        button.setMinimumHeight(44)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 500;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color, 20)};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color, 20)};
                border-color: {self._darken_color(color, 20)};
            }}
        """)
        return button

    def _darken_color(self, hex_color, amount=10):
        # Simple color darkening function
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(max(0, c - amount) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"