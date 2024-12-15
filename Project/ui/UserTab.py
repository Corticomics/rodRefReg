# ui/user_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, 
    QMessageBox, QFrame, QGridLayout, QSizePolicy, QInputDialog
)
from PyQt5.QtCore import pyqtSignal, Qt, QDateTime
from PyQt5.QtGui import QFont, QIcon
import traceback

class UserTab(QWidget):
    login_signal = pyqtSignal(dict)
    logout_signal = pyqtSignal()
    size_changed_signal = pyqtSignal()

    def __init__(self, login_system):
        super().__init__()
        self.login_system = login_system
        self.current_user = None
        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(main_layout)

        # Info label with custom styling
        self.info_label = QLabel("You are running the application in Guest mode.")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.info_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(self.info_label)

        # Login form container
        self.login_container = QFrame()
        self.login_container.setFrameStyle(QFrame.StyledPanel)
        self.login_container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        # Grid layout for form elements
        form_layout = QGridLayout(self.login_container)
        form_layout.setSpacing(10)

        # Username field
        username_label = QLabel("Username:")
        username_label.setFont(QFont("Arial", 10))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setStyleSheet(self._get_input_style())
        
        # Password field
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Arial", 10))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self._get_input_style())

        # Add form elements to grid
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username_input, 0, 1)
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_input, 1, 1)

        main_layout.addWidget(self.login_container)

        # Buttons container
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)

        # Style and create buttons
        self.login_button = self._create_button("Log In", "#007bff")
        self.create_profile_button = self._create_button("Create New Profile", "#28a745")
        self.logout_button = self._create_button("Log Out", "#dc3545")
        
        self.login_button.clicked.connect(self.handle_login)
        self.create_profile_button.clicked.connect(self.handle_create_profile)
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setVisible(False)

        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.create_profile_button)
        buttons_layout.addWidget(self.logout_button)

        main_layout.addLayout(buttons_layout)
        main_layout.addStretch()

    def _get_input_style(self):
        return """
            QLineEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: #80bdff;
                outline: 0;
                box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
            }
        """

    def _create_button(self, text, color):
        button = QPushButton(text)
        button.setFont(QFont("Arial", 10))
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color, 20)};
            }}
        """)
        return button

    def _darken_color(self, hex_color, amount=10):
        # Simple color darkening function
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(max(0, c - amount) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def handle_login(self):
        try:
            print('1')
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
            
            # Clear and hide login form container
            self.login_container.hide()
            
            # Create and show user profile container
            self.profile_container = QFrame()
            self.profile_container.setFrameStyle(QFrame.StyledPanel)
            self.profile_container.setStyleSheet("""
                QFrame {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 20px;
                }
            """)
            
            profile_layout = QVBoxLayout(self.profile_container)
            
            # User avatar/icon (placeholder)
            user_icon = QLabel()
            user_icon.setPixmap(QIcon(":/icons/user.png").pixmap(64, 64))
            user_icon.setAlignment(Qt.AlignCenter)
            profile_layout.addWidget(user_icon)
            
            # Username display
            username_label = QLabel(f"Welcome, {user_info.get('username', 'Unknown')}")
            username_label.setAlignment(Qt.AlignCenter)
            username_label.setFont(QFont("Arial", 14, QFont.Bold))
            username_label.setStyleSheet("color: #2c3e50; margin: 10px 0;")
            profile_layout.addWidget(username_label)
            
            # Role display
            role_label = QLabel(f"Role: {user_info.get('role', 'User').capitalize()}")
            role_label.setAlignment(Qt.AlignCenter)
            role_label.setStyleSheet("color: #6c757d; margin-bottom: 20px;")
            profile_layout.addWidget(role_label)
            
            # Stats container
            stats_container = QFrame()
            stats_layout = QGridLayout(stats_container)
            stats_container.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 4px;
                    padding: 10px;
                }
            """)
            
            # Add some user stats (customize based on your needs)
            stats = [
                ("Trainer ID", str(user_info.get('trainer_id', 'N/A'))),
                ("Last Login", QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm")),
                ("Active Animals", str(len(self.database_handler.get_animals(user_info['trainer_id']))))
            ]
            
            for i, (label, value) in enumerate(stats):
                stat_label = QLabel(label + ":")
                stat_label.setStyleSheet("color: #6c757d;")
                stat_value = QLabel(value)
                stat_value.setStyleSheet("color: #2c3e50; font-weight: bold;")
                stats_layout.addWidget(stat_label, i, 0)
                stats_layout.addWidget(stat_value, i, 1)
            
            profile_layout.addWidget(stats_container)
            
            # Logout button with refined styling
            self.logout_button = self._create_button("Log Out", "#dc3545")
            self.logout_button.clicked.connect(self.logout)
            profile_layout.addWidget(self.logout_button)
            
            self.layout.addWidget(self.profile_container)
            
            # Adjust the size and emit the signal
            self.adjustSize()
            self.size_changed_signal.emit()
            
        except ValueError as ve:
            QMessageBox.critical(self, "Profile View Error", str(ve))
            print(f"Profile View Error: {ve}")
        
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {str(e)}")
            print(f"Unexpected error in set_user: {e}")

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
            
            # Adjust the size and emit the signal
            

        
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
            self.adjustSize()
            self.size_changed_signal.emit()
        
        except Exception as e:
            QMessageBox.critical(self, "View Error", f"An unexpected error occurred while resetting to guest view: {str(e)}")
            print(f"Unexpected error in set_guest_view: {e}")