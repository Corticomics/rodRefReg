# models/animal.py

class Animal:
    def __init__(self, animal_id, lab_animal_id, name, initial_weight, last_weight, last_weighted, last_watering=None):
        self.animal_id = animal_id  # Database-generated ID
        self.lab_animal_id = lab_animal_id  # User-defined lab animal ID
        self.name = name
        self.initial_weight = initial_weight
        self.last_weight = last_weight
        self.last_weighted = last_weighted
        self.last_watering = last_watering

    def to_dict(self):
        return {
            'animal_id': self.animal_id,
            'lab_animal_id': self.lab_animal_id,
            'name': self.name,
            'initial_weight': self.initial_weight,
            'last_weight': self.last_weight,
            'last_weighted': self.last_weighted,
            'last_watering': self.last_watering
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