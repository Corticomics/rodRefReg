import json
import os

from PyQt5.QtCore import QObject, pyqtSignal
from utils import paths


class SystemController(QObject):
    settings_updated = pyqtSignal(dict)
    system_status = pyqtSignal(str)

    # Settings this release no longer has. v2.1.0 removed the global Pulse
    # Width: every cage pulses at the width and rest stored with its
    # calibration. A value an older release saved is deleted from the
    # database when settings load, and never written back or kept in memory,
    # so it cannot reach a delivery. Reverting to 2.0.0 is safe: its
    # ensure_solenoid_defaults writes pulse_width_ms (20) back at its first
    # start, the value it forced at every start anyway.
    RETIRED_KEYS = ('pulse_width_ms',)

    # Settings that are no longer the operator's to change. Pulse delivery is
    # the only delivery mode for the production valves (v2.1.0 removed the
    # Enable Pulse Mode checkbox): forced when settings load, on every save
    # and by ensure_solenoid_defaults at every start, and never taken from a
    # backup (SettingsTab.restore_from_backup). A value an older release
    # saved therefore cannot switch a delivery to continuous mode, which
    # times the valve without its calibration. SolenoidFlowStrategy and
    # utils.calibration_gate read it.
    FIXED_SETTINGS = {'use_pulse_delivery': True}

    # The theme. v2.1.0 makes dark the default (ui/style/tokens.py's DEFAULT_THEME, which
    # test_dark_default.py keeps equal to this) and keeps the theme under a key of its own,
    # THEME_KEY. A device without that row is fresh, or has not run 2.1.0 yet: the load
    # stores the default there, which is the one-time switch to dark, and from then on the
    # operator's choice (Settings > General > Appearance) is kept there.
    # LEGACY_THEME_KEY is the row v1.5.0 to 2.0.0 keep their theme in. 2.1.0 never writes,
    # changes or deletes it, and never reads it as the theme, so a revert opens 2.0.0 in
    # the theme 2.0.0 saved: light on the lab's devices, its readable theme (2.0.0's dark
    # one shows every other table row near-white). 2.0.0's saves write only its own keys,
    # so the next update finds THEME_KEY as 2.1.0 left it. (Pre-release builds of 2.1.0
    # recorded the switch in a row of their own, ui_dark_default_applied. Nothing reads
    # such a row, and it is left as it is.)
    DEFAULT_THEME = 'dark'
    THEME_KEY = 'ui_theme'
    LEGACY_THEME_KEY = 'theme'

    def __init__(self, database_handler):
        super().__init__()
        self.database_handler = database_handler
        self.settings = self.load_settings()

    def load_settings(self):
        """Load settings from the DB and the dedicated secrets file.

        On the first run after the v1.5.0 upgrade, values in the legacy
        ``settings.json`` are copied into the DB. On the first run after
        the v1.5.1 upgrade, Slack credentials are extracted into a
        mode-0600 ``secrets.json`` (and removed from the DB). Defaults fill
        any keys still missing. See docs/UPDATE_SYSTEM.md §13.8. Retired
        settings are deleted from the DB and fixed ones forced, in the DB
        too (see RETIRED_KEYS and FIXED_SETTINGS), and the theme is switched
        to dark once (DEFAULT_THEME, THEME_KEY).
        """
        try:
            self._migrate_legacy_json_if_needed()
            self._ensure_secrets_migrated()
            self._settle_stored_settings()
            settings = self._create_default_settings()
            settings.update(self._load_database_settings())
            settings.update(self._load_secrets())
            return self._normalised(settings)
        except Exception as e:
            self.system_status.emit(f"Error loading settings: {str(e)}")
            return self._normalised(self._create_default_settings())

    def save_settings(self, settings_dict):
        """Persist managed settings: secrets to ``secrets.json``, the rest to
        the DB; merge everything into ``self.settings``.

        Unmanaged keys (runtime objects, ephemeral state) are kept in memory
        but not persisted — see :meth:`_get_persisted_keys`. A retired
        setting is neither saved nor kept, and a fixed one keeps its value
        (RETIRED_KEYS, FIXED_SETTINGS).
        """
        try:
            settings_dict = self._normalised(settings_dict, only_present=True)
            self._save_secrets_if_present(settings_dict)
            self._save_database_settings(settings_dict)
            self.settings.update(settings_dict)
            # The caller may have handed in self.settings itself, after
            # writing to it directly: make memory follow the same rules.
            for key in self.RETIRED_KEYS:
                self.settings.pop(key, None)
            self.settings.update(self.FIXED_SETTINGS)
            self.settings_updated.emit(self.settings)
        except Exception as e:
            self.system_status.emit(f"Error saving settings: {str(e)}")

    def _normalised(self, settings_dict, only_present=False):
        """A copy of ``settings_dict`` under this release's rules: without the
        retired settings, and with the fixed ones at their values.
        ``only_present`` leaves out a fixed setting the dict does not have,
        so a save of other keys writes only those."""
        cleaned = {
            key: value for key, value in settings_dict.items() if key not in self.RETIRED_KEYS
        }
        for key, value in self.FIXED_SETTINGS.items():
            if key in cleaned or not only_present:
                cleaned[key] = value
        return cleaned

    def _settle_stored_settings(self):
        """Bring what an older release saved under this release's rules:
        delete the retired settings, store a fixed one at its value where
        it was saved with another, so the DB says what RRR does, and make
        the one-time switch to the dark theme (_switch_to_dark_once). (The
        force-merge in ensure_solenoid_defaults compares with memory, which
        the load has already put right, so it would not write it.)

        Printed as well as emitted: nothing is connected to system_status
        while settings load, and the journal is where it can be looked up.
        """
        try:
            stored = self.database_handler.get_system_settings()
        except Exception:
            return
        if not isinstance(stored, dict):
            return
        messages = []
        for key in self.RETIRED_KEYS:
            if key not in stored:
                continue
            # The DatabaseHandler reports a database error by returning False.
            if self.database_handler.delete_system_setting(key):
                messages.append(f"Removed the retired setting {key}={stored[key]!r}")
            else:
                messages.append(
                    f"Could not remove the retired setting {key}={stored[key]!r}; "
                    "it is ignored, and the next start tries again"
                )
        for key, value in self.FIXED_SETTINGS.items():
            if key not in stored or stored[key] == value:
                continue
            try:
                written, why = self._write_setting_to_db(key, value), ""
            except Exception as exc:
                written, why = False, f" ({exc})"
            if written:
                messages.append(f"Stored the fixed setting {key}={value!r} (was {stored[key]!r})")
            else:
                messages.append(
                    f"Could not store the fixed setting {key}={value!r}{why}; the database "
                    f"still holds {stored[key]!r}, RRR uses {value!r}, and the next start "
                    "tries again"
                )
        messages.extend(self._switch_to_dark_once(stored))
        for message in messages:
            print(f"[SETTINGS] {message}", flush=True)
            self.system_status.emit(message)

    def _switch_to_dark_once(self, stored):
        """The one-time switch to dark, the default from 2.1.0: store it as the
        theme (THEME_KEY) on a device that has no theme there yet, a fresh
        install or one on its first start of 2.1.0. Nothing once that row
        exists: the operator's choice stays. Returns the journal lines: one
        when the theme the older release saved was not dark, or when the row
        cannot be stored.

        The older release's row (LEGACY_THEME_KEY) is read only to say what
        the theme was, and is left as it is, for a revert. When the database
        refuses the row, RRR starts dark all the same (a device without the
        row starts in the default), and the next start stores it.
        """
        if self.THEME_KEY in stored:
            return []
        try:
            written, why = self._write_setting_to_db(self.THEME_KEY, self.DEFAULT_THEME), ""
        except Exception as exc:
            written, why = False, f" ({exc})"
        if not written:
            return [
                f"Could not store {self.THEME_KEY}={self.DEFAULT_THEME!r}{why}; RRR starts "
                "in it all the same, and the next start tries again"
            ]
        before = stored.get(self.LEGACY_THEME_KEY)
        if before is None or before == self.DEFAULT_THEME:
            return []
        return [
            f"Switched the theme to {self.DEFAULT_THEME!r}, the default from 2.1.0, once "
            f"(it was {before!r}, which is kept for a revert to 2.0.0); Settings > General > "
            "Appearance switches it back, and that choice is kept"
        ]

    @classmethod
    def theme_at_start(cls, stored):
        """The theme these stored settings (system_settings rows) give once
        they load: the operator's choice under THEME_KEY, or the default where
        there is none yet, which the load stores (the one-time switch). Never
        the older release's row. main.py reads the rows and applies this
        before any window shows, the splash included.
        """
        return stored.get(cls.THEME_KEY, cls.DEFAULT_THEME)

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
            # Dose rounding policy: nearest whole pulse unless the operator
            # opts into rounding up. Deliberately NOT in the force-merged
            # pulse_mode_settings block (ensure_solenoid_defaults), which
            # would reset the choice on every start.
            'round_doses_up': False,
            # Valve topology: 'shared_manifold' (master valve + manifold, the
            # production rig) or 'independent' (one syringe and valve per
            # animal, no master). Read by utils.topology; like round_doses_up
            # it is kept out of the force-merged pulse block below.
            'valve_topology': 'shared_manifold',
            # The theme: dark from v2.1.0, under a key of its own (THEME_KEY). 2.0.0
            # had no theme default here; its main.py fell back to light.
            self.THEME_KEY: self.DEFAULT_THEME,
            'debug_mode': False,
            'log_level': 2,
            'log_level_map': {0: 'DEBUG', 1: 'INFO', 2: 'WARNING', 3: 'ERROR', 4: 'CRITICAL'},
        }

    def _get_persisted_keys(self):
        """Every setting persisted to the SQLite system_settings table.

        Anything else lives in self.settings in memory only — useful for
        runtime objects (e.g. relay_unit_manager) and ephemeral state.
        Single source of truth as of v1.5.0; replaces the prior split
        between ``_get_json_settings_keys`` and ``_get_db_settings_keys``.
        """
        return {
            # Note: slack_token + channel_id are NOT here — they live in the
            # dedicated mode-0600 secrets.json since Phase 2.5b.
            'num_hats',
            'hardware_mode',
            'global_master_relay_id',
            'i2c_bus',
            'flow_sensor_type',
            'uart_port',
            'flow_sampling_hz',
            'predictive_close_ms',
            'residual_check_ms',
            'residual_flow_threshold_ml_min',
            'max_consecutive_sensor_errors',
            'cage_relays',
            # Pulse-mode persistence (Parker Series 3). use_pulse_delivery is
            # fixed on (FIXED_SETTINGS); pulse_width_ms is retired (v2.1.0).
            'use_pulse_delivery',
            'pulse_settling_ms',
            'max_pulses_per_delivery',
            'max_pulse_delivery_time_s',
            # Dose rounding policy (v1.19.0): round every dose up to the
            # next whole pulse instead of to the nearest one.
            'round_doses_up',
            # Valve topology (v1.20.0): shared_manifold | independent.
            'valve_topology',
            'debug_mode',
            'log_level',
            # Scheduler tuning
            'min_trigger_interval_ms',
            'cycle_interval',
            'stagger_interval',
            # The theme, under a key of its own from v2.1.0. Not 'theme', which
            # v1.5.0 to 2.0.0 persist (pre-v1.5.0 silently dropped it): 2.1.0
            # leaves that row as an older release saved it, for a revert
            # (LEGACY_THEME_KEY).
            self.THEME_KEY,
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
            # Pulse-mode types
            'use_pulse_delivery': bool,
            'pulse_settling_ms': int,
            'max_pulses_per_delivery': int,
            'max_pulse_delivery_time_s': float,
            'round_doses_up': bool,
            'valve_topology': str,
            self.THEME_KEY: str,
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
            # The construction IS the probe (side effect); the instance is
            # intentionally unused, so we don't bind it.
            manager = RelayUnitManager(temp_settings)
            RelayHandler(manager, temp_settings.get('num_hats', 1))
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
            # Prefer persistent udev symlink if present
            if os.path.exists('/dev/teensy_flow'):
                return '/dev/teensy_flow'

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
            # Prefer persistent udev symlink if present
            if os.path.exists('/dev/teensy_flow'):
                self.system_status.emit("Teensy symlink detected at /dev/teensy_flow")
                return '/dev/teensy_flow'

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
                    import json
                    import time

                    import serial

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
            self.system_status.emit(
                f"Teensy auto-detection failed, using configured port {current_port}"
            )
            return current_port

        except Exception as e:
            self.system_status.emit(
                f"Teensy detection error: {e}, using configured port {current_port}"
            )
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
                self.system_status.emit(
                    f"Auto-detected Teensy port: {current_port} → {detected_port}"
                )
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
                'num_hats': 1,
            }

            # CRITICAL: Pulse mode settings (ALWAYS enforce these)
            # These are deployment-specific and must be present for Parker Series 3 valves.
            # No pulse width: each cage pulses at the width and rest it was
            # calibrated at (valve_calibration); the global one is retired.
            pulse_mode_settings = {
                # Pulse delivery is the only mode (FIXED_SETTINGS).
                'use_pulse_delivery': True,
                'pulse_settling_ms': 100,  # 100ms settling time after pulse
                'max_pulses_per_delivery': 100,  # Safety limit
                'max_pulse_delivery_time_s': 120.0,  # 2 minute timeout
            }

            # Add missing solenoid defaults
            for key, default_value in solenoid_defaults.items():
                if key not in s:
                    s[key] = default_value
                    settings_changed = True

            # FORCE-MERGE pulse mode settings (always update, not just when missing)
            # Reason: These are critical for Parker Series 3 valve operation
            for key, required_value in pulse_mode_settings.items():
                if s.get(key) != required_value:
                    s[key] = required_value
                    settings_changed = True
                    self.system_status.emit(f"Set pulse mode parameter: {key}={required_value}")

            # If pulse mode is enabled, align sampling rate with pulse integration best practice
            try:
                if s.get('use_pulse_delivery'):
                    current_rate = float(s.get('flow_sampling_hz', 50.0))
                    if current_rate > 20.0:
                        s['flow_sampling_hz'] = 20.0
                        settings_changed = True
                        self.system_status.emit(
                            "Adjusted flow_sampling_hz to 20.0 Hz for pulse mode"
                        )
            except Exception:
                pass

            from utils import topology as topo

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
                self.system_status.emit(
                    f"Created cage mapping: {len(new_map)} cages; relay {master_id} is "
                    f"{topo.reserved_relay_reason(s)}"
                )

            # Valve topology: a value nobody recognises would leave the app
            # unsure whether a master valve exists. Fall back to the shared
            # manifold (today's behaviour) and say so, rather than guess —
            # and announce the resolved topology on every boot, so a rig set
            # to 'independent' says so in its log before any water moves.

            # Printed as well as emitted: at boot nothing is connected to
            # system_status yet, and the journal is where an operator looks.
            def _announce(message):
                print(f"[TOPOLOGY] {message}", flush=True)
                self.system_status.emit(message)

            stored_topology = s.get('valve_topology')
            topology = topo.normalize(stored_topology)
            if stored_topology != topology:
                s['valve_topology'] = topology
                settings_changed = True
                if topo.is_known(stored_topology):
                    _announce(f"Normalised valve_topology {stored_topology!r} -> '{topology}'")
                else:
                    _announce(f"Unknown valve_topology {stored_topology!r}; using '{topology}'")
            _announce(f"Valve topology: {topology} ({topo.describe(topology)})")

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

    # Sentinel row marking that the v1.5.0 migration from settings.json
    # has already run on this device; presence skips the migration thereafter.
    _MIGRATION_SENTINEL_KEY = '_migrated_from_json_v1'

    def _load_database_settings(self):
        """Settings persisted in the SQLite system_settings table."""
        try:
            return self.database_handler.get_system_settings()
        except Exception as exc:
            self.system_status.emit(f"Could not read DB settings: {exc}")
            return {}

    def _save_database_settings(self, settings_dict):
        """Write each managed setting to the system_settings table."""
        managed = self._get_persisted_keys()
        for key, value in settings_dict.items():
            if key in managed:
                self._write_setting_to_db(key, value)

    def _write_setting_to_db(self, key, value):
        """Type-tag and persist a single setting via DatabaseHandler. Returns
        what it returns: False when the database refused the write."""
        if isinstance(value, bool):
            type_name = 'bool'
        elif isinstance(value, int):
            type_name = 'int'
        elif isinstance(value, float):
            type_name = 'float'
        elif isinstance(value, (list, dict)):
            type_name = 'json'
            value = json.dumps(value, default=str)
        else:
            type_name = 'str'
        return self.database_handler.update_system_setting(key, value, type_name)

    def _migrate_legacy_json_if_needed(self):
        """One-time copy of legacy settings.json into the system_settings table.

        Runs the first time SystemController starts on a device that was on a
        pre-v1.5.0 release; leaves a sentinel row so later launches skip it.
        The legacy file is left untouched (copy-not-move).
        """
        existing = {}
        try:
            existing = self.database_handler.get_system_settings()
        except Exception:
            pass
        if self._MIGRATION_SENTINEL_KEY in existing:
            return

        legacy = {}
        legacy_path = paths.settings_path()
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, 'r') as handle:
                    legacy = json.load(handle)
            except Exception as exc:
                self.system_status.emit(
                    f"Could not read legacy settings.json for migration: {exc}"
                )

        for key in self._get_persisted_keys():
            if key in legacy:
                try:
                    self._write_setting_to_db(key, legacy[key])
                except Exception as exc:
                    self.system_status.emit(f"Could not migrate setting {key}: {exc}")

        try:
            self.database_handler.update_system_setting(self._MIGRATION_SENTINEL_KEY, '1', 'str')
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Secrets (Phase 2.5b) — credentials live in a dedicated mode-0600
    # file, never in the DB and never in git. See docs/UPDATE_SYSTEM.md §13.8.
    # ------------------------------------------------------------------

    _SECRET_KEYS = ('slack_token', 'channel_id')

    def _load_secrets(self):
        """Return whatever is in the secrets file (empty dict when absent)."""
        from utils import secrets

        try:
            return secrets.get_credentials()
        except Exception as exc:
            self.system_status.emit(f"Could not read secrets file: {exc}")
            return {}

    def _save_secrets_if_present(self, settings_dict):
        """Persist Slack credentials to ``secrets.json`` when the caller
        touched any secret key.

        Merges into existing values so a partial save (e.g. token only) does
        not clobber an unrelated field.
        """
        if not any(key in settings_dict for key in self._SECRET_KEYS):
            return
        from utils import secrets

        merged = self._load_secrets()
        for key in self._SECRET_KEYS:
            if key in settings_dict:
                merged[key] = settings_dict[key]
        secrets.save_credentials(
            slack_token=merged.get('slack_token', ''),
            channel_id=merged.get('channel_id', ''),
        )

    def _ensure_secrets_migrated(self):
        """One-time: move legacy Slack credentials into ``secrets.json``.

        Sources, in priority order:
            (1) the dedicated file — if it already exists, sweep any
                stale DB rows and return;
            (2) the v1.5.0 ``system_settings`` rows (Phase 2.5a wrote
                slack creds there briefly);
            (3) the pre-v1.5.0 legacy ``settings.json``.
        After a copy, the DB rows are deleted. The legacy JSON is left
        intact (copy-not-move).
        """
        from utils import secrets

        db_rows = {}
        try:
            db_rows = self.database_handler.get_system_settings()
        except Exception:
            pass
        if not isinstance(db_rows, dict):
            db_rows = {}

        if secrets.exists():
            # Defensive: even if the secrets file is already present, sweep
            # leftover DB rows from a partial earlier run.
            for key in self._SECRET_KEYS:
                if key in db_rows:
                    try:
                        self.database_handler.delete_system_setting(key)
                    except Exception:
                        pass
            return

        token = db_rows.get('slack_token') or ''
        channel = db_rows.get('channel_id') or ''

        if not token and not channel:
            legacy_path = paths.settings_path()
            if os.path.exists(legacy_path):
                try:
                    with open(legacy_path, 'r') as handle:
                        legacy = json.load(handle)
                    token = legacy.get('slack_token') or ''
                    channel = legacy.get('channel_id') or ''
                except Exception:
                    pass

        secrets.save_credentials(slack_token=token, channel_id=channel)

        for key in self._SECRET_KEYS:
            if key in db_rows:
                try:
                    self.database_handler.delete_system_setting(key)
                except Exception:
                    pass

    def get_pump_controller(self):
        """Get or create a pump controller instance"""
        if not hasattr(self, '_pump_controller'):
            from controllers.pump_controller import PumpController

            self._pump_controller = PumpController(self.settings)
        return self._pump_controller
