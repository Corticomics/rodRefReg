# gpio_handler.py

import logging
import os
import time

from models.relay_unit import RelayUnit

# Prefer the vendor's standard module by default. Only use the custom module
# when explicitly enabled via environment (to avoid multi-bus side effects).
USE_CUSTOM_SM16 = os.getenv('RRR_USE_CUSTOM_SM16', '0') == '1'
# Import I2C coordination for hardware-level conflict prevention
try:
    from drivers.i2c_coordinator import get_i2c_coordinator

    I2C_COORDINATION_AVAILABLE = True
except ImportError:
    I2C_COORDINATION_AVAILABLE = False
    print("I2C coordination not available, relay operations may conflict with sensors")

if USE_CUSTOM_SM16:
    try:
        from .custom_SM16relind import SM16relind, find_available_i2c_buses

        USING_CUSTOM_MODULE = True
        print("Using custom SM16relind module with multi-bus support (RRR_USE_CUSTOM_SM16=1)")
    except ImportError:
        USING_CUSTOM_MODULE = False
        print("Custom SM16relind not available; falling back to standard module")

if not USE_CUSTOM_SM16 or not 'USING_CUSTOM_MODULE' in globals() or not USING_CUSTOM_MODULE:
    # Fall back to standard module
    try:
        import SM16relind

        USING_CUSTOM_MODULE = False
        print("Using standard SM16relind module")
    except ImportError:
        # Try alternate casing
        try:
            import sm_16relind as SM16relind

            USING_CUSTOM_MODULE = False
            print("Using standard sm_16relind module")
        except ImportError:
            print("WARNING: SM16relind module not found. Hardware control will not work.")

            # Create a mock module for testing
            class MockSM16relind:
                def __init__(self, stack=0, bus_id=None):
                    self.stack = stack
                    self.bus_id = bus_id
                    print(f"MOCK: Initialized MockSM16relind (stack={stack}, bus_id={bus_id})")

                def set(self, relay, state):
                    print(f"MOCK: Setting relay {relay} to state {state}")
                    return True

                def set_all(self, state):
                    print(f"MOCK: Setting all relays to state {state}")
                    return True

            SM16relind = MockSM16relind
            USING_CUSTOM_MODULE = False


def _say(*args, **kwargs) -> None:
    """Print a diagnostic line. Never raises: a broken stdout (the journal
    pipe gone) must not stop a relay write, above all the all-off of an
    emergency stop."""
    try:
        print(*args, **kwargs)
    except Exception:
        pass


