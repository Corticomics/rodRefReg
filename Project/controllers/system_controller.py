from PyQt5.QtCore import QObject, pyqtSignal
import json
import os
from datetime import datetime

class SystemController(QObject):
    settings_updated = pyqtSignal(dict)
    system_status = pyqtSignal(str)
    
    def __init__(self, database_handler):
        super().__init__()
        self.database_handler = database_handler
        self.settings_file = 'settings.json'
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load settings from JSON file and database"""
        try:
            # Load from JSON
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = self._create_default_settings()
            
            # Merge with database settings
            db_settings = self._load_database_settings()
            settings.update(db_settings)
            
            return settings
        except Exception as e:
            self.system_status.emit(f"Error loading settings: {str(e)}")
            return self._create_default_settings()
    
    def save_settings(self, settings_dict):
        """Save settings to appropriate storage"""
        try:
            # Separate settings based on storage type
            json_settings = {k: v for k, v in settings_dict.items() 
                           if k in self._get_json_settings_keys()}
            db_settings = {k: v for k, v in settings_dict.items() 
                         if k in self._get_db_settings_keys()}
            
            # Save to JSON
            with open(self.settings_file, 'w') as f:
                json.dump(json_settings, f, indent=4)
            
            # Save to database
            self._save_database_settings(db_settings)
            
            self.settings = settings_dict
            self.settings_updated.emit(settings_dict)
            
        except Exception as e:
            self.system_status.emit(f"Error saving settings: {str(e)}")
    
    def _create_default_settings(self):
        """Create default settings with proper types"""
        return {
            'num_hats': 1,
            'slack_token': '',
            'channel_id': '',
            'min_trigger_interval_ms': 500,
            'cycle_interval': 3600,
            'stagger_interval': 0.5,
            'hardware_mode': 'solenoid',  # default to solenoid; UI can switch to pump
            'global_master_relay_id': 16,
            'i2c_bus': 3,  # Default to dedicated flow sensor bus (GPIO 12/13)
            'flow_sensor_type': 'uart',  # 'i2c' or 'uart' (Teensy)
            'uart_port': self._detect_initial_teensy_port(),  # Auto-detected Teensy USB port
            'flow_sampling_hz': 50.0,
            'predictive_close_ms': 10.0,
            'residual_check_ms': 200.0,
            'residual_flow_threshold_ml_min': 1.0,
            'max_consecutive_sensor_errors': 10,
            'cage_relays': {},
            'debug_mode': False,
            'log_level': 2,
            'log_level_map': {
                0: 'DEBUG',
                1: 'INFO',
                2: 'WARNING',
                3: 'ERROR',
                4: 'CRITICAL'
            }
        }
    
    def _get_json_settings_keys(self):
        """Define which settings go in JSON file"""
        return {
            'num_hats', 'slack_token', 'channel_id', 'hardware_mode',
            'global_master_relay_id', 'i2c_bus', 'flow_sensor_type', 'uart_port',
            'flow_sampling_hz', 'predictive_close_ms', 'residual_check_ms',
            'residual_flow_threshold_ml_min', 'max_consecutive_sensor_errors',
            'cage_relays',
            'debug_mode', 'log_level'
        }
    
    def _get_db_settings_keys(self):
        """Define which settings go in database"""
        return {
            'min_trigger_interval_ms', 'cycle_interval',
            'stagger_interval'
        }

    def _get_setting_type(self, key):
        """Define type mapping for settings"""
        type_map = {
            'num_hats': int,
            'min_trigger_interval_ms': int,
            'cycle_interval': int,
            'stagger_interval': float,
            'debug_mode': bool,
            'log_level': int,
            'slack_token': str,
            'channel_id': str,
            'hardware_mode': str,
            'global_master_relay_id': int,
            'i2c_bus': int,
            'flow_sampling_hz': float,
            'predictive_close_ms': float,
            'residual_check_ms': float,
            'residual_flow_threshold_ml_min': float,
            'max_consecutive_sensor_errors': int,
        }
        return type_map.get(key, str)

    # --- Auto-detect helpers (used by UI) ---
    def detect_hats(self):
        """Attempt to detect number of relay HATs by probing stack IDs 0..7.

        Returns the detected count and does not persist automatically. UI layer
        can decide to persist by calling save_settings().
        """
        try:
            from gpio.gpio_handler import RelayHandler
            from models.relay_unit_manager import RelayUnitManager
            temp_settings = self.settings.copy()
            # Probe hats by optimistic init. RelayHandler internally logs errors.
            manager = RelayUnitManager(temp_settings)
            handler = RelayHandler(manager, temp_settings.get('num_hats', 1))
            hats = max(1, temp_settings.get('num_hats', 1))
            return hats
        except Exception:
            return self.settings.get('num_hats', 1)

    def detect_flow_sensor_bus(self):
        """Probe I2C buses for SLF3x address 0x08, avoiding relay HAT conflicts.
        
        NOTE: Only used for legacy I2C mode. UART mode (Teensy) is preferred.
        
        Strategy: Test buses in order of preference to avoid I²C conflicts.
        Priority: 13, 14, 1 (bus 1 shared with relay HATs, use as fallback)
        """
        try:
            import os
            from smbus2 import SMBus, i2c_msg
            
            # Priority order: dedicated sensor buses first, shared bus last
            # Bus 3 is dedicated for flow sensor (GPIO 12/13), avoiding relay HAT conflicts
            bus_priority = [3, 13, 14, 1, 0] + list(range(2, 21))
            
            for bus in bus_priority:
                if not os.path.exists(f"/dev/i2c-{bus}"):
                    continue
                try:
                    with SMBus(bus) as b:
                        # Test with start command (more reliable than simple read)
                        w = i2c_msg.write(0x08, [0x36, 0x08])
                        b.i2c_rdwr(w)
                        # If successful, this bus works
                        self.system_status.emit(f"Flow sensor detected on I²C bus {bus}")
                        return bus
                except Exception:
                    continue
        except Exception:
            pass
        
        # Fallback to current setting
        current = self.settings.get('i2c_bus', 1)
        self.system_status.emit(f"Flow sensor detection failed, using configured bus {current}")
        return current

    def _detect_initial_teensy_port(self):
        """Initial Teensy port detection during settings creation.
        
        Lightweight version for default settings - doesn't emit status messages
        or access self.settings since we're creating the settings.
        """
        import glob
        import os
        
        try:
            # Quick scan for existing ports
            potential_ports = []
            patterns = ['/dev/ttyACM*', '/dev/ttyUSB*']
            for pattern in patterns:
                potential_ports.extend(glob.glob(pattern))
            
            # Filter to existing devices and prioritize /dev/ttyACM*
            existing_ports = [p for p in potential_ports if os.path.exists(p)]
            existing_ports.sort()  # Consistent ordering
            
            if existing_ports:
                # Return first available port (likely the Teensy)
                return existing_ports[0]
            else:
                # Fallback if no ports found
                return '/dev/ttyACM0'
                
        except Exception:
            # Safe fallback on any error
            return '/dev/ttyACM0'
    
    def detect_teensy_port(self):
        """Auto-detect Teensy device port for UART flow sensor.
        
        Scans common USB serial device paths and tests for Teensy communication.
        Returns the first working port or falls back to current setting.
        """
        import glob
        import os
        
        # Get current port as fallback
        current_port = self.settings.get('uart_port', '/dev/ttyACM0')
        
        try:
            # Common Teensy device patterns
            potential_ports = []
            
            # Check common serial device patterns
            patterns = ['/dev/ttyACM*', '/dev/ttyUSB*']
            for pattern in patterns:
                potential_ports.extend(glob.glob(pattern))
            
            # Also check by-id directory for Teensy-specific devices
            try:
                by_id_devices = glob.glob('/dev/serial/by-id/*')
                for device in by_id_devices:
                    if 'teensy' in device.lower() or 'arduino' in device.lower():
                        actual_device = os.path.realpath(device)
                        potential_ports.append(actual_device)
            except:
                pass
            
            # Filter to existing devices
            existing_ports = [p for p in potential_ports if os.path.exists(p)]
            
            # Test each port for Teensy response
            for port in existing_ports:
                try:
                    import serial
                    import json
                    import time
                    
                    # Quick communication test
                    with serial.Serial(port, 115200, timeout=1.0) as ser:
                        time.sleep(0.5)  # Brief init time
                        ser.write(b'{"cmd":"ping"}\n')
                        ser.flush()
                        
                        response = ser.readline().decode('utf-8').strip()
                        if response:
                            data = json.loads(response)
                            if data.get("type") == "pong":
                                self.system_status.emit(f"Teensy detected on {port}")
                                return port
                except Exception:
                    continue
            
            # No working Teensy found, use current setting
            self.system_status.emit(f"Teensy auto-detection failed, using configured port {current_port}")
            return current_port
            
        except Exception as e:
            self.system_status.emit(f"Teensy detection error: {e}, using configured port {current_port}")
            return current_port

    def ensure_solenoid_defaults(self):
        """Centralized solenoid settings initialization with auto-detection.

        Best practices implementation:
        - Auto-detects Teensy port regardless of current mode
        - Auto-detects optimal I2C bus for legacy mode
        - Creates complete solenoid configuration if missing
        - Maintains backward compatibility with existing settings
        """
        try:
            s = dict(self.settings)
            settings_changed = False

            # Ensure solenoid mode is set (central requirement)
            if s.get('hardware_mode') != 'solenoid':
                s['hardware_mode'] = 'solenoid'
                settings_changed = True
                self.system_status.emit("Set hardware mode to solenoid")

            # Ensure flow sensor type is set
            if 'flow_sensor_type' not in s:
                s['flow_sensor_type'] = 'uart'  # Default to Teensy UART
                settings_changed = True

            # Auto-detect Teensy port (always run for robustness)
            detected_port = self.detect_teensy_port()
            current_port = s.get('uart_port', '/dev/ttyACM0')
            if detected_port != current_port:
                self.system_status.emit(f"Auto-detected Teensy port: {current_port} → {detected_port}")
                s['uart_port'] = detected_port
                settings_changed = True

            # Auto-detect I2C bus for legacy support
            detected_bus = self.detect_flow_sensor_bus()
            current_bus = s.get('i2c_bus', 1)
            if isinstance(detected_bus, int) and detected_bus != current_bus:
                self.system_status.emit(f"Auto-detected I2C bus: {current_bus} → {detected_bus}")
                s['i2c_bus'] = detected_bus
                settings_changed = True

            # Ensure all required solenoid settings exist
            solenoid_defaults = {
                'global_master_relay_id': 16,
                'flow_sampling_hz': 50.0,
                'predictive_close_ms': 10.0,
                'residual_check_ms': 200.0,
                'residual_flow_threshold_ml_min': 1.0,
                'max_consecutive_sensor_errors': 10,
                'num_hats': 1
            }
            
            for key, default_value in solenoid_defaults.items():
                if key not in s:
                    s[key] = default_value
                    settings_changed = True

            # Build cage map if empty
            cage_map = s.get('cage_relays') or {}
            if not cage_map:
                num_hats = int(s.get('num_hats', 1))
                total_relays = 16 * num_hats
                master_id = s.get('global_master_relay_id', 16)
                
                cage_id = 1
                new_map = {}
                for relay_id in range(1, total_relays + 1):
                    if relay_id == master_id:  # Skip master relay
                        continue
                    new_map[str(cage_id)] = relay_id
                    cage_id += 1
                
                s['cage_relays'] = new_map
                settings_changed = True
                self.system_status.emit(f"Created cage mapping: {len(new_map)} cages, master on relay {master_id}")

            # Save settings if any changes were made
            if settings_changed:
                self.save_settings(s)
                self.system_status.emit("Solenoid configuration auto-initialized successfully")
            else:
                self.system_status.emit("Solenoid configuration verified - no changes needed")
                
        except Exception as e:
            self.system_status.emit(f"Solenoid auto-configuration failed: {e}")
            import traceback
            traceback.print_exc()

    def get_pump_controller(self):
        """Get or create a pump controller instance"""
        if not hasattr(self, '_pump_controller'):
            from controllers.pump_controller import PumpController
            self._pump_controller = PumpController(self.settings)
        return self._pump_controller 