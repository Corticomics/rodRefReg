#!/usr/bin/env python3
"""
I2C Coordination Manager for RRR
===============================

Provides exclusive time-sliced access to I2C bus for relay HAT and flow sensor.
Prevents simultaneous access conflicts by coordinating device operations.

Architecture:
- Relay operations get exclusive windows for switching
- Flow sensor gets exclusive windows for reading  
- No simultaneous I2C access
- Configurable timing for different device requirements

Based on I2C arbitration best practices for shared bus systems.
"""

import asyncio
import threading
import time
import logging
from typing import Optional, Callable, Any
from contextlib import asynccontextmanager

class I2CCoordinator:
    """
    Coordinates exclusive I2C access between relay HAT and flow sensor.
    
    Uses time-slicing approach:
    - Relay operations: 50ms exclusive windows
    - Flow sensor reads: 20ms exclusive windows  
    - Inter-device gaps: 10ms stabilization
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._active_device = None
        self._operation_start = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Device-specific timing (based on datasheets)
        self._device_timings = {
            'relay': {
                'max_duration': 0.05,  # 50ms max for relay switching
                'stabilization': 0.01, # 10ms post-operation delay
            },
            'flow_sensor': {
                'max_duration': 0.02,  # 20ms max for sensor read
                'stabilization': 0.01, # 10ms post-read delay
            }
        }
    
    @asynccontextmanager
    async def exclusive_access(self, device_type: str, operation_name: str = ""):
        """
        Context manager for exclusive I2C device access.
        
        Args:
            device_type: 'relay' or 'flow_sensor'
            operation_name: Description for logging
            
        Usage:
            async with coordinator.exclusive_access('relay', 'open_master'):
                # Safe relay operations
                relay_controller.open_master()
        """
        max_wait = 0.5  # 500ms max wait for bus access
        wait_start = time.time()
        
        # Wait for exclusive access
        while True:
            with self._lock:
                if self._active_device is None:
                    # Bus is free, claim it
                    self._active_device = device_type
                    self._operation_start = time.time()
                    break
                elif self._active_device == device_type:
                    # Same device, allow reentrant access
                    break
                else:
                    # Different device is active, check if it's exceeded its time
                    elapsed = time.time() - self._operation_start
                    max_duration = self._device_timings[self._active_device]['max_duration']
                    
                    if elapsed > max_duration:
                        # Force release stuck device
                        self.logger.warning(f"Force releasing stuck device {self._active_device} after {elapsed:.3f}s")
                        self._active_device = device_type
                        self._operation_start = time.time()
                        break
            
            # Check timeout
            if time.time() - wait_start > max_wait:
                raise TimeoutError(f"I2C bus access timeout for {device_type}")
            
            # Brief wait before retry
            await asyncio.sleep(0.001)  # 1ms
        
        try:
            self.logger.debug(f"I2C access granted to {device_type}: {operation_name}")
            yield
            
        finally:
            # Release access with stabilization delay
            with self._lock:
                if self._active_device == device_type:
                    # Add stabilization delay
                    stabilization = self._device_timings[device_type]['stabilization']
                    await asyncio.sleep(stabilization)
                    
                    self._active_device = None
                    self._operation_start = None
                    self.logger.debug(f"I2C access released by {device_type}")
    
    def sync_exclusive_access(self, device_type: str, operation_func: Callable, *args, **kwargs) -> Any:
        """
        Synchronous wrapper for exclusive I2C access.
        
        Args:
            device_type: 'relay' or 'flow_sensor'
            operation_func: Function to execute with exclusive access
            *args, **kwargs: Arguments for operation_func
            
        Returns:
            Result of operation_func
        """
        max_wait = 0.5
        wait_start = time.time()
        
        # Wait for exclusive access (synchronous)
        while True:
            with self._lock:
                if self._active_device is None:
                    self._active_device = device_type
                    self._operation_start = time.time()
                    break
                elif self._active_device == device_type:
                    break
                else:
                    elapsed = time.time() - self._operation_start
                    max_duration = self._device_timings[self._active_device]['max_duration']
                    
                    if elapsed > max_duration:
                        self.logger.warning(f"Force releasing stuck device {self._active_device}")
                        self._active_device = device_type
                        self._operation_start = time.time()
                        break
            
            if time.time() - wait_start > max_wait:
                raise TimeoutError(f"I2C bus access timeout for {device_type}")
            
            time.sleep(0.001)
        
        try:
            # Execute operation with exclusive access
            result = operation_func(*args, **kwargs)
            return result
            
        finally:
            # Release with stabilization delay
            with self._lock:
                if self._active_device == device_type:
                    stabilization = self._device_timings[device_type]['stabilization']
                    time.sleep(stabilization)
                    
                    self._active_device = None
                    self._operation_start = None

# Global coordinator instance
_coordinator = None

def get_i2c_coordinator() -> I2CCoordinator:
    """Get global I2C coordinator instance."""
    global _coordinator
    if _coordinator is None:
        _coordinator = I2CCoordinator()
    return _coordinator
