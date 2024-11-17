# models/login_system.py

import traceback

class LoginSystem:
    def __init__(self, database_handler):
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
            print("Switched to Normal Mode.")
        else:
            # Verify super user credentials (you might prompt for a password)
            # For simplicity, assuming they can switch directly
            self.current_trainer['role'] = 'super'
            print("Switched to Super Mode.")

    def set_guest_mode(self):
        """Set the system to 'Guest' mode."""
        self.current_trainer = None
        print("Running in Guest mode. Displaying all data.")


    