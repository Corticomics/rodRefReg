"""
Database migration for IR sensor module.

This module provides functions for initializing and upgrading the
database schema for the IR sensor module.
"""

import logging
import sqlite3
import os
import sys

# Add the project root to the path to allow imports from ir_module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from ir_module.model.database_schema import IRDatabaseExtensions

logger = logging.getLogger(__name__)

def initialize_database(database_handler):
    """
    Initialize the database for IR sensor module.
    
    This function creates the necessary tables and extends the database
    handler with IR-specific methods.
    
    Args:
        database_handler: Database handler from the main RRR application.
        
    Returns:
        bool: True if initialization was successful, False otherwise.
    """
    try:
        # Create database extensions
        extensions = IRDatabaseExtensions(database_handler)
        
        # Create tables
        if not extensions.create_tables():
            logger.error("Failed to create IR database tables")
            return False
        
        # Extend database handler with IR-specific methods
        extensions.extend_database_handler()
        
        logger.info("IR database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize IR database: {e}")
        return False

def check_migration_needed(database_handler):
    """
    Check if a database migration is needed.
    
    Args:
        database_handler: Database handler from the main RRR application.
        
    Returns:
        bool: True if migration is needed, False otherwise.
    """
    try:
        with database_handler.connect() as conn:
            cursor = conn.cursor()
            
            # Check if drinking_sessions table exists
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='drinking_sessions'
            ''')
            
            result = cursor.fetchone()
            return result is None
            
    except sqlite3.Error as e:
        logger.error(f"Error checking migration status: {e}")
        return True  # If we can't check, assume migration is needed

if __name__ == "__main__":
    # For testing purposes
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("IR Module Database Migration Tool")
    print("================================")
    
    # Simple command-line interface
    import argparse
    
    parser = argparse.ArgumentParser(description='IR Module Database Migration Tool')
    parser.add_argument('--db-path', required=True, help='Path to the RRR database file')
    args = parser.parse_args()
    
    # Create a simple database handler for testing
    class SimpleDBHandler:
        def __init__(self, db_path):
            self.db_path = db_path
            
        def connect(self):
            return sqlite3.connect(self.db_path)
    
    db_handler = SimpleDBHandler(args.db_path)
    
    # Check if migration is needed
    if check_migration_needed(db_handler):
        print("Migration needed. Initializing database...")
        if initialize_database(db_handler):
            print("Database migration completed successfully")
        else:
            print("Database migration failed")
    else:
        print("No migration needed. Database schema is up to date.") 