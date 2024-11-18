# models/database_handler.py

import sqlite3
import hashlib
import os
import traceback
import datetime
from models.animal import Animal
from models.Schedule import Schedule
from models.relay_unit import RelayUnit

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
                # Create trainers table with role column
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trainers (
                        trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trainer_name TEXT UNIQUE NOT NULL,
                        salt TEXT NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT DEFAULT 'normal'
                    )
                ''')

                # Create animals table with trainer reference
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS animals (
                        animal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lab_animal_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        initial_weight REAL,
                        last_weight REAL,
                        last_weighted TEXT,
                        trainer_id INTEGER,
                        FOREIGN KEY(trainer_id) REFERENCES trainers(trainer_id)
                    )
                ''')

                # Create relay units table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS relay_units (
                        relay_unit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        relay_ids TEXT NOT NULL
                    )
                ''')

                # Create schedules table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedules (
                        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        relay_unit_id INTEGER NOT NULL,
                        water_volume REAL NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        created_by INTEGER NOT NULL,
                        is_super_user BOOLEAN DEFAULT 0,
                        FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id),
                        FOREIGN KEY(created_by) REFERENCES trainers(trainer_id)
                    )
                ''')

                # Create schedule_animals table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedule_animals (
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        PRIMARY KEY (schedule_id, animal_id),
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    )
                ''')

                # Create logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS logs (
                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        action TEXT NOT NULL,
                        super_user_id INTEGER NOT NULL,
                        details TEXT,
                        FOREIGN KEY(super_user_id) REFERENCES trainers(trainer_id)
                    )
                ''')
                conn.commit()
                print("Tables created or confirmed to exist.")
        except sqlite3.Error as e:
            print(f"Database error during table creation: {e}")
            traceback.print_exc()

    # Add methods to handle relay units
    def add_relay_unit(self, relay_unit):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                relay_ids_str = ','.join(map(str, relay_unit.relay_ids))
                cursor.execute('''
                    INSERT INTO relay_units (relay_ids)
                    VALUES (?)
                ''', (relay_ids_str,))
                conn.commit()
                relay_unit.unit_id = cursor.lastrowid
                print(f"Relay Unit added with ID: {relay_unit.unit_id}")
                return relay_unit.unit_id
        except sqlite3.Error as e:
            print(f"Database error when adding relay unit: {e}")
            traceback.print_exc()
            return None

    def get_all_relay_units(self):
        relay_units = []
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT relay_unit_id, relay_ids FROM relay_units')
                rows = cursor.fetchall()
                for row in rows:
                    relay_ids = tuple(map(int, row[1].split(',')))
                    relay_unit = RelayUnit(unit_id=row[0], relay_ids=relay_ids)
                    relay_units.append(relay_unit)
            return relay_units
        except sqlite3.Error as e:
            print(f"Error retrieving relay units: {e}")
            traceback.print_exc()
            return []

    # Add methods to handle schedules
    def add_schedule(self, schedule):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO schedules (name, relay_unit_id, water_volume, start_time, end_time, created_by, is_super_user)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (schedule.name, schedule.relay_unit_id, schedule.water_volume, schedule.start_time,
                      schedule.end_time, schedule.created_by, schedule.is_super_user))
                schedule.schedule_id = cursor.lastrowid

                # Insert into schedule_animals
                for animal_id in schedule.animals:
                    cursor.execute('''
                        INSERT INTO schedule_animals (schedule_id, animal_id)
                        VALUES (?, ?)
                    ''', (schedule.schedule_id, animal_id))

                conn.commit()
                print(f"Schedule '{schedule.name}' added with ID: {schedule.schedule_id}")
                return schedule.schedule_id
        except sqlite3.Error as e:
            print(f"Database error when adding schedule: {e}")
            traceback.print_exc()
            return None

    def remove_schedule(self, schedule_id):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM schedules WHERE schedule_id = ?', (schedule_id,))
                cursor.execute('DELETE FROM schedule_animals WHERE schedule_id = ?', (schedule_id,))
                conn.commit()
                print(f"Schedule with ID {schedule_id} removed.")
        except sqlite3.Error as e:
            print(f"Database error when removing schedule: {e}")
            traceback.print_exc()

    def get_all_schedules(self):
        schedules = []
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT schedule_id, name, relay_unit_id, water_volume, start_time, end_time, created_by, is_super_user FROM schedules')
                rows = cursor.fetchall()
                for row in rows:
                    schedule = Schedule(
                        schedule_id=row[0],
                        name=row[1],
                        relay_unit_id=row[2],
                        water_volume=row[3],
                        start_time=row[4],
                        end_time=row[5],
                        created_by=row[6],
                        is_super_user=row[7]
                    )
                    # Retrieve associated animals
                    cursor.execute('SELECT animal_id FROM schedule_animals WHERE schedule_id = ?', (schedule.schedule_id,))
                    animal_rows = cursor.fetchall()
                    schedule.animals = [animal_id for (animal_id,) in animal_rows]
                    schedules.append(schedule)
            return schedules
        except sqlite3.Error as e:
            print(f"Error retrieving all schedules: {e}")
            traceback.print_exc()
            return []

    def get_schedules_by_trainer(self, trainer_id):
        schedules = []
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT schedule_id, name, relay_unit_id, water_volume, start_time, end_time, created_by, is_super_user FROM schedules WHERE created_by = ?', (trainer_id,))
                rows = cursor.fetchall()
                for row in rows:
                    schedule = Schedule(
                        schedule_id=row[0],
                        name=row[1],
                        relay_unit_id=row[2],
                        water_volume=row[3],
                        start_time=row[4],
                        end_time=row[5],
                        created_by=row[6],
                        is_super_user=row[7]
                    )
                    # Retrieve associated animals
                    cursor.execute('SELECT animal_id FROM schedule_animals WHERE schedule_id = ?', (schedule.schedule_id,))
                    animal_rows = cursor.fetchall()
                    schedule.animals = [animal_id for (animal_id,) in animal_rows]
                    schedules.append(schedule)
            return schedules
        except sqlite3.Error as e:
            print(f"Error retrieving schedules for trainer_id {trainer_id}: {e}")
            traceback.print_exc()
            return []

    # Modify existing methods to handle user roles
    def get_animals(self, trainer_id, role):
        if role == 'super':
            return self.get_all_animals()
        else:
            return self.get_animals_by_trainer(trainer_id)

    def authenticate_trainer(self, trainer_name, password):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT trainer_id, salt, password, role FROM trainers WHERE trainer_name = ?', (trainer_name,))
                result = cursor.fetchone()

                if result:
                    trainer_id, salt, stored_hashed_password, role = result
                    hashed_password = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

                    if hashed_password == stored_hashed_password:
                        print("Authentication successful.")
                        return {'trainer_id': trainer_id, 'role': role}
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

    # Ensure get_trainer_by_id returns the 'role'
    def get_trainer_by_id(self, trainer_id):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT trainer_id, trainer_name, role FROM trainers WHERE trainer_id = ?', (int(trainer_id),))
                row = cursor.fetchone()
                if row:
                    trainer_info = {
                        'trainer_id': row[0],
                        'username': row[1],
                        'role': row[2]
                    }
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
        """Update an existing animal's information based on animal_id."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE animals
                    SET lab_animal_id = ?, name = ?, initial_weight = ?, last_weight = ?, last_weighted = ?
                    WHERE animal_id = ?
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
                cursor.execute('SELECT animal_id, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals')
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
                    'SELECT animal_id, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals WHERE trainer_id = ?',
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

    # Method to log super user actions
    def log_action(self, super_user_id, action, details):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                timestamp = datetime.datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO logs (timestamp, action, super_user_id, details)
                    VALUES (?, ?, ?, ?)
                ''', (timestamp, action, super_user_id, details))
                conn.commit()
                print(f"Action '{action}' logged by super user ID {super_user_id}")
        except sqlite3.Error as e:
            print(f"Database error logging action: {e}")
            traceback.print_exc()
        except Exception as e:
            print(f"Unexpected error logging action: {e}")
            traceback.print_exc()

    def close(self):
        """No longer needed since connections are managed per method."""
        pass  # Method retained for backward compatibility if needed