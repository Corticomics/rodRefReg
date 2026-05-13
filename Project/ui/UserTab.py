# ui/user_tab.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, 
    QMessageBox, QFrame, QGridLayout, QSizePolicy, QInputDialog, QFormLayout, QHBoxLayout, QDialog, QDialogButtonBox
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
        # Main layout
        self.layout = QVBoxLayout()
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.layout)

        # Info label
        self.info_label = QLabel("You are running the application in Guest mode.")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("InfoBanner")
        self.layout.addWidget(self.info_label)

        # Login form container - use Card component
        from ui.components.card import Card
        self.login_container = Card()

        # Form layout for login inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(16, 16, 16, 16)

        # Create input fields - rely on QSS styling
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)

        # Add fields to form layout
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        
        # Set form layout to login container
        self.login_container.setLayout(form_layout)
        self.layout.addWidget(self.login_container)

        # Setup buttons
        self._setup_buttons()
        self.layout.addStretch()


    def _setup_buttons(self):
        # Create buttons container
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        # Create buttons - use property-based styling
        self.login_button = QPushButton("Log In")
        self.login_button.setProperty("variant", "primary")
        
        self.create_profile_button = QPushButton("Create New Profile")
        
        self.logout_button = QPushButton("Log Out")
        self.logout_button.setProperty("variant", "danger")
        
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
            self.login_button.hide()
            self.create_profile_button.hide()
            
            # Create profile container using Card
            from ui.components.card import Card
            self.profile_container = Card()
            profile_layout = QVBoxLayout(self.profile_container)
            profile_layout.setSpacing(16)
            profile_layout.setContentsMargins(20, 20, 20, 20)
            
            # Welcome message
            welcome_label = QLabel(f"Welcome, {user_info['username']}")
            welcome_label.setObjectName("ProfileWelcome")
            welcome_label.setAlignment(Qt.AlignCenter)
            profile_layout.addWidget(welcome_label)
            
            # Stats container - use a simple QFrame styled by QSS
            from PyQt5.QtWidgets import QGroupBox
            stats_container = QGroupBox("Profile Information")
            stats_layout = QGridLayout(stats_container)
            stats_layout.setSpacing(12)
            stats_layout.setContentsMargins(12, 12, 12, 12)
            
            # Simplified stats
            stats = [
                ("Trainer ID", str(user_info.get('trainer_id', 'N/A'))),
                ("Last Login", QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm"))
            ]
            
            for i, (label, value) in enumerate(stats):
                stat_label = QLabel(label + ":")
                stat_label.setProperty("variant", "label")
                stat_value = QLabel(value)
                stats_layout.addWidget(stat_label, i, 0)
                stats_layout.addWidget(stat_value, i, 1)
            
            profile_layout.addWidget(stats_container)
            
            # Logout button
            self.logout_button = QPushButton("Log Out")
            self.logout_button.setProperty("variant", "danger")
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
        """Handle the profile creation process with improved form."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Profile")
        dialog.setMinimumWidth(350)
        
        # Create layout
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Username field
        username_input = QLineEdit()
        username_input.setPlaceholderText("Choose a username")
        
        # Password fields container
        password_container = QVBoxLayout()
        password_container.setSpacing(4)
        
        # Password input with show/hide link
        password_input = QLineEdit()
        password_input.setPlaceholderText("Choose a password")
        password_input.setEchoMode(QLineEdit.Password)
        
        confirm_password_input = QLineEdit()
        confirm_password_input.setPlaceholderText("Confirm password")
        confirm_password_input.setEchoMode(QLineEdit.Password)
        
        # Show password link
        show_password_label = QLabel("Show password")
        show_password_label.setObjectName("LinkLabel")
        show_password_label.setCursor(Qt.PointingHandCursor)
        
        def toggle_password_visibility(event):
            current_mode = password_input.echoMode()
            new_mode = QLineEdit.Normal if current_mode == QLineEdit.Password else QLineEdit.Password
            password_input.setEchoMode(new_mode)
            confirm_password_input.setEchoMode(new_mode)
            show_password_label.setText("Hide password" if new_mode == QLineEdit.Normal else "Show password")
        
        show_password_label.mousePressEvent = toggle_password_visibility
        
        # Add fields to layouts
        form_layout.addRow("Username:", username_input)
        form_layout.addRow("Password:", password_input)
        form_layout.addRow("Confirm Password:", confirm_password_input)
        form_layout.addRow("", show_password_label)
        
        layout.addLayout(form_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.button(QDialogButtonBox.Ok).setText("Create Profile")
        button_box.button(QDialogButtonBox.Ok).setProperty("variant", "primary")
        
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            try:
                username = username_input.text().strip()
                password = password_input.text()
                confirm_password = confirm_password_input.text()
                
                # Validate inputs
                if not username:
                    raise ValueError("Username cannot be empty.")
                if not password:
                    raise ValueError("Password cannot be empty.")
                if password != confirm_password:
                    raise ValueError("Passwords do not match.")
                
                success = self.login_system.create_user(username, password)
                if success:
                    QMessageBox.information(
                        self, "Profile Created", 
                        f"Profile for '{username}' created successfully."
                    )
                else:
                    QMessageBox.warning(
                        self, "Creation Failed", 
                        f"Username '{username}' is already taken."
                    )
            except ValueError as ve:
                QMessageBox.warning(self, "Invalid Input", str(ve))
            except Exception as e:
                QMessageBox.critical(
                    self, "Profile Creation Error", 
                    f"An unexpected error occurred: {str(e)}"
                )

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
