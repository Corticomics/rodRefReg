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
        """Attempt to log in a trainer by their ID."""
        trainer = self.database_handler.get_trainer_by_id(trainer_id)
        if trainer:
            self.current_trainer = trainer
            print(f"Trainer '{trainer['username']}' logged in successfully.")
            return True
        else:
            print("Invalid trainer ID.")
            return False

    def logout(self):
        """Log out the current trainer and switch to 'Guest' mode."""
        self.current_trainer = None
        print("Trainer logged out. Switched to Guest mode.")

    def get_current_trainer(self):
        """Return the current trainer or None if in Guest mode."""
        return self.current_trainer

    def authenticate(self, username, password):
        """Authenticate a trainer by username and password."""
        trainer_id = self.database_handler.authenticate_trainer(username, password)
        if trainer_id:
            self.login(trainer_id)
            return self.current_trainer
        return None

    def create_user(self, username, password):
        """Create a new trainer profile."""
        success = self.database_handler.add_trainer(username, password)
        if success:
            print(f"Trainer '{username}' created successfully.")
            return True
        else:
            print(f"Failed to create trainer '{username}'. Username may already exist.")
            return False