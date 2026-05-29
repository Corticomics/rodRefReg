# models/cage.py
"""
Cage Model - Represents a physical cage connected to a relay.

Design Pattern: Value Object
- Encapsulates cage identity and user-defined naming
- Supports both solenoid mode (1:1 mapping) and legacy pump mode

Architecture:
- cage_id: Logical cage number (1-15 per HAT)
- relay_id: Physical relay number the cage is connected to
- name: User-friendly name for identification
- description: Optional notes about the cage/animal

Reference:
- Sequent Microsystems 16-relay HAT: R1-R16 terminals
- Solenoid mode: R16 reserved for master solenoid, R1-R15 for cages
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Cage:
    """
    Represents a physical cage with its relay mapping and user-defined name.

    Attributes:
        cage_id: Unique identifier for the cage (1-15 per HAT)
        relay_id: Physical relay ID this cage is connected to
        name: User-friendly name (default: "Cage N")
        description: Optional description or notes
        created_at: Timestamp when cage was first configured
        updated_at: Timestamp of last modification

    Example:
        cage = Cage(cage_id=1, relay_id=1, name="Mouse Lab A")
        print(cage.display_name)  # "Cage 1 - Mouse Lab A"
    """

    cage_id: int
    relay_id: int
    name: str = ""
    description: str = ""
    created_at: Optional[datetime] = field(default=None)
    updated_at: Optional[datetime] = field(default=None)

    def __post_init__(self):
        """Set default name if not provided."""
        if not self.name:
            self.name = f"Cage {self.cage_id}"

        # Initialize timestamps if not provided
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    @property
    def display_name(self) -> str:
        """
        Get display name for UI components (dropdowns, labels).

        Returns:
            "Cage N" if name is default, otherwise "Cage N - CustomName"
        """
        default_name = f"Cage {self.cage_id}"
        if self.name == default_name:
            return default_name
        return f"Cage {self.cage_id} - {self.name}"

    @property
    def has_custom_name(self) -> bool:
        """Check if cage has a user-defined custom name."""
        return self.name != f"Cage {self.cage_id}"

    def to_dict(self) -> dict:
        """
        Convert to dictionary for database storage/JSON serialization.

        Returns:
            dict with all cage attributes
        """
        return {
            'cage_id': self.cage_id,
            'relay_id': self.relay_id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at,
            'updated_at': self.updated_at.isoformat()
            if isinstance(self.updated_at, datetime)
            else self.updated_at,
            'display_name': self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Cage':
        """
        Create Cage instance from dictionary (database row or JSON).

        Args:
            data: Dict with cage_id, relay_id, name, etc.

        Returns:
            Cage instance
        """
        created_at = data.get('created_at')
        updated_at = data.get('updated_at')

        # Parse datetime strings if needed
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except (ValueError, TypeError):
                created_at = None

        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at)
            except (ValueError, TypeError):
                updated_at = None

        return cls(
            cage_id=data['cage_id'],
            relay_id=data['relay_id'],
            name=data.get('name', ''),
            description=data.get('description', ''),
            created_at=created_at,
            updated_at=updated_at,
        )

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"Cage({self.cage_id}, relay={self.relay_id}, name='{self.name}')"

    def __repr__(self) -> str:
        return self.__str__()
