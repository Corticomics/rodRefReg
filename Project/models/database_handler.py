# models/database_handler.py

import sqlite3
import hashlib
import os
import traceback
import datetime
from models.animal import Animal
from models.Schedule import Schedule
from models.relay_unit import RelayUnit
from datetime import datetime
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
                
                # First, check if dispensing_history exists and get its columns
                cursor.execute("PRAGMA table_info(dispensing_history)")
                existing_columns = {col[1] for col in cursor.fetchall()}
                
                # If table doesn't exist, create it
                if not existing_columns:
                    cursor.execute('''
                        CREATE TABLE dispensing_history (
                            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            schedule_id INTEGER NOT NULL,
                            animal_id INTEGER NOT NULL,
                            relay_unit_id INTEGER NOT NULL,
                            timestamp TEXT NOT NULL,
                            volume_dispensed REAL NOT NULL,
                            status TEXT NOT NULL,
                            cycle_index INTEGER DEFAULT NULL,
                            FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                            FOREIGN KEY(animal_id) REFERENCES animals(animal_id),
                            FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id)
                        )
                    ''')
                # If table exists but needs cycle_index column
                elif 'cycle_index' not in existing_columns:
                    cursor.execute('''
                        ALTER TABLE dispensing_history 
                        ADD COLUMN cycle_index INTEGER DEFAULT NULL
                    ''')
                
                # Create trainers table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trainers (
                        trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trainer_name TEXT UNIQUE NOT NULL,
                        salt TEXT NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT DEFAULT 'normal'
                    )
                ''')

                # Create animals table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS animals (
                        animal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lab_animal_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        initial_weight REAL,
                        last_weight REAL,
                        last_weighted TEXT,
                        last_watering TEXT,
                        last_water_volume REAL,
                        trainer_id INTEGER,
                        gender TEXT CHECK(gender IN ('male', 'female')) DEFAULT NULL,
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

                # Create schedules table with delivery_mode
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedules (
                        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        water_volume REAL NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        created_by INTEGER NOT NULL,
                        is_super_user BOOLEAN DEFAULT 0,
                        delivery_mode TEXT DEFAULT 'staggered',
                        dispensing_status TEXT DEFAULT 'pending',
                        FOREIGN KEY(created_by) REFERENCES trainers(trainer_id)
                    )
                ''')

                # Create schedule_animals table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedule_animals (
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        relay_unit_id INTEGER,
                        PRIMARY KEY (schedule_id, animal_id),
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id),
                        FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id)
                    )
                ''')

                # Create schedule_desired_outputs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedule_desired_outputs (
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        desired_output REAL NOT NULL,
                        interval_minutes INTEGER DEFAULT 60,
                        volume_per_interval REAL,
                        PRIMARY KEY (schedule_id, animal_id),
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    )
                ''')

                # Create schedule_instant_deliveries table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedule_instant_deliveries (
                        delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        delivery_datetime TEXT NOT NULL,
                        water_volume REAL NOT NULL,
                        relay_unit_id INTEGER,
                        completed BOOLEAN DEFAULT 0,
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id),
                        FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id)
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

                # Create schedule_staggered_windows table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schedule_staggered_windows (
                        window_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        target_volume REAL NOT NULL,
                        delivered_volume REAL DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    )
                ''')

                # Add cycle_tracking table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cycle_tracking (
                        tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        cycle_index INTEGER NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        target_volume REAL NOT NULL,
                        delivered_volume REAL DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        completed_at TEXT,
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    )
                ''')

                # Add system_settings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_settings (
                        setting_key TEXT PRIMARY KEY,
                        setting_value TEXT NOT NULL,
                        setting_type TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')

                # Add gender column to animals table if it doesn't exist
                cursor.execute("PRAGMA table_info(animals)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'gender' not in columns:
                    cursor.execute('''
                        ALTER TABLE animals
                        ADD COLUMN gender TEXT CHECK(gender IN ('male', 'female')) DEFAULT NULL
                    ''')

                conn.commit()
                print("Database schema created/updated successfully.")
                
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


    def add_schedule(self, schedule):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                # Insert main schedule without relay_unit_id
                cursor.execute('''
                    INSERT INTO schedules (
                        name, water_volume, start_time, end_time, 
                        created_by, is_super_user, delivery_mode
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    schedule.name, schedule.water_volume, 
                    schedule.start_time, schedule.end_time, schedule.created_by, 
                    schedule.is_super_user, schedule.delivery_mode
                ))
                schedule.schedule_id = cursor.lastrowid

                # Insert animal assignments with relay units
                for animal_id in schedule.animals:
                    relay_unit_id = schedule.relay_unit_assignments.get(str(animal_id))
                    cursor.execute('''
                        INSERT INTO schedule_animals 
                        (schedule_id, animal_id, relay_unit_id)
                        VALUES (?, ?, ?)
                    ''', (schedule.schedule_id, animal_id, relay_unit_id))

                if schedule.delivery_mode == 'instant':
                    for delivery in schedule.instant_deliveries:
                        cursor.execute('''
                            INSERT INTO schedule_instant_deliveries 
                            (schedule_id, animal_id, delivery_datetime, water_volume, relay_unit_id)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            schedule.schedule_id, delivery['animal_id'],
                            delivery['datetime'], delivery['volume'],
                            delivery['relay_unit_id']
                        ))

                conn.commit()
                return schedule.schedule_id
        except sqlite3.Error as e:
            print(f"Database error when adding schedule: {str(e)}")
            traceback.print_exc()
            return None

    def get_schedule_details(self, schedule_id):
        """Retrieve detailed information about a schedule."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                # Get main schedule data
                cursor.execute('''
                    SELECT name, water_volume, start_time, end_time, 
                           created_by, is_super_user, delivery_mode
                    FROM schedules 
                    WHERE schedule_id = ?
                ''', (schedule_id,))
                
                schedule_row = cursor.fetchone()
                if not schedule_row:
                    print(f"No schedule found with ID {schedule_id}")
                    return []

                result = {
                    'delivery_mode': schedule_row[6],  # delivery_mode
                    'water_volume': schedule_row[1],   # water_volume
                    'start_time': schedule_row[2],     # start_time
                    'end_time': schedule_row[3],       # end_time
                }

                # Get assigned animals with their relay units
                cursor.execute('''
                    SELECT sa.animal_id, sa.relay_unit_id 
                    FROM schedule_animals sa
                    WHERE sa.schedule_id = ?
                ''', (schedule_id,))
                
                animal_rows = cursor.fetchall()
                result['animal_ids'] = [row[0] for row in animal_rows]
                result['relay_unit_assignments'] = {str(row[0]): row[1] for row in animal_rows}
                
                if result['delivery_mode'] == 'instant':
                    cursor.execute('''
                        SELECT animal_id, delivery_datetime, water_volume, relay_unit_id
                        FROM schedule_instant_deliveries
                        WHERE schedule_id = ?
                        ORDER BY delivery_datetime
                    ''', (schedule_id,))
                    result['delivery_schedule'] = [
                        {
                            'animal_id': row[0],
                            'datetime': row[1],
                            'volume': row[2],
                            'relay_unit_id': row[3]
                        } for row in cursor.fetchall()
                    ]
                else:
                    cursor.execute('''
                        SELECT animal_id, desired_output 
                        FROM schedule_desired_outputs 
                        WHERE schedule_id = ?
                    ''', (schedule_id,))
                    result['desired_water_outputs'] = {
                        str(row[0]): row[1] for row in cursor.fetchall()
                    }

                return [result]
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            traceback.print_exc()
            return []

    def get_animal_by_id(self, animal_id):
        """Retrieve an animal by its ID."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT animal_id, lab_animal_id, name, initial_weight, last_weight, last_weighted, last_watering
                    FROM animals WHERE animal_id = ?
                ''', (animal_id,))
                row = cursor.fetchone()
                if row:
                    animal = Animal(
                        animal_id=row[0],
                        lab_animal_id=row[1],
                        name=row[2],
                        initial_weight=row[3],
                        last_weight=row[4],
                        last_weighted=row[5],
                        last_watering=row[6]  # Added last_watering
                    )
                    return animal
                else:
                    print(f"No animal found with ID {animal_id}")
                    return None
        except sqlite3.Error as e:
            print(f"Error retrieving animal with ID {animal_id}: {e}")
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
                cursor.execute('''
                    SELECT schedule_id, name, water_volume, 
                           start_time, end_time, created_by, is_super_user, 
                           delivery_mode
                    FROM schedules
                ''')
                rows = cursor.fetchall()
                for row in rows:
                    schedule = Schedule(
                        schedule_id=row[0],
                        name=row[1],
                        water_volume=row[2],
                        start_time=row[3],
                        end_time=row[4],
                        created_by=row[5],
                        is_super_user=row[6],
                        delivery_mode=row[7]
                    )
                    
                    # Get associated data based on delivery mode
                    if schedule.delivery_mode == 'instant':
                        cursor.execute('''
                            SELECT animal_id, delivery_datetime, water_volume, relay_unit_id
                            FROM schedule_instant_deliveries 
                            WHERE schedule_id = ?
                        ''', (schedule.schedule_id,))
                        schedule.instant_deliveries = [
                            {
                                'animal_id': row[0],
                                'datetime': row[1],
                                'volume': row[2],
                                'relay_unit_id': row[3]
                            } for row in cursor.fetchall()
                        ]
                    else:
                        # Get animals and desired outputs for staggered mode
                        cursor.execute('''
                            SELECT animal_id, relay_unit_id FROM schedule_animals 
                            WHERE schedule_id = ?
                        ''', (schedule.schedule_id,))
                        for animal_id, relay_unit_id in cursor.fetchall():
                            schedule.animals.append(animal_id)
                            schedule.relay_unit_assignments[str(animal_id)] = relay_unit_id
                        
                        cursor.execute('''
                            SELECT animal_id, desired_output 
                            FROM schedule_desired_outputs 
                            WHERE schedule_id = ?
                        ''', (schedule.schedule_id,))
                        schedule.desired_water_outputs = {
                            str(row[0]): row[1] for row in cursor.fetchall()
                        }
                    
                    schedules.append(schedule)
                return schedules
        except sqlite3.Error as e:
            print(f"Error retrieving all schedules: {e}")
            traceback.print_exc()
            return []

    def get_schedules_by_trainer(self, trainer_id):
        """Get all schedules created by a specific trainer."""
        schedules = []
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT schedule_id, name, water_volume, start_time, end_time, 
                           created_by, is_super_user, delivery_mode
                    FROM schedules 
                    WHERE created_by = ?
                ''', (trainer_id,))
                rows = cursor.fetchall()
                for row in rows:
                    schedule = Schedule(
                        schedule_id=row[0],
                        name=row[1],
                        water_volume=row[2],
                        start_time=row[3],
                        end_time=row[4],
                        created_by=row[5],
                        is_super_user=row[6],
                        delivery_mode=row[7]
                    )
                    
                    # Get associated data based on delivery mode
                    if schedule.delivery_mode == 'instant':
                        cursor.execute('''
                            SELECT animal_id, delivery_datetime, water_volume, relay_unit_id
                            FROM schedule_instant_deliveries 
                            WHERE schedule_id = ?
                        ''', (schedule.schedule_id,))
                        schedule.instant_deliveries = [
                            {
                                'animal_id': row[0],
                                'datetime': row[1],
                                'volume': row[2],
                                'relay_unit_id': row[3]
                            } for row in cursor.fetchall()
                        ]
                    else:
                        # Get animals and relay unit assignments for staggered mode
                        cursor.execute('''
                            SELECT animal_id, relay_unit_id FROM schedule_animals 
                            WHERE schedule_id = ?
                        ''', (schedule.schedule_id,))
                        for animal_id, relay_unit_id in cursor.fetchall():
                            schedule.animals.append(animal_id)
                            schedule.relay_unit_assignments[str(animal_id)] = relay_unit_id
                        
                        cursor.execute('''
                            SELECT animal_id, desired_output 
                            FROM schedule_desired_outputs 
                            WHERE schedule_id = ?
                        ''', (schedule.schedule_id,))
                        schedule.desired_water_outputs = {
                            str(row[0]): row[1] for row in cursor.fetchall()
                        }
                    
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
        """Add a new animal with lab_animal_id, gender, and trainer association."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO animals (
                        lab_animal_id, name, initial_weight, last_weight, 
                        last_weighted, last_watering, trainer_id, gender
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    animal.lab_animal_id, animal.name, animal.initial_weight, 
                    animal.last_weight, animal.last_weighted, animal.last_watering, 
                    trainer_id, animal.gender
                ))
                conn.commit()
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
                    SET lab_animal_id = ?, name = ?, initial_weight = ?, 
                        last_weight = ?, last_weighted = ?, last_watering = ?,
                        gender = ?
                    WHERE animal_id = ?
                ''', (
                    animal.lab_animal_id, animal.name, animal.initial_weight,
                    animal.last_weight, animal.last_weighted, animal.last_watering,
                    animal.gender, animal.animal_id
                ))
                conn.commit()
                if cursor.rowcount > 0:
                    print(f"Animal with lab ID {animal.lab_animal_id} updated.")
                else:
                    print(f"No animal found with lab ID {animal.lab_animal_id} to update.")
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
                cursor.execute('''
                    SELECT animal_id, lab_animal_id, name, initial_weight, 
                           last_weight, last_weighted, last_watering, gender 
                    FROM animals
                ''')
                rows = cursor.fetchall()
                for row in rows:
                    animal = Animal(
                        animal_id=row[0],
                        lab_animal_id=row[1],
                        name=row[2],
                        initial_weight=row[3],
                        last_weight=row[4],
                        last_weighted=row[5],
                        last_watering=row[6],
                        gender=row[7]
                    )
                    animals.append(animal)
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
                    '''SELECT animal_id, lab_animal_id, name, initial_weight, 
                              last_weight, last_weighted, last_watering, gender 
                       FROM animals 
                       WHERE trainer_id = ?''',
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
                        last_weighted=row[5],
                        last_watering=row[6],
                        gender=row[7]
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

    def update_schedule_status(self, schedule_id, status, dispensed_volumes=None):
        """Update schedule status and record dispensed volumes"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE schedules SET status = ? WHERE schedule_id = ?",
                    (status, schedule_id)
                )
                
                if dispensed_volumes:
                    # Log the volumes in the logs table
                    details = f"Dispensed volumes: {str(dispensed_volumes)}"
                    cursor.execute('''
                        INSERT INTO logs (timestamp, action, super_user_id, details)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        'schedule_paused',
                        0,  # System action
                        details
                    ))
                conn.commit()
                
        except sqlite3.Error as e:
            print(f"Database error updating schedule status: {e}")
            raise

    def get_active_schedules(self):
        """Get all active schedules that need processing."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.*, sdo.interval_minutes, sdo.volume_per_interval, sdo.animal_id
                    FROM schedules s
                    JOIN schedule_desired_outputs sdo ON s.schedule_id = sdo.schedule_id
                    WHERE s.dispensing_status = 'active'
                    AND datetime(s.start_time) <= datetime('now')
                    AND datetime(s.end_time) >= datetime('now')
                ''')
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error retrieving active schedules: {e}")
            traceback.print_exc()
            return []

    async def update_animal_watering(self, animal_id, volume, timestamp):
        """Update animal's last watering record"""
        query = """
            UPDATE animals 
            SET last_watering = ?, last_water_volume = ?
            WHERE animal_id = ?
        """
        await self.execute(query, (timestamp, volume, animal_id))

    def add_schedule_instant(self, schedule_id, animal_id, delivery_time, water_volume):
        """Add a new schedule time instant"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO schedule_time_instants 
                    (schedule_id, animal_id, delivery_time, water_volume)
                    VALUES (?, ?, ?, ?)
                ''', (schedule_id, animal_id, delivery_time.isoformat(), water_volume))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            traceback.print_exc()
            return None

    def get_pending_schedule_instants(self, schedule_id=None):
        """Get all pending water delivery instants"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                if schedule_id:
                    query = '''
                        SELECT sti.*, ru.relay_unit_id 
                        FROM schedule_time_instants sti
                        JOIN schedules s ON sti.schedule_id = s.schedule_id
                        JOIN relay_units ru ON s.relay_unit_id = ru.relay_unit_id
                        WHERE sti.schedule_id = ? AND sti.completed = 0
                        ORDER BY sti.delivery_time ASC
                    '''
                    cursor.execute(query, (schedule_id,))
                else:
                    query = '''
                        SELECT sti.*, ru.relay_unit_id 
                        FROM schedule_time_instants sti
                        JOIN schedules s ON sti.schedule_id = s.schedule_id
                        JOIN relay_units ru ON s.relay_unit_id = ru.relay_unit_id
                        WHERE sti.completed = 0
                        ORDER BY sti.delivery_time ASC
                    '''
                    cursor.execute(query)
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            traceback.print_exc()
            return []

    def mark_instant_completed(self, instant_id, volume_dispensed):
        """Mark a schedule instant as completed and log the dispensing"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                # Get instant details
                cursor.execute('''
                    SELECT sti.schedule_id, sti.animal_id, s.relay_unit_id
                    FROM schedule_time_instants sti
                    JOIN schedules s ON sti.schedule_id = s.schedule_id
                    WHERE sti.instant_id = ?
                ''', (instant_id,))
                schedule_id, animal_id, relay_unit_id = cursor.fetchone()
                
                # Mark instant completed
                cursor.execute('''
                    UPDATE schedule_time_instants
                    SET completed = 1
                    WHERE instant_id = ?
                ''', (instant_id,))
                
                # Log in dispensing_history
                cursor.execute('''
                    INSERT INTO dispensing_history 
                    (schedule_id, animal_id, relay_unit_id, timestamp, volume_dispensed, status)
                    VALUES (?, ?, ?, datetime('now'), ?, 'completed')
                ''', (schedule_id, animal_id, relay_unit_id, volume_dispensed))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            traceback.print_exc()
            return False

    def add_instant_schedule(self, schedule_name, created_by, is_super_user, deliveries):
        """Add a new instant delivery schedule"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                # Insert main schedule without relay_unit_id
                cursor.execute('''
                    INSERT INTO schedules 
                    (name, delivery_mode, created_by, is_super_user)
                    VALUES (?, 'instant', ?, ?)
                ''', (schedule_name, created_by, is_super_user))
                schedule_id = cursor.lastrowid
                
                # Insert delivery times with relay_unit_id
                for delivery in deliveries:
                    cursor.execute('''
                        INSERT INTO schedule_instant_deliveries 
                        (schedule_id, animal_id, delivery_datetime, water_volume, relay_unit_id)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (schedule_id, delivery['animal_id'], 
                         delivery['datetime'].isoformat(), 
                         delivery['volume'],
                         delivery['relay_unit_id']))
                
                conn.commit()
                return schedule_id
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            traceback.print_exc()
            return None

    def get_schedule_instant_deliveries(self, schedule_id):
        """Get all instant deliveries for a schedule with animal details"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT sid.animal_id, a.lab_animal_id, a.name, 
                           sid.delivery_datetime, sid.water_volume, sid.completed,
                           sid.relay_unit_id
                    FROM schedule_instant_deliveries sid
                    JOIN animals a ON sid.animal_id = a.animal_id
                    WHERE sid.schedule_id = ?
                    ORDER BY sid.delivery_datetime
                ''', (schedule_id,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            traceback.print_exc()
            return []

    def add_staggered_schedule(self, schedule):
        """Add a new staggered delivery schedule"""
        try:
            print(f"Adding staggered schedule: {schedule.name}")
            print(f"Animals: {schedule.animals}")
            print(f"Relay assignments: {schedule.relay_unit_assignments}")
            print(f"Water outputs: {schedule.desired_water_outputs}")
            
            with self.connect() as conn:
                cursor = conn.cursor()
                # Insert main schedule
                cursor.execute('''
                    INSERT INTO schedules (
                        name, water_volume, start_time, end_time, 
                        created_by, is_super_user, delivery_mode
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'staggered')
                ''', (
                    schedule.name, schedule.water_volume,
                    schedule.start_time, schedule.end_time,
                    schedule.created_by, schedule.is_super_user
                ))
                schedule_id = cursor.lastrowid
                
                # Insert animal assignments and windows
                for animal_id in schedule.animals:
                    # Add animal assignment
                    relay_unit_id = schedule.relay_unit_assignments.get(str(animal_id))
                    cursor.execute('''
                        INSERT INTO schedule_animals 
                        (schedule_id, animal_id, relay_unit_id)
                        VALUES (?, ?, ?)
                    ''', (schedule_id, animal_id, relay_unit_id))
                    
                    # Add desired output
                    desired_output = schedule.desired_water_outputs.get(str(animal_id), schedule.water_volume)
                    cursor.execute('''
                        INSERT INTO schedule_desired_outputs 
                        (schedule_id, animal_id, desired_output)
                        VALUES (?, ?, ?)
                    ''', (schedule_id, animal_id, desired_output))
                    
                    # Parse datetime strings using strptime
                    start_time = datetime.strptime(schedule.start_time, "%Y-%m-%dT%H:%M:%S.%f")
                    end_time = datetime.strptime(schedule.end_time, "%Y-%m-%dT%H:%M:%S.%f")
                    
                    cursor.execute('''
                        INSERT INTO schedule_staggered_windows
                        (schedule_id, animal_id, start_time, end_time, target_volume)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        schedule_id, animal_id,
                        start_time.isoformat(),
                        end_time.isoformat(),
                        desired_output
                    ))
                
                conn.commit()
                return schedule_id
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            traceback.print_exc()
            return None
        except ValueError as e:
            print(f"DateTime parsing error: {e}")
            traceback.print_exc()
            return None

    def get_active_staggered_windows(self):
        """Get all active staggered delivery windows"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        w.window_id, w.schedule_id, w.animal_id,
                        w.start_time, w.end_time, w.target_volume,
                        w.delivered_volume, sa.relay_unit_id
                    FROM schedule_staggered_windows w
                    JOIN schedule_animals sa 
                        ON w.schedule_id = sa.schedule_id 
                        AND w.animal_id = sa.animal_id
                    WHERE w.status = 'pending'
                        AND datetime(w.start_time) <= datetime('now')
                        AND datetime(w.end_time) >= datetime('now')
                    ORDER BY w.start_time ASC
                ''')
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            traceback.print_exc()
            return []

    def create_staggered_delivery_window(self, schedule_id, animal_id, start_time, end_time, target_volume):
        """Create a new staggered delivery window"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO schedule_staggered_windows
                    (schedule_id, animal_id, start_time, end_time, target_volume, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                ''', (
                    schedule_id,
                    animal_id,
                    start_time.isoformat(),
                    end_time.isoformat(),
                    target_volume
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error creating staggered window: {e}")
            return None

    def update_staggered_window_progress(self, window_id, delivered_volume, status=None):
        """Update the progress of a staggered delivery window"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                if status:
                    cursor.execute('''
                        UPDATE schedule_staggered_windows
                        SET delivered_volume = delivered_volume + ?,
                            status = ?
                        WHERE window_id = ?
                    ''', (delivered_volume, status, window_id))
                else:
                    cursor.execute('''
                        UPDATE schedule_staggered_windows
                        SET delivered_volume = delivered_volume + ?
                        WHERE window_id = ?
                    ''', (delivered_volume, window_id))
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error updating staggered window: {e}")
            return False

    def get_staggered_window_status(self, window_id):
        """Get the current status of a staggered delivery window"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        w.*,
                        s.water_volume as base_volume,
                        sa.relay_unit_id,
                        COALESCE(
                            (SELECT SUM(volume_dispensed) 
                             FROM dispensing_history 
                             WHERE schedule_id = w.schedule_id 
                             AND animal_id = w.animal_id
                             AND timestamp BETWEEN w.start_time AND w.end_time),
                            0
                        ) as actual_delivered
                    FROM schedule_staggered_windows w
                    JOIN schedules s ON w.schedule_id = s.schedule_id
                    JOIN schedule_animals sa 
                        ON w.schedule_id = sa.schedule_id 
                        AND w.animal_id = sa.animal_id
                    WHERE w.window_id = ?
                ''', (window_id,))
                return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Error getting staggered window status: {e}")
            return None

    def log_staggered_delivery(self, schedule_id, animal_id, relay_unit_id, volume, status='completed'):
        """Log a staggered delivery attempt"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().isoformat()
                
                # Log in dispensing history
                cursor.execute('''
                    INSERT INTO dispensing_history 
                    (schedule_id, animal_id, relay_unit_id, timestamp, volume_dispensed, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (schedule_id, animal_id, relay_unit_id, timestamp, volume, status))
                
                # Update animal's last watering
                cursor.execute('''
                    UPDATE animals
                    SET last_watering = ?,
                        last_water_volume = ?
                    WHERE animal_id = ?
                ''', (timestamp, volume, animal_id))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error logging staggered delivery: {e}")
            return False

    def get_schedule_progress(self, schedule_id):
        """Get detailed progress for a schedule"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        s.schedule_id,
                        s.delivery_mode,
                        s.water_volume as base_volume,
                        a.animal_id,
                        a.name as animal_name,
                        COALESCE(sdo.desired_output, s.water_volume) as target_volume,
                        COALESCE(
                            (SELECT SUM(volume_dispensed) 
                             FROM dispensing_history 
                             WHERE schedule_id = s.schedule_id 
                             AND animal_id = a.animal_id
                             AND status = 'completed'),
                            0
                        ) as total_delivered,
                        sa.relay_unit_id
                    FROM schedules s
                    JOIN schedule_animals sa ON s.schedule_id = sa.schedule_id
                    JOIN animals a ON sa.animal_id = a.animal_id
                    LEFT JOIN schedule_desired_outputs sdo 
                        ON s.schedule_id = sdo.schedule_id 
                        AND a.animal_id = sdo.animal_id
                    WHERE s.schedule_id = ?
                ''', (schedule_id,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error getting schedule progress: {e}")
            return None

    def track_cycle_progress(self, schedule_id, animal_id, cycle_data):
        """Track cycle progress in database"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO cycle_tracking (
                        schedule_id, animal_id, cycle_index,
                        start_time, end_time, target_volume
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    schedule_id,
                    animal_id,
                    cycle_data['cycle_index'],
                    cycle_data['start_time'].isoformat(),
                    cycle_data['end_time'].isoformat(),
                    cycle_data['target_volume']
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error tracking cycle progress: {e}")
            return None

    def update_cycle_progress(self, schedule_id, animal_id, cycle_index, delivered_volume):
        """Update cycle progress"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE cycle_tracking
                    SET delivered_volume = delivered_volume + ?,
                        status = CASE 
                            WHEN delivered_volume + ? >= target_volume THEN 'completed'
                            ELSE status
                        END,
                        completed_at = CASE 
                            WHEN delivered_volume + ? >= target_volume THEN datetime('now')
                            ELSE completed_at
                        END
                    WHERE schedule_id = ? 
                    AND animal_id = ? 
                    AND cycle_index = ?
                ''', (
                    delivered_volume, delivered_volume, delivered_volume,
                    schedule_id, animal_id, cycle_index
                ))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating cycle progress: {e}")

    def get_schedule_staggered_windows(self, schedule_id):
        """Get staggered delivery windows for a schedule"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        w.window_id,
                        w.animal_id,
                        w.start_time,
                        w.end_time,
                        w.target_volume,
                        w.delivered_volume,
                        w.status,
                        sa.relay_unit_id
                    FROM schedule_staggered_windows w
                    JOIN schedule_animals sa 
                        ON w.schedule_id = sa.schedule_id 
                        AND w.animal_id = sa.animal_id
                    WHERE w.schedule_id = ?
                    ORDER BY w.start_time ASC
                ''', (schedule_id,))
                
                windows = []
                for row in cursor.fetchall():
                    window = {
                        'window_id': row[0],
                        'animal_id': row[1],
                        'start_time': row[2],
                        'end_time': row[3],
                        'target_volume': row[4],
                        'delivered_volume': row[5],
                        'status': row[6],
                        'relay_unit_id': row[7]
                    }
                    windows.append(window)
                return windows
                
        except sqlite3.Error as e:
            print(f"Error getting staggered windows: {e}")
            traceback.print_exc()
            return []
    def log_delivery(self, delivery_data):
        """
        Log a water delivery attempt in the dispensing_history table.
        
        Args:
            delivery_data (dict): Dictionary containing:
                - schedule_id: ID of the schedule
                - animal_id: ID of the animal
                - relay_unit_id: ID of the relay unit used
                - volume_delivered: Amount of water delivered
                - timestamp: Time of delivery
                - status: Status of delivery ('completed' or 'failed')
        """
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO dispensing_history 
                    (schedule_id, animal_id, relay_unit_id, timestamp, 
                     volume_dispensed, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    delivery_data['schedule_id'],
                    delivery_data['animal_id'],
                    delivery_data['relay_unit_id'],
                    delivery_data['timestamp'],
                    delivery_data['volume_delivered'],
                    delivery_data['status']
                ))
                
                # If delivery was successful, update animal's last watering info
                if delivery_data['status'] == 'completed' and delivery_data['volume_delivered'] > 0:
                    cursor.execute('''
                        UPDATE animals
                        SET last_watering = ?,
                            last_water_volume = ?
                        WHERE animal_id = ?
                    ''', (
                        delivery_data['timestamp'],
                        delivery_data['volume_delivered'],
                        delivery_data['animal_id']
                    ))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            print(f"Error logging delivery: {e}")
            traceback.print_exc()
            return False

    def get_system_settings(self):
        """Retrieve all system settings from database with proper type conversion"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT setting_key, setting_value, setting_type FROM system_settings')
                settings = {}
                for row in cursor.fetchall():
                    key, value, type_name = row
                    # Convert value based on type
                    if type_name == 'int':
                        settings[key] = int(float(value))  # Handle potential float strings
                    elif type_name == 'float':
                        settings[key] = float(value)
                    elif type_name == 'bool':
                        settings[key] = value.lower() == 'true'
                    else:
                        settings[key] = value
                return settings
        except sqlite3.Error as e:
            print(f"Error retrieving system settings: {e}")
            return {}

    def update_system_setting(self, key, value, setting_type):
        """Update or insert a system setting"""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO system_settings 
                    (setting_key, setting_value, setting_type, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (key, str(value), setting_type))
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error updating system setting: {e}")
            return False
