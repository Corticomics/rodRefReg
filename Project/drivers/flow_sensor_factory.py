#!/usr/bin/env python3
"""
Flow Sensor Factory for RRR
===========================

Creates the appropriate flow sensor driver based on configuration.

This module is the extension seam for flow sensors: a new sensor plugs in
as a new ``flow_sensor_type`` branch returning a driver that satisfies the
duck-typed sensor contract the delivery strategy uses (see
``strategies/solenoid_flow_strategy.py``). The legacy direct-I²C Sensirion
driver ('i2c') was retired in v1.9.0; 'uart' (Teensy bridge) is the only
shipped type. Do not resurrect the i2c path — a future sensor is different
hardware and gets its own driver + branch.

Configuration:
- flow_sensor_type: 'uart' (Teensy bridge)
- uart_port: Serial port for Teensy connection
"""

import logging


def create_flow_sensor(settings: dict) -> 'UARTFlowSensor':
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
    sensor_type = settings.get('flow_sensor_type', 'uart').lower()
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

    else:
        raise ValueError(f"Invalid flow sensor type: {sensor_type}. Must be 'uart'")


def get_available_sensor_types() -> list:
    """
    Get list of available sensor types based on installed drivers.

    Returns:
        List of available sensor type strings
    """
    available = []

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
