"""
Main entry point for the IR sensor module.

This module serves as the central integration point for the IR sensor system,
providing a clean API for the main RRR application to use, and handling the
progressive enabling of features based on configuration.
"""

import logging
import time
import os
import sys
from threading import Thread
import signal

# Add the project root to the path to allow imports from ir_module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from ir_module.config import is_feature_enabled, get_hardware_config, print_config_status
from ir_module.hardware.sensor_mapper import SensorManager

logger = logging.getLogger(__name__)

class IRModule:
    """
    Main class for the IR sensor module.
    
    This class serves as the main entry point for the IR sensor module,
    and handles the initialization and management of all components.
    """
    
    def __init__(self, database_handler=None, system_controller=None):
        """
        Initialize the IR module.
        
        Args:
            database_handler: Database handler for storing events (optional).
            system_controller: System controller for integration (optional).
        """
        # Print configuration status
        print_config_status()
        
        # Store references to external components
        self.database_handler = database_handler
        self.system_controller = system_controller
        
        # Initialize components based on configuration
        self._initialize_components()
        
        logger.info("IR module initialized")
    
    def _initialize_components(self):
        """Initialize components based on configuration flags."""
        # Always initialize the sensor manager for basic functionality
        self.sensor_manager = SensorManager(
            callback=self._handle_sensor_event if is_feature_enabled("ENABLE_DATA_PROCESSING") else None
        )
        
        # Initialize data processing if enabled
        self.event_manager = None
        if is_feature_enabled("ENABLE_DATA_PROCESSING"):
            try:
                # Import and initialize components only if enabled
                from ir_module.data.drink_event_manager import DrinkEventManager
                self.event_manager = DrinkEventManager(
                    database_handler=self.database_handler if is_feature_enabled("ENABLE_DATABASE_STORAGE") else None,
                    animal_relay_mapping=self.sensor_manager
                )
                logger.info("Data processing components initialized")
            except Exception as e:
                logger.error(f"Failed to initialize data processing: {e}")
                self.event_manager = None
        
        # Initialize visualization components if enabled
        self.data_analysis_tab = None
        if is_feature_enabled("ENABLE_VISUALIZATION_TAB") and self.database_handler:
            try:
                # Import and initialize UI components only if enabled
                from ir_module.ui.data_analysis_tab import DataAnalysisTab
                # Note: actual instantiation happens later when requested by the main app
                logger.info("Visualization components prepared")
            except Exception as e:
                logger.error(f"Failed to prepare visualization components: {e}")
    
    def _handle_sensor_event(self, relay_unit_id, timestamp, animal_id=None):
        """
        Handle a sensor event.
        
        Args:
            relay_unit_id (int): ID of the relay unit that triggered the event.
            timestamp (float): Timestamp of the event in milliseconds.
            animal_id (int, optional): ID of the animal associated with the relay unit.
        """
        if self.event_manager:
            # Queue the event for processing
            self.event_manager.queue_event({
                'type': 'beam_break',
                'relay_unit_id': relay_unit_id,
                'timestamp': timestamp,
                'animal_id': animal_id
            })
    
    def update_animal_mapping(self, mapping):
        """
        Update the mapping between relay units and animals.
        
        Args:
            mapping (dict): Dictionary mapping relay unit IDs to animal IDs.
        """
        if self.sensor_manager:
            self.sensor_manager.update_animal_mapping(mapping)
    
    def get_data_analysis_tab(self, parent=None):
        """
        Get the data analysis tab for the UI.
        
        Args:
            parent: Parent widget for the tab.
            
        Returns:
            DataAnalysisTab or None: The data analysis tab if enabled, None otherwise.
        """
        if not is_feature_enabled("ENABLE_VISUALIZATION_TAB"):
            logger.warning("Visualization tab requested but not enabled in configuration")
            return None
        
        try:
            from ir_module.ui.data_analysis_tab import DataAnalysisTab
            self.data_analysis_tab = DataAnalysisTab(
                database_handler=self.database_handler,
                ir_sensor_manager=self if is_feature_enabled("ENABLE_INTEGRATION") else None,
                parent=parent
            )
            return self.data_analysis_tab
        except Exception as e:
            logger.error(f"Failed to create data analysis tab: {e}")
            return None
    
    def test_sensor(self, relay_unit_id):
        """
        Test a specific sensor by simulating a beam break.
        
        Args:
            relay_unit_id (int): ID of the relay unit to test.
            
        Returns:
            bool: True if test was successful, False otherwise.
        """
        if self.sensor_manager:
            return self.sensor_manager.simulate_beam_break(int(relay_unit_id))
        return False
    
    def get_sensor_status(self, relay_unit_id=None):
        """
        Get the status of sensors.
        
        Args:
            relay_unit_id (int, optional): Specific relay unit to get status for.
            
        Returns:
            dict: Status information for the requested sensors.
        """
        if self.sensor_manager:
            return self.sensor_manager.get_sensor_status(relay_unit_id)
        return {}
    
    def shutdown(self):
        """Clean shutdown of all components."""
        logger.info("Shutting down IR module")
        
        # Shutdown event manager if enabled
        if self.event_manager:
            if hasattr(self.event_manager, 'shutdown'):
                self.event_manager.shutdown()
        
        # Always clean up sensor manager
        if self.sensor_manager:
            self.sensor_manager.cleanup()
        
        logger.info("IR module shutdown complete")

# Standalone execution
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("IR Module Standalone Test")
    print("========================")
    print("Press Ctrl+C to exit")
    
    # Create the IR module
    ir_module = IRModule()
    
    # Print sensor status
    status = ir_module.get_sensor_status()
    print("\nSensor Status:")
    for unit_id, sensor_status in status.items():
        print(f"Relay Unit {unit_id}: {'Initialized' if sensor_status['is_initialized'] else 'Not Initialized'} "
              f"({'Simulation' if sensor_status['simulation_mode'] else 'Hardware'} mode)")
    
    # Simulate a beam break for testing
    print("\nSimulating beam breaks...")
    for unit_id in status.keys():
        ir_module.test_sensor(unit_id)
        time.sleep(1)
    
    # Keep running until interrupted
    try:
        # Set up signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print("\nExiting...")
            ir_module.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        ir_module.shutdown() 