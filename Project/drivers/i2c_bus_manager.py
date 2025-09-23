#!/usr/bin/env python3
"""
I2C Bus Manager for RRR
========================

Provides thread-safe, device-aware I2C access management to prevent 
bus conflicts between flow sensor and relay HATs on shared buses.

Key Features:
- Thread-safe I2C access serialization
- Device-specific timeouts and retry logic
- Automatic conflict detection and recovery
- Production-grade error handling

Based on Linux I2C best practices and smbus2 documentation.
"""

import threading
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any
from smbus2 import SMBus, i2c_msg

class I2CBusManager:
    """Thread-safe I2C bus access manager."""
    
    def __init__(self):
        self._bus_locks: Dict[int, threading.RLock] = {}
        self._active_buses: Dict[int, SMBus] = {}
        self._lock = threading.RLock()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Device-specific timeouts (based on datasheets)
        self._device_timeouts = {
            0x08: 0.1,   # Flow sensor: 100ms max measurement time
            0x27: 0.05,  # Relay HAT: 50ms max response time
        }
    
    def _get_bus_lock(self, bus_id: int) -> threading.RLock:
        """Get or create bus-specific lock."""
        with self._lock:
            if bus_id not in self._bus_locks:
                self._bus_locks[bus_id] = threading.RLock()
            return self._bus_locks[bus_id]
    
    @contextmanager
    def get_bus(self, bus_id: int, device_addr: Optional[int] = None):
        """
        Context manager for thread-safe I2C bus access.
        
        Args:
            bus_id: I2C bus number
            device_addr: Device address (for timeout optimization)
            
        Usage:
            with bus_manager.get_bus(1, 0x08) as bus:
                # Safe I2C operations
                result = bus.read_byte_data(0x08, reg)
        """
        bus_lock = self._get_bus_lock(bus_id)
        bus = None
        
        # Device-specific timeout
        timeout = self._device_timeouts.get(device_addr, 0.1)
        
        try:
            # Acquire bus lock with timeout
            if not bus_lock.acquire(timeout=timeout * 10):  # 10x device timeout for lock
                raise TimeoutError(f"I2C bus {bus_id} lock timeout (device 0x{device_addr:02X})")
            
            try:
                # Create or reuse bus instance
                with self._lock:
                    if bus_id not in self._active_buses:
                        self._active_buses[bus_id] = SMBus(bus_id)
                    bus = self._active_buses[bus_id]
                
                # Brief inter-device delay for bus stabilization
                if device_addr:
                    time.sleep(0.001)  # 1ms stabilization
                
                yield bus
                
            except OSError as e:
                if e.errno == 121:  # Remote I/O error
                    self.logger.warning(f"I2C conflict detected on bus {bus_id}, device 0x{device_addr:02X}")
                    # Force bus reset
                    self._reset_bus(bus_id)
                raise
                
        finally:
            bus_lock.release()
    
    def _reset_bus(self, bus_id: int):
        """Reset bus connection after conflict."""
        try:
            with self._lock:
                if bus_id in self._active_buses:
                    self._active_buses[bus_id].close()
                    del self._active_buses[bus_id]
                    time.sleep(0.01)  # 10ms bus recovery time
        except Exception as e:
            self.logger.error(f"Bus reset failed for bus {bus_id}: {e}")
    
    def safe_write(self, bus_id: int, device_addr: int, data: bytes, retries: int = 3) -> bool:
        """
        Thread-safe I2C write with automatic retry.
        
        Args:
            bus_id: I2C bus number  
            device_addr: Device address
            data: Data to write
            retries: Number of retry attempts
            
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(retries + 1):
            try:
                with self.get_bus(bus_id, device_addr) as bus:
                    write_msg = i2c_msg.write(device_addr, data)
                    bus.i2c_rdwr(write_msg)
                    return True
                    
            except Exception as e:
                if attempt < retries:
                    wait_time = 0.01 * (2 ** attempt)  # Exponential backoff
                    self.logger.debug(f"I2C write retry {attempt + 1}/{retries} after {wait_time}s")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"I2C write failed after {retries} retries: {e}")
                    
        return False
    
    def safe_read(self, bus_id: int, device_addr: int, length: int, retries: int = 3) -> Optional[bytes]:
        """
        Thread-safe I2C read with automatic retry.
        
        Args:
            bus_id: I2C bus number
            device_addr: Device address  
            length: Number of bytes to read
            retries: Number of retry attempts
            
        Returns:
            Data bytes if successful, None if failed
        """
        for attempt in range(retries + 1):
            try:
                with self.get_bus(bus_id, device_addr) as bus:
                    read_msg = i2c_msg.read(device_addr, length)
                    bus.i2c_rdwr(read_msg)
                    return bytes(read_msg)
                    
            except Exception as e:
                if attempt < retries:
                    wait_time = 0.01 * (2 ** attempt)  # Exponential backoff
                    self.logger.debug(f"I2C read retry {attempt + 1}/{retries} after {wait_time}s")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"I2C read failed after {retries} retries: {e}")
                    
        return None
    
    def close(self):
        """Close all bus connections."""
        with self._lock:
            for bus in self._active_buses.values():
                try:
                    bus.close()
                except:
                    pass
            self._active_buses.clear()

# Global bus manager instance
_bus_manager = None

def get_bus_manager() -> I2CBusManager:
    """Get global I2C bus manager instance."""
    global _bus_manager
    if _bus_manager is None:
        _bus_manager = I2CBusManager()
    return _bus_manager
