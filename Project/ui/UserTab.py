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

    def __init__(self, login_system, database_handler=None):
        super().__init__()
        self.login_system = login_system
        self.database_handler = database_handler
        self.current_user = None
        self.init_ui()

    def init_ui(self):
        # Main layout with modern spacing
        self.layout = QVBoxLayout()
        self.layout.setSpacing(24)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.setLayout(self.layout)

        # Info label with modern typography and subtle animation
        self.info_label = QLabel("You are running the application in Guest mode.")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setFont(QFont("Segoe UI", 14, QFont.Medium))
        self.info_label.setStyleSheet("""
            QLabel {
                color: #1a73e8;
                padding: 16px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f8f9fa, stop:1 #ffffff);
                border-radius: 12px;
            }
        """)
        self.layout.addWidget(self.info_label)

        # Login form container with card-like appearance
        self.login_container = QFrame()
        self.login_container.setFrameStyle(QFrame.NoFrame)
        self.login_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                padding: 24px;
                margin: 8px;
            }
            QFrame {
                border: 1px solid #e0e4e8;
                box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
            }
        """)

        # Grid layout for form elements
        form_layout = QGridLayout(self.login_container)
        form_layout.setSpacing(16)
        form_layout.setContentsMargins(24, 24, 24, 24)

        # Style input fields and labels
        self._setup_form_fields(form_layout)
        
        self.layout.addWidget(self.login_container)
        
        # Buttons with modern styling
        self._setup_buttons()
        self.layout.addStretch()

    def _setup_form_fields(self, form_layout):
        labels = ["Username:", "Password:"]
        inputs = [self.username_input, self.password_input]
        
        for i, (label_text, input_widget) in enumerate(zip(labels, inputs)):
            label = QLabel(label_text)
            label.setFont(QFont("Segoe UI", 11))
            label.setStyleSheet("color: #202124; margin-bottom: 4px;")
            
            input_widget.setPlaceholderText(f"Enter {label_text.lower().rstrip(':')}")
            input_widget.setStyleSheet(self._get_input_style())
            input_widget.setMinimumHeight(40)
            
            form_layout.addWidget(label, i, 0)
            form_layout.addWidget(input_widget, i, 1)

    def _get_input_style(self):
        return """
            QLineEdit {
                border: 2px solid #e0e4e8;
                border-radius: 8px;
                padding: 8px 16px;
                background: white;
                font-size: 11pt;
                font-family: 'Segoe UI';
                transition: all 0.3s;
            }
            QLineEdit:hover {
                border-color: #1a73e8;
                background: #f8f9fa;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
                background: white;
                box-shadow: 0 0 0 4px rgba(26, 115, 232, 0.1);
            }
        """

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
            ]
            
            # Only add active animals stat if database_handler exists
            if self.database_handler:
                active_animals = len(self.database_handler.get_animals(user_info['trainer_id']))
                stats.append(("Active Animals", str(active_animals)))
            
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