# shared/models/database.py

import sqlite3
import os
from .animal import Animal
from .project import Project
import datetime

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'rrr_app.db')
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        self.settings = self.load_settings()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Table for animals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS animals (
                animal_id TEXT PRIMARY KEY,
                species TEXT NOT NULL,
                body_weight REAL NOT NULL
            )
        ''')
        # Table for projects
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                creation_date TEXT NOT NULL
            )
        ''')
        # Table to map projects to animals and relay pairs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_animals (
                project_id INTEGER,
                animal_id TEXT,
                relay_pair TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
            )
        ''')
        self.conn.commit()

    def load_settings(self):
        # Load settings from a settings file or define default relay pairs
        settings_file = os.path.join(os.path.dirname(__file__), 'settings.json')
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                return json.load(f)
        else:
            # Define default relay pairs (example)
            return {
                "relay_pairs": [(1, 2), (3, 4), (5, 6), (7, 8),
                                (9, 10), (11, 12), (13, 14), (15, 16)]
            }

    def save_settings(self):
        settings_file = os.path.join(os.path.dirname(__file__), 'settings.json')
        with open(settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def add_animal(self, animal_id, species, body_weight):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO animals (animal_id, species, body_weight) VALUES (?, ?, ?)',
                       (animal_id, species, body_weight))
        self.conn.commit()
        return Animal(animal_id, species, body_weight)

    def get_animals(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT animal_id, species, body_weight FROM animals')
        rows = cursor.fetchall()
        return [Animal(*row) for row in rows]

    def get_animal_by_id(self, animal_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT animal_id, species, body_weight FROM animals WHERE animal_id = ?', (animal_id,))
        row = cursor.fetchone()
        if row:
            return Animal(*row)
        return None

    def create_project(self, animals):
        cursor = self.conn.cursor()
        creation_date = datetime.datetime.now().isoformat()
        cursor.execute('INSERT INTO projects (creation_date) VALUES (?)', (creation_date,))
        project_id = cursor.lastrowid
        for animal in animals:
            # Assign relay pairs based on availability
            relay_pair = self.assign_relay_pair()
            if relay_pair is None:
                raise Exception("No available relay pairs to assign.")
            cursor.execute('INSERT INTO project_animals (project_id, animal_id, relay_pair) VALUES (?, ?, ?)',
                           (project_id, animal.animal_id, str(relay_pair)))
        self.conn.commit()
        return Project(project_id, creation_date, animals)

    def get_projects(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT project_id, creation_date FROM projects')
        project_rows = cursor.fetchall()
        projects = []
        for project_row in project_rows:
            project_id, creation_date = project_row
            cursor.execute('SELECT animal_id, relay_pair FROM project_animals WHERE project_id = ?', (project_id,))
            project_animals = cursor.fetchall()
            animals = []
            for animal_id, relay_pair_str in project_animals:
                animal = self.get_animal_by_id(animal_id)
                if animal:
                    relay_pair = tuple(map(int, relay_pair_str.strip('()').split(',')))
                    animals.append(animal)
            projects.append(Project(project_id, creation_date, animals))
        return projects

    def get_project_by_id(self, project_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT project_id, creation_date FROM projects WHERE project_id = ?', (project_id,))
        project_row = cursor.fetchone()
        if project_row:
            project_id, creation_date = project_row
            cursor.execute('SELECT animal_id, relay_pair FROM project_animals WHERE project_id = ?', (project_id,))
            project_animals = cursor.fetchall()
            animals = []
            for animal_id, relay_pair_str in project_animals:
                animal = self.get_animal_by_id(animal_id)
                if animal:
                    relay_pair = tuple(map(int, relay_pair_str.strip('()').split(',')))
                    animals.append(animal)
            return Project(project_id, creation_date, animals)
        return None

    def delete_project(self, project_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM project_animals WHERE project_id = ?', (project_id,))
        cursor.execute('DELETE FROM projects WHERE project_id = ?', (project_id,))
        self.conn.commit()

    def assign_relay_pair(self):
        # Fetch all current relay pairs in projects
        cursor = self.conn.cursor()
        cursor.execute('SELECT relay_pair FROM project_animals')
        existing_relay_pairs = [tuple(map(int, row[0].strip('()').split(','))) for row in cursor.fetchall()]
        for relay_pair in self.settings['relay_pairs']:
            if relay_pair not in existing_relay_pairs:
                return relay_pair
        # If all relay pairs are occupied, return None
        return None

    def get_mouse_by_relay(self, relay_pair):
        cursor = self.conn.cursor()
        relay_pair_str = str(relay_pair)
        cursor.execute('SELECT animal_id FROM project_animals WHERE relay_pair = ?', (relay_pair_str,))
        row = cursor.fetchone()
        if row:
            animal_id = row[0]
            return self.get_animal_by_id(animal_id)
        return None