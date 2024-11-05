# shared/models/project.py

class Project:
    def __init__(self, project_id, name, animals=None, created_at=None):
        self.project_id = project_id
        self.name = name
        self.animals = animals if animals else []  # List of Animal instances
        self.created_at = created_at if created_at else time.time()

    def add_animal(self, animal, water_volume):
        """
        Add an animal to the project with the specified water volume.
        """
        self.animals.append({'animal': animal, 'water_volume': water_volume})

    def remove_animal(self, animal_id):
        """
        Remove an animal from the project by its ID.
        """
        self.animals = [a for a in self.animals if a['animal'].animal_id != animal_id]