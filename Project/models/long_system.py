# models/login_system.py
from models.database_handler import DatabaseHandler

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
            print(f"Trainer '{trainer['name']}' logged in successfully.")
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