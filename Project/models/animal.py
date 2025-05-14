class Animal:
    """
    Represents a laboratory animal in the Rodent Refreshment Regulator system.
    
    This class stores animal identification, physical characteristics,
    and watering history data. It also provides methods for calculating
    recommended water volumes and validating water delivery amounts.
    """
    
    def __init__(self, animal_id=None, lab_animal_id=None, name=None, initial_weight=None, 
                 last_weight=None, last_weighted=None, last_watering=None, sex=None):
        """
        Initialize an Animal instance.
        
        Args:
            animal_id (int, optional): Database ID for the animal.
            lab_animal_id (str, optional): Laboratory ID/identifier for the animal.
            name (str, optional): Name of the animal.
            initial_weight (float, optional): Initial weight in grams.
            last_weight (float, optional): Most recent weight in grams.
            last_weighted (str, optional): Date of last weighing (ISO format).
            last_watering (str, optional): Date of last watering (ISO format).
            sex (str, optional): Sex of the animal ('M' or 'F').
        """
        self.animal_id = animal_id
        self.lab_animal_id = lab_animal_id
        self.name = name
        self.initial_weight = initial_weight
        self.last_weight = last_weight
        self.last_weighted = last_weighted
        self.last_watering = last_watering
        self.sex = sex
        self.water_history = []
        self.recommended_volume = None

    def to_dict(self):
        return {
            'animal_id': self.animal_id,
            'lab_animal_id': self.lab_animal_id,
            'name': self.name,
            'initial_weight': self.initial_weight,
            'last_weight': self.last_weight,
            'last_weighted': self.last_weighted,
            'last_watering': self.last_watering,
            'sex': self.sex
        }

    @staticmethod
    def from_dict(data):
        return Animal(
            animal_id=data['animal_id'],
            lab_animal_id=data['lab_animal_id'],
            name=data['name'],
            initial_weight=data['initial_weight'],
            last_weight=data['last_weight'],
            last_weighted=data['last_weighted']
        )

    def calculate_recommended_water(self):
        """Calculate recommended water volume based on weight"""
        if not self.last_weight:
            return None
        
        # Standard calculation: 10% of body weight per day
        daily_volume = self.last_weight * 0.1
        # Adjust for multiple sessions if needed
        return round(daily_volume, 2)
    
    def validate_water_volume(self, desired_volume):
        """Validate desired water volume against recommendations"""
        if not self.recommended_volume:
            self.recommended_volume = self.calculate_recommended_water()
            
        # Allow ±20% deviation from recommended volume
        min_volume = self.recommended_volume * 0.8
        max_volume = self.recommended_volume * 1.2
        
        return min_volume <= desired_volume <= max_volume