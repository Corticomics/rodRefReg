# shared/models/animal.py

class Animal:
    def __init__(self, animal_id, species, body_weight, notes=""):
        self.animal_id = animal_id
        self.species = species
        self.body_weight = body_weight  # in grams
        self.notes = notes

    def calculate_min_water(self):
        """
        Calculate the minimum water volume based on body weight.
        Example: 0.05 mL per gram.
        """
        return 0.05 * self.body_weight

    def calculate_max_water(self):
        """
        Calculate the maximum water volume based on body weight.
        Example: 0.1 mL per gram.
        """
        return 0.1 * self.body_weight