class RelayHandler:
    def __init__(self, relay_unit_manager, num_hats=1):
        """Initialize RelayHandler with relay unit manager and hats"""
        self.num_hats = num_hats
        self.relay_hats = []

        # Initialize I2C coordinator for hardware-level conflict prevention
        if I2C_COORDINATION_AVAILABLE:
            self._coordinator = get_i2c_coordinator()
        else:
            self._coordinator = None

        # Initialize relay units dictionary from manager
        self.relay_units = {}
        if hasattr(relay_unit_manager, 'get_all_relay_units'):
            units = relay_unit_manager.get_all_relay_units()
            for unit in units:
                self.relay_units[unit.unit_id] = unit
        else:
            # Handle legacy input where relay_unit_manager is a list of units
            for unit in relay_unit_manager:
                if isinstance(unit, RelayUnit):
                    self.relay_units[unit.unit_id] = unit
                elif isinstance(unit, tuple):
                    unit_id = len(self.relay_units) + 1
                    self.relay_units[unit_id] = RelayUnit(unit_id=unit_id, relay_ids=unit)

        # Initialize relay hats
        self._initialize_hats()

    def _find_available_i2c_buses(self):
        """Find available I2C buses on the system"""
        if USING_CUSTOM_MODULE:
            # Use the implementation from custom module only if explicitly enabled
            try:
                return find_available_i2c_buses()
            except Exception:
                pass

        # Fallback implementation
        available_buses = []
        try:
            import os

            # Check the common I2C device paths
            for i in range(0, 20):  # Check a reasonable range of I2C devices
                if os.path.exists(f"/dev/i2c-{i}"):
                    available_buses.append(i)

            if available_buses:
                _say(f"Found I2C buses: {available_buses}")
            else:
                _say("No I2C buses found. Make sure I2C is enabled.")

            return available_buses
        except Exception as e:
            _say(f"Error finding I2C buses: {e}")
            return [0, 1]  # Default fallback

    def _initialize_hats(self):
        """Initialize relay hat hardware.

        Standard module (SM16relind):
          - Instantiate with stack index 0..num_hats-1 (per Sequent docs).
        Custom module (custom_SM16relind):
          - Supports bus_id; iterate detected I2C buses and stacks.

        ``relay_hats`` keeps one slot per configured stack, None where the
        HAT did not initialise. Relays are routed by stack (relay 17 is
        stack 1, relay 1), so a missing HAT must leave its slot empty: a
        compacted list would send stack 0's relays to stack 1, another
        animal's valve, and report the write as made.
        """
        self.relay_hats = [None] * self._expected_hats()

        success = False

        if USING_CUSTOM_MODULE:
            # When custom module is explicitly enabled, still prefer the default Pi bus (1)
            # to avoid unintended bus probing that can disrupt the flow sensor.
            preferred_buses = [1]
            for bus in preferred_buses:
                for stack in range(self.num_hats):
                    try:
                        hat = SM16relind(stack=stack, bus_id=bus)
                        hat.set_all(0)
                        self.relay_hats[stack] = hat
                        _say(f"Initialized relay hat stack={stack} on I2C bus {bus}")
                        success = True
                    except Exception as e:
                        _say(f"Failed to initialize custom hat stack={stack} bus={bus}: {e}")
            if not success:
                error_msg = "Failed to initialize relay hats via custom module on preferred buses."
                _say(error_msg)
                logging.error(error_msg)
            return

        # Standard module path: use stack indices only
        for stack in range(self.num_hats):
            try:
                ctor = getattr(SM16relind, 'SM16relind', None)
                if ctor is None:
                    raise AttributeError("SM16relind class not found in module")
                hat = ctor(stack)
                hat.set_all(0)
                self.relay_hats[stack] = hat
                _say(f"Initialized relay hat stack={stack}")
                success = True
            except Exception as e:
                _say(f"Failed to initialize hat stack={stack}: {e}")
                logging.error(f"Hat initialization error: {str(e)}")

        if not success:
            error_msg = (
                "Failed to initialize any relay hats. Check I2C configuration and connections."
            )
            _say(error_msg)
            logging.error(error_msg)

    def set_all_relays(self, state):
        """Set all relays to given state (0 or 1) with I2C coordination.

        Returns True only when every configured HAT took the command. A HAT
        that failed to initialise, or whose write raised, leaves its relays
        in an unknown state: the caller must say so (an emergency stop must
        not report "all closed") rather than assume they switched.
        """

        def _hardware_set_all_operation():
            hats = self._initialized_hats()
            ok = bool(hats) and len(hats) >= self._expected_hats()
            if not ok:
                message = (
                    f"Relay HAT(s) missing: {len(hats)} of {self.num_hats} "
                    "initialised; the missing ones were not switched"
                )
                _say(message)
                logging.error(message)
            for hat in hats:
                try:
                    hat.set_all(0 if state == 0 else 65535)  # 65535 = all relays ON
                except Exception as e:
                    _say(f"Error setting all relays: {e}")
                    logging.error(f"Relay state error: {str(e)}")
                    ok = False
            return ok

        return self._run_coordinated(_hardware_set_all_operation, "set_all")

    def _initialized_hats(self):
        """The HATs that answered at start-up, in stack order."""
        return [hat for hat in self.relay_hats if hat is not None]

    def _expected_hats(self):
        """How many HATs the device is configured for (at least one)."""
        try:
            return max(1, int(self.num_hats))
        except (TypeError, ValueError):
            return 1

    def _run_coordinated(self, operation, what):
        """Run a HAT write under the I2C coordinator when there is one.

        Returns the operation's own result: True when every write went
        through. If the coordinator itself fails, the write runs directly.
        """
        if self._coordinator:
            try:
                return bool(self._coordinator.sync_exclusive_access('relay', operation))
            except Exception as e:
                logging.error(f"I2C coordination failed for {what} operation: {e}")
        return bool(operation())

    def trigger_relays(self, selected_units, num_triggers, stagger):
        """Triggers the specified relay units with verification.

        A unit that did not complete every trigger is left out of the
        returned list; ``last_trigger_counts`` then says, per unit id, how
        many triggers fired before a relay did not switch.
        """
        relay_info = []
        self.last_trigger_counts = {}

        if not self._initialized_hats():
            logging.error("Trigger requested but no relay hats are initialized")
            return []

        for unit_id in selected_units:
            # Get relay unit from dictionary
            relay_unit = self.relay_units.get(unit_id)
            if not relay_unit:
                _say(
                    f"Relay unit {unit_id} not found in available units: {list(self.relay_units.keys())}"
                )
                continue

            # Get number of triggers for this specific unit
            unit_triggers = num_triggers.get(str(unit_id))
            if unit_triggers is None:
                _say(f"No trigger count specified for relay unit {unit_id}")
                continue

            success = self._execute_triggers(relay_unit, unit_triggers, stagger)
            self.last_trigger_counts[unit_id] = self._fired

            if success:
                relay_info.append(f"Relay Unit {unit_id} triggered {unit_triggers} times")

        return relay_info

    def _execute_triggers(self, relay_unit, num_triggers, stagger):
        """Execute the specified number of triggers for a relay unit.

        ``self._fired`` counts the triggers that switched on (their water
        was pumped), so a caller can credit them when a later one fails.
        """
        self._fired = 0
        try:
            for trigger in range(num_triggers):
                # Log trigger attempt
                _say(
                    f"Executing trigger {trigger + 1}/{num_triggers} "
                    f"for relay unit {relay_unit.unit_id}"
                )

                # Activate relays. A relay that did not switch fails the
                # unit: the trigger did not happen and must not be counted.
                switched_on = [self._set_relay_states([r], 1) for r in relay_unit.relay_ids]
                if not all(switched_on):
                    went_on = [r for r, ok in zip(relay_unit.relay_ids, switched_on) if ok]
                    self._switch_unit_off(relay_unit, trigger, went_on)
                    logging.error(
                        f"Relay unit {relay_unit.unit_id}: trigger {trigger + 1} did not "
                        "switch on; stopping"
                    )
                    return False
                self._fired += 1

                # Wait for activation duration
                time.sleep(stagger)

                # Deactivate relays
                if not self._switch_unit_off(relay_unit, trigger, relay_unit.relay_ids):
                    return False

                # Wait between triggers
                if trigger < num_triggers - 1:  # Don't wait after last trigger
                    time.sleep(stagger)

            return True

        except Exception as e:
            logging.error(f"Trigger execution error: {str(e)}")
            return False

    def _switch_unit_off(self, relay_unit, trigger, known_on):
        """Switch a unit's relays off, trying a lost write again at once.

        False, with a [VALVE CRITICAL] line, when a relay did not switch off.
        It always follows a switch-on attempt, and a write can take effect
        yet report a failure, so every such relay may still be running the
        pump: one known to be on, or one whose switch-on reported a failure
        (``known_on`` tells them apart, for the wording).
        """
        stuck = [
            relay_id
            for relay_id in relay_unit.relay_ids
            if not (self._set_relay_states([relay_id], 0) or self._set_relay_states([relay_id], 0))
        ]
        if not stuck:
            return True
        on = [r for r in stuck if r in known_on]
        unknown = [r for r in stuck if r not in known_on]
        parts = []
        if on:
            parts.append(
                f"relay(s) {', '.join(map(str, on))} did not switch off at trigger "
                f"{trigger + 1}; they may still be ON"
            )
        if unknown:
            parts.append(
                f"relay(s) {', '.join(map(str, unknown))} are not answering, so they cannot "
                "be confirmed off; they may be ON"
            )
        message = (
            f"[VALVE CRITICAL] relay unit {relay_unit.unit_id}: {'; '.join(parts)}. Check the "
            "rig; Settings > Priming > CLOSE ALL RELAYS retries every relay."
        )
        _say(message, flush=True)
        logging.error(message)
        return False

    def _set_relay_states(self, relay_ids, state):
        """Set the state of specified relay IDs with I2C coordination.

        Returns True only when every relay was written to its HAT. A relay
        whose HAT did not initialise, an id below 1 (divmod would wrap it
        onto the last HAT), and a vendor error each make it False, so a
        valve that never moved is not reported as having moved.
        """

        def _hardware_relay_operation():
            ok = True
            for relay_id in relay_ids:
                hat_index, relay_num = divmod(relay_id - 1, 16)
                hat = self.relay_hats[hat_index] if 0 <= hat_index < len(self.relay_hats) else None
                if hat is None:
                    message = (
                        f"Relay {relay_id} not switched: no initialised relay HAT for it "
                        f"({len(self._initialized_hats())} of {self.num_hats} initialised)"
                    )
                    _say(message)
                    logging.error(message)
                    ok = False
                    continue
                try:
                    hat.set(relay_num + 1, state)
                except Exception as e:
                    _say(f"Error setting relay {relay_id} to state {state}: {e}")
                    logging.error(f"Relay state change error: {str(e)}")
                    ok = False
            return ok

        return self._run_coordinated(_hardware_relay_operation, "relay")

    def set_relays(self, relay_ids, state):
        """Public method to set one or more relay channels ON (1) or OFF (0).

        This wraps the internal `_set_relay_states` and should be preferred by
        higher-level controllers (e.g., solenoid controller) instead of calling
        `_execute_triggers` when a sustained ON/OFF state is desired.

        Returns False when any of the relays did not switch (see
        ``_set_relay_states``).
        """
        try:
            return self._set_relay_states(relay_ids, 1 if state else 0)
        except Exception as e:
            logging.error(f"set_relays error: {str(e)}")
            return False

    def update_relay_units(self, relay_units, num_hats):
        """Updates the relay units and reinitializes the relay hats"""
        self.relay_units = {unit.unit_id: unit for unit in relay_units}
        self.num_hats = num_hats
        self._initialize_hats()

    def get_relay_unit(self, unit_id):
        """Get a relay unit by ID"""
        return self.relay_units.get(unit_id)

    def get_all_relay_units(self):
        """Get all relay units"""
        return list(self.relay_units.values())
