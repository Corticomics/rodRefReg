"""
Integration module for connecting IR module with main RRR application.

This module provides functions and classes for integrating the IR sensor
module with the main RRR application, including UI integration, database
integration, and event handling.
"""

import logging
import time
import sys
import os

# Add the project root to the path to allow imports from ir_module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from ir_module.config import is_feature_enabled, print_config_status
from ir_module.main import IRModule
from ir_module.model.database_migration import initialize_database, check_migration_needed

logger = logging.getLogger(__name__)

class IRModuleIntegration:
    """
    Integration class for the IR sensor module.
    
    This class handles the integration of the IR sensor module with the
    main RRR application, including UI, database, and event handling.
    """
    
    def __init__(self, app_controller=None, database_handler=None):
        """
        Initialize the IR module integration.
        
        Args:
            app_controller: Main application controller from RRR.
            database_handler: Database handler from RRR.
        """
        self.app_controller = app_controller
        self.database_handler = database_handler
        self.ir_module = None
        self.data_analysis_tab = None
        
        # Log integration startup
        logger.info("IR module integration initializing")
        print_config_status()
        
        # Initialize the IR module if integration is enabled
        if is_feature_enabled("ENABLE_INTEGRATION"):
            self._initialize_module()
        else:
            logger.info("IR module integration disabled in configuration")
    
    def _initialize_module(self):
        """Initialize the IR module and integrate with RRR."""
        try:
            # Initialize database if needed
            if is_feature_enabled("ENABLE_DATABASE_STORAGE") and self.database_handler:
                if check_migration_needed(self.database_handler):
                    logger.info("Database migration needed, initializing...")
                    if not initialize_database(self.database_handler):
                        logger.error("Failed to initialize IR database")
                        return
                    logger.info("Database initialized successfully")
            
            # Create IR module
            self.ir_module = IRModule(
                database_handler=self.database_handler,
                system_controller=self.app_controller
            )
            
            # Initialize animal-relay mapping if possible
            if hasattr(self.app_controller, 'get_animal_relay_mapping'):
                animal_mapping = self.app_controller.get_animal_relay_mapping()
                self.ir_module.update_animal_mapping(animal_mapping)
            
            # Add event handler for animal-relay mapping changes
            if hasattr(self.app_controller, 'relay_assignments_changed'):
                self.app_controller.relay_assignments_changed.connect(
                    self._handle_relay_assignments_changed
                )
            
            # Integration complete
            logger.info("IR module integration complete")
            
        except Exception as e:
            logger.error(f"Error initializing IR module: {e}")
            self.ir_module = None
    
    def _handle_relay_assignments_changed(self):
        """Handle changes to relay assignments."""
        if not self.ir_module or not hasattr(self.app_controller, 'get_animal_relay_mapping'):
            return
        
        try:
            # Get updated animal mapping
            animal_mapping = self.app_controller.get_animal_relay_mapping()
            
            # Update IR module
            self.ir_module.update_animal_mapping(animal_mapping)
            logger.info("Updated animal-relay mapping in IR module")
            
        except Exception as e:
            logger.error(f"Error updating animal-relay mapping: {e}")
    
    def get_data_analysis_tab(self, parent=None):
        """
        Get the data analysis tab for the UI.
        
        Args:
            parent: Parent widget for the tab.
            
        Returns:
            QWidget or None: The data analysis tab if available, None otherwise.
        """
        if not self.ir_module or not is_feature_enabled("ENABLE_VISUALIZATION_TAB"):
            logger.warning("Data analysis tab requested but not available")
            return None
        
        try:
            # Get the tab from the IR module
            self.data_analysis_tab = self.ir_module.get_data_analysis_tab(parent)
            return self.data_analysis_tab
            
        except Exception as e:
            logger.error(f"Error creating data analysis tab: {e}")
            return None
    
    def test_ir_sensor(self, relay_unit_id):
        """
        Test a specific IR sensor.
        
        Args:
            relay_unit_id (int): ID of the relay unit to test.
            
        Returns:
            bool: True if test was successful, False otherwise.
        """
        if not self.ir_module:
            return False
        
        return self.ir_module.test_sensor(relay_unit_id)
    
    def get_ir_sensor_status(self, relay_unit_id=None):
        """
        Get the status of IR sensors.
        
        Args:
            relay_unit_id (int, optional): Specific relay unit to get status for.
            
        Returns:
            dict: Status information for the requested sensors.
        """
        if not self.ir_module:
            return {}
        
        return self.ir_module.get_sensor_status(relay_unit_id)
    
    def shutdown(self):
        """Clean shutdown of the IR module integration."""
        if self.ir_module:
            logger.info("Shutting down IR module integration")
            self.ir_module.shutdown()
            self.ir_module = None
            logger.info("IR module integration shutdown complete")

# Simple module test
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create a mock database handler
    class MockDatabaseHandler:
        def connect(self):
            import sqlite3
            return sqlite3.connect(':memory:')
        
        def get_all_animals(self):
            return [(1, "Animal 1"), (2, "Animal 2")]
    
    # Create a mock application controller
    class MockAppController:
        def __init__(self):
            from PyQt5.QtCore import pyqtSignal
            self.relay_assignments_changed = pyqtSignal()
        
        def get_animal_relay_mapping(self):
            return {1: 1, 2: 2}
    
    print("IR Module Integration Test")
    print("=========================")
    
    try:
        # Create mock objects
        db_handler = MockDatabaseHandler()
        app_controller = MockAppController()
        
        # Initialize integration
        integration = IRModuleIntegration(app_controller, db_handler)
        
        # Test IR sensor
        print("\nTesting IR sensors...")
        for relay_id in [1, 2]:
            result = integration.test_ir_sensor(relay_id)
            print(f"Relay unit {relay_id}: {'Success' if result else 'Failed'}")
        
        # Get sensor status
        print("\nSensor status:")
        status = integration.get_ir_sensor_status()
        for unit_id, sensor_status in status.items():
            print(f"Relay unit {unit_id}: {sensor_status}")
        
        # Clean shutdown
        integration.shutdown()
        print("\nIR module integration test completed successfully")
        
    except Exception as e:
        print(f"Error during integration test: {e}")
        import traceback
        traceback.print_exc() 