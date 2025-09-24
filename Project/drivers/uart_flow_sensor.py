#!/usr/bin/env python3
"""
UART Flow Sensor Driver for RRR
===============================

Communicates with Teensy 4.1 flow sensor reader via UART/Serial.
Provides the same interface as the I2C flow sensor driver for seamless integration.

Hardware Setup:
- Teensy 4.1 connected to Pi via USB 
- SLF3S-0600F sensor connected to Teensy I2C
- Teensy firmware: teensy_flow_reader.ino

Protocol:
Pi → Teensy: {"cmd":"start","rate":50}
Teensy → Pi: {"flow":123.4,"temp":25.1,"time":1234567890}
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple, AsyncIterator
import asyncio
from queue import Queue, Empty

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    serial = None


@dataclass
class FlowSample:
    flow_ml_min: float
    temperature_c: float


class UARTFlowSensor:
    """
    UART-based flow sensor driver for Teensy 4.1 integration.
    
    Provides same interface as I2C driver for seamless replacement.
    Handles serial communication, JSON protocol, and data buffering.
    """
    
    def __init__(
        self,
        port: str = '/dev/ttyACM0',
        sampling_hz: float = 50.0,
        zero_offset_ml_min: float = 0.0,
        span_scale: float = 1.0,
        baud_rate: int = 115200,
        timeout: float = 1.0
    ) -> None:
        if not SERIAL_AVAILABLE:
            raise ImportError("pyserial not available. Install with: pip install pyserial")
        
        self.port = port
        self.sampling_hz = sampling_hz
        self.zero_offset = zero_offset_ml_min
        self.span_scale = span_scale
        self.baud_rate = baud_rate
        self.timeout = timeout
        
        self._serial = None
        self._running = False
        self._reader_thread = None
        self._data_queue = Queue(maxsize=100)
        self._latest_sample = None
        self._sample_count = 0
        self._error_count = 0
        
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Connection management
        self._connected = False
        self._last_ping = 0
        self._ping_interval = 5.0  # seconds
        
    def start(self) -> None:
        """Start sensor and begin continuous reading."""
        try:
            self._connect()
            self._start_sensor()
            self._running = True
            
            # Start reader thread
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()
            
            self._logger.info(f"UART flow sensor started on {self.port} at {self.sampling_hz} Hz")
            
        except Exception as e:
            self._logger.error(f"Failed to start UART flow sensor: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop sensor and close connection."""
        self._running = False
        
        if self._serial and self._serial.is_open:
            try:
                self._send_command({"cmd": "stop"})
                time.sleep(0.1)  # Allow stop command to process
            except Exception:
                pass
        
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        
        self._connected = False
        self._logger.info("UART flow sensor stopped")
    
    def _connect(self) -> None:
        """Establish serial connection to Teensy."""
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # Wait for Teensy to initialize
            time.sleep(2.0)
            
            # Test connection with ping
            if self._test_connection():
                self._connected = True
                self._logger.info(f"Connected to Teensy on {self.port}")
            else:
                raise ConnectionError("Teensy ping test failed")
                
        except Exception as e:
            self._logger.error(f"Failed to connect to Teensy: {e}")
            raise
    
    def _test_connection(self) -> bool:
        """Test connection with ping command."""
        try:
            self._send_command({"cmd": "ping"})
            
            # Wait for pong response
            start_time = time.time()
            while time.time() - start_time < 2.0:
                if self._serial.in_waiting:
                    line = self._serial.readline().decode('utf-8').strip()
                    if line:
                        try:
                            response = json.loads(line)
                            if response.get("type") == "pong":
                                return True
                        except json.JSONDecodeError:
                            continue
                time.sleep(0.01)
            
            return False
            
        except Exception as e:
            self._logger.error(f"Connection test failed: {e}")
            return False
    
    def _start_sensor(self) -> None:
        """Send start command to Teensy."""
        command = {
            "cmd": "start",
            "rate": self.sampling_hz
        }
        self._send_command(command)
        
        # Wait for confirmation
        time.sleep(0.5)
    
    def _send_command(self, command: dict) -> None:
        """Send JSON command to Teensy."""
        if not self._serial or not self._serial.is_open:
            raise ConnectionError("Serial connection not open")
        
        command_str = json.dumps(command) + '\n'
        self._serial.write(command_str.encode('utf-8'))
        self._serial.flush()
    
    def _reader_loop(self) -> None:
        """Background thread to read data from Teensy."""
        while self._running:
            try:
                if not self._serial or not self._serial.is_open:
                    time.sleep(0.1)
                    continue
                
                # Check for periodic ping
                if time.time() - self._last_ping > self._ping_interval:
                    self._send_command({"cmd": "status"})
                    self._last_ping = time.time()
                
                # Read data
                if self._serial.in_waiting:
                    line = self._serial.readline().decode('utf-8').strip()
                    if line:
                        self._process_message(line)
                else:
                    time.sleep(0.001)  # Small delay to prevent CPU spinning
                    
            except Exception as e:
                self._logger.error(f"Reader loop error: {e}")
                self._error_count += 1
                time.sleep(0.1)
    
    def _process_message(self, line: str) -> None:
        """Process JSON message from Teensy."""
        try:
            message = json.loads(line)
            msg_type = message.get("type")
            
            if msg_type == "measurement":
                flow_raw = message.get("flow", 0.0)
                temp = message.get("temp", 0.0)
                
                # Apply calibration
                flow_calibrated = (flow_raw - self.zero_offset) * self.span_scale
                
                sample = FlowSample(flow_ml_min=flow_calibrated, temperature_c=temp)
                self._latest_sample = sample
                self._sample_count += 1
                
                # Add to queue (non-blocking)
                try:
                    self._data_queue.put_nowait(sample)
                except:
                    # Queue full, drop oldest
                    try:
                        self._data_queue.get_nowait()
                        self._data_queue.put_nowait(sample)
                    except:
                        pass
                        
            elif msg_type == "error":
                error_msg = message.get("error", "Unknown error")
                self._logger.warning(f"Teensy error: {error_msg}")
                self._error_count += 1
                
            elif msg_type == "status":
                self._logger.debug(f"Teensy status: {message.get('message', '')}")
                
        except json.JSONDecodeError as e:
            self._logger.warning(f"Invalid JSON from Teensy: {line}")
            self._error_count += 1
        except Exception as e:
            self._logger.error(f"Message processing error: {e}")
            self._error_count += 1
    
    def read_one(self) -> Optional[Tuple[float, float, int]]:
        """
        Read one sample from sensor.
        
        Returns:
            Tuple of (flow_ul_min, temp_c, flags) or None if no data
            
        Note: Returns μL/min to match I2C driver interface
        """
        if not self._running:
            return None
        
        try:
            # Try to get latest sample from queue
            sample = self._data_queue.get_nowait()
            
            # Convert mL/min to μL/min for interface compatibility
            flow_ul_min = sample.flow_ml_min * 1000.0
            temp_c = sample.temperature_c
            flags = 0  # No flags in UART protocol
            
            return (flow_ul_min, temp_c, flags)
            
        except Empty:
            # No new data available
            return None
        except Exception as e:
            self._logger.error(f"Error reading sample: {e}")
            return None
    
    async def read(self) -> AsyncIterator[FlowSample]:
        """
        Async generator for continuous flow readings.
        
        Yields:
            FlowSample objects with calibrated flow data
        """
        while self._running:
            sample = self.read_one()
            if sample:
                flow_ul_min, temp_c, _ = sample
                flow_ml_min = flow_ul_min / 1000.0
                yield FlowSample(flow_ml_min=flow_ml_min, temperature_c=temp_c)
            else:
                await asyncio.sleep(1.0 / self.sampling_hz)
    
    def zero_calibrate(self) -> None:
        """Reset zero offset to current flow reading."""
        if self._latest_sample:
            self.zero_offset = self._latest_sample.flow_ml_min
            self._logger.info(f"Zero calibrated to {self.zero_offset:.3f} mL/min")
    
    def set_zero_offset(self, offset_ml_min: float) -> None:
        """Set zero offset manually."""
        self.zero_offset = float(offset_ml_min)
    
    def set_span_scale(self, scale: float) -> None:
        """Set span scale factor."""
        self.span_scale = float(scale)
    
    def backend_mode(self) -> str:
        """Return backend identifier."""
        return "uart"
    
    def bus_id(self) -> str:
        """Return port identifier."""
        return self.port
    
    def close(self) -> None:
        """Close sensor connection."""
        self.stop()
    
    def get_status(self) -> dict:
        """Get sensor status information."""
        return {
            "connected": self._connected,
            "running": self._running,
            "port": self.port,
            "samples": self._sample_count,
            "errors": self._error_count,
            "latest_flow": self._latest_sample.flow_ml_min if self._latest_sample else None,
            "latest_temp": self._latest_sample.temperature_c if self._latest_sample else None
        }
