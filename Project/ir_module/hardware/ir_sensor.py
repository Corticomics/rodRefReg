"""
Basic IR sensor implementation with fallback to simulation.

This module provides the core IR sensor functionality with both real hardware
support and simulation capabilities for development and testing purposes.
"""

import logging
import time
from threading import Timer, Thread
from queue import Queue, Empty
import sys
import os

# Add the project root to the path to allow imports from ir_module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from ir_module.config import is_feature_enabled, get_hardware_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import GPIO libraries
GPIO_AVAILABLE = False
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    logger.info("RPi.GPIO module available - hardware mode enabled")
except ImportError:
    logger.warning("RPi.GPIO module not available - using simulation mode")

class IRSensor:
    """
    Basic IR sensor class that works with both real hardware and simulation.
    
    This class provides a clean abstraction over the IR sensor hardware,
    with fallback to simulation when actual hardware is not available.
    """
    
    def __init__(self, gpio_pin, relay_unit_id, callback=None, debounce_ms=None):
        """
        Initialize an IR sensor for a specific GPIO pin.
        
        Args:
            gpio_pin (int): The GPIO pin number the IR sensor is connected to.
            relay_unit_id (int): The ID of the relay unit this sensor is associated with.
            callback (callable, optional): Function to call when beam is broken.
            debounce_ms (int, optional): Debounce time in milliseconds.
        """
        self.gpio_pin = gpio_pin
        self.relay_unit_id = relay_unit_id
        self.callback = callback
        self.debounce_ms = debounce_ms or get_hardware_config("DEBOUNCE_MS", 300)
        
        # State tracking
        self.last_trigger_time = 0
        self.is_beam_broken = False
        self.is_initialized = False
        self.simulate_mode = is_feature_enabled("SIMULATE_SENSORS") or not GPIO_AVAILABLE
        
        # Initialize the sensor
        if not self.simulate_mode and GPIO_AVAILABLE:
            self._initialize_hardware()
        else:
            self._initialize_simulation()
    
    def _initialize_hardware(self):
        """Initialize the physical IR sensor using GPIO."""
        try:
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            
            # Configure the pin as input with pull-up resistor
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Add event detection for falling edge (beam break)
            GPIO.add_event_detect(
                self.gpio_pin,
                GPIO.FALLING,
                callback=self._gpio_callback,
                bouncetime=self.debounce_ms
            )
            
            self.is_initialized = True
            logger.info(f"IR sensor initialized on GPIO pin {self.gpio_pin} for relay unit {self.relay_unit_id}")
        except Exception as e:
            logger.error(f"Failed to initialize IR sensor on GPIO pin {self.gpio_pin}: {e}")
            self.is_initialized = False
            self.simulate_mode = True
            self._initialize_simulation()
    
    def _initialize_simulation(self):
        """Initialize simulation mode for the IR sensor."""
        logger.info(f"IR sensor simulation initialized for relay unit {self.relay_unit_id}")
        self.is_initialized = True
    
    def _gpio_callback(self, channel):
        """
        GPIO interrupt callback function.
        
        Args:
            channel: GPIO channel that triggered the interrupt.
        """
        current_time = time.time() * 1000  # ms precision
        
        # Simple debounce check
        if (current_time - self.last_trigger_time) < self.debounce_ms:
            return
        
        self.last_trigger_time = current_time
        self.is_beam_broken = True
        
        # Basic terminal output for hardware testing
        print(f"[{time.strftime('%H:%M:%S')}] IR beam break detected on relay unit {self.relay_unit_id} (GPIO {self.gpio_pin})")
        
        # Call the callback function if provided
        if self.callback:
            self.callback(self.relay_unit_id, current_time)
        
        # Schedule a beam restore check
        Timer(0.5, self._check_beam_restore).start()
    
    def _check_beam_restore(self):
        """Check if the beam has been restored."""
        if self.simulate_mode:
            self.is_beam_broken = False
            return
        
        try:
            # Read the current state of the GPIO pin
            current_state = GPIO.input(self.gpio_pin)
            
            # For a pull-up configuration, HIGH means beam is intact
            if current_state == GPIO.HIGH:
                self.is_beam_broken = False
                print(f"[{time.strftime('%H:%M:%S')}] IR beam restored on relay unit {self.relay_unit_id}")
        except Exception as e:
            logger.error(f"Error checking beam state: {e}")
    
    def simulate_beam_break(self):
        """
        Simulate a beam break for testing purposes.
        
        This method allows testing without actual hardware.
        """
        current_time = time.time() * 1000
        self.is_beam_broken = True
        
        print(f"[{time.strftime('%H:%M:%S')}] SIMULATED IR beam break on relay unit {self.relay_unit_id}")
        
        if self.callback:
            self.callback(self.relay_unit_id, current_time)
        
        # Automatically restore the beam after a short delay
        Timer(0.5, self._simulate_beam_restore).start()
    
    def _simulate_beam_restore(self):
        """Simulate the beam being restored."""
        self.is_beam_broken = False
        print(f"[{time.strftime('%H:%M:%S')}] SIMULATED IR beam restored on relay unit {self.relay_unit_id}")
    
    def get_status(self):
        """
        Get the current status of the IR sensor.
        
        Returns:
            dict: Status information including initialization state and beam state.
        """
        return {
            "relay_unit_id": self.relay_unit_id,
            "gpio_pin": self.gpio_pin,
            "is_initialized": self.is_initialized,
            "is_beam_broken": self.is_beam_broken,
            "simulation_mode": self.simulate_mode,
            "last_trigger": self.last_trigger_time
        }
    
    def cleanup(self):
        """Clean up GPIO resources."""
        if not self.simulate_mode and GPIO_AVAILABLE and self.is_initialized:
            try:
                GPIO.remove_event_detect(self.gpio_pin)
                logger.info(f"Removed event detection for GPIO pin {self.gpio_pin}")
            except Exception as e:
                logger.error(f"Error cleaning up GPIO for pin {self.gpio_pin}: {e}") 