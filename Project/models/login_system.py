# models/login_system.py

import traceback

class LoginSystem:
    def __init__(self, database_handler):
        self.database_handler = database_handler
        self.current_trainer = None

    def authenticate(self, username, password):
        try:
            print(f"Authenticating username: {username}")
            trainer_id = self.database_handler.authenticate_trainer(username, password)
            print(f"Authentication result for {username}: {trainer_id}")

            if trainer_id:
                # Set current trainer as a dictionary with 'username' and 'trainer_id'
                self.current_trainer = {'username': username, 'trainer_id': trainer_id}
                
                login_successful = self.login(trainer_id)
                if login_successful:
                    print(f"Authentication and login successful for trainer ID: {trainer_id}")
                    return self.current_trainer  # Returning a dictionary as expected
                else:
                    print("Login failed after authentication.")
            else:
                print("Authentication failed: invalid username or password.")
            return None
        except Exception as e:
            print(f"Error during authentication: {e}")
            traceback.print_exc()
            return None

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

    def logout(self):
        """Log out the current trainer."""
        self.current_trainer = None
        print("Trainer logged out. Switched to Guest mode.")

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
    # Rest of the methods remain unchanged.
    def is_logged_in(self):
        """Check if a trainer is currently logged in."""
        return self.current_trainer is not None

    def set_guest_mode(self):
        """Set the system to 'Guest' mode."""
        self.current_trainer = None
        print("Running in Guest mode. Displaying all data.")


    