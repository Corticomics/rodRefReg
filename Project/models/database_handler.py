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
            # Drop the table if it exists to avoid conflicts (only for development or testing)
            cursor.execute('DROP TABLE IF EXISTS animals')
            
            # Create animals table with both 'ID' and 'lab_animal_id'
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS animals (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    lab_animal_id TEXT UNIQUE NOT NULL,  -- User-defined animal ID
                    name TEXT NOT NULL,
                    initial_weight REAL,
                    last_weight REAL,
                    last_weighted TEXT
                )
            ''')

            # Drop and recreate the schedules table similarly (if needed)
            cursor.execute('DROP TABLE IF EXISTS schedules')
            
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
        """Add a new animal to the database with manual lab_animal_id."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO animals (lab_animal_id, name, initial_weight, last_weight, last_weighted)
                VALUES (?, ?, ?, ?, ?)
            ''', (animal.lab_animal_id, animal.name, animal.initial_weight, animal.last_weight, animal.last_weighted))
            conn.commit()
            print(f"Animal '{animal.name}' added with lab ID: {animal.lab_animal_id}")
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Error: Animal ID '{animal.lab_animal_id}' already exists.")
            return None
        except sqlite3.Error as e:
            print(f"Database error when adding animal: {e}")
            return None

    def remove_animal(self, lab_animal_id):
        """
        Removes an animal from the database based on its lab_animal_id.
        
        Args:
            lab_animal_id (str): The lab-specific animal ID to remove.
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM animals WHERE lab_animal_id = ?', (lab_animal_id,))
            if cursor.rowcount > 0:
                print(f"Animal with lab ID {lab_animal_id} removed.")
            else:
                print(f"No animal found with lab ID {lab_animal_id}.")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error removing animal with lab ID {lab_animal_id}: {e}")

    def update_animal(self, animal):
        """
        Updates an existing animal's information in the database.
        
        Args:
            animal (Animal): The animal object with updated information.
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE animals
                SET name = ?, initial_weight = ?, last_weight = ?, last_weighted = ?
                WHERE lab_animal_id = ?
            ''', (animal.name, animal.initial_weight, animal.last_weight, animal.last_weighted, animal.lab_animal_id))
            if cursor.rowcount > 0:
                print(f"Animal with lab ID {animal.lab_animal_id} updated.")
            else:
                print(f"No animal found with lab ID {animal.lab_animal_id} to update.")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating animal with lab ID {animal.lab_animal_id}: {e}")

    def get_all_animals(self):
        """
        Retrieves all animals from the database.
        
        Returns:
            list[Animal]: A list of Animal objects retrieved from the database.
        """
        animals = []
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT ID, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals')
            rows = cursor.fetchall()
            for row in rows:
                animal = Animal(
                    id=row[0],  # Primary key ID
                    lab_animal_id=row[1],
                    name=row[2],
                    initial_weight=row[3],
                    last_weight=row[4],
                    last_weighted=row[5]
                )
                animals.append(animal)
            print(f"Retrieved {len(animals)} animals from the database.")
        except sqlite3.Error as e:
            print(f"Error retrieving animals: {e}")
        return animals

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            print("Database connection closed.")