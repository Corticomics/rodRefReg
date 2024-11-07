import sqlite3
import os
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
        """Create the necessary tables if they don't exist."""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            # Create animals table with weights as REAL
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS animals (
                    animal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    initial_weight REAL,
                    last_weight REAL,
                    last_weighted TEXT
                )
            ''')

            # Create schedules table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    relay TEXT NOT NULL,
                    animals TEXT NOT NULL  -- Comma-separated animal IDs
                )
            ''')
            conn.commit()
            print("Tables created or confirmed to exist.")
        except sqlite3.Error as e:
            print(f"Database error during table creation: {e}")

    def add_animal(self, animal):
        """Add a new animal to the database."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO animals (name, initial_weight, last_weight, last_weighted)
                VALUES (?, ?, ?, ?)
            ''', (animal.name, animal.initial_weight, animal.last_weight, animal.last_weighted))
            conn.commit()
            print(f"Animal '{animal.name}' added with ID: {cursor.lastrowid}")
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error when adding animal: {e}")
            return None

    def remove_animal(self, animal_id):
        """Remove an animal from the database."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM animals WHERE animal_id = ?', (animal_id,))
            conn.commit()
            print(f"Animal with ID {animal_id} removed.")
        except sqlite3.Error as e:
            print(f"Database error when removing animal: {e}")

    def update_animal(self, animal):
        """Update an existing animal's information."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE animals
                SET name = ?, initial_weight = ?, last_weight = ?, last_weighted = ?
                WHERE animal_id = ?
            ''', (animal.name, animal.initial_weight, animal.last_weight, animal.last_weighted, animal.animal_id))
            conn.commit()
            print(f"Animal with ID {animal.animal_id} updated.")
        except sqlite3.Error as e:
            print(f"Database error when updating animal: {e}")

    def get_all_animals(self):
        """Retrieve all animals from the database."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM animals')
            rows = cursor.fetchall()
            animals = []
            for row in rows:
                animal = Animal(
                    animal_id=row[0],
                    name=row[1],
                    initial_weight=row[2],
                    last_weight=row[3],
                    last_weighted=row[4]
                )
                animals.append(animal)
            print(f"Retrieved {len(animals)} animals from the database.")
            return animals
        except sqlite3.Error as e:
            print(f"Database error when retrieving animals: {e}")
            return []

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None