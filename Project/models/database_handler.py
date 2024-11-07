# models/database_handler.py

import sqlite3
from models.animal import Animal

class DatabaseHandler:
    def __init__(self, db_path='rrr_database.db'):
        self.db_path = db_path
        self.connection = None
        self.create_tables()

    def connect(self):
        """Establish a connection to the SQLite database."""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path)
        return self.connection

    def create_tables(self):
        """Create necessary tables if they don't exist."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            # Create trainers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trainers (
                    trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trainer_name TEXT UNIQUE NOT NULL,
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

    def authenticate_trainer(self, trainer_name, password):
        """Authenticate a trainer by username and password."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT trainer_id FROM trainers WHERE trainer_name = ? AND password = ?', (trainer_name, password))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error authenticating trainer: {e}")
            return None

    def add_animal(self, animal, trainer_id):
        """Add a new animal with lab_animal_id and trainer association."""
        try:
            conn = self.connect()
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
            return None

    def get_animals_by_trainer(self, trainer_id):
        """Retrieve animals belonging to a specific trainer."""
        animals = []
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT ID, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals WHERE trainer_id = ?', (trainer_id,))
            rows = cursor.fetchall()
            for row in rows:
                animal = Animal(
                    id=row[0],
                    lab_animal_id=row[1],
                    name=row[2],
                    initial_weight=row[3],
                    last_weight=row[4],
                    last_weighted=row[5]
                )
                animals.append(animal)
            print(f"Retrieved {len(animals)} animals for trainer ID {trainer_id}.")
        except sqlite3.Error as e:
            print(f"Error retrieving animals: {e}")
        return animals

    def get_all_animals(self):
        """Retrieve all animals in the database, regardless of trainer."""
        animals = []
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT ID, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals')
            rows = cursor.fetchall()
            for row in rows:
                animal = Animal(
                    id=row[0],
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
        return animals

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            print("Database connection closed.")