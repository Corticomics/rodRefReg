#!/usr/bin/env python3
"""
Flow Sensor Factory for RRR
===========================

Creates appropriate flow sensor driver based on configuration.
Supports both I2C (direct Pi connection) and UART (Teensy bridge) modes.

Configuration:
- flow_sensor_type: 'i2c' or 'uart'
- i2c_bus: I2C bus number for direct connection
- uart_port: Serial port for Teensy connection
"""

import logging
from typing import Union


def create_flow_sensor(settings: dict) -> Union['SLF3S0600FDriver', 'UARTFlowSensor']:
    """
    Create appropriate flow sensor driver based on settings.

    Args:
        settings: System settings dictionary

    Returns:
        Flow sensor driver instance

    Raises:
        ValueError: If sensor type is invalid or required settings missing
        ImportError: If required drivers not available
    """
    sensor_type = settings.get('flow_sensor_type', 'i2c').lower()
    sampling_hz = settings.get('flow_sampling_hz', 50.0)

    logger = logging.getLogger(__name__)

    if sensor_type == 'uart':
        # UART mode - use Teensy bridge
        try:
            from .uart_flow_sensor import UARTFlowSensor

            uart_port = settings.get('uart_port', '/dev/ttyACM0')

            logger.info(f"Creating UART flow sensor on {uart_port}")

            return UARTFlowSensor(
                port=uart_port, sampling_hz=sampling_hz, zero_offset_ml_min=0.0, span_scale=1.0
            )

        except ImportError as e:
            logger.error(f"UART flow sensor driver not available: {e}")
            raise

    elif sensor_type == 'i2c':
        # I2C mode - direct Pi connection
        try:
            from .flow_sensor import SLF3S0600FDriver

            i2c_bus = settings.get('i2c_bus', 1)

            logger.info(f"Creating I2C flow sensor on bus {i2c_bus}")

            return SLF3S0600FDriver(
                i2c_bus=i2c_bus, sampling_hz=sampling_hz, zero_offset_ml_min=0.0, span_scale=1.0
            )

        except ImportError as e:
            logger.error(f"I2C flow sensor driver not available: {e}")
            raise

    else:
        raise ValueError(f"Invalid flow sensor type: {sensor_type}. Must be 'i2c' or 'uart'")


def get_available_sensor_types() -> list:
    """
    Get list of available sensor types based on installed drivers.

    Returns:
        List of available sensor type strings
    """
    available = []

    try:
        from .flow_sensor import SLF3S0600FDriver  # noqa: F401  (import IS the availability probe)

        available.append('i2c')
    except ImportError:
        pass

    try:
        from .uart_flow_sensor import (
            UARTFlowSensor,  # noqa: F401  (import IS the availability probe)
        )

        available.append('uart')
    except ImportError:
        pass

    return available


def detect_teensy_port() -> str:
    """
    Auto-detect Teensy USB serial port.

    Returns:
        Device path for Teensy or default if not found
    """
    import glob

    import serial.tools.list_ports

    # Common Teensy USB device patterns
    teensy_patterns = [
        '/dev/ttyACM*',  # Linux USB CDC
        '/dev/ttyUSB*',  # Linux USB serial adapter
        '/dev/cu.usbmodem*',  # macOS
    ]

    # Try to find Teensy by VID/PID
    try:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # Teensy 4.1 USB VID:PID is 16C0:0483
            if port.vid == 0x16C0 and port.pid == 0x0483:
                return port.device
    except Exception:
        pass

    # Fallback to pattern matching
    for pattern in teensy_patterns:
        devices = glob.glob(pattern)
        if devices:
            return devices[0]

    # Default fallback
    return '/dev/ttyACM0'
