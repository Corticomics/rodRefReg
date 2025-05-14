"""
Sensor mapper module for managing multiple IR sensors.

This module handles the mapping between relay units and IR sensors,
and provides centralized management of sensor initialization and events.
"""

import logging
import time
import json
import os
from threading import Timer
import sys

# Add the project root to the path to allow imports from ir_module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from ir_module.config import is_feature_enabled, get_hardware_config
from ir_module.hardware.ir_sensor import IRSensor

logger = logging.getLogger(__name__)

class SensorManager:
    """
    Manager for multiple IR sensors.
    
    This class handles the creation, configuration, and management of
    multiple IR sensors, and maps them to relay units.
    """
    
    def __init__(self, custom_sensor_map=None, callback=None):
        """
        Initialize the sensor manager.
        
        Args:
            custom_sensor_map (dict, optional): Custom mapping of relay unit IDs to GPIO pins.
            callback (callable, optional): Callback function for sensor events.
        """
        self.sensors = {}
        self.callback = callback
        self.sensor_map = custom_sensor_map or get_hardware_config("DEFAULT_SENSOR_MAP", {})
        self.animal_relay_mapping = {}  # Maps relay units to animals
        
        # Initialize sensors based on configuration
        self._initialize_sensors()
        
        logger.info(f"SensorManager initialized with {len(self.sensors)} sensors")
    
    def _initialize_sensors(self):
        """Initialize IR sensors based on the sensor map."""
        for relay_unit_id, gpio_pin in self.sensor_map.items():
            try:
                # Create a sensor for each mapped relay unit
                sensor = IRSensor(
                    gpio_pin=int(gpio_pin),
                    relay_unit_id=int(relay_unit_id),
                    callback=self._handle_beam_break,
                    debounce_ms=get_hardware_config("DEBOUNCE_MS")
                )
                
                self.sensors[int(relay_unit_id)] = sensor
                logger.info(f"Initialized IR sensor for relay unit {relay_unit_id} on GPIO pin {gpio_pin}")
            except Exception as e:
                logger.error(f"Failed to initialize IR sensor for relay unit {relay_unit_id}: {e}")
    
    def _handle_beam_break(self, relay_unit_id, timestamp):
        """
        Handle a beam break event from a sensor.
        
        Args:
            relay_unit_id (int): ID of the relay unit associated with the sensor.
            timestamp (float): Timestamp of the event in milliseconds.
        """
        # Basic terminal output
        animal_id = self.get_animal_for_relay(relay_unit_id)
        animal_info = f" (Animal ID: {animal_id})" if animal_id else ""
        print(f"[{time.strftime('%H:%M:%S')}] Beam break on relay unit {relay_unit_id}{animal_info}")
        
        # Only proceed with advanced processing if enabled
        if not is_feature_enabled("ENABLE_DATA_PROCESSING"):
            return
        
        # Forward the event to the callback if provided
        if self.callback:
            self.callback(relay_unit_id, timestamp, animal_id)
    
    def update_animal_mapping(self, mapping):
        """
        Update the mapping between relay units and animals.
        
        Args:
            mapping (dict): Dictionary mapping relay unit IDs to animal IDs.
        """
        self.animal_relay_mapping = {int(k): v for k, v in mapping.items()}
        logger.debug(f"Updated animal-relay mapping: {self.animal_relay_mapping}")
    
    def get_animal_for_relay(self, relay_unit_id):
        """
        Get the animal ID associated with a relay unit.
        
        Args:
            relay_unit_id (int): ID of the relay unit.
            
        Returns:
            int or None: The associated animal ID, or None if not found.
        """
        return self.animal_relay_mapping.get(int(relay_unit_id))
    
    def get_sensor_status(self, relay_unit_id=None):
        """
        Get the status of sensors.
        
        Args:
            relay_unit_id (int, optional): Specific relay unit to get status for.
            
        Returns:
            dict: Status information for the requested sensors.
        """
        if relay_unit_id is not None:
            sensor = self.sensors.get(int(relay_unit_id))
            return sensor.get_status() if sensor else None
        
        return {unit_id: sensor.get_status() for unit_id, sensor in self.sensors.items()}
    
    def simulate_beam_break(self, relay_unit_id):
        """
        Simulate a beam break for testing.
        
        Args:
            relay_unit_id (int): ID of the relay unit to simulate a beam break for.
            
        Returns:
            bool: True if simulation was triggered, False otherwise.
        """
        sensor = self.sensors.get(int(relay_unit_id))
        if sensor:
            sensor.simulate_beam_break()
            return True
        return False
    
    def cleanup(self):
        """Clean up all sensors."""
        for sensor in self.sensors.values():
            sensor.cleanup()
        logger.info("All sensors cleaned up") 