# models/database_handler.py

from models.animal import Animal

import sqlite3
import hashlib
import os
import traceback

class DatabaseHandler:
    def __init__(self, db_path='rrr_database.db'):
        self.db_path = db_path
        self.create_tables()

    def connect(self):
        """Establish a new connection to the SQLite database."""
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        """Create necessary tables if they don't exist."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                # Create trainers table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trainers (
                        trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trainer_name TEXT UNIQUE NOT NULL,
                        salt TEXT NOT NULL,
                        password TEXT NOT NULL
                    )
                ''')

                # Create animals table with trainer reference
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS animals (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        lab_animal_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        initial_weight REAL,
                        last_weight REAL,
                        last_weighted TEXT,
                        trainer_id INTEGER,
                        FOREIGN KEY(trainer_id) REFERENCES trainers(trainer_id)
                    )
                ''')

                # Create schedules table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedules (
                        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        relay TEXT NOT NULL,
                        animals TEXT NOT NULL
                    )
                ''')
                conn.commit()
                print("Tables created or confirmed to exist.")
        except sqlite3.Error as e:
            print(f"Database error during table creation: {e}")
            traceback.print_exc()

    def authenticate_trainer(self, trainer_name, password):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT trainer_id, salt, password FROM trainers WHERE trainer_name = ?', (trainer_name,))
                result = cursor.fetchone()

                print(f"Retrieved data for {trainer_name}: {result}")

                if result:
                    trainer_id, salt, stored_hashed_password = result
                    hashed_password = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

                    if hashed_password == stored_hashed_password:
                        print("Authentication successful.")
                        return trainer_id
                    else:
                        print("Authentication failed: hashed password does not match.")
                        return None
                else:
                    print("Trainer not found in the database.")
                    return None
        except sqlite3.Error as e:
            print(f"Database error during authentication: {e}")
            traceback.print_exc()
            raise
        except Exception as e:
            print(f"Unexpected error during authentication: {e}")
            traceback.print_exc()
            raise

    def add_trainer(self, trainer_name, password):
        """Add a new trainer to the database with salted SHA-256 hashed password."""
        try:
            # Generate a unique salt
            salt = os.urandom(16).hex()
            # Hash the password with the salt
            hashed_password = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trainers (trainer_name, salt, password)
                    VALUES (?, ?, ?)
                ''', (trainer_name, salt, hashed_password))
                conn.commit()
                print(f"Trainer '{trainer_name}' added successfully with a hashed password.")
                return True
        except sqlite3.IntegrityError:
            print(f"Error: Trainer '{trainer_name}' already exists.")
            return False
        except sqlite3.Error as e:
            print(f"Database error when adding trainer '{trainer_name}': {e}")
            traceback.print_exc()
            return False

    def get_trainer_by_id(self, trainer_id):
        """Retrieve a trainer's information based on their trainer ID."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT trainer_id, trainer_name FROM trainers WHERE trainer_id = ?', (int(trainer_id),))
                row = cursor.fetchone()
                print(f"Data retrieved for trainer ID {trainer_id}: {row}")
                if row:
                    trainer_info = {
                        'trainer_id': row[0],
                        'username': row[1]
                    }
                    print(f"Trainer found: {trainer_info}")
                    return trainer_info
                else:
                    print(f"No trainer found with ID {trainer_id}")
                    return None
        except sqlite3.Error as e:
            print(f"Database error retrieving trainer by ID {trainer_id}: {e}")
            traceback.print_exc()
            raise
        except Exception as e:
            print(f"Unexpected error retrieving trainer by ID {trainer_id}: {e}")
            traceback.print_exc()
            raise

    def add_animal(self, animal, trainer_id):
        """Add a new animal with lab_animal_id and trainer association."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO animals (lab_animal_id, name, initial_weight, last_weight, last_weighted, trainer_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (animal.lab_animal_id, animal.name, animal.initial_weight, animal.last_weight, animal.last_weighted, trainer_id))
                conn.commit()
                print(f"Animal '{animal.name}' added with lab ID: {animal.lab_animal_id} for trainer ID: {trainer_id}")
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Error: Animal ID '{animal.lab_animal_id}' already exists.")
            return None
        except sqlite3.Error as e:
            print(f"Database error when adding animal: {e}")
            traceback.print_exc()
            return None

    def update_animal(self, animal):
        """Update an existing animal's information based on lab_animal_id."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE animals
                    SET lab_animal_id = ?, name = ?, initial_weight = ?, last_weight = ?, last_weighted = ?
                    WHERE ID = ?
                ''', (animal.lab_animal_id, animal.name, animal.initial_weight, animal.last_weight, animal.last_weighted, animal.animal_id))
                if cursor.rowcount > 0:
                    print(f"Animal with lab ID {animal.lab_animal_id} updated.")
                else:
                    print(f"No animal found with lab ID {animal.lab_animal_id} to update.")
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating animal with lab ID {animal.lab_animal_id}: {e}")
            traceback.print_exc()

    def remove_animal(self, lab_animal_id):
        """Remove an animal from the database based on its lab_animal_id."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM animals WHERE lab_animal_id = ?', (lab_animal_id,))
                if cursor.rowcount > 0:
                    print(f"Animal with lab ID {lab_animal_id} removed.")
                else:
                    print(f"No animal found with lab ID {lab_animal_id}.")
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error removing animal with lab ID {lab_animal_id}: {e}")
            traceback.print_exc()

    def get_all_animals(self):
        """Retrieve all animals in the database, regardless of trainer."""
        animals = []
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT ID, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals')
                rows = cursor.fetchall()
                for row in rows:
                    animal = Animal(
                        animal_id=row[0],
                        lab_animal_id=row[1],
                        name=row[2],
                        initial_weight=row[3],
                        last_weight=row[4],
                        last_weighted=row[5]
                    )
                    animals.append(animal)
                print(f"Retrieved {len(animals)} animals from the database.")
        except sqlite3.Error as e:
            print(f"Error retrieving all animals: {e}")
            traceback.print_exc()
        return animals

    def get_animals_by_trainer(self, trainer_id):
        """Retrieve animals belonging to a specific trainer."""
        animals = []
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT ID, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals WHERE trainer_id = ?',
                    (int(trainer_id),)
                )
                rows = cursor.fetchall()
                print(f"Retrieved {len(rows)} animals from the database for trainer_id {trainer_id}")
                for row in rows:
                    animal = Animal(
                        animal_id=row[0],
                        lab_animal_id=row[1],
                        name=row[2],
                        initial_weight=row[3],
                        last_weight=row[4],
                        last_weighted=row[5]
                    )
                    animals.append(animal)
        except sqlite3.Error as e:
            print(f"Error retrieving animals for trainer_id {trainer_id}: {e}")
            traceback.print_exc()
        except Exception as e:
            print(f"Unexpected error retrieving animals for trainer_id {trainer_id}: {e}")
            traceback.print_exc()
        return animals

    def close(self):
        """No longer needed since connections are managed per method."""
        pass  # Method retained for backward compatibility if needed