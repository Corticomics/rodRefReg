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

        # Create animals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS animals (
                animal_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                initial_weight INTEGER,
                last_weight INTEGER,
                last_weighted TEXT
            )
        ''')

        # Create schedules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                schedule_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                relay TEXT NOT NULL,
                animals TEXT NOT NULL  -- Comma-separated animal IDs
            )
        ''')

        conn.commit()

    def add_animal(self, animal):
        """Add a new animal to the database."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO animals (name, initial_weight, last_weight, last_weighted)
            VALUES (?, ?, ?, ?)
        ''', (animal.name, animal.initial_weight, animal.last_weight, animal.last_weighted))
        conn.commit()
        return cursor.lastrowid

    def remove_animal(self, animal_id):
        """Remove an animal from the database."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM animals WHERE animal_id = ?', (animal_id,))
        conn.commit()

    def update_animal(self, animal):
        """Update an existing animal's information."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE animals
            SET name = ?, initial_weight = ?, last_weight = ?, last_weighted = ?
            WHERE animal_id = ?
        ''', (animal.name, animal.initial_weight, animal.last_weight, animal.last_weighted, animal.animal_id))
        conn.commit()

    def get_all_animals(self):
        """Retrieve all animals from the database."""
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
        return animals

    def add_schedule(self, schedule):
        """Add a new schedule to the database."""
        conn = self.connect()
        cursor = conn.cursor()
        animals_str = ','.join(map(str, schedule['animals']))
        cursor.execute('''
            INSERT INTO schedules (name, relay, animals)
            VALUES (?, ?, ?)
        ''', (schedule['name'], schedule['relay'], animals_str))
        conn.commit()
        return cursor.lastrowid

    def remove_schedule(self, schedule_id):
        """Remove a schedule from the database."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM schedules WHERE schedule_id = ?', (schedule_id,))
        conn.commit()

    def get_all_schedules(self):
        """Retrieve all schedules from the database."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedules')
        rows = cursor.fetchall()
        schedules = []
        for row in rows:
            schedule = {
                'schedule_id': row[0],
                'name': row[1],
                'relay': row[2],
                'animals': list(map(int, row[3].split(',')))  # Convert back to list of integers
            }
            schedules.append(schedule)
        return schedules

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None