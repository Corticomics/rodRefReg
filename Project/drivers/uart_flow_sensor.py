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
import os
import fcntl

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    serial = None


class TeensyUnavailableError(ConnectionError):
    """Raised when Teensy is not responding to communication attempts."""
    pass


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
        self._ping_interval = 10.0  # seconds (reduce chatter during delivery)
        self._pings_suspended = False
        self._reads_suspended = False
        self._recovering = False
        self._i2c_error_count = 0
        
        # Frame activity monitoring (detect firmware hangs)
        self._last_frame_time = 0
        self._frame_timeout_s = 10.0  # No frames for 10s = potential hang (increased for rapid pulse testing)
        
    def start(self) -> None:
        """Start sensor and begin continuous reading.
        
        Best Practices:
        - Fail-fast: Verify streaming is active before returning
        - Resource validation: Confirm reader thread is producing data
        - Clear error messages: Report specific failure modes
        
        Raises:
            TeensyUnavailableError: If sensor doesn't stream within timeout
            ConnectionError: If serial connection fails
        """
        try:
            self._logger.info(f"[UART] Starting flow sensor on {self.port} at {self.sampling_hz} Hz")
            
            self._connect()
            self._logger.info(f"[UART] Connection established to {self.port}")
            
            self._start_sensor()
            self._logger.info(f"[UART] Sensor start command sent")
            
            self._running = True
            
            # Start reader thread
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()
            self._logger.info(f"[UART] Reader thread started")
            
            # CRITICAL: Verify streaming is active (fail-fast principle)
            # Don't return success until we've confirmed measurements are arriving
            self._logger.info(f"[UART] Verifying stream health...")
            verification_timeout_s = 5.0
            min_frames_required = 5  # ~0.5s at 10 Hz, ~0.1s at 50 Hz
            
            if not self.wait_for_frames(min_frames=min_frames_required, timeout_s=verification_timeout_s):
                error_msg = (
                    f"Stream verification failed: No measurements received within {verification_timeout_s}s. "
                    f"Expected {min_frames_required} frames. "
                    f"Sample count: {self._sample_count}, Error count: {self._error_count}. "
                    f"Check: 1) I²C wiring (SDA/SCL/GND), 2) Pullup resistors (2kΩ), 3) Teensy firmware loaded."
                )
                self._logger.error(f"[UART] {error_msg}")
                self.stop()
                raise TeensyUnavailableError(error_msg)
            
            self._logger.info(f"[UART] Stream health verified ({self._sample_count} measurements received)")
            self._logger.info(f"[UART] Flow sensor fully initialized on {self.port} at {self.sampling_hz} Hz")
            
        except TeensyUnavailableError:
            # Re-raise sensor-specific errors without wrapping
            raise
        except Exception as e:
            self._logger.error(f"[UART] Failed to start flow sensor: {e}", exc_info=True)
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop sensor and close connection."""
        self._running = False
        
        if self._serial and self._serial.is_open:
            try:
                # Clear input buffer to ensure stop command is seen
                try:
                    self._serial.reset_input_buffer()
                except Exception:
                    pass
                
                self._send_command({"cmd": "stop"})
                
                # CRITICAL: Wait for firmware to process stop and turn off LED
                # At 20 Hz sampling, worst case is 50ms between loop iterations
                # Plus 10ms sensor settling time = 60ms minimum
                time.sleep(0.15)  # 150ms to ensure complete stop
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
        # Release inter-process lock
        self._release_lock()
    
    def _connect(self) -> None:
        """Establish serial connection to Teensy with robust retry logic.
        
        Based on Teensy CDC and PySerial best practices:
        - Teensy resets when serial port opens (USB re-enumeration)
        - Allow 2-3 seconds for firmware initialization
        - Retry ping commands with backoff
        - Auto-detect port changes if initial connection fails
        """
        max_retries = 3
        retry_delay = 0.5
        
        self._logger.info(f"[UART] Attempting connection to {self.port} (max {max_retries} retries)")
        
        for attempt in range(max_retries):
            try:
                # Close any existing connection
                if self._serial and self._serial.is_open:
                    self._serial.close()
                    time.sleep(0.5)
                
                self._logger.info(f"[UART] Connection attempt {attempt + 1}/{max_retries} on {self.port}")
                
                # Acquire cross-process lock to avoid multiple access on port
                self._logger.debug(f"[UART] Acquiring file lock for {self.port}")
                self._acquire_lock()
                self._logger.debug(f"[UART] Lock acquired")

                # Open serial connection
                self._logger.info(f"[UART] Opening serial port {self.port} at {self.baud_rate} baud")
                self._serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baud_rate,
                    timeout=self.timeout,
                    write_timeout=self.timeout
                )
                self._logger.info(f"[UART] Serial port opened successfully")
                
                # Teensy USB CDC reset delay (critical for stable communication)
                # Pi requires longer wait than Mac due to slower USB enumeration
                self._logger.debug(f"[UART] Waiting 3.5s for Teensy USB CDC enumeration...")
                time.sleep(3.5)  # Extended wait for Teensy firmware initialization
                self._logger.debug(f"[UART] CDC enumeration wait complete")
                
                # Test connection with multiple ping attempts
                self._logger.info(f"[UART] Testing connection with ping...")
                if self._test_connection_robust():
                    self._connected = True
                    self._logger.info(f"[UART] Connected to Teensy on {self.port}")
                    return
                else:
                    self._logger.warning(f"[UART] Ping test failed on {self.port}, attempt {attempt + 1}/{max_retries}")
                    
            except Exception as e:
                self._logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            
            # Wait before retry
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        # All attempts failed - try auto-detection as last resort
        self._logger.warning("Primary connection failed, attempting auto-detection...")
        if self._try_auto_detection():
            return
        
        # Connection completely failed
        raise TeensyUnavailableError(f"Teensy not responding on {self.port} after {max_retries} attempts")
    
    def _test_connection_robust(self) -> bool:
        """Test connection with multiple ping attempts and extended timeout."""
        max_ping_attempts = 5
        ping_timeout = 1.0
        
        for ping_attempt in range(max_ping_attempts):
            try:
                # Send ping command
                # Clear any existing buffered data to avoid stale frames interfering
                try:
                    if self._serial:
                        self._serial.reset_input_buffer()
                except Exception:
                    pass

                self._send_command({"cmd": "ping"})
                
                # Wait for pong response with timeout
                start_time = time.time()
                while time.time() - start_time < ping_timeout:
                    if self._serial.in_waiting:
                        line = self._serial.readline().decode('utf-8').strip()
                        if line:
                            try:
                                response = json.loads(line)
                                if response.get("type") == "pong":
                                    self._logger.debug(f"Ping successful on attempt {ping_attempt + 1}")
                                    return True
                            except json.JSONDecodeError:
                                continue
                    time.sleep(0.01)
                
                self._logger.debug(f"Ping attempt {ping_attempt + 1} timeout")
                time.sleep(0.2)  # Brief delay between ping attempts
                
            except Exception as e:
                self._logger.debug(f"Ping attempt {ping_attempt + 1} error: {e}")
                time.sleep(0.2)
        
        return False
    
    def _try_auto_detection(self) -> bool:
        """Attempt to auto-detect Teensy on different port as fallback."""
        try:
            # Import here to avoid circular imports
            from controllers.system_controller import SystemController
            
            # Create temporary instance for detection
            temp_controller = SystemController(None)
            detected_port = temp_controller.detect_teensy_port()
            
            if detected_port and detected_port != self.port:
                self._logger.info(f"Auto-detected Teensy on different port: {self.port} → {detected_port}")
                self.port = detected_port
                
                # Try connection on the new port
                return self._connect_to_port(detected_port)
            
        except Exception as e:
            self._logger.error(f"Auto-detection failed: {e}")
        
        return False

    def _acquire_lock(self) -> None:
        """Acquire exclusive lock file to prevent multiple processes accessing the port."""
        if hasattr(self, '_lock_fd') and self._lock_fd is not None:
            return
        try:
            lock_path = '/var/lock/teensy_flow.lock'
            os.makedirs('/var/lock', exist_ok=True)
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o664)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(fd, str.encode(self.port))
            self._lock_fd = fd
        except Exception as e:
            raise ConnectionError(f"Serial port in use by another process. Close other tools and retry. Details: {e}")

    def _release_lock(self) -> None:
        try:
            if hasattr(self, '_lock_fd') and self._lock_fd is not None:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
                self._lock_fd = None
        except Exception:
            pass
    
    def _connect_to_port(self, port: str) -> bool:
        """Connect to a specific port (helper for auto-detection)."""
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
                time.sleep(0.5)
            
            self._serial = serial.Serial(
                port=port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            time.sleep(3.5)  # Teensy initialization time (Pi needs longer than Mac)
            
            if self._test_connection_robust():
                self._connected = True
                self._logger.info(f"Connected to Teensy on auto-detected port {port}")
                return True
                
        except Exception as e:
            self._logger.debug(f"Failed to connect to auto-detected port {port}: {e}")
        
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
        
        try:
            command_str = json.dumps(command) + '\n'
            self._serial.write(command_str.encode('utf-8'))
            self._serial.flush()
        except Exception as e:
            if "Input/output error" in str(e) or "write failed" in str(e):
                raise ConnectionError(f"USB connection lost during command: {e}")
            else:
                raise
    
    def _reader_loop(self) -> None:
        """Background thread to read data from Teensy.
        
        Best Practices:
        - Defensive programming: Handle all exception types gracefully
        - Observability: Log key metrics (sample rate, queue depth, errors)
        - Resource management: Monitor frame timeouts for hang detection
        """
        self._last_frame_time = time.time()  # Initialize frame activity monitor
        last_stats_log = time.time()  # For periodic health logging
        stats_interval_s = 10.0  # Log stats every 10 seconds
        
        while self._running:
            try:
                if not self._serial or not self._serial.is_open:
                    time.sleep(0.1)
                    continue
                # Allow strategy to temporarily suspend reads during noisy valve switching
                if self._reads_suspended:
                    time.sleep(0.01)
                    continue
                
                # Check for frame activity timeout (detects firmware hangs)
                if not self._recovering and (time.time() - self._last_frame_time > self._frame_timeout_s):
                    self._logger.error(f"No frames received for {self._frame_timeout_s}s - firmware may be hung, attempting recovery...")
                    if self._attempt_reconnection():
                        self._logger.info("Frame stream restored after recovery")
                        self._last_frame_time = time.time()
                    else:
                        self._logger.error("Recovery failed, will retry")
                        time.sleep(1.0)
                    continue
                
                # Periodic health stats logging (observability best practice)
                now = time.time()
                if now - last_stats_log >= stats_interval_s:
                    queue_depth = self._data_queue.qsize()
                    time_since_last_frame = now - self._last_frame_time
                    avg_rate = self._sample_count / (now - last_stats_log + stats_interval_s) if self._sample_count > 0 else 0
                    self._logger.debug(
                        f"Stream health: samples={self._sample_count}, errors={self._error_count}, "
                        f"queue={queue_depth}/100, last_frame={time_since_last_frame:.1f}s ago, "
                        f"rate={avg_rate:.1f} Hz"
                    )
                    last_stats_log = now
                
                # Check for periodic ping
                if (not self._pings_suspended) and (time.time() - self._last_ping > self._ping_interval):
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
                
                # Attempt to recover connection on I/O errors
                if "Input/output error" in str(e) or "write failed" in str(e):
                    self._logger.warning("USB connection lost, attempting to reconnect...")
                    if self._attempt_reconnection():
                        self._logger.info("USB connection restored")
                        self._error_count = 0  # Reset error count on successful reconnection
                        self._last_frame_time = time.time()  # Reset activity monitor
                    else:
                        self._logger.error("USB reconnection failed")
                        time.sleep(1.0)  # Longer delay on connection failure
                else:
                    time.sleep(0.1)

    def suspend_reads(self, suspend: bool) -> None:
        """Suspend or resume reading frames from the serial port."""
        self._reads_suspended = suspend
        if suspend:
            self._logger.debug("Serial reads suspended.")
        else:
            self._logger.debug("Serial reads resumed.")
    
    def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect to Teensy after connection loss."""
        try:
            # Close existing connection
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except:
                    pass
            
            # Wait for device to settle
            time.sleep(2.0)
            
            # Try to reopen connection
            self._serial = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            time.sleep(3.5)  # Allow Teensy to initialize fully (Pi needs longer than Mac)
            
            # Test connection with ping
            test_successful = self._test_connection_robust()
            if test_successful:
                # Attempt a clean stop->start sequence to clear Teensy I2C state
                try:
                    self._send_command({"cmd": "stop"})
                    time.sleep(0.1)
                except Exception:
                    pass
                # Retry start up to 3 times with small backoff
                for attempt in range(3):
                    try:
                        self._start_sensor()
                        break
                    except Exception:
                        time.sleep(0.2 * (attempt + 1))
                return True
            else:
                # Close and attempt auto-detection on alternate port (e.g., ACM0 -> ACM1)
                try:
                    self._serial.close()
                except Exception:
                    pass

                # Attempt auto-detection fallback
                self._logger.info("Primary reconnection failed; attempting port auto-detection...")
                if self._try_auto_detection():
                    return True
                return False
                
        except Exception as e:
            self._logger.error(f"Reconnection attempt failed: {e}")
            # Try auto-detection immediately if open failed
            try:
                self._logger.info("Attempting port auto-detection after open failure…")
                if self._try_auto_detection():
                    return True
            except Exception:
                pass
            return False
    
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
                
                # Update frame activity timestamp (for hang detection)
                self._last_frame_time = time.time()
                
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
                
                # Handle partial/empty frames as benign idle/transient conditions
                if "received" in error_msg.lower() and "bytes" in error_msg.lower():
                    # This is normal when no flow is present (idle state)
                    self._logger.debug(f"Sensor transient frame: {error_msg}")
                else:
                    # Other errors are more significant
                    self._logger.warning(f"Teensy error: {error_msg}")
                    self._error_count += 1
                    # Attempt recovery on I2C NACK or start failure
                    eml = error_msg.lower()
                    if ("i2c error" in eml or "nack" in eml or "failed to start sensor" in eml):
                        try:
                            self._recover_i2c_error()
                        except Exception as _:
                            pass
                    elif "unknown command" in eml and "reset" in eml:
                        # Firmware lacks reset support – fallback to stop/start recovery
                        try:
                            self._recover_i2c_error()
                        except Exception:
                            pass
                
            elif msg_type == "status":
                self._logger.debug(f"Teensy status: {message.get('message', '')}")
                
        except json.JSONDecodeError as e:
            self._logger.warning(f"Invalid JSON from Teensy: {line}")
            self._error_count += 1
        except Exception as e:
            self._logger.error(f"Message processing error: {e}")
            self._error_count += 1
    
    def _recover_i2c_error(self) -> None:
        """Attempt to recover from I2C NACK/start failures per SLF3x best practices.
        Sequence: reset (0x0006) → 25ms → start (0x3608) → wait for frames.
        """
        if self._recovering:
            return
        self._recovering = True
        try:
            # Suspend pings during recovery
            self._pings_suspended = True
            # Try firmware-supported JSON reset; fall back to stop/start
            try:
                self._send_command({"cmd": "reset"})
                time.sleep(0.03)  # 25–30ms for reset complete
            except Exception:
                # Fallback: stop with small delay
                try:
                    self._send_command({"cmd": "stop"})
                except Exception:
                    pass
                time.sleep(0.2)
            # Start and wait for frames
            try:
                self._start_sensor()
            except Exception:
                pass
            self.wait_for_frames(min_frames=3, timeout_s=3.0)
        finally:
            self._pings_suspended = False
            self._recovering = False

    # Public reset hook for strategies/tests
    def reset(self) -> bool:
        try:
            self._recover_i2c_error()
            return True
        except Exception:
            return False

    def wait_for_frames(self, min_frames: int = 3, timeout_s: float = 5.0) -> bool:
        """Wait for at least min_frames new measurements within timeout_s.
        
        Best Practices:
        - Polling with timeout: Efficient busy-wait for async operations
        - Delta-based validation: Count new frames, not total frames
        """
        start_time = time.time()
        start_count = self._sample_count
        while time.time() - start_time < timeout_s:
            if (self._sample_count - start_count) >= min_frames:
                return True
            time.sleep(0.01)
        return (self._sample_count - start_count) >= min_frames
    
    def clear_queue(self) -> int:
        """Clear all pending measurements from the data queue.
        
        Best Practices:
        - Idempotent operations: Start each delivery from clean state
        - Resource cleanup: Prevent stale data from affecting new deliveries
        
        Returns:
            Number of measurements cleared
        """
        cleared_count = 0
        try:
            while not self._data_queue.empty():
                self._data_queue.get_nowait()
                cleared_count += 1
        except Empty:
            pass
        
        if cleared_count > 0:
            self._logger.debug(f"Cleared {cleared_count} stale measurements from queue")
        
        return cleared_count

    def ensure_streaming(self, min_frames: int = 3, timeout_s: float = 2.0) -> bool:
        """Ensure streaming is active; if not, attempt to start and wait for frames.
        
        Best Practices:
        - Idempotent: Safe to call multiple times without I²C conflicts
        - Defensive: Only restart if actually needed
        - Fail-fast: Return quickly if already streaming
        
        Critical Fix:
        - DO NOT send multiple "start" commands to a running sensor
        - Sensirion SLF3x: Sending "start" while already running causes I²C NACK (error 2)
        - Test file works because it explicitly stops before restarting
        """
        # Fast path: If already running and receiving frames, just verify
        if self._running:
            if self.wait_for_frames(min_frames=min_frames, timeout_s=timeout_s):
                self._logger.debug("Sensor already streaming, verified frames")
                return True
            else:
                self._logger.warning("Sensor marked running but no frames received, attempting recovery")
        
        # Slow path: Start sensor if not running
        if not self._running:
            try:
                self.start()
                return self.wait_for_frames(min_frames=min_frames, timeout_s=timeout_s)
            except Exception as e:
                self._logger.error(f"Failed to start sensor: {e}")
                return False
        
        # Recovery path: Sensor running but not streaming (firmware hung)
        # Adopt test file pattern: explicit stop → wait → start
        self._logger.warning("Sensor running but not streaming, attempting restart recovery...")
        try:
            # Stop sensor cleanly
            self._send_command({"cmd": "stop"})
            time.sleep(0.5)  # Critical: wait for clean shutdown
            self._running = False
            
            # Fresh start
            self.start()
            time.sleep(0.5)  # Critical: wait for sensor warm-up (datasheet: 60ms typical)
            
            # Verify streaming
            if self.wait_for_frames(min_frames=min_frames, timeout_s=timeout_s):
                self._logger.info("Sensor restart recovery successful")
                return True
            else:
                self._logger.error("Sensor restart recovery failed - no frames after restart")
                return False
        except Exception as e:
            self._logger.error(f"Sensor restart recovery failed: {e}")
            return False
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
