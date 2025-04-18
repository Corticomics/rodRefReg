# models/login_system.py

import traceback
from PyQt5.QtCore import QObject, pyqtSignal

class LoginSystem(QObject):
    login_status_changed = pyqtSignal()  # Signal for login status changes
    
    def __init__(self, database_handler):
        super().__init__()
        self.database_handler = database_handler
        self.current_trainer = None

    def authenticate(self, username, password):
        try:
            result = self.database_handler.authenticate_trainer(username, password)

            if result:
                self.current_trainer = {
                    'username': username,
                    'trainer_id': result['trainer_id'],
                    'role': result['role']
                }
                self.login_status_changed.emit()  # Emit signal
                return self.current_trainer
            else:
                print("Authentication failed: invalid username or password.")
                return None
        except Exception as e:
            print(f"Error during authentication: {e}")
            traceback.print_exc()
            return None

    def logout(self):
        """Log out the current trainer."""
        self.current_trainer = None
        self.login_status_changed.emit()  # Emit signal
        print("Trainer logged out. Switched to Guest mode.")

    def get_current_trainer(self):
        """Return the current trainer or None if not logged in."""
        return self.current_trainer

    def is_logged_in(self):
        """Check if a trainer is currently logged in."""
        return self.current_trainer is not None

    def switch_mode(self):
        """Toggle between normal and super modes."""
        if self.current_trainer and self.current_trainer['role'] == 'super':
            self.current_trainer['role'] = 'normal'
        else:
            # Verify super user credentials (you might prompt for a password)
            # For simplicity, assuming they can switch directly
            self.current_trainer['role'] = 'super'

    def set_guest_mode(self):
        """Set the system to 'Guest' mode."""
        self.current_trainer = None
        print("Running in Guest mode. Displaying all data.")

    def login(self, trainer_id):
        """Attempt to log in a trainer by their ID."""
        try:
            trainer = self.database_handler.get_trainer_by_id(trainer_id)
            if trainer:
                self.current_trainer = trainer
                return True
            else:
                print(f"Login failed: No trainer found with ID {trainer_id}")
                return False
        except Exception as e:
            print(f"Error during login: {e}")
            traceback.print_exc()
            return False

    def get_current_trainer(self):
        """Return the current trainer or None if not logged in."""
        return self.current_trainer

    def create_user(self, username, password):
        """Create a new trainer profile."""
        try:
            success = self.database_handler.add_trainer(username, password)
            if success:
                print(f"Trainer '{username}' created successfully.")
                return True
            else:
                print(f"Failed to create trainer '{username}'. Username may already exist.")
                return False
        except Exception as e:
            print(f"Error during user creation: {e}")
            traceback.print_exc()
            return False



    