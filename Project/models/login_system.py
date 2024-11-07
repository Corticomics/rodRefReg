# models/login_system.py

class LoginSystem:
    def __init__(self, database_handler):
        self.database_handler = database_handler
        self.current_trainer = None  # Set to None for guest mode

    def is_logged_in(self):
        """Check if a trainer is currently logged in."""
        return self.current_trainer is not None

    def set_guest_mode(self):
        """Set the system to 'Guest' mode."""
        self.current_trainer = None
        print("Running in Guest mode. Displaying all data.")


    def login(self, trainer_id):
        """Attempt to log in a trainer by their ID, with error handling."""
        try:
            print(f"Attempting to retrieve trainer by ID: {trainer_id}")  # Debug
            trainer = self.database_handler.get_trainer_by_id(trainer_id)
            if trainer:
                self.current_trainer = trainer
                print(f"Trainer '{trainer['username']}' logged in successfully.")
                return True
            else:
                print(f"Login failed: Invalid trainer data received. Data: {trainer}")
                return False
        except Exception as e:
            print(f"Error during login: {e}")
            return False

    def authenticate(self, username, password):
        """Authenticate a trainer by username and password, with error handling."""
        try:
            print(f"Authenticating username: {username}")  # Debug
            trainer_id = self.database_handler.authenticate_trainer(username, password)
            print(f"Authentication result for {username}: {trainer_id}")  # Debug

            if trainer_id:
                login_successful = self.login(trainer_id)
                if login_successful:
                    print(f"Authentication and login successful for trainer ID: {trainer_id}")
                    return self.current_trainer
                else:
                    print("Login failed after authentication.")
            else:
                print("Authentication failed: invalid username or password.")
            return None
        except Exception as e:
            print(f"Error during authentication: {e}")
            return None
        
    def logout(self):
        """Log out the current trainer and switch to 'Guest' mode."""
        try:
            self.current_trainer = None
            print("Trainer logged out. Switched to Guest mode.")
        except Exception as e:
            print(f"Error during logout: {e}")

    def get_current_trainer(self):
        """Return the current trainer or None if in Guest mode."""
        return self.current_trainer

    def create_user(self, username, password):
        """Create a new trainer profile, with error handling."""
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
            return False