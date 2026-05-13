"""
Test utilities for the IR sensor module.

This module provides helper functions for testing IR sensors
and simulating sensor events.
"""

import logging
import time
import random
import threading
import sys
import os

# Add the project root to the path to allow imports from ir_module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

logger = logging.getLogger(__name__)

class SensorSimulator:
    """
    Simulator for IR sensor events.
    
    This class provides methods for simulating IR sensor events for testing
    without requiring physical hardware.
    """
    
    def __init__(self, sensor_manager=None, event_manager=None):
        """
        Initialize the sensor simulator.
        
        Args:
            sensor_manager: SensorManager to simulate events on.
            event_manager: DrinkEventManager to send events to.
        """
        self.sensor_manager = sensor_manager
        self.event_manager = event_manager
        self.running = False
        self.simulation_thread = None
        
        logger.info("SensorSimulator initialized")
    
    def simulate_single_event(self, relay_unit_id):
        """
        Simulate a single beam break event.
        
        Args:
            relay_unit_id (int): ID of the relay unit to simulate an event for.
            
        Returns:
            bool: True if simulation was triggered, False otherwise.
        """
        if self.sensor_manager:
            return self.sensor_manager.simulate_beam_break(relay_unit_id)
        
        if self.event_manager:
            current_time = time.time() * 1000
            self.event_manager.queue_event({
                'type': 'beam_break',
                'relay_unit_id': relay_unit_id,
                'timestamp': current_time
            })
            return True
        
        return False
    
    def start_random_simulation(self, relay_unit_ids=None, min_interval=1.0, max_interval=10.0):
        """
        Start simulating random beam break events.
        
        Args:
            relay_unit_ids (list, optional): List of relay unit IDs to simulate events for.
            min_interval (float): Minimum interval between events in seconds.
            max_interval (float): Maximum interval between events in seconds.
            
        Returns:
            bool: True if simulation was started, False otherwise.
        """
        if not self.sensor_manager and not self.event_manager:
            logger.error("No sensor manager or event manager provided")
            return False
        
        if self.running:
            logger.warning("Simulation already running")
            return False
        
        self.running = True
        self.simulation_thread = threading.Thread(
            target=self._run_simulation,
            args=(relay_unit_ids, min_interval, max_interval)
        )
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        
        logger.info("Started random simulation")
        return True
    
    def _run_simulation(self, relay_unit_ids, min_interval, max_interval):
        """
        Run the simulation loop.
        
        Args:
            relay_unit_ids (list): List of relay unit IDs to simulate events for.
            min_interval (float): Minimum interval between events in seconds.
            max_interval (float): Maximum interval between events in seconds.
        """
        # If no relay units provided, get them from the sensor manager
        if not relay_unit_ids and self.sensor_manager:
            relay_unit_ids = list(self.sensor_manager.sensors.keys())
        
        # If still no relay units, use default
        if not relay_unit_ids:
            relay_unit_ids = [1, 2, 3, 4]
        
        logger.info(f"Running simulation for relay units: {relay_unit_ids}")
        
        while self.running:
            try:
                # Choose a random relay unit
                relay_unit_id = random.choice(relay_unit_ids)
                
                # Simulate a beam break
                self.simulate_single_event(relay_unit_id)
                
                # Wait for a random interval
                interval = random.uniform(min_interval, max_interval)
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                time.sleep(1)  # Sleep to avoid busy loop on error
    
    def stop_simulation(self):
        """
        Stop the simulation.
        
        Returns:
            bool: True if simulation was stopped, False otherwise.
        """
        if not self.running:
            logger.warning("Simulation not running")
            return False
        
        self.running = False
        
        # Wait for thread to finish
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=2.0)
        
        logger.info("Stopped simulation")
        return True

def simulate_drinking_pattern(sensor_simulator, pattern_data, speed_factor=1.0):
    """
    Simulate a specific drinking pattern.
    
    Args:
        sensor_simulator (SensorSimulator): Simulator to use.
        pattern_data (dict): Pattern data with timestamps and relay units.
        speed_factor (float): Factor to speed up or slow down the pattern.
        
    Returns:
        bool: True if simulation was started, False otherwise.
    """
    if not sensor_simulator:
        logger.error("No sensor simulator provided")
        return False
    
    if not pattern_data or not pattern_data.get('events'):
        logger.error("Invalid pattern data")
        return False
    
    # Start a thread to run the pattern
    thread = threading.Thread(
        target=_run_pattern_simulation,
        args=(sensor_simulator, pattern_data, speed_factor)
    )
    thread.daemon = True
    thread.start()
    
    logger.info("Started pattern simulation")
    return True

def _run_pattern_simulation(sensor_simulator, pattern_data, speed_factor):
    """
    Run a pattern simulation.
    
    Args:
        sensor_simulator (SensorSimulator): Simulator to use.
        pattern_data (dict): Pattern data with timestamps and relay units.
        speed_factor (float): Factor to speed up or slow down the pattern.
    """
    events = pattern_data['events']
    
    # Sort events by timestamp
    events.sort(key=lambda e: e.get('timestamp', 0))
    
    # Track the start time
    start_time = time.time()
    first_event_time = events[0].get('timestamp', 0) / 1000
    
    for event in events:
        try:
            # Get event data
            relay_unit_id = event.get('relay_unit_id')
            timestamp = event.get('timestamp', 0) / 1000  # Convert to seconds
            
            # Calculate the time to wait
            target_time = (timestamp - first_event_time) / speed_factor
            current_time = time.time() - start_time
            
            if target_time > current_time:
                # Wait until it's time for this event
                time.sleep(target_time - current_time)
            
            # Simulate the event
            sensor_simulator.simulate_single_event(relay_unit_id)
            
        except Exception as e:
            logger.error(f"Error in pattern simulation: {e}")
    
    logger.info("Pattern simulation completed") 