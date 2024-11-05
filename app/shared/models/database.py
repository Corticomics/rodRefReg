# shared/models/database.py

import sqlite3
from datetime import datetime

# Data Models
class Animal:
    def __init__(self, animal_id, species, initial_weight, body_weight, last_watering):
        self.animal_id = animal_id
        self.species = species
        self.initial_weight = initial_weight
        self.body_weight = body_weight
        self.last_watering = last_watering

class Project:
    def __init__(self, project_id, project_name, creation_date, animals, relay_volumes=None):
        self.project_id = project_id
        self.project_name = project_name
        self.creation_date = creation_date
        self.animals = animals  # List of Animal instances
        self.relay_volumes = relay_volumes or {}

# Database Manager
class DatabaseManager:
    def __init__(self, db_path='shared/models/rrr_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Animals Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS animals (
                animal_id TEXT PRIMARY KEY,
                species TEXT NOT NULL,
                initial_weight REAL NOT NULL,
                body_weight REAL NOT NULL,
                last_watering TEXT
            )
        ''')
        # Projects Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                creation_date TEXT NOT NULL
            )
        ''')
        # Project Assignments Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_assignments (
                project_id INTEGER,
                animal_id TEXT,
                relay_pair TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
            )
        ''')
        self.conn.commit()

    # --- Animal Methods ---

    def get_animals(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM animals')
        rows = cursor.fetchall()
        animals = []
        for row in rows:
            animal = Animal(
                animal_id=row[0],
                species=row[1],
                initial_weight=row[2],
                body_weight=row[3],
                last_watering=row[4]
            )
            animals.append(animal)
        return animals

    def add_animal(self, animal_id, species, body_weight):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO animals (animal_id, species, initial_weight, body_weight, last_watering)
                VALUES (?, ?, ?, ?, ?)
            ''', (animal_id, species, body_weight, body_weight, None))
            self.conn.commit()
            return Animal(animal_id, species, body_weight, body_weight, None)
        except sqlite3.IntegrityError:
            # Animal ID already exists
            return None

    def get_animal_by_id(self, animal_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM animals WHERE animal_id = ?', (animal_id,))
        row = cursor.fetchone()
        if row:
            return Animal(
                animal_id=row[0],
                species=row[1],
                initial_weight=row[2],
                body_weight=row[3],
                last_watering=row[4]
            )
        return None

    def update_animal_weight(self, animal_id, new_weight):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE animals
            SET body_weight = ?, last_watering = ?
            WHERE animal_id = ?
        ''', (new_weight, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), animal_id))
        self.conn.commit()
        return cursor.rowcount > 0

    # --- Project Methods ---

    def create_project(self, project_name, animals, relay_volumes=None):
        cursor = self.conn.cursor()
        creation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO projects (project_name, creation_date)
            VALUES (?, ?)
        ''', (project_name, creation_date))
        project_id = cursor.lastrowid

        # Assign animals to the project
        for animal in animals:
            # Assuming each animal has an 'assigned_relay_pair' attribute
            relay_pair_str = self.format_relay_pair(animal.assigned_relay_pair) if hasattr(animal, 'assigned_relay_pair') else "Unassigned"
            cursor.execute('''
                INSERT INTO project_assignments (project_id, animal_id, relay_pair)
                VALUES (?, ?, ?)
            ''', (project_id, animal.animal_id, relay_pair_str))
        self.conn.commit()

        return Project(project_id, project_name, creation_date, animals, relay_volumes)

    def get_past_projects(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM projects ORDER BY creation_date DESC')
        rows = cursor.fetchall()
        projects = []
        for row in rows:
            project_id = row[0]
            project_name = row[1]
            creation_date = row[2]
            # Fetch assigned animals
            cursor.execute('SELECT animal_id, relay_pair FROM project_assignments WHERE project_id = ?', (project_id,))
            assignments = cursor.fetchall()
            animals = []
            for assignment in assignments:
                animal = self.get_animal_by_id(assignment[0])
                if animal:
                    animals.append(animal)
            project = Project(project_id, project_name, creation_date, animals)
            projects.append(project)
        return projects

    def format_relay_pair(self, relay_pair):
        return f"{relay_pair[0]}&{relay_pair[1]}"

    def close_connection(self):
        self.conn.close()