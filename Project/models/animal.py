class Animal:
    def __init__(self, animal_id, name, initial_weight, last_weight, last_weighted):
        self.animal_id = animal_id
        self.name = name
        self.initial_weight = initial_weight
        self.last_weight = last_weight
        self.last_weighted = last_weighted

    def to_dict(self):
        return {
            'animal_id': self.animal_id,
            'name': self.name,
            'initial_weight': self.initial_weight,
            'last_weight': self.last_weight,
            'last_weighted': self.last_weighted
        }

    @staticmethod
    def from_dict(data):
        return Animal(
            animal_id=data['animal_id'],
            name=data['name'],
            initial_weight=data['initial_weight'],
            last_weight=data['last_weight'],
            last_weighted=data['last_weighted']
        )