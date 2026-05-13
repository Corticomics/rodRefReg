"""
Database schema extensions for IR sensor module.

This module defines the database schema extensions needed to store
IR sensor data, including drinking sessions and events.
"""

import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

class IRDatabaseExtensions:
    """
    Extends the RRR database with tables for IR sensor data.
    
    This class provides methods for creating and maintaining the
    database tables used by the IR sensor module.
    """
    
    def __init__(self, database_handler):
        """
        Initialize the database extensions.
        
        Args:
            database_handler: Database handler from the main RRR application.
        """
        self.db_handler = database_handler
        logger.info("IR database extensions initialized")
    
    def create_tables(self):
        """
        Create the necessary tables for storing IR sensor data.
        
        Returns:
            bool: True if tables were created successfully, False otherwise.
        """
        try:
            with self.db_handler.connect() as conn:
                cursor = conn.cursor()
                
                # Create drinking_sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS drinking_sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        animal_id INTEGER NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        duration_ms INTEGER NOT NULL,
                        estimated_volume_ml REAL NOT NULL,
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    )
                ''')
                
                # Create drinking_events table for individual beam breaks
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS drinking_events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        animal_id INTEGER NOT NULL,
                        timestamp TEXT NOT NULL,
                        duration_ms INTEGER NOT NULL,
                        session_id INTEGER,
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id),
                        FOREIGN KEY(session_id) REFERENCES drinking_sessions(session_id)
                    )
                ''')
                
                # Create drinking_patterns table for aggregated time-bin data
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS drinking_patterns (
                        pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        animal_id INTEGER NOT NULL,
                        time_bin TEXT NOT NULL,
                        event_count INTEGER NOT NULL,
                        total_duration_ms INTEGER NOT NULL,
                        total_volume_ml REAL NOT NULL,
                        date TEXT NOT NULL,
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    )
                ''')
                
                conn.commit()
                logger.info("IR database tables created successfully")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error creating IR database tables: {e}")
            return False
    
    def extend_database_handler(self):
        """
        Extend the database handler with IR-specific methods.
        
        This method adds IR-specific methods to the database handler
        for storing and retrieving IR sensor data.
        """
        # Add methods to the database handler
        self.db_handler.add_drinking_session = self.add_drinking_session
        self.db_handler.add_drinking_event = self.add_drinking_event
        self.db_handler.get_drinking_data_for_animal = self.get_drinking_data_for_animal
        self.db_handler.get_circadian_drinking_pattern = self.get_circadian_drinking_pattern
    
    def add_drinking_session(self, animal_id, start_time, end_time, duration_ms, estimated_volume_ml):
        """
        Add a drinking session to the database.
        
        Args:
            animal_id (int): ID of the animal.
            start_time (str): Start time in ISO format.
            end_time (str): End time in ISO format.
            duration_ms (int): Duration in milliseconds.
            estimated_volume_ml (float): Estimated water volume in ml.
            
        Returns:
            int: ID of the newly created session, or None on error.
        """
        try:
            with self.db_handler.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO drinking_sessions 
                    (animal_id, start_time, end_time, duration_ms, estimated_volume_ml)
                    VALUES (?, ?, ?, ?, ?)
                ''', (animal_id, start_time, end_time, duration_ms, estimated_volume_ml))
                
                conn.commit()
                return cursor.lastrowid
                
        except sqlite3.Error as e:
            logger.error(f"Error adding drinking session: {e}")
            return None
    
    def add_drinking_event(self, animal_id, timestamp, duration_ms, session_id=None):
        """
        Add a drinking event to the database.
        
        Args:
            animal_id (int): ID of the animal.
            timestamp (str): Timestamp in ISO format.
            duration_ms (int): Duration in milliseconds.
            session_id (int, optional): ID of the associated session.
            
        Returns:
            int: ID of the newly created event, or None on error.
        """
        try:
            with self.db_handler.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO drinking_events 
                    (animal_id, timestamp, duration_ms, session_id)
                    VALUES (?, ?, ?, ?)
                ''', (animal_id, timestamp, duration_ms, session_id))
                
                conn.commit()
                return cursor.lastrowid
                
        except sqlite3.Error as e:
            logger.error(f"Error adding drinking event: {e}")
            return None
    
    def get_drinking_data_for_animal(self, animal_id, start_date=None, end_date=None):
        """
        Get drinking data for an animal, optionally within a date range.
        
        Args:
            animal_id (int): ID of the animal.
            start_date (str, optional): Start date in ISO format.
            end_date (str, optional): End date in ISO format.
            
        Returns:
            list: List of drinking sessions for the animal.
        """
        try:
            with self.db_handler.connect() as conn:
                cursor = conn.cursor()
                
                if start_date and end_date:
                    query = '''
                        SELECT session_id, start_time, end_time, duration_ms, estimated_volume_ml
                        FROM drinking_sessions
                        WHERE animal_id = ?
                          AND start_time >= ?
                          AND end_time <= ?
                        ORDER BY start_time DESC
                    '''
                    cursor.execute(query, (animal_id, start_date, end_date))
                else:
                    query = '''
                        SELECT session_id, start_time, end_time, duration_ms, estimated_volume_ml
                        FROM drinking_sessions
                        WHERE animal_id = ?
                        ORDER BY start_time DESC
                    '''
                    cursor.execute(query, (animal_id,))
                
                return cursor.fetchall()
                
        except sqlite3.Error as e:
            logger.error(f"Error getting drinking data: {e}")
            return []
    
    def get_circadian_drinking_pattern(self, animal_id, days=7, bin_minutes=5):
        """
        Get circadian drinking pattern for an animal.
        
        Args:
            animal_id (int): ID of the animal.
            days (int): Number of days to include in the analysis.
            bin_minutes (int): Size of time bins in minutes.
            
        Returns:
            dict: Circadian pattern data with time bins and counts.
        """
        try:
            with self.db_handler.connect() as conn:
                cursor = conn.cursor()
                
                # Use SQLite's time functions to extract hour and minute
                # and bin data into time-of-day slots
                query = '''
                    SELECT 
                        strftime('%H:%M', start_time) AS time_bin,
                        COUNT(*) AS event_count,
                        SUM(duration_ms) AS total_duration,
                        SUM(estimated_volume_ml) AS total_volume
                    FROM drinking_sessions
                    WHERE animal_id = ?
                      AND start_time >= datetime('now', '-' || ? || ' days')
                    GROUP BY time_bin
                    ORDER BY 
                        CAST(strftime('%H', start_time) AS INTEGER),
                        CAST(strftime('%M', start_time) AS INTEGER)
                '''
                cursor.execute(query, (animal_id, days))
                rows = cursor.fetchall()
                
                # Extract results into time bins
                time_bins = []
                counts = []
                durations = []
                volumes = []
                
                for row in rows:
                    time_bins.append(row[0])
                    counts.append(row[1])
                    durations.append(row[2])
                    volumes.append(row[3])
                
                return {
                    'time_bins': time_bins,
                    'counts': counts,
                    'durations': durations,
                    'volumes': volumes
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error getting circadian pattern: {e}")
            return {
                'time_bins': [],
                'counts': [],
                'durations': [],
                'volumes': []
            } 