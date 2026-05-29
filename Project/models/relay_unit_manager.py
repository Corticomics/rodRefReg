from models.relay_unit import RelayUnit


class RelayUnitManager:
    """
    Manages relay unit configuration for both pump and solenoid modes.

    Design Patterns:
    - Factory Pattern: Creates appropriate relay units based on hardware mode
    - Strategy Pattern: Different initialization logic for pump vs solenoid

    Best Practices:
    - Mode-aware initialization (respects hardware_mode setting)
    - Scalable for multi-hat configurations
    - Maintains backward compatibility with pump mode
    """

    def __init__(self, settings):
        """
        Initialize relay unit manager with mode-aware configuration.

        Args:
            settings (dict): System settings containing:
                - hardware_mode: 'pump' or 'solenoid'
                - num_hats: Number of Sequent Microsystems relay HATs
                - global_master_relay_id: Master solenoid relay (solenoid mode only)
                - cage_relays: Dict mapping cage_id to relay_id (solenoid mode only)
                - relay_pairs: List of relay pairs (pump mode only)
        """
        self.settings = settings
        self.relay_units = {}
        self.hardware_mode = settings.get('hardware_mode', 'pump').lower()
        self.initialize_relay_units()

    def initialize_relay_units(self):
        """
        Initialize relay units based on hardware mode.

        Solenoid Mode (hardware_mode='solenoid'):
        - Each cage has ONE dedicated relay (e.g., cage 1 → relay 1)
        - Master solenoid on separate relay (usually relay 16)
        - Supports 1-15 cages per HAT (master excluded)

        Pump Mode (hardware_mode='pump'):
        - Each unit controls TWO relays (e.g., unit 1 → relays 1,2)
        - Supports 8 units per HAT (16 relays / 2)
        """
        if self.hardware_mode == 'solenoid':
            self._initialize_solenoid_mode()
        else:
            self._initialize_pump_mode()

    def _initialize_solenoid_mode(self):
        """
        Initialize relay units for solenoid mode.

        Architecture:
        - One relay per cage (1:1 mapping)
        - Master relay excluded from cage assignments
        - Unit ID matches cage ID for intuitive mapping

        Scalability:
        - Supports stacking multiple HATs (15 cages × num_hats)
        - Auto-generates cage_relays if not configured
        """
        num_hats = self.settings.get('num_hats', 1)
        master_id = self.settings.get('global_master_relay_id', 16)
        cage_relays = self.settings.get('cage_relays', {})

        # Auto-generate cage_relays if empty (best practice: explicit > implicit)
        if not cage_relays:
            print(
                f"[RelayUnitManager] No cage_relays configured, auto-generating for {num_hats} HAT(s)"
            )
            cage_relays = self._generate_default_cage_relays(num_hats, master_id)

        # Create one relay unit per cage
        for cage_id_str, relay_id in cage_relays.items():
            cage_id = int(cage_id_str)

            # Create single-relay unit (solenoid mode)
            relay_unit = RelayUnit(
                unit_id=cage_id,  # Unit ID = Cage ID for intuitive mapping
                relay_ids=relay_id,  # Single relay (will be normalized to tuple internally)
            )
            self.relay_units[cage_id] = relay_unit
            print(f"[Solenoid Mode] Initialized cage {cage_id} → relay {relay_id}")

        print(
            f"[RelayUnitManager] Solenoid mode initialized: {len(self.relay_units)} cages (master on relay {master_id})"
        )

    def _initialize_pump_mode(self):
        """
        Initialize relay units for pump mode (legacy).

        Architecture:
        - Two relays per unit (paired operation)
        - Standard configuration: 8 units per HAT

        Backward Compatibility:
        - Maintains existing relay_pairs logic
        - No breaking changes to pump-based schedules
        """
        relay_pairs = self.settings.get(
            'relay_pairs', [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12], [13, 14], [15, 16]]
        )

        for unit_id, relay_pair in enumerate(relay_pairs, start=1):
            # Convert list to tuple for relay_ids
            relay_ids = tuple(relay_pair)
            relay_unit = RelayUnit(unit_id=unit_id, relay_ids=relay_ids)
            self.relay_units[unit_id] = relay_unit
            print(f"[Pump Mode] Initialized relay unit {unit_id} with relays {relay_ids}")

        print(f"[RelayUnitManager] Pump mode initialized: {len(self.relay_units)} paired units")

    def _generate_default_cage_relays(self, num_hats: int, master_id: int) -> dict:
        """
        Generate default cage-to-relay mapping for solenoid mode.

        Args:
            num_hats (int): Number of relay HATs installed
            master_id (int): Relay ID reserved for master solenoid

        Returns:
            dict: Mapping of cage_id (str) to relay_id (int)

        Logic:
        - Sequential assignment: cage 1 → relay 1, cage 2 → relay 2, etc.
        - Skip master relay ID
        - Support multi-hat stacking (relays 1-16, 17-32, ...)
        """
        cage_relays = {}
        cage_id = 1

        for hat_index in range(num_hats):
            base_relay = hat_index * 16  # HAT 0: 1-16, HAT 1: 17-32, etc.

            for relay_offset in range(1, 17):  # Relays 1-16 per HAT
                relay_id = base_relay + relay_offset

                # Skip master relay
                if relay_id == master_id:
                    continue

                cage_relays[str(cage_id)] = relay_id
                cage_id += 1

        return cage_relays

    def get_relay_unit(self, unit_id):
        """
        Get relay unit by ID.

        Args:
            unit_id (int): Unit/cage ID

        Returns:
            RelayUnit: Relay unit object or None if not found
        """
        return self.relay_units.get(unit_id)

    def get_all_relay_units(self):
        """
        Get all relay units.

        Returns:
            list[RelayUnit]: List of all configured relay units
        """
        return list(self.relay_units.values())

    def get_hardware_mode(self):
        """Get current hardware mode ('pump' or 'solenoid')."""
        return self.hardware_mode